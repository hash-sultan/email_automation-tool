import { create } from 'zustand'
import { campaignsApi, type Campaign } from '../api/client'
import toast from 'react-hot-toast'

interface CampaignStore {
  campaigns: Campaign[]
  loading: boolean
  error: string | null
  
  // Actions
  setCampaigns: (campaigns: Campaign[]) => void
  updateCampaign: (id: number, updates: Partial<Campaign>) => void
  addCampaign: (campaign: Campaign) => void
  removeCampaign: (id: number) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  
  // Optimistic actions
  optimisticPause: (id: number) => Promise<void>
  optimisticResume: (id: number) => Promise<void>
  optimisticStart: (id: number) => Promise<void>
  
  // Data fetching
  fetchCampaigns: () => Promise<void>
}

export const useCampaignStore = create<CampaignStore>((set, get) => ({
  campaigns: [],
  loading: false,
  error: null,
  
  setCampaigns: (campaigns) => set({ campaigns }),
  
  updateCampaign: (id, updates) => set((state) => ({
    campaigns: state.campaigns.map((c) =>
      c.id === id ? { ...c, ...updates } : c
    ),
  })),
  
  addCampaign: (campaign) => set((state) => ({
    campaigns: [...state.campaigns, campaign],
  })),
  
  removeCampaign: (id) => set((state) => ({
    campaigns: state.campaigns.filter((c) => c.id !== id),
  })),
  
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  
  // Optimistic pause - update UI immediately, sync in background
  optimisticPause: async (id) => {
    const campaign = get().campaigns.find((c) => c.id === id)
    if (!campaign) return
    
    // Optimistic update
    set((state) => ({
      campaigns: state.campaigns.map((c) =>
        c.id === id ? { ...c, status: 'paused' as const } : c
      ),
    }))
    
    try {
      await campaignsApi.pause(id)
      // Background sync - fetch updated campaign to ensure consistency
      const updated = await campaignsApi.get(id)
      set((state) => ({
        campaigns: state.campaigns.map((c) =>
          c.id === id ? updated : c
        ),
      }))
    } catch (err) {
      // Rollback on error
      set((state) => ({
        campaigns: state.campaigns.map((c) =>
          c.id === id ? campaign : c
        ),
      }))
      const errorMsg = err instanceof Error ? err.message : 'Failed to pause campaign'
      toast.error(errorMsg)
      throw err
    }
  },
  
  // Optimistic resume
  optimisticResume: async (id) => {
    const campaign = get().campaigns.find((c) => c.id === id)
    if (!campaign) return
    
    set((state) => ({
      campaigns: state.campaigns.map((c) =>
        c.id === id ? { ...c, status: 'active' as const } : c
      ),
    }))
    
    try {
      await campaignsApi.resume(id)
      const updated = await campaignsApi.get(id)
      set((state) => ({
        campaigns: state.campaigns.map((c) =>
          c.id === id ? updated : c
        ),
      }))
    } catch (err) {
      set((state) => ({
        campaigns: state.campaigns.map((c) =>
          c.id === id ? campaign : c
        ),
      }))
      const errorMsg = err instanceof Error ? err.message : 'Failed to resume campaign'
      toast.error(errorMsg)
      throw err
    }
  },
  
  // Optimistic start
  optimisticStart: async (id) => {
    const campaign = get().campaigns.find((c) => c.id === id)
    if (!campaign) return
    
    set((state) => ({
      campaigns: state.campaigns.map((c) =>
        c.id === id ? { ...c, status: 'active' as const } : c
      ),
    }))
    
    try {
      await campaignsApi.start(id)
      const updated = await campaignsApi.get(id)
      set((state) => ({
        campaigns: state.campaigns.map((c) =>
          c.id === id ? updated : c
        ),
      }))
    } catch (err) {
      set((state) => ({
        campaigns: state.campaigns.map((c) =>
          c.id === id ? campaign : c
        ),
      }))
      const errorMsg = err instanceof Error ? err.message : 'Failed to start campaign'
      toast.error(errorMsg)
      throw err
    }
  },
  
  fetchCampaigns: async () => {
    set({ loading: true, error: null })
    try {
      const campaigns = await campaignsApi.list()
      set({ campaigns, loading: false })
    } catch (err) {
      const error = err instanceof Error ? err.message : 'Failed to load campaigns'
      set({ error, loading: false })
    }
  },
}))
