import { create } from 'zustand'
import { sendersApi, type Sender } from '../api/client'
import toast from 'react-hot-toast'

interface SenderStore {
  senders: Sender[]
  loading: boolean
  error: string | null
  
  // Actions
  setSenders: (senders: Sender[]) => void
  updateSender: (id: number, updates: Partial<Sender>) => void
  addSender: (sender: Sender) => void
  removeSender: (id: number) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  
  // Optimistic actions
  optimisticToggleActive: (id: number) => Promise<void>
  
  // Data fetching
  fetchSenders: () => Promise<void>
}

export const useSenderStore = create<SenderStore>((set, get) => ({
  senders: [],
  loading: false,
  error: null,
  
  setSenders: (senders) => set({ senders }),
  
  updateSender: (id, updates) => set((state) => ({
    senders: state.senders.map((s) =>
      s.id === id ? { ...s, ...updates } : s
    ),
  })),
  
  addSender: (sender) => set((state) => ({
    senders: [...state.senders, sender],
  })),
  
  removeSender: (id) => set((state) => ({
    senders: state.senders.filter((s) => s.id !== id),
  })),
  
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  
  // Optimistic toggle active state
  optimisticToggleActive: async (id) => {
    const sender = get().senders.find((s) => s.id === id)
    if (!sender) return
    
    const newActive = !sender.is_active
    
    // Optimistic update
    set((state) => ({
      senders: state.senders.map((s) =>
        s.id === id ? { ...s, is_active: newActive } : s
      ),
    }))
    
    try {
      // Update via API
      const updated = await sendersApi.update(id, { is_active: newActive })
      // Background sync
      set((state) => ({
        senders: state.senders.map((s) =>
          s.id === id ? updated : s
        ),
      }))
    } catch (err) {
      // Rollback
      set((state) => ({
        senders: state.senders.map((s) =>
          s.id === id ? sender : s
        ),
      }))
      const errorMsg = err instanceof Error ? err.message : 'Failed to update sender'
      toast.error(errorMsg)
      throw err
    }
  },
  
  fetchSenders: async () => {
    set({ loading: true, error: null })
    try {
      const senders = await sendersApi.list()
      set({ senders, loading: false })
    } catch (err) {
      const error = err instanceof Error ? err.message : 'Failed to load senders'
      set({ error, loading: false })
    }
  },
}))
