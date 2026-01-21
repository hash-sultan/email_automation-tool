import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import {
  Mail,
  Plus,
  Trash2,
  CheckCircle,
  XCircle,
  RefreshCw,
  Shield,
  AlertTriangle,
  X,
  Server,
  Pencil,
} from 'lucide-react'
import Button from '../components/Button'
import Badge from '../components/Badge'
import { sendersApi, type Sender, type SenderCreate } from '../api/client'

interface SenderFormData {
  email: string
  name: string
  provider: 'smtp' | 'gmail' | 'outlook'
  smtp_host: string
  smtp_port: number
  smtp_username: string
  smtp_password: string
  use_tls: boolean
  daily_limit: number
  imap_host: string
  imap_port: number
  imap_username: string
  imap_password: string
}

const defaultFormData: SenderFormData = {
  email: '',
  name: '',
  provider: 'smtp',
  smtp_host: 'smtp.gmail.com',
  smtp_port: 587,
  smtp_username: '',
  smtp_password: '',
  use_tls: true,
  daily_limit: 50,
  imap_host: 'imap.gmail.com',
  imap_port: 993,
  imap_username: '',
  imap_password: '',
}

export default function Senders() {
  const [senders, setSenders] = useState<Sender[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [editingSenderId, setEditingSenderId] = useState<number | null>(null)
  const [formData, setFormData] = useState<SenderFormData>(defaultFormData)
  const [submitting, setSubmitting] = useState(false)

  const fetchSenders = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await sendersApi.list()
      setSenders(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load senders')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSenders()
  }, [])

  const openAddModal = () => {
    setEditingSenderId(null)
    setFormData(defaultFormData)
    setShowModal(true)
  }

  const openEditModal = (sender: Sender) => {
    setFormData({
      email: sender.email,
      name: sender.name,
      provider: sender.provider === 'smtp' ? 'smtp' : sender.provider,
      smtp_host: sender.smtp_host || 'smtp.gmail.com',
      smtp_port: sender.smtp_port || 587,
      smtp_username: sender.smtp_username || sender.email,
      smtp_password: '',
      use_tls: sender.use_tls ?? true,
      daily_limit: sender.daily_limit,
      imap_host: sender.imap_host || '',
      imap_port: sender.imap_port || 993,
      imap_username: sender.email,
      imap_password: '',
    })
    setEditingSenderId(sender.id)
    setShowModal(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)

    // Validate required fields
    if (!formData.email) {
      setError('Email is required')
      setSubmitting(false)
      return
    }

    if (!formData.smtp_password) {
      setError('SMTP password is required')
      setSubmitting(false)
      return
    }

    if (!formData.smtp_host) {
      setError('SMTP host is required')
      setSubmitting(false)
      return
    }

    try {
      const providerType: 'custom_smtp' | 'gmail' | 'outlook' = 
        formData.provider === 'smtp' ? 'custom_smtp' : formData.provider

      if (editingSenderId) {
        // Update existing sender
        const updatePayload: any = {
          name: (formData.name || formData.email).trim(),
          base_daily_limit: formData.daily_limit,
          smtp_config: {
            host: formData.smtp_host.trim(),
            port: formData.smtp_port,
            username: (formData.smtp_username || formData.email).trim(),
            password: formData.smtp_password,
            use_tls: formData.use_tls,
          },
          ...(formData.imap_host && {
            imap_config: {
              host: formData.imap_host.trim(),
              port: formData.imap_port,
              username: (formData.imap_username || formData.email).trim(),
              password: formData.imap_password || formData.smtp_password,
              use_ssl: true,
              folder: 'INBOX',
            },
          }),
        }

        await sendersApi.update(editingSenderId, updatePayload)
      } else {
        // Create new sender
        const payload: SenderCreate = {
          email: formData.email.trim(),
          name: (formData.name || formData.email).trim(),
          provider_type: providerType,
          base_daily_limit: formData.daily_limit,
          smtp_config: {
            host: formData.smtp_host.trim(),
            port: formData.smtp_port,
            username: (formData.smtp_username || formData.email).trim(),
            password: formData.smtp_password,
            use_tls: formData.use_tls,
          },
          ...(formData.imap_host && {
            imap_config: {
              host: formData.imap_host.trim(),
              port: formData.imap_port,
              username: (formData.imap_username || formData.email).trim(),
              password: formData.imap_password || formData.smtp_password,
              use_ssl: true,
            },
          }),
        }

        await sendersApi.create(payload)
      }

      setShowModal(false)
      setEditingSenderId(null)
      setFormData(defaultFormData)
      fetchSenders()
    } catch (err) {
      console.error('Error creating sender:', err)
      let errorMessage = err instanceof Error ? err.message : 'Failed to create sender'
      
      // Provide helpful message for duplicate email
      if (errorMessage.includes('already exists')) {
        errorMessage = `A sender with email "${formData.email}" already exists. Please delete it first or use a different email.`
      }
      
      setError(errorMessage)
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this sender?')) return

    try {
      await sendersApi.delete(id)
      fetchSenders()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete sender')
    }
  }

  const handleVerify = async (id: number) => {
    console.log('Verify button clicked, sender ID:', id)
    try {
      console.log('Calling sendersApi.verify...')
      const result = await sendersApi.verify(id) as any
      console.log('Verify API call succeeded', result)
      
      // Refresh immediately to get updated status
      await fetchSenders()
      
      // Show appropriate message based on result
      if (result.smtp_verified) {
        toast.success('SMTP connection verified! Sender is now active.', {
          duration: 3000,
        })
      } else {
        const errorMsg = result.error || 'SMTP connection test failed'
        toast.error(`Verification failed: ${errorMsg}`, {
          duration: 5000,
        })
        setError(errorMsg)
      }
    } catch (err) {
      console.error('Verify error:', err)
      const errorMessage = err instanceof Error ? err.message : 'Verification failed'
      setError(errorMessage)
      toast.error(errorMessage, {
        duration: 4000,
      })
      // Still refresh to get any status updates
      fetchSenders()
    }
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
            Email Senders
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-xen-dark-400 mt-1"
          >
            Manage your sending email accounts
          </motion.p>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="ghost" onClick={fetchSenders} disabled={loading}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          <Button onClick={openAddModal}>
            <Plus className="w-4 h-4 mr-2" />
            Add Sender
          </Button>
        </div>
      </div>

      {/* Error Banner */}
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

      {/* Senders Grid */}
      {loading && senders.length === 0 ? (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 text-xen-red-400 animate-spin" />
        </div>
      ) : senders.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass rounded-2xl p-12 border border-xen-dark-700/50 text-center"
        >
          <Mail className="w-16 h-16 mx-auto text-xen-dark-600 mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">No senders yet</h3>
          <p className="text-xen-dark-400 mb-6">
            Add your first email sender to start sending campaigns
          </p>
          <Button onClick={openAddModal}>
            <Plus className="w-4 h-4 mr-2" />
            Add Your First Sender
          </Button>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {senders.map((sender, index) => (
            <motion.div
              key={sender.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="glass rounded-2xl p-6 border border-xen-dark-700/50 hover:border-xen-dark-600/50 transition-colors"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-xl bg-xen-red-500/20 flex items-center justify-center">
                    <Mail className="w-6 h-6 text-xen-red-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">{sender.name || sender.email}</h3>
                    <p className="text-sm text-xen-dark-400">{sender.email}</p>
                  </div>
                </div>
                <Badge variant={sender.is_active ? 'success' : 'warning'}>
                  {sender.is_active ? 'Active' : 'Inactive'}
                </Badge>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="p-3 rounded-lg bg-xen-dark-800/50">
                  <p className="text-xs text-xen-dark-500">Sent Today</p>
                  <p className="text-lg font-semibold text-white">
                    {sender.emails_sent_today} / {sender.daily_limit}
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-xen-dark-800/50">
                  <p className="text-xs text-xen-dark-500">This Hour</p>
                  <p className="text-lg font-semibold text-white">
                    {sender.emails_sent_this_hour} / {sender.hourly_limit}
                  </p>
                </div>
              </div>

              {/* Warmup Status */}
              {sender.warmup_enabled && (
                <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/30 mb-4">
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-blue-400" />
                    <span className="text-sm text-blue-400">
                      Warmup Day {sender.warmup_day}
                    </span>
                  </div>
                </div>
              )}

              {/* Provider Info */}
              <div className="flex items-center gap-2 mb-4 text-sm text-xen-dark-400">
                <Server className="w-4 h-4" />
                <span className="capitalize">{sender.provider}</span>
                {sender.smtp_host && <span>• {sender.smtp_host}</span>}
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => openEditModal(sender)}
                  className="flex-1"
                >
                  <Pencil className="w-4 h-4 mr-1" />
                  Edit
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleVerify(sender.id)}
                  className="flex-1"
                >
                  {sender.is_verified ? (
                    <>
                      <CheckCircle className="w-4 h-4 mr-1 text-green-400" />
                      Verified
                    </>
                  ) : (
                    <>
                      <XCircle className="w-4 h-4 mr-1" />
                      Verify
                    </>
                  )}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleDelete(sender.id)}
                  className="text-red-400 hover:text-red-300"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Add Sender Modal */}
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
                <h2 className="text-xl font-semibold text-white">
                  {editingSenderId ? 'Edit Email Sender' : 'Add Email Sender'}
                </h2>
                <button
                  onClick={() => setShowModal(false)}
                  className="p-2 rounded-lg hover:bg-xen-dark-800 transition-colors"
                >
                  <X className="w-5 h-5 text-xen-dark-400" />
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                {/* Basic Info */}
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                      Email Address *
                    </label>
                    <input
                      type="email"
                      required
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      className="w-full px-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white placeholder-xen-dark-500 focus:outline-none focus:border-xen-red-500"
                      placeholder="your-email@gmail.com"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                      Display Name
                    </label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="w-full px-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white placeholder-xen-dark-500 focus:outline-none focus:border-xen-red-500"
                      placeholder="John Smith"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                      Daily Limit
                    </label>
                    <input
                      type="number"
                      value={formData.daily_limit}
                      onChange={(e) => setFormData({ ...formData, daily_limit: parseInt(e.target.value) })}
                      className="w-full px-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white placeholder-xen-dark-500 focus:outline-none focus:border-xen-red-500"
                      min={1}
                      max={500}
                    />
                    <p className="text-xs text-xen-dark-500 mt-1">Max 500/day for safety</p>
                  </div>
                </div>

                {/* SMTP Settings */}
                <div className="border-t border-xen-dark-700 pt-4">
                  <h3 className="text-sm font-medium text-xen-dark-300 mb-3">SMTP Settings</h3>
                  
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-xen-dark-400 mb-1">SMTP Host</label>
                      <input
                        type="text"
                        value={formData.smtp_host}
                        onChange={(e) => setFormData({ ...formData, smtp_host: e.target.value })}
                        className="w-full px-3 py-2 rounded-lg bg-xen-dark-800 border border-xen-dark-700 text-white text-sm focus:outline-none focus:border-xen-red-500"
                        placeholder="smtp.gmail.com"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-xen-dark-400 mb-1">Port</label>
                      <input
                        type="number"
                        value={formData.smtp_port}
                        onChange={(e) => setFormData({ ...formData, smtp_port: parseInt(e.target.value) })}
                        className="w-full px-3 py-2 rounded-lg bg-xen-dark-800 border border-xen-dark-700 text-white text-sm focus:outline-none focus:border-xen-red-500"
                      />
                    </div>
                  </div>

                  <div className="mt-3">
                    <label className="block text-xs text-xen-dark-400 mb-1">SMTP Username</label>
                    <input
                      type="text"
                      value={formData.smtp_username}
                      onChange={(e) => setFormData({ ...formData, smtp_username: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg bg-xen-dark-800 border border-xen-dark-700 text-white text-sm focus:outline-none focus:border-xen-red-500"
                      placeholder="Same as email (leave blank)"
                    />
                  </div>

                  <div className="mt-3">
                    <label className="block text-xs text-xen-dark-400 mb-1">SMTP Password / App Password *</label>
                    <input
                      type="password"
                      required
                      value={formData.smtp_password}
                      onChange={(e) => setFormData({ ...formData, smtp_password: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg bg-xen-dark-800 border border-xen-dark-700 text-white text-sm focus:outline-none focus:border-xen-red-500"
                      placeholder="Your app password"
                    />
                    <p className="text-xs text-xen-dark-500 mt-1">
                      For Gmail: Use App Password (not your regular password)
                    </p>
                  </div>

                  <div className="mt-3 flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="use_tls"
                      checked={formData.use_tls}
                      onChange={(e) => setFormData({ ...formData, use_tls: e.target.checked })}
                      className="rounded border-xen-dark-700 bg-xen-dark-800 text-xen-red-500 focus:ring-xen-red-500"
                    />
                    <label htmlFor="use_tls" className="text-sm text-xen-dark-300">
                      Use TLS encryption
                    </label>
                  </div>
                </div>

                {/* Gmail Help */}
                <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/30">
                  <h4 className="text-sm font-medium text-blue-400 mb-2">Gmail Setup</h4>
                  <ol className="text-xs text-blue-300/80 space-y-1 list-decimal list-inside">
                    <li>Enable 2-Factor Authentication on your Gmail</li>
                    <li>Go to myaccount.google.com/apppasswords</li>
                    <li>Create an App Password for "Mail"</li>
                    <li>Use that 16-character password above</li>
                  </ol>
                </div>

                {/* IMAP Settings (optional, for reply tracking) */}
                <div className="border-t border-xen-dark-700 pt-4">
                  <h3 className="text-sm font-medium text-xen-dark-300 mb-3">IMAP Settings (for reply tracking)</h3>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-xen-dark-400 mb-1">IMAP Host</label>
                      <input
                        type="text"
                        value={formData.imap_host}
                        onChange={(e) => setFormData({ ...formData, imap_host: e.target.value })}
                        className="w-full px-3 py-2 rounded-lg bg-xen-dark-800 border border-xen-dark-700 text-white text-sm focus:outline-none focus:border-xen-red-500"
                        placeholder="imap.gmail.com"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-xen-dark-400 mb-1">Port</label>
                      <input
                        type="number"
                        value={formData.imap_port}
                        onChange={(e) => setFormData({ ...formData, imap_port: parseInt(e.target.value) })}
                        className="w-full px-3 py-2 rounded-lg bg-xen-dark-800 border border-xen-dark-700 text-white text-sm focus:outline-none focus:border-xen-red-500"
                      />
                    </div>
                  </div>

                  <div className="mt-3">
                    <label className="block text-xs text-xen-dark-400 mb-1">IMAP Username</label>
                    <input
                      type="text"
                      value={formData.imap_username}
                      onChange={(e) => setFormData({ ...formData, imap_username: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg bg-xen-dark-800 border border-xen-dark-700 text-white text-sm focus:outline-none focus:border-xen-red-500"
                      placeholder="Usually same as email"
                    />
                  </div>

                  <div className="mt-3">
                    <label className="block text-xs text-xen-dark-400 mb-1">IMAP Password / App Password</label>
                    <input
                      type="password"
                      value={formData.imap_password}
                      onChange={(e) => setFormData({ ...formData, imap_password: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg bg-xen-dark-800 border border-xen-dark-700 text-white text-sm focus:outline-none focus:border-xen-red-500"
                      placeholder="Leave empty to reuse SMTP password"
                    />
                    <p className="text-xs text-xen-dark-500 mt-1">
                      For Gmail, this should be the same App Password you use for SMTP.
                    </p>
                  </div>
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
                  <Button type="submit" disabled={submitting} className="flex-1">
                    {submitting ? (
                      <>
                        <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                        {editingSenderId ? 'Saving...' : 'Adding...'}
                      </>
                    ) : (
                      <>
                        <Plus className="w-4 h-4 mr-2" />
                        {editingSenderId ? 'Save Changes' : 'Add Sender'}
                      </>
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
