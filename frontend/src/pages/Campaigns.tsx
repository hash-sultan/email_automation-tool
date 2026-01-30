import { useEffect, useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Send,
  Plus,
  RefreshCw,
  AlertTriangle,
  X,
  Play,
  Pause,
  Mail,
  MessageSquare,
  CheckCircle,
  AlertCircle,
} from 'lucide-react'
import Button from '../components/Button'
import CampaignCard from '../components/CampaignCard'
import { SkeletonCard } from '../components/SkeletonLoader'
import { campaignsApi, type Campaign } from '../api/client'
import { useCampaignStore } from '../stores/campaignStore'
import { useSenderStore } from '../stores/senderStore'
import { useTemplateStore } from '../stores/templateStore'
import toast from 'react-hot-toast'

interface CampaignFormData {
  name: string
  description: string
  sender_id: number | null
  sender_rotation_enabled: boolean
  sender_ids: number[]
  max_senders?: number | null
  template_category: string
  followup_enabled: boolean
  followup_delay_days: number
  max_followups: number
  send_weekdays_only: boolean
  send_window_start: string
  send_window_end: string
}

const defaultFormData: CampaignFormData = {
  name: '',
  description: '',
  sender_id: null,
  sender_rotation_enabled: false,
  sender_ids: [],
  max_senders: undefined,
  template_category: '',
  followup_enabled: true,
  followup_delay_days: 3,
  max_followups: 1,
  send_weekdays_only: false,  // Allow weekends
  send_window_start: '00:00',  // 24/7 sending
  send_window_end: '23:59',  // 24/7 sending
}


export default function Campaigns() {
  // Zustand stores
  const { 
    campaigns, 
    loading: campaignsLoading, 
    error: campaignsError,
    fetchCampaigns,
    optimisticPause,
    optimisticResume,
    optimisticStart,
    addCampaign,
    removeCampaign,
  } = useCampaignStore()
  
  const { 
    senders, 
    loading: sendersLoading,
    fetchSenders 
  } = useSenderStore()
  
  const { 
    templates, 
    loading: templatesLoading,
    fetchTemplates 
  } = useTemplateStore()
  
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [editingCampaign, setEditingCampaign] = useState<Campaign | null>(null)
  const [formData, setFormData] = useState<CampaignFormData>(defaultFormData)
  const [submitting, setSubmitting] = useState(false)
  const [actionLoading, setActionLoading] = useState<number | null>(null)

  // Derive available template categories from templates
  const templateCategories = useMemo(
    () => Array.from(new Set(templates.map(t => t.category))).sort(),
    [templates]
  )
  
  const loading = campaignsLoading || sendersLoading || templatesLoading
  const displayError = campaignsError || error

  const fetchData = async (showLoading = true) => {
    if (showLoading) {
      useCampaignStore.getState().setLoading(true)
      useSenderStore.getState().setLoading(true)
      useTemplateStore.getState().setLoading(true)
    }
    setError(null)
    try {
      await Promise.all([
        fetchCampaigns(),
        fetchSenders(),
        fetchTemplates(),
      ])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      if (showLoading) {
        useCampaignStore.getState().setLoading(false)
        useSenderStore.getState().setLoading(false)
        useTemplateStore.getState().setLoading(false)
      }
    }
  }

  useEffect(() => {
    fetchData()
    
    // Auto-refresh campaign data every 30 seconds to show updated reply counts
    // Don't show loading spinner for auto-refresh to avoid UI flicker
    const interval = setInterval(() => {
      fetchCampaigns() // Only refresh campaigns for updated stats
    }, 30000) // Refresh every 30 seconds
    
    return () => clearInterval(interval)
  }, [])

  const openEditModal = (campaign: Campaign) => {
    setEditingCampaign(campaign)
    setFormData({
      name: campaign.name,
      description: campaign.description || '',
      sender_id: campaign.sender_rotation_enabled ? null : campaign.sender_id,
      sender_rotation_enabled: campaign.sender_rotation_enabled,
      sender_ids: campaign.sender_ids || [],
      max_senders: campaign.max_senders || undefined,
      template_category: campaign.template_category || '',
      followup_enabled: campaign.followup_enabled,
      followup_delay_days: campaign.followup_delay_days,
      max_followups: campaign.max_followups,
      send_weekdays_only: campaign.send_weekdays_only,
      send_window_start: campaign.send_window_start,
      send_window_end: campaign.send_window_end,
    })
    setShowModal(true)
    setError(null)
  }

  const openAddModal = () => {
    setEditingCampaign(null)
    setFormData(defaultFormData)
    setShowModal(true)
    setError(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.template_category) {
      setError('Please select a template category')
      return
    }
    if (!formData.sender_rotation_enabled && !formData.sender_id) {
      setError('Please select a sender')
      return
    }
    if (formData.sender_rotation_enabled && formData.sender_ids.length === 0) {
      setError('Please select at least one sender for rotation')
      return
    }

    setSubmitting(true)
    setError(null)

    try {
      if (editingCampaign) {
        // Update existing campaign
        const primarySenderId = formData.sender_rotation_enabled
          ? formData.sender_ids[0]
          : formData.sender_id!

        await campaignsApi.update(editingCampaign.id, {
          name: formData.name,
          description: formData.description,
          sender_id: primarySenderId,
          sender_rotation_enabled: formData.sender_rotation_enabled,
          sender_ids: formData.sender_rotation_enabled ? formData.sender_ids : undefined,
          max_senders: formData.sender_rotation_enabled ? formData.max_senders : undefined,
          template_category: formData.template_category,
          followup_enabled: formData.followup_enabled,
          followup_delay_days: formData.followup_delay_days,
          max_followup_steps: formData.max_followups,
          send_weekdays_only: formData.send_weekdays_only,
          send_window_start: formData.send_window_start,
          send_window_end: formData.send_window_end,
        } as any)
        
        setShowModal(false)
        setFormData(defaultFormData)
        setEditingCampaign(null)
        await fetchData(false) // Refresh campaigns
        toast.success('Campaign updated successfully!')
      } else {
        // Create new campaign
        const primarySenderId = formData.sender_rotation_enabled
          ? formData.sender_ids[0]
          : formData.sender_id!

        const result = await campaignsApi.create({
          name: formData.name,
          description: formData.description,
          sender_id: primarySenderId,
          sender_rotation_enabled: formData.sender_rotation_enabled,
          sender_ids: formData.sender_rotation_enabled ? formData.sender_ids : undefined,
          max_senders: formData.sender_rotation_enabled ? formData.max_senders : undefined,
          template_category: formData.template_category,
          followup_enabled: formData.followup_enabled,
          followup_delay_days: formData.followup_delay_days,
          max_followup_steps: formData.max_followups,
          send_weekdays_only: formData.send_weekdays_only,
          send_window_start: formData.send_window_start,
          send_window_end: formData.send_window_end,
        } as any)
        setShowModal(false)
        setFormData(defaultFormData)
        addCampaign(result)
        toast.success('Campaign created successfully!')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${editingCampaign ? 'update' : 'create'} campaign`)
    } finally {
      setSubmitting(false)
    }
  }

  const handleStart = async (id: number) => {
    setActionLoading(id)
    try {
      await optimisticStart(id)
      toast.success('Campaign started!')
    } catch (err) {
      // Error already handled in store
    } finally {
      setActionLoading(null)
    }
  }

  const handlePause = async (id: number) => {
    setActionLoading(id)
    try {
      await optimisticPause(id)
      toast.success('Campaign paused')
    } catch (err) {
      // Error already handled in store
    } finally {
      setActionLoading(null)
    }
  }

  const handleResume = async (id: number) => {
    setActionLoading(id)
    try {
      await optimisticResume(id)
      toast.success('Campaign resumed!')
    } catch (err) {
      // Error already handled in store
    } finally {
      setActionLoading(null)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this campaign?')) return

    try {
      await campaignsApi.delete(id)
      removeCampaign(id)
      toast.success('Campaign deleted')
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to delete campaign'
      setError(errorMsg)
      toast.error(errorMsg)
    }
  }

  const handleTriggerFollowups = async (campaignId: number) => {
    setActionLoading(campaignId)
    try {
      const result = await campaignsApi.triggerFollowups(campaignId)
      toast.success(result.message || `Follow-ups triggered for campaign`)
      // Refresh campaigns to update follow-ups count
      await fetchData(false)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to trigger follow-ups'
      setError(errorMsg)
      toast.error(errorMsg)
    } finally {
      setActionLoading(null)
    }
  }

  // Stats
  const stats = {
    total: campaigns.length,
    active: campaigns.filter(c => c.status === 'active').length,
    paused: campaigns.filter(c => c.status === 'paused').length,
    totalSent: campaigns.reduce((sum, c) => sum + c.emails_sent, 0),
    totalReplies: campaigns.reduce((sum, c) => sum + c.replies_count, 0),
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <motion.h1
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-3xl font-semibold text-gray-900"
          >
            Campaigns
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-gray-500 mt-1"
          >
            Create and manage your email campaigns
          </motion.p>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="ghost" onClick={() => fetchData()} disabled={loading}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          <Button onClick={openAddModal}>
            <Plus className="w-4 h-4 mr-2" />
            New Campaign
          </Button>
        </div>
      </div>

      {/* Stats Bar */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="grid grid-cols-5 gap-4"
      >
        {[
          { label: 'Total Campaigns', value: stats.total, icon: Send, color: 'text-enterprise-red' },
          { label: 'Active', value: stats.active, icon: Play, color: 'text-green-600' },
          { label: 'Paused', value: stats.paused, icon: Pause, color: 'text-yellow-600' },
          { label: 'Emails Sent', value: stats.totalSent, icon: Mail, color: 'text-enterprise-red' },
          { label: 'Replies', value: stats.totalReplies, icon: MessageSquare, color: 'text-purple-600' },
        ].map((stat) => (
          <div key={stat.label} className="card p-4">
            <div className="flex items-center gap-2 mb-1">
              <stat.icon className={`w-4 h-4 ${stat.color}`} />
              <p className="text-xs text-gray-500">{stat.label}</p>
            </div>
            <p className={`text-2xl font-semibold ${stat.color}`}>{stat.value}</p>
          </div>
        ))}
      </motion.div>

      {/* Messages */}
      {displayError && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center gap-3"
        >
          <AlertTriangle className="w-5 h-5 text-red-400" />
          <p className="text-red-400">{displayError}</p>
          <button onClick={() => { setError(null); useCampaignStore.getState().setError(null) }} className="ml-auto">
            <X className="w-4 h-4 text-red-400" />
          </button>
        </motion.div>
      )}

      {success && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-xl bg-green-500/10 border border-green-500/30 flex items-center gap-3"
        >
          <CheckCircle className="w-5 h-5 text-green-400" />
          <p className="text-green-400">{success}</p>
          <button onClick={() => setSuccess(null)} className="ml-auto">
            <X className="w-4 h-4 text-green-400" />
          </button>
        </motion.div>
      )}

      {/* Pre-requisites Warning */}
      {(senders.length === 0 || templateCategories.length === 0) && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/30"
        >
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-yellow-400 mt-0.5" />
            <div>
              <p className="text-yellow-400 font-medium">Before creating a campaign</p>
              <ul className="text-sm text-yellow-300/80 mt-1 space-y-1">
                {senders.length === 0 && (
                  <li>• <a href="/senders" className="underline">Add a sender</a> (email account)</li>
                )}
                {templateCategories.length === 0 && (
                  <li>• <a href="/templates" className="underline">Create a template category & templates</a></li>
                )}
              </ul>
            </div>
          </div>
        </motion.div>
      )}

      {/* Campaigns Grid */}
      {loading && campaigns.length === 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : campaigns.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="card p-12 text-center"
        >
          <Send className="w-16 h-16 mx-auto text-gray-400 mb-4" />
          <h3 className="text-xl font-semibold text-gray-900 mb-2">No campaigns yet</h3>
          <p className="text-gray-500 mb-6">
            Create your first campaign to start sending emails
          </p>
          <Button 
            onClick={() => setShowModal(true)}
            disabled={senders.length === 0 || templateCategories.length === 0}
          >
            <Plus className="w-4 h-4 mr-2" />
            Create First Campaign
          </Button>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {campaigns.map((campaign, index) => (
            <CampaignCard
              key={campaign.id}
              campaign={campaign}
              index={index}
              actionLoading={actionLoading}
              onStart={handleStart}
              onPause={handlePause}
              onResume={handleResume}
              onDelete={handleDelete}
              onEdit={openEditModal}
              onTriggerFollowups={handleTriggerFollowups}
            />
          ))}
        </div>
      )}

      {/* Create Campaign Modal */}
      <AnimatePresence>
        {showModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => {
              setShowModal(false)
              setEditingCampaign(null)
              setFormData(defaultFormData)
            }}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="card p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-gray-900">
                  {editingCampaign ? 'Edit Campaign' : 'Create Campaign'}
                </h2>
                <button
                  onClick={() => {
                    setShowModal(false)
                    setEditingCampaign(null)
                    setFormData(defaultFormData)
                  }}
                  className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <X className="w-5 h-5 text-gray-500" />
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                    Campaign Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="input"
                    placeholder="e.g., Q1 Outreach"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                    Description
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    rows={2}
                    className="input"
                    placeholder="Brief description of this campaign..."
                  />
                </div>

                {/* Sender selection / rotation */}
                <div>
                  <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                    Sending Mode
                  </label>
                  <div className="flex gap-2 mb-3">
                    <button
                      type="button"
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium border ${
                        !formData.sender_rotation_enabled
                          ? 'bg-enterprise-red text-white border-enterprise-red'
                          : 'bg-xen-dark-800 text-xen-dark-300 border-xen-dark-700'
                      }`}
                      onClick={() =>
                        setFormData({
                          ...formData,
                          sender_rotation_enabled: false,
                          sender_ids: [],
                          max_senders: undefined,
                        })
                      }
                    >
                      Single Sender
                    </button>
                    <button
                      type="button"
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium border ${
                        formData.sender_rotation_enabled
                          ? 'bg-enterprise-red text-white border-enterprise-red'
                          : 'bg-xen-dark-800 text-xen-dark-300 border-xen-dark-700'
                      }`}
                      onClick={() =>
                        setFormData({
                          ...formData,
                          sender_rotation_enabled: true,
                          sender_ids: formData.sender_id ? [formData.sender_id] : formData.sender_ids,
                        })
                      }
                    >
                      Multiple Senders (Rotation)
                    </button>
                  </div>

                  {!formData.sender_rotation_enabled ? (
                    <div>
                      <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                        Sender *
                      </label>
                      <select
                        required
                        value={formData.sender_id || ''}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            sender_id: e.target.value ? parseInt(e.target.value) : null,
                          })
                        }
                        className="input"
                      >
                        <option value="">Select a sender...</option>
                        {senders.map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.name || s.email} ({s.email})
                          </option>
                        ))}
                      </select>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <div>
                        <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                          Select Senders for Rotation *
                        </label>
                        <div className="space-y-1 max-h-40 overflow-y-auto rounded-xl bg-xen-dark-800 border border-xen-dark-700 p-2">
                          {senders.map((s) => {
                            const checked = formData.sender_ids.includes(s.id)
                            return (
                              <label
                                key={s.id}
                                className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer"
                              >
                                <input
                                  type="checkbox"
                                  checked={checked}
                                  onChange={(e) => {
                                    const next = e.target.checked
                                      ? [...formData.sender_ids, s.id]
                                      : formData.sender_ids.filter((id) => id !== s.id)
                                    setFormData({ ...formData, sender_ids: next })
                                  }}
                                  className="rounded border-gray-300 text-enterprise-red focus:ring-enterprise-red"
                                />
                                <span>
                                  {s.name || s.email} ({s.email})
                                </span>
                              </label>
                            )
                          })}
                          {senders.length === 0 && (
                            <p className="text-xs text-yellow-400">
                              <a href="/senders" className="underline">
                                Add a sender first
                              </a>
                            </p>
                          )}
                        </div>
                        <p className="text-xs text-xen-dark-500 mt-1">
                          Emails will be automatically rotated across the selected senders.
                        </p>
                      </div>

                      <div>
                        <label className="block text-xs text-xen-dark-400 mb-1">
                          Number of senders to use (optional)
                        </label>
                        <input
                          type="number"
                          min={1}
                          max={Math.max(1, formData.sender_ids.length || senders.length || 1)}
                          value={formData.max_senders ?? ''}
                          onChange={(e) =>
                            setFormData({
                              ...formData,
                              max_senders: e.target.value ? parseInt(e.target.value) : undefined,
                            })
                          }
                          className="input text-sm"
                          placeholder="Use all selected senders by default"
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* Template Category Section */}
                <div className="border-t border-xen-dark-700 pt-4">
                  <h3 className="text-sm font-semibold text-gray-900 mb-2">Template Category</h3>
                  <p className="text-xs text-xen-dark-400 mb-3">
                    Campaign will automatically rotate between all initial and follow-up templates in the selected category.
                  </p>
                  <div>
                    <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                      Template Category *
                    </label>
                    <select
                      required
                      value={formData.template_category}
                      onChange={(e) => setFormData({ ...formData, template_category: e.target.value })}
                      className="input"
                    >
                      <option value="">Select a category...</option>
                      {templateCategories.map((cat) => (
                        <option key={cat} value={cat}>
                          {cat}
                        </option>
                      ))}
                    </select>
                    {templateCategories.length === 0 && (
                      <p className="text-xs text-yellow-400 mt-1">
                        <a href="/templates" className="underline">Create a template category first</a>
                      </p>
                    )}
                  </div>
                </div>

                {/* Follow-up Settings */}
                <div className="border-t border-xen-dark-700 pt-4">
                  <div className="flex items-center gap-2 mb-3">
                    <input
                      type="checkbox"
                      id="followup_enabled"
                      checked={formData.followup_enabled}
                      onChange={(e) => setFormData({ ...formData, followup_enabled: e.target.checked })}
                      className="rounded border-gray-300 text-enterprise-red focus:ring-enterprise-red"
                    />
                    <label htmlFor="followup_enabled" className="text-sm font-medium text-xen-dark-300">
                      Enable automated follow-ups
                    </label>
                  </div>

                  {formData.followup_enabled && (
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs text-xen-dark-400 mb-1">
                          Days between emails
                        </label>
                        <input
                          type="number"
                          min={1}
                          max={14}
                          value={formData.followup_delay_days}
                          onChange={(e) => setFormData({ ...formData, followup_delay_days: parseInt(e.target.value) })}
                          className="input text-sm"
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-xen-dark-400 mb-1">
                          Max follow-ups
                        </label>
                        <input
                          type="number"
                          min={1}
                          max={10}
                          value={formData.max_followups}
                          onChange={(e) => setFormData({ ...formData, max_followups: parseInt(e.target.value) })}
                          className="input text-sm"
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* Info */}
                <div className="p-4 rounded-xl bg-gray-100 border border-gray-300">
                  <p className="text-sm text-gray-700">
                    💡 After creating the campaign, add leads to it from the Leads page, 
                    then come back here to start it.
                  </p>
                </div>

                {/* Submit */}
                <div className="flex items-center gap-3 pt-4">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => {
                      setShowModal(false)
                      setEditingCampaign(null)
                      setFormData(defaultFormData)
                    }}
                    className="flex-1"
                  >
                    Cancel
                  </Button>
                  <Button 
                    type="submit" 
                    disabled={submitting || senders.length === 0 || templates.length === 0} 
                    className="flex-1"
                  >
                    {submitting ? (
                      <>
                        <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                        {editingCampaign ? 'Updating...' : 'Creating...'}
                      </>
                    ) : (
                      editingCampaign ? 'Update Campaign' : 'Create Campaign'
                    )}
                  </Button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  )
}
