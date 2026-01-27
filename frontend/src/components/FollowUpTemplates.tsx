import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plus,
  Trash2,
  Edit2,
  RefreshCw,
  AlertTriangle,
  X,
  Clock,
  Mail,
  CheckCircle,
} from 'lucide-react'
import Button from './Button'
import Badge from './Badge'
import { followupTemplatesApi, type FollowUpTemplate, type FollowUpTemplateCreate } from '../api/client'

interface FollowUpTemplatesProps {
  campaignId: number
  campaignName: string
  onClose: () => void
}

interface FollowUpFormData {
  step: number
  delay_days: number
  delay_hours: number
  subject: string
  body_html: string
  body_plain: string
  reply_to_thread: boolean
  is_active: boolean
}

const defaultFormData: FollowUpFormData = {
  step: 1,
  delay_days: 3,
  delay_hours: 0,
  subject: '',
  body_html: '',
  body_plain: '',
  reply_to_thread: true,
  is_active: true,
}

export default function FollowUpTemplates({ campaignId, campaignName, onClose }: FollowUpTemplatesProps) {
  const [templates, setTemplates] = useState<FollowUpTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [formData, setFormData] = useState<FollowUpFormData>(defaultFormData)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const fetchTemplates = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await followupTemplatesApi.list(campaignId)
      setTemplates(data.sort((a, b) => a.step - b.step))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load follow-up templates')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (campaignId) {
      fetchTemplates()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [campaignId])

  const generatePlainText = (html: string) => {
    return html
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<\/p>/gi, '\n\n')
      .replace(/<[^>]+>/g, '')
      .trim()
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)

    try {
      const data: FollowUpTemplateCreate = {
        campaign_id: campaignId,
        step: formData.step,
        delay_days: formData.delay_days,
        delay_hours: formData.delay_hours,
        subject: formData.subject,
        body_html: formData.body_html,
        body_plain: formData.body_plain || generatePlainText(formData.body_html),
        reply_to_thread: formData.reply_to_thread,
        is_active: formData.is_active,
      }

      if (editingId) {
        await followupTemplatesApi.update(editingId, data)
        setSuccess('Follow-up template updated!')
      } else {
        await followupTemplatesApi.create(data)
        setSuccess('Follow-up template created!')
      }
      
      setShowModal(false)
      setFormData(defaultFormData)
      setEditingId(null)
      fetchTemplates()
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save follow-up template')
    } finally {
      setSubmitting(false)
    }
  }

  const handleEdit = (template: FollowUpTemplate) => {
    setFormData({
      step: template.step,
      delay_days: template.delay_days,
      delay_hours: template.delay_hours,
      subject: template.subject,
      body_html: template.body_html,
      body_plain: template.body_plain || generatePlainText(template.body_html),
      reply_to_thread: template.reply_to_thread,
      is_active: template.is_active,
    })
    setEditingId(template.id)
    setShowModal(true)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this follow-up template?')) return

    try {
      await followupTemplatesApi.delete(id)
      setSuccess('Follow-up template deleted')
      fetchTemplates()
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete follow-up template')
    }
  }

  const getNextStep = () => {
    if (templates.length === 0) return 1
    const maxStep = Math.max(...templates.map(t => t.step))
    return maxStep + 1
  }

  const handleNewTemplate = () => {
    setFormData({
      ...defaultFormData,
      step: getNextStep(),
    })
    setEditingId(null)
    setShowModal(true)
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="glass rounded-2xl border border-xen-dark-700/50 w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col"
      >
        {/* Header */}
        <div className="p-6 border-b border-xen-dark-700/50 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-white">Follow-up Templates</h2>
            <p className="text-sm text-xen-dark-400 mt-1">Manage follow-up emails for: {campaignName}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-xen-dark-800 transition-colors"
          >
            <X className="w-5 h-5 text-xen-dark-400" />
          </button>
        </div>

        {/* Messages */}
        <div className="px-6 pt-4">
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center gap-3 mb-4"
            >
              <AlertTriangle className="w-5 h-5 text-red-400" />
              <p className="text-red-400 text-sm">{error}</p>
              <button onClick={() => setError(null)} className="ml-auto">
                <X className="w-4 h-4 text-red-400" />
              </button>
            </motion.div>
          )}

          {success && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-3 rounded-xl bg-green-500/10 border border-green-500/30 flex items-center gap-3 mb-4"
            >
              <CheckCircle className="w-5 h-5 text-green-400" />
              <p className="text-green-400 text-sm">{success}</p>
              <button onClick={() => setSuccess(null)} className="ml-auto">
                <X className="w-4 h-4 text-green-400" />
              </button>
            </motion.div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Placeholders Info */}
          <div className="p-4 rounded-xl bg-xen-dark-800/50 border border-xen-dark-700/50 mb-4">
            <h3 className="text-sm font-medium text-xen-dark-300 mb-2">Available Placeholders</h3>
            <div className="flex flex-wrap gap-2">
              {['{{name}}', '{{first_name}}', '{{last_name}}', '{{company}}', '{{industry}}', '{{title}}'].map((placeholder) => (
                <code key={placeholder} className="px-2 py-1 rounded bg-xen-dark-700 text-xen-red-400 text-xs">
                  {placeholder}
                </code>
              ))}
            </div>
            <p className="text-xs text-xen-dark-500 mt-2">
              💡 Use "Re: " prefix in subject to reply in thread
            </p>
          </div>

          {/* Action Bar */}
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-xen-dark-400">
              {templates.length} follow-up template{templates.length !== 1 ? 's' : ''} configured
            </p>
            <Button onClick={handleNewTemplate} size="sm">
              <Plus className="w-4 h-4 mr-2" />
              Add Follow-up
            </Button>
          </div>

          {/* Templates List */}
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <RefreshCw className="w-8 h-8 text-xen-red-400 animate-spin" />
            </div>
          ) : templates.length === 0 ? (
            <div className="text-center py-12">
              <Mail className="w-16 h-16 mx-auto text-xen-dark-600 mb-4" />
              <h3 className="text-lg font-semibold text-white mb-2">No follow-up templates</h3>
              <p className="text-xen-dark-400 mb-6">
                Create your first follow-up template to automatically send follow-up emails
              </p>
              <Button onClick={handleNewTemplate}>
                <Plus className="w-4 h-4 mr-2" />
                Create First Follow-up
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {templates.map((template) => (
                <motion.div
                  key={template.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="glass rounded-xl p-4 border border-xen-dark-700/50 hover:border-xen-dark-600/50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <Badge variant="info">Step {template.step}</Badge>
                        <div className="flex items-center gap-2 text-xs text-xen-dark-400">
                          <Clock className="w-3 h-3" />
                          <span>
                            {template.delay_days} day{template.delay_days !== 1 ? 's' : ''}
                            {template.delay_hours > 0 && ` ${template.delay_hours} hour${template.delay_hours !== 1 ? 's' : ''}`}
                          </span>
                        </div>
                        {template.reply_to_thread && (
                          <Badge variant="success" size="sm">Thread Reply</Badge>
                        )}
                        {!template.is_active && (
                          <Badge variant="warning" size="sm">Inactive</Badge>
                        )}
                      </div>
                      <h4 className="font-medium text-white mb-1">{template.subject}</h4>
                      <p className="text-sm text-xen-dark-400 line-clamp-2">
                        {generatePlainText(template.body_html)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 ml-4">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleEdit(template)}
                      >
                        <Edit2 className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(template.id)}
                        className="text-red-400 hover:text-red-300"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>

        {/* Create/Edit Modal */}
        <AnimatePresence>
          {showModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/70 backdrop-blur-sm z-[60] flex items-center justify-center p-4"
              onClick={() => setShowModal(false)}
            >
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 20 }}
                className="glass rounded-2xl p-6 border border-xen-dark-700/50 w-full max-w-2xl max-h-[90vh] overflow-y-auto"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold text-white">
                    {editingId ? 'Edit Follow-up Template' : 'Create Follow-up Template'}
                  </h3>
                  <button
                    onClick={() => setShowModal(false)}
                    className="p-2 rounded-lg hover:bg-xen-dark-800 transition-colors"
                  >
                    <X className="w-5 h-5 text-xen-dark-400" />
                  </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                        Step Number *
                      </label>
                      <input
                        type="number"
                        required
                        min={1}
                        max={10}
                        value={formData.step}
                        onChange={(e) => setFormData({ ...formData, step: parseInt(e.target.value) })}
                        className="w-full px-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white focus:outline-none focus:border-xen-red-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                        Delay (Days) *
                      </label>
                      <input
                        type="number"
                        required
                        min={1}
                        max={14}
                        value={formData.delay_days}
                        onChange={(e) => setFormData({ ...formData, delay_days: parseInt(e.target.value) })}
                        className="w-full px-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white focus:outline-none focus:border-xen-red-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                        Delay (Hours)
                      </label>
                      <input
                        type="number"
                        min={0}
                        max={23}
                        value={formData.delay_hours}
                        onChange={(e) => setFormData({ ...formData, delay_hours: parseInt(e.target.value) })}
                        className="w-full px-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white focus:outline-none focus:border-xen-red-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                      Subject Line *
                    </label>
                    <input
                      type="text"
                      required
                      value={formData.subject}
                      onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                      className="w-full px-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white placeholder-xen-dark-500 focus:outline-none focus:border-xen-red-500"
                      placeholder="e.g., Re: Quick question about {{company}}"
                    />
                    <p className="text-xs text-xen-dark-500 mt-1">
                      Use "Re: " prefix to reply in the same email thread
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                      Email Body (HTML) *
                    </label>
                    <textarea
                      required
                      value={formData.body_html}
                      onChange={(e) => {
                        setFormData({
                          ...formData,
                          body_html: e.target.value,
                          body_plain: generatePlainText(e.target.value),
                        })
                      }}
                      rows={8}
                      className="w-full px-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white placeholder-xen-dark-500 focus:outline-none focus:border-xen-red-500 font-mono text-sm"
                      placeholder="<p>Hi {{name}},</p><p>Just following up on my previous email...</p>"
                    />
                    <p className="text-xs text-xen-dark-500 mt-1">
                      Use HTML tags for formatting. Placeholders like {'{{name}}'} will be replaced.
                    </p>
                  </div>

                  <div className="flex items-center gap-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.reply_to_thread}
                        onChange={(e) => setFormData({ ...formData, reply_to_thread: e.target.checked })}
                        className="rounded border-xen-dark-700 bg-xen-dark-800 text-xen-red-500 focus:ring-xen-red-500"
                      />
                      <span className="text-sm text-xen-dark-300">Reply in same thread</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.is_active}
                        onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                        className="rounded border-xen-dark-700 bg-xen-dark-800 text-xen-red-500 focus:ring-xen-red-500"
                      />
                      <span className="text-sm text-xen-dark-300">Active</span>
                    </label>
                  </div>

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
                          Saving...
                        </>
                      ) : (
                        editingId ? 'Update Template' : 'Create Template'
                      )}
                    </Button>
                  </div>
                </form>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  )
}

