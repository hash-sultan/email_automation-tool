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
  base_daily_limit: number;
  current_daily_limit: number;
  hourly_limit: number;
  emails_sent_today: number;
  emails_sent_this_hour: number;
  total_emails_sent: number;
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
  warmup_enabled?: boolean;
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
  category: string;
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
  status: 'new' | 'queued' | 'contacted' | 'replied' | 'bounced' | 'unsubscribed' | 'converted';
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
  template_category?: string;
  sender?: Sender;
  template?: Template;
  total_leads: number;
  emails_sent: number;
  followups_sent: number;
  emails_today: number;
  // Number of unique leads that have received at least one email
  leads_contacted?: number;
  replies_count: number;
  bounces_count: number;
  unsubscribes_count: number;
  followup_enabled: boolean;
  followup_delay_days: number;
  max_followups: number;
  daily_limit: number;
  hourly_limit: number;
  send_weekdays_only: boolean;
  send_window_start: string;
  send_window_end: string;
  created_at: string;
  started_at?: string;
  // Sender rotation
  sender_rotation_enabled: boolean;
  sender_ids?: number[];
  max_senders?: number | null;
}

export interface DashboardStats {
  total_leads: number;
  active_campaigns: number;
  total_senders: number;
  emails_sent_today: number;
  followups_sent_today: number;
  replies_today: number;
  bounces_today: number;
  total_emails_sent: number;
  total_followups_sent: number;
  total_replies: number;
  overall_reply_rate: number;
  overall_bounce_rate: number;
  emails_by_day: Array<{ date: string; sent: number; replies: number; bounces: number }>;
  recent_replies: Array<{
    lead_id: number;
    email: string;
    name: string | null;
    replied_at: string | null;
    sender_id: number;
    sender_email: string;
    sender_name: string;
    subject: string;
    campaign_id: number | null;
  }>;
  top_campaigns: Array<{ id: number; name: string; sent: number; replies: number; reply_rate: number }>;
  sender_health: Array<{ id: number; email: string; bounce_rate: number; daily_usage: number }>;
}

export interface Reply {
  id: number;
  lead_id: number;
  lead_email: string;
  lead_name: string | null;
  sender_id: number;
  sender_email: string;
  sender_name: string;
  campaign_id: number | null;
  campaign_name: string | null;
  subject: string;
  original_message_id: string | null;
  replied_at: string | null;
  created_at: string;
  body_text?: string | null;
  body_preview?: string | null;
}

export interface SendReplyRequest {
  email_log_id: number;
  body_html: string;
  body_text?: string;
  subject?: string;
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
  getStats: (days: number = 7) => apiFetch<DashboardStats>(`/analytics/dashboard?days=${days}`),
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
  getStatsByDate: (id: number, days: number = 30) => apiFetch<{ sender_id: number; days: number; stats_by_date: Record<string, number> }>(`/senders/${id}/stats-by-date?days=${days}`),
  skipWarmup: (id: number) => apiFetch<{ status: string; sender_id: number }>(`/senders/${id}/skip-warmup`, {
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
  deleteCategory: (categoryName: string) => apiFetch<{ status: string; category: string; templates_deleted: number }>(`/templates/category/${encodeURIComponent(categoryName)}`, {
    method: 'DELETE',
  }),
};

// Follow-up Template types
export interface FollowUpTemplate {
  id: number;
  campaign_id: number;
  step: number;
  delay_days: number;
  delay_hours: number;
  subject: string;
  body_html: string;
  body_plain?: string;
  reply_to_thread: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface FollowUpTemplateCreate {
  campaign_id: number;
  step: number;
  delay_days: number;
  delay_hours: number;
  subject: string;
  body_html: string;
  body_plain?: string;
  reply_to_thread: boolean;
  is_active: boolean;
}

export interface FollowUpTemplateUpdate {
  delay_days?: number;
  delay_hours?: number;
  subject?: string;
  body_html?: string;
  body_plain?: string;
  reply_to_thread?: boolean;
  is_active?: boolean;
}

// Settings API
export const settingsApi = {
  getSettings: () => apiFetch<{
    campaign_daily_limit: number;
    sender_daily_limit: number;
    reply_check_interval_minutes: number;
    reply_look_back_hours: number;
  }>('/settings'),
  
  updateSettings: (settings: {
    campaign_daily_limit: number;
    sender_daily_limit: number;
    reply_check_interval_minutes: number;
    reply_look_back_hours: number;
  }) => apiFetch<{ status: string; message: string }>('/settings', {
    method: 'PUT',
    body: JSON.stringify(settings),
  }),
  
  resetAllData: () => apiFetch<{
    status: string;
    message: string;
    deleted: {
      campaigns: number;
      email_logs: number;
      leads: number;
      campaign_senders: number;
      followup_templates: number;
    };
    preserved: {
      senders: string;
      templates: string;
    };
  }>('/settings/reset-all-data', {
    method: 'POST',
  }),
};

// Follow-up Templates API
export const followupTemplatesApi = {
  list: (campaignId: number) => apiFetch<FollowUpTemplate[]>(`/templates/followups/${campaignId}`),
  create: (data: FollowUpTemplateCreate) => apiFetch<FollowUpTemplate>('/templates/followups', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  update: (id: number, data: FollowUpTemplateUpdate) => apiFetch<FollowUpTemplate>(`/templates/followups/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),
  delete: (id: number) => apiFetch<void>(`/templates/followups/${id}`, {
    method: 'DELETE',
  }),
};

// Leads API
export const leadsApi = {
  list: (campaignId?: number, page: number = 1, pageSize: number = 100) => {
    const params = new URLSearchParams();
    if (campaignId) params.append('campaign_id', campaignId.toString());
    params.append('page', page.toString());
    params.append('page_size', pageSize.toString()); // Backend enforces max 100
    return apiFetch<PaginatedList<Lead>>(`/leads?${params.toString()}`);
  },
  stats: (campaignId?: number) => {
    const params = campaignId ? `?campaign_id=${campaignId}` : '';
    return apiFetch<{
      total: number;
      new: number;
      queued: number;
      contacted: number;
      replied: number;
      bounced: number;
      unsubscribed: number;
      converted: number;
    }>(`/leads/stats${params}`);
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
  deleteByCampaign: (campaignId: number) =>
    apiFetch<{ status: string; campaign_id: number; deleted: number }>(
      `/leads/by-campaign/${campaignId}`,
      { method: 'DELETE' }
    ),
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
  triggerFollowups: (id: number) => apiFetch<{ status: string; campaign_id: number; task_id: string; message: string }>(`/campaigns/${id}/trigger-followups`, {
    method: 'POST',
  }),
};

// Analytics API
export const analyticsApi = {
  dashboard: () => apiFetch<DashboardStats>('/analytics/dashboard'),
  campaign: (id: number) => apiFetch<any>(`/analytics/campaigns/${id}`),
  sender: (id: number) => apiFetch<any>(`/analytics/senders/${id}`),
};

// Replies API
export const repliesApi = {
  list: (page: number = 1, pageSize: number = 20, senderId?: number, campaignId?: number) => {
    const params = new URLSearchParams();
    params.append('page', page.toString());
    params.append('page_size', pageSize.toString());
    if (senderId) params.append('sender_id', senderId.toString());
    if (campaignId) params.append('campaign_id', campaignId.toString());
    return apiFetch<PaginatedList<Reply>>(`/replies?${params.toString()}`);
  },
  send: (data: SendReplyRequest) => apiFetch<{ status: string; message_id: string; to: string }>('/replies/send', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
};
