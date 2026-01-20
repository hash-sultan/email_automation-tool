import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Send,
  Plus,
  Trash2,
  Play,
  Pause,
  RefreshCw,
  AlertTriangle,
  X,
  Mail,
  MessageSquare,
  AlertCircle,
  CheckCircle,
  Clock,
} from 'lucide-react'
import Button from '../components/Button'
import Badge from '../components/Badge'
import { campaignsApi, sendersApi, templatesApi, type Campaign, type Sender, type Template } from '../api/client'

interface CampaignFormData {
  name: string
  description: string
  sender_id: number | null
  template_id: number | null
  followup_enabled: boolean
  followup_delay_days: number
  max_followups: number
}

const defaultFormData: CampaignFormData = {
  name: '',
  description: '',
  sender_id: null,
  template_id: null,
  followup_enabled: true,
  followup_delay_days: 3,
  max_followups: 3,
}

const statusConfig: Record<string, { color: string; icon: typeof Play; label: string }> = {
  draft: { color: 'gray', icon: Clock, label: 'Draft' },
  active: { color: 'green', icon: Play, label: 'Active' },
  paused: { color: 'yellow', icon: Pause, label: 'Paused' },
  completed: { color: 'blue', icon: CheckCircle, label: 'Completed' },
  cancelled: { color: 'red', icon: X, label: 'Cancelled' },
}

export default function Campaigns() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [senders, setSenders] = useState<Sender[]>([])
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [formData, setFormData] = useState<CampaignFormData>(defaultFormData)
  const [submitting, setSubmitting] = useState(false)
  const [actionLoading, setActionLoading] = useState<number | null>(null)

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [campaignsData, sendersData, templatesData] = await Promise.all([
        campaignsApi.list(),
        sendersApi.list(),
        templatesApi.list(),
      ])
      setCampaigns(campaignsData)
      setSenders(sendersData)
      setTemplates(templatesData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.sender_id || !formData.template_id) {
      setError('Please select a sender and template')
      return
    }

    setSubmitting(true)
    setError(null)

    try {
      await campaignsApi.create({
        name: formData.name,
        description: formData.description,
        sender_id: formData.sender_id,
        template_id: formData.template_id,
        followup_enabled: formData.followup_enabled,
        followup_delay_days: formData.followup_delay_days,
        max_followups: formData.max_followups,
      })
      setShowModal(false)
      setFormData(defaultFormData)
      setSuccess('Campaign created successfully!')
      fetchData()
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create campaign')
    } finally {
      setSubmitting(false)
    }
  }

  const handleStart = async (id: number) => {
    setActionLoading(id)
    try {
      await campaignsApi.start(id)
      setSuccess('Campaign started!')
      fetchData()
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start campaign')
    } finally {
      setActionLoading(null)
    }
  }

  const handlePause = async (id: number) => {
    setActionLoading(id)
    try {
      await campaignsApi.pause(id)
      setSuccess('Campaign paused')
      fetchData()
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to pause campaign')
    } finally {
      setActionLoading(null)
    }
  }

  const handleResume = async (id: number) => {
    setActionLoading(id)
    try {
      await campaignsApi.resume(id)
      setSuccess('Campaign resumed!')
      fetchData()
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to resume campaign')
    } finally {
      setActionLoading(null)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this campaign?')) return

    try {
      await campaignsApi.delete(id)
      setSuccess('Campaign deleted')
      fetchData()
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete campaign')
    }
  }

  // Stats
  const stats = {
    total: campaigns.length,
    active: campaigns.filter(c => c.status === 'active').length,
    paused: campaigns.filter(c => c.status === 'paused').length,
    totalSent: campaigns.reduce((sum, c) => sum + c.emails_sent, 0),
    totalReplies: campaigns.reduce((sum, c) => sum + c.emails_replied, 0),
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <motion.h1
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-2xl font-bold text-white"
          >
            Campaigns
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-xen-dark-400 mt-1"
          >
            Create and manage your email campaigns
          </motion.p>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="ghost" onClick={fetchData} disabled={loading}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          <Button onClick={() => setShowModal(true)}>
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
          { label: 'Total Campaigns', value: stats.total, icon: Send, color: 'text-white' },
          { label: 'Active', value: stats.active, icon: Play, color: 'text-green-400' },
          { label: 'Paused', value: stats.paused, icon: Pause, color: 'text-yellow-400' },
          { label: 'Emails Sent', value: stats.totalSent, icon: Mail, color: 'text-blue-400' },
          { label: 'Replies', value: stats.totalReplies, icon: MessageSquare, color: 'text-purple-400' },
        ].map((stat) => (
          <div key={stat.label} className="glass rounded-xl p-4 border border-xen-dark-700/50">
            <div className="flex items-center gap-2 mb-1">
              <stat.icon className={`w-4 h-4 ${stat.color}`} />
              <p className="text-xs text-xen-dark-500">{stat.label}</p>
            </div>
            <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
          </div>
        ))}
      </motion.div>

      {/* Messages */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center gap-3"
        >
          <AlertTriangle className="w-5 h-5 text-red-400" />
          <p className="text-red-400">{error}</p>
          <button onClick={() => setError(null)} className="ml-auto">
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
      {(senders.length === 0 || templates.length === 0) && (
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
                {templates.length === 0 && (
                  <li>• <a href="/templates" className="underline">Create a template</a> (email content)</li>
                )}
              </ul>
            </div>
          </div>
        </motion.div>
      )}

      {/* Campaigns Grid */}
      {loading && campaigns.length === 0 ? (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 text-xen-red-400 animate-spin" />
        </div>
      ) : campaigns.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass rounded-2xl p-12 border border-xen-dark-700/50 text-center"
        >
          <Send className="w-16 h-16 mx-auto text-xen-dark-600 mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">No campaigns yet</h3>
          <p className="text-xen-dark-400 mb-6">
            Create your first campaign to start sending emails
          </p>
          <Button 
            onClick={() => setShowModal(true)}
            disabled={senders.length === 0 || templates.length === 0}
          >
            <Plus className="w-4 h-4 mr-2" />
            Create First Campaign
          </Button>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {campaigns.map((campaign, index) => {
            const status = statusConfig[campaign.status] || statusConfig.draft
            const replyRate = campaign.emails_sent > 0 
              ? ((campaign.emails_replied / campaign.emails_sent) * 100).toFixed(1)
              : '0.0'

            return (
              <motion.div
                key={campaign.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className="glass rounded-2xl p-6 border border-xen-dark-700/50 hover:border-xen-dark-600/50 transition-colors"
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                      campaign.status === 'active' ? 'bg-green-500/20' : 'bg-xen-red-500/20'
                    }`}>
                      <Send className={`w-6 h-6 ${
                        campaign.status === 'active' ? 'text-green-400' : 'text-xen-red-400'
                      }`} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-white">{campaign.name}</h3>
                      <p className="text-xs text-xen-dark-400">
                        Created {new Date(campaign.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <Badge 
                    variant={
                      campaign.status === 'active' ? 'success' : 
                      campaign.status === 'paused' ? 'warning' : 
                      campaign.status === 'completed' ? 'info' : 'default'
                    }
                    pulse={campaign.status === 'active'}
                  >
                    {status.label}
                  </Badge>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-3 gap-2 mb-4">
                  <div className="p-2 rounded-lg bg-xen-dark-800/50 text-center">
                    <p className="text-lg font-bold text-white">{campaign.total_leads}</p>
                    <p className="text-xs text-xen-dark-500">Leads</p>
                  </div>
                  <div className="p-2 rounded-lg bg-xen-dark-800/50 text-center">
                    <p className="text-lg font-bold text-blue-400">{campaign.emails_sent}</p>
                    <p className="text-xs text-xen-dark-500">Sent</p>
                  </div>
                  <div className="p-2 rounded-lg bg-xen-dark-800/50 text-center">
                    <p className="text-lg font-bold text-green-400">{campaign.emails_replied}</p>
                    <p className="text-xs text-xen-dark-500">Replies</p>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="mb-4">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-xen-dark-400">Reply Rate</span>
                    <span className="text-green-400">{replyRate}%</span>
                  </div>
                  <div className="h-2 bg-xen-dark-800 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-green-500 to-green-400 rounded-full transition-all"
                      style={{ width: `${Math.min(parseFloat(replyRate), 100)}%` }}
                    />
                  </div>
                </div>

                {/* Bounce indicator */}
                {campaign.emails_bounced > 0 && (
                  <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/30 mb-4">
                    <div className="flex items-center gap-2 text-sm text-red-400">
                      <AlertCircle className="w-4 h-4" />
                      <span>{campaign.emails_bounced} bounces</span>
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex items-center gap-2">
                  {campaign.status === 'draft' && (
                    <Button
                      size="sm"
                      onClick={() => handleStart(campaign.id)}
                      disabled={actionLoading === campaign.id || campaign.total_leads === 0}
                      className="flex-1"
                    >
                      {actionLoading === campaign.id ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                      ) : (
                        <>
                          <Play className="w-4 h-4 mr-1" />
                          Start
                        </>
                      )}
                    </Button>
                  )}
                  {campaign.status === 'active' && (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => handlePause(campaign.id)}
                      disabled={actionLoading === campaign.id}
                      className="flex-1"
                    >
                      {actionLoading === campaign.id ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                      ) : (
                        <>
                          <Pause className="w-4 h-4 mr-1" />
                          Pause
                        </>
                      )}
                    </Button>
                  )}
                  {campaign.status === 'paused' && (
                    <Button
                      size="sm"
                      onClick={() => handleResume(campaign.id)}
                      disabled={actionLoading === campaign.id}
                      className="flex-1"
                    >
                      {actionLoading === campaign.id ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                      ) : (
                        <>
                          <Play className="w-4 h-4 mr-1" />
                          Resume
                        </>
                      )}
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(campaign.id)}
                    className="text-red-400 hover:text-red-300"
                    disabled={campaign.status === 'active'}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </motion.div>
            )
          })}
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
            onClick={() => setShowModal(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="glass rounded-2xl p-6 border border-xen-dark-700/50 w-full max-w-lg max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-white">Create Campaign</h2>
                <button
                  onClick={() => setShowModal(false)}
                  className="p-2 rounded-lg hover:bg-xen-dark-800 transition-colors"
                >
                  <X className="w-5 h-5 text-xen-dark-400" />
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
                    className="w-full px-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white placeholder-xen-dark-500 focus:outline-none focus:border-xen-red-500"
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
                    className="w-full px-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white placeholder-xen-dark-500 focus:outline-none focus:border-xen-red-500"
                    placeholder="Brief description of this campaign..."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                    Sender *
                  </label>
                  <select
                    required
                    value={formData.sender_id || ''}
                    onChange={(e) => setFormData({ ...formData, sender_id: parseInt(e.target.value) })}
                    className="w-full px-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white focus:outline-none focus:border-xen-red-500"
                  >
                    <option value="">Select a sender...</option>
                    {senders.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name || s.email} ({s.email})
                      </option>
                    ))}
                  </select>
                  {senders.length === 0 && (
                    <p className="text-xs text-yellow-400 mt-1">
                      <a href="/senders" className="underline">Add a sender first</a>
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                    Email Template *
                  </label>
                  <select
                    required
                    value={formData.template_id || ''}
                    onChange={(e) => setFormData({ ...formData, template_id: parseInt(e.target.value) })}
                    className="w-full px-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white focus:outline-none focus:border-xen-red-500"
                  >
                    <option value="">Select a template...</option>
                    {templates.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name} - {t.subject.substring(0, 30)}...
                      </option>
                    ))}
                  </select>
                  {templates.length === 0 && (
                    <p className="text-xs text-yellow-400 mt-1">
                      <a href="/templates" className="underline">Create a template first</a>
                    </p>
                  )}
                </div>

                {/* Follow-up Settings */}
                <div className="border-t border-xen-dark-700 pt-4">
                  <div className="flex items-center gap-2 mb-3">
                    <input
                      type="checkbox"
                      id="followup_enabled"
                      checked={formData.followup_enabled}
                      onChange={(e) => setFormData({ ...formData, followup_enabled: e.target.checked })}
                      className="rounded border-xen-dark-700 bg-xen-dark-800 text-xen-red-500 focus:ring-xen-red-500"
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
                          className="w-full px-3 py-2 rounded-lg bg-xen-dark-800 border border-xen-dark-700 text-white text-sm focus:outline-none focus:border-xen-red-500"
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
                          className="w-full px-3 py-2 rounded-lg bg-xen-dark-800 border border-xen-dark-700 text-white text-sm focus:outline-none focus:border-xen-red-500"
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* Info */}
                <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/30">
                  <p className="text-sm text-blue-400">
                    💡 After creating the campaign, add leads to it from the Leads page, 
                    then come back here to start it.
                  </p>
                </div>

                {/* Submit */}
                <div className="flex items-center gap-3 pt-4">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => setShowModal(false)}
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
                        Creating...
                      </>
                    ) : (
                      'Create Campaign'
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
