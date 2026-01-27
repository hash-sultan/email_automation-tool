import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FileText,
  Plus,
  Trash2,
  Edit2,
  RefreshCw,
  AlertTriangle,
  X,
  Copy,
  Eye,
} from 'lucide-react'
import Button from '../components/Button'
import Badge from '../components/Badge'
import { templatesApi, type Template } from '../api/client'

interface TemplateFormData {
  name: string
  subject: string
  body_html: string
  body_text: string
  template_type: 'initial' | 'followup'
  followup_step?: number
}

const defaultFormData: TemplateFormData = {
  name: '',
  subject: '',
  body_html: '',
  body_text: '',
  template_type: 'initial',
}

export default function Templates() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [showPreview, setShowPreview] = useState<Template | null>(null)
  const [formData, setFormData] = useState<TemplateFormData>(defaultFormData)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const fetchTemplates = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await templatesApi.list()
      setTemplates(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load templates')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTemplates()
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)

    try {
      if (editingId) {
        await templatesApi.update(editingId, formData)
      } else {
        await templatesApi.create(formData)
      }
      setShowModal(false)
      setFormData(defaultFormData)
      setEditingId(null)
      fetchTemplates()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save template')
    } finally {
      setSubmitting(false)
    }
  }

  const handleEdit = (template: Template) => {
    setFormData({
      name: template.name,
      subject: template.subject,
      body_html: template.body_html,
      body_text: template.body_text,
      template_type: template.template_type,
      followup_step: template.followup_step,
    })
    setEditingId(template.id)
    setShowModal(true)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this template?')) return

    try {
      await templatesApi.delete(id)
      fetchTemplates()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete template')
    }
  }

  const handleDuplicate = async (template: Template) => {
    try {
      await templatesApi.create({
        name: `${template.name} (Copy)`,
        subject: template.subject,
        body_html: template.body_html,
        body_text: template.body_text,
        template_type: template.template_type,
      })
      fetchTemplates()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to duplicate template')
    }
  }

  // Generate plain text from HTML
  const generatePlainText = (html: string) => {
    return html
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<\/p>/gi, '\n\n')
      .replace(/<[^>]+>/g, '')
      .trim()
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
            Email Templates
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-xen-dark-400 mt-1"
          >
            Create and manage your email templates
          </motion.p>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="ghost" onClick={fetchTemplates} disabled={loading}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          <Button onClick={() => { setEditingId(null); setFormData(defaultFormData); setShowModal(true); }}>
            <Plus className="w-4 h-4 mr-2" />
            New Template
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

      {/* Placeholders Info */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-4 rounded-xl bg-xen-dark-800/50 border border-xen-dark-700/50"
      >
        <h3 className="text-sm font-medium text-xen-dark-300 mb-2">Available Placeholders</h3>
        <div className="flex flex-wrap gap-2">
          {['{{name}}', '{{first_name}}', '{{last_name}}', '{{company}}', '{{industry}}', '{{title}}'].map((placeholder) => (
            <code key={placeholder} className="px-2 py-1 rounded bg-xen-dark-700 text-xen-red-400 text-xs">
              {placeholder}
            </code>
          ))}
        </div>
      </motion.div>

      {/* Templates Grid */}
      {loading && templates.length === 0 ? (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 text-xen-red-400 animate-spin" />
        </div>
      ) : templates.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass rounded-2xl p-12 border border-xen-dark-700/50 text-center"
        >
          <FileText className="w-16 h-16 mx-auto text-xen-dark-600 mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">No templates yet</h3>
          <p className="text-xen-dark-400 mb-6">
            Create your first email template to use in campaigns
          </p>
          <Button onClick={() => setShowModal(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Create First Template
          </Button>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {templates.map((template, index) => (
            <motion.div
              key={template.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="glass rounded-2xl p-6 border border-xen-dark-700/50 hover:border-xen-dark-600/50 transition-colors"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-xl bg-purple-500/20 flex items-center justify-center">
                    <FileText className="w-6 h-6 text-purple-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">{template.name}</h3>
                    <div className="mt-1">
                      <Badge 
                        variant={template.template_type === 'followup' ? 'info' : 'success'}
                      >
                        {template.template_type === 'followup' 
                          ? 'Follow-up Template' 
                          : 'Main Email Template'}
                      </Badge>
                    </div>
                  </div>
                </div>
                <Badge variant={template.is_active ? 'success' : 'warning'}>
                  {template.is_active ? 'Active' : 'Draft'}
                </Badge>
              </div>

              {/* Subject Preview */}
              <div className="mb-4 p-3 rounded-lg bg-xen-dark-800/50">
                <p className="text-xs text-xen-dark-500 mb-1">Subject</p>
                <p className="text-sm text-white font-medium truncate">{template.subject}</p>
              </div>

              {/* Body Preview */}
              <div className="mb-4 p-3 rounded-lg bg-xen-dark-800/50">
                <p className="text-xs text-xen-dark-500 mb-1">Preview</p>
                <p className="text-sm text-xen-dark-300 line-clamp-3">
                  {template.body_text || generatePlainText(template.body_html)}
                </p>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowPreview(template)}
                  className="flex-1"
                >
                  <Eye className="w-4 h-4 mr-1" />
                  Preview
                </Button>
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
                  onClick={() => handleDuplicate(template)}
                >
                  <Copy className="w-4 h-4" />
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
            </motion.div>
          ))}
        </div>
      )}

      {/* Template Editor Modal */}
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
              className="glass rounded-2xl p-6 border border-xen-dark-700/50 w-full max-w-2xl max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-white">
                  {editingId ? 'Edit Template' : 'Create Template'}
                </h2>
                <button
                  onClick={() => setShowModal(false)}
                  className="p-2 rounded-lg hover:bg-xen-dark-800 transition-colors"
                >
                  <X className="w-5 h-5 text-xen-dark-400" />
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                      Template Name *
                    </label>
                    <input
                      type="text"
                      required
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="w-full px-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white placeholder-xen-dark-500 focus:outline-none focus:border-xen-red-500"
                      placeholder="e.g., Initial Outreach"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                      Type
                    </label>
                    <select
                      value={formData.template_type}
                      onChange={(e) => setFormData({ ...formData, template_type: e.target.value as 'initial' | 'followup' })}
                      className="w-full px-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white focus:outline-none focus:border-xen-red-500"
                    >
                      <option value="initial">Main Email</option>
                      <option value="followup">Follow-up</option>
                    </select>
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
                    placeholder="e.g., Quick question about {{company}}"
                  />
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
                        body_text: generatePlainText(e.target.value)
                      })
                    }}
                    rows={8}
                    className="w-full px-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white placeholder-xen-dark-500 focus:outline-none focus:border-xen-red-500 font-mono text-sm"
                    placeholder="<p>Hi {{name}},</p><p>I noticed {{company}} is doing great work...</p>"
                  />
                  <p className="text-xs text-xen-dark-500 mt-1">
                    Use HTML tags for formatting. Placeholders like {'{{name}}'} will be replaced.
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                    Plain Text Version (auto-generated)
                  </label>
                  <textarea
                    value={formData.body_text}
                    onChange={(e) => setFormData({ ...formData, body_text: e.target.value })}
                    rows={4}
                    className="w-full px-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white placeholder-xen-dark-500 focus:outline-none focus:border-xen-red-500 font-mono text-sm"
                    placeholder="Plain text version..."
                  />
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
                        Saving...
                      </>
                    ) : (
                      <>
                        {editingId ? 'Update Template' : 'Create Template'}
                      </>
                    )}
                  </Button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Preview Modal */}
      <AnimatePresence>
        {showPreview && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setShowPreview(null)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="glass rounded-2xl p-6 border border-xen-dark-700/50 w-full max-w-2xl max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-white">Preview: {showPreview.name}</h2>
                <button
                  onClick={() => setShowPreview(null)}
                  className="p-2 rounded-lg hover:bg-xen-dark-800 transition-colors"
                >
                  <X className="w-5 h-5 text-xen-dark-400" />
                </button>
              </div>

              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-xen-dark-800/50 border border-xen-dark-700">
                  <p className="text-xs text-xen-dark-500 mb-1">Subject</p>
                  <p className="text-white font-medium">{showPreview.subject}</p>
                </div>

                <div className="p-4 rounded-xl bg-white">
                  <div 
                    className="prose prose-sm max-w-none text-gray-800"
                    dangerouslySetInnerHTML={{ __html: showPreview.body_html }}
                  />
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
