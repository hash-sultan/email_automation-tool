import { create } from 'zustand'
import { templatesApi, type Template } from '../api/client'

interface TemplateStore {
  templates: Template[]
  loading: boolean
  error: string | null
  
  // Actions
  setTemplates: (templates: Template[]) => void
  updateTemplate: (id: number, updates: Partial<Template>) => void
  addTemplate: (template: Template) => void
  removeTemplate: (id: number) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  
  // Data fetching
  fetchTemplates: () => Promise<void>
}

export const useTemplateStore = create<TemplateStore>((set) => ({
  templates: [],
  loading: false,
  error: null,
  
  setTemplates: (templates) => set({ templates }),
  
  updateTemplate: (id, updates) => set((state) => ({
    templates: state.templates.map((t) =>
      t.id === id ? { ...t, ...updates } : t
    ),
  })),
  
  addTemplate: (template) => set((state) => ({
    templates: [...state.templates, template],
  })),
  
  removeTemplate: (id) => set((state) => ({
    templates: state.templates.filter((t) => t.id !== id),
  })),
  
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  
  fetchTemplates: async () => {
    set({ loading: true, error: null })
    try {
      const templates = await templatesApi.list()
      set({ templates, loading: false })
    } catch (err) {
      const error = err instanceof Error ? err.message : 'Failed to load templates'
      set({ error, loading: false })
    }
  },
}))
