/**
 * XenFlow Mailer - API Client
 * Handles all communication with the backend API
 */

// Use explicit backend URL to avoid port/proxy issues
const API_BASE_URL = 'http://localhost:8000/api/v1';

// Types
export interface Sender {
  id: number;
  email: string;
  name: string;
  provider: 'smtp' | 'gmail' | 'outlook';
  is_active: boolean;
  is_verified: boolean;
  daily_limit: number;
  hourly_limit: number;
  emails_sent_today: number;
  emails_sent_this_hour: number;
  warmup_enabled: boolean;
  warmup_day: number;
  created_at: string;
  smtp_host?: string;
  smtp_port?: number;
  smtp_username?: string;
  use_tls?: boolean;
  imap_host?: string;
  imap_port?: number;
}

export interface SMTPConfig {
  host: string;
  port: number;
  username: string;
  password: string;
  use_tls?: boolean;
}

export interface IMAPConfig {
  host: string;
  port: number;
  username: string;
  password: string;
  use_ssl?: boolean;
  folder?: string;
}

export interface SenderCreate {
  email: string;
  name: string;
  provider_type?: 'gmail' | 'outlook' | 'custom_smtp';
  base_daily_limit?: number;
  smtp_config?: SMTPConfig;
  imap_config?: IMAPConfig;
}

export interface Template {
  id: number;
  name: string;
  subject: string;
  body_html: string;
  body_text: string;
  is_active: boolean;
  template_type: 'initial' | 'followup';
  followup_step?: number;
  created_at: string;
  updated_at: string;
}

export interface Lead {
  id: number;
  email: string;
  name?: string;
  first_name?: string;
  last_name?: string;
  company?: string;
  industry?: string;
  title?: string;
  phone?: string;
  timezone?: string;
  status: 'new' | 'contacted' | 'replied' | 'bounced' | 'unsubscribed' | 'converted';
  campaign_id?: number;
  source?: string;
  custom_fields?: Record<string, string>;
  created_at: string;
}

export interface Campaign {
  id: number;
  name: string;
  description?: string;
  status: 'draft' | 'active' | 'paused' | 'completed' | 'cancelled';
  sender_id: number;
  template_id: number;
  sender?: Sender;
  template?: Template;
  total_leads: number;
  emails_sent: number;
  emails_opened: number;
  emails_replied: number;
  emails_bounced: number;
  followup_enabled: boolean;
  followup_delay_days: number;
  max_followups: number;
  created_at: string;
  started_at?: string;
}

export interface DashboardStats {
  total_leads: number;
  active_campaigns: number;
  total_senders: number;
  emails_sent_today: number;
  replies_today: number;
  bounces_today: number;
  total_emails_sent: number;
  total_replies: number;
  overall_reply_rate: number;
  overall_bounce_rate: number;
  emails_by_day: Array<{ date: string; sent: number; replies: number; bounces: number }>;
  top_campaigns: Array<{ id: number; name: string; sent: number; replies: number; reply_rate: number }>;
  sender_health: Array<{ id: number; email: string; bounce_rate: number; daily_usage: number }>;
}

export interface ApiError {
  detail: string | Array<{ loc: (string | number)[]; msg: string; type: string }>;
}

// Paginated list responses
interface PaginatedList<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// Generic fetch wrapper
async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const defaultHeaders: HeadersInit = {
    'Content-Type': 'application/json',
  };

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error: ApiError = await response.json().catch(() => ({ detail: 'Unknown error' }));
    
    // Handle FastAPI validation errors (array format)
    if (Array.isArray(error.detail)) {
      const messages = error.detail.map((e: any) => {
        const field = e.loc?.slice(1).join('.') || 'field';
        return `${field}: ${e.msg}`;
      });
      throw new Error(messages.join('; ') || `Validation error: HTTP ${response.status}`);
    }
    
    throw new Error(typeof error.detail === 'string' ? error.detail : `HTTP ${response.status}`);
  }

  return response.json();
}

// Dashboard API
export const dashboardApi = {
  getStats: () => apiFetch<DashboardStats>('/analytics/dashboard'),
};

// Senders API
export const sendersApi = {
  list: () => apiFetch<Sender[]>('/senders'),
  get: (id: number) => apiFetch<Sender>(`/senders/${id}`),
  create: (data: SenderCreate) => apiFetch<Sender>('/senders/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  update: (id: number, data: Partial<Sender>) => apiFetch<Sender>(`/senders/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),
  delete: (id: number) => apiFetch<void>(`/senders/${id}`, {
    method: 'DELETE',
  }),
  verify: (id: number) => apiFetch<{ status: string; sender_id: number; smtp_verified: boolean; error?: string }>(`/senders/${id}/verify`, {
    method: 'POST',
  }),
};

// Templates API
export const templatesApi = {
  list: () => apiFetch<Template[]>('/templates'),
  get: (id: number) => apiFetch<Template>(`/templates/${id}`),
  create: (data: Partial<Template>) => apiFetch<Template>('/templates/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  update: (id: number, data: Partial<Template>) => apiFetch<Template>(`/templates/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),
  delete: (id: number) => apiFetch<void>(`/templates/${id}`, {
    method: 'DELETE',
  }),
};

// Leads API
export const leadsApi = {
  list: (campaignId?: number) => {
    const params = campaignId ? `?campaign_id=${campaignId}` : '';
    return apiFetch<PaginatedList<Lead>>(`/leads${params}`).then(res => res.items);
  },
  get: (id: number) => apiFetch<Lead>(`/leads/${id}`),
  create: (data: Partial<Lead>) => apiFetch<Lead>('/leads/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  update: (id: number, data: Partial<Lead>) => apiFetch<Lead>(`/leads/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),
  delete: (id: number) => apiFetch<void>(`/leads/${id}`, {
    method: 'DELETE',
  }),
  import: async (file: File, campaignId?: number) => {
    const formData = new FormData();
    formData.append('file', file);
    if (campaignId) {
      formData.append('campaign_id', campaignId.toString());
    }
    
    const response = await fetch(`${API_BASE_URL}/leads/import`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Import failed' }));
      throw new Error(error.detail);
    }
    
    return response.json();
  },
};

// Campaigns API
export const campaignsApi = {
  list: () => apiFetch<PaginatedList<Campaign>>('/campaigns').then(res => res.items),
  get: (id: number) => apiFetch<Campaign>(`/campaigns/${id}`),
  create: (data: Partial<Campaign>) => apiFetch<Campaign>('/campaigns/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  update: (id: number, data: Partial<Campaign>) => apiFetch<Campaign>(`/campaigns/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),
  delete: (id: number) => apiFetch<void>(`/campaigns/${id}`, {
    method: 'DELETE',
  }),
  start: (id: number) => apiFetch<Campaign>(`/campaigns/${id}/start`, {
    method: 'POST',
  }),
  pause: (id: number) => apiFetch<Campaign>(`/campaigns/${id}/pause`, {
    method: 'POST',
  }),
  resume: (id: number) => apiFetch<Campaign>(`/campaigns/${id}/resume`, {
    method: 'POST',
  }),
};

// Analytics API
export const analyticsApi = {
  dashboard: () => apiFetch<DashboardStats>('/analytics/dashboard'),
  campaign: (id: number) => apiFetch<any>(`/analytics/campaigns/${id}`),
  sender: (id: number) => apiFetch<any>(`/analytics/senders/${id}`),
};

