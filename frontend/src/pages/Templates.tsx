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
  category: string
}

const defaultFormData: TemplateFormData = {
  name: '',
  subject: '',
  body_html: '',
  body_text: '',
  template_type: 'initial',
  category: '',
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
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)

  // Derive template categories from existing templates
  const templateCategories = Array.from(new Set(templates.map(t => t.category))).sort()

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
      category: template.category || 'General',
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
        category: template.category || 'General',
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
            className="text-3xl font-semibold text-gray-900"
          >
            Email Templates
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-gray-500 mt-1"
          >
            Create and manage your email templates
          </motion.p>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="ghost" onClick={fetchTemplates} disabled={loading}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          {/* When no categories/templates exist, the primary CTA is shown in the empty state card below.
              Hide the generic New Template button in that case to reduce confusion. */}
          {templateCategories.length > 0 && (
            <Button
              onClick={() => {
                setEditingId(null)
                setFormData(defaultFormData)
                setShowModal(true)
              }}
            >
              <Plus className="w-4 h-4 mr-2" />
              New Template
            </Button>
          )}
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
        className="p-4 rounded-xl bg-gray-50 border border-gray-200"
        >
        <h3 className="text-sm font-medium text-gray-700 mb-2">Available Placeholders</h3>
        <div className="flex flex-wrap gap-2">
          {['{{name}}', '{{first_name}}', '{{last_name}}', '{{company}}', '{{industry}}', '{{title}}'].map((placeholder) => (
            <code key={placeholder} className="px-2 py-1 rounded bg-gray-200 text-enterprise-red text-xs">
              {placeholder}
            </code>
          ))}
        </div>
      </motion.div>

      {/* Category-first Templates UX */}
      {loading && templates.length === 0 ? (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 text-enterprise-red animate-spin" />
        </div>
      ) : (
        <>
          {/* If no categories yet: prompt to create first category */}
          {templateCategories.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="card p-12 text-center"
            >
              <FileText className="w-16 h-16 mx-auto text-gray-400 mb-4" />
              <h3 className="text-xl font-semibold text-gray-900 mb-2">No template categories yet</h3>
              <p className="text-gray-500 mb-6">
                Create your first template category and template to use in campaigns
              </p>
              <Button
                onClick={() => {
                  setSelectedCategory(null)
                  setEditingId(null)
                  setFormData(defaultFormData)
                  setShowModal(true)
                }}
              >
                <Plus className="w-4 h-4 mr-2" />
                Create First Template Category
              </Button>
            </motion.div>
          ) : selectedCategory === null ? (
            // Category list view
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-4"
            >
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-gray-700">Template Categories</h3>
                <Button
                  size="sm"
                  onClick={() => {
                    setEditingId(null)
                    setFormData(defaultFormData)
                    setShowModal(true)
                  }}
                >
                  <Plus className="w-4 h-4 mr-1" />
                  New Category & Template
                </Button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {templateCategories.map((category, index) => {
                  const inCategory = templates.filter(t => t.category === category)
                  const initialCount = inCategory.filter(t => t.template_type === 'initial').length
                  const followupCount = inCategory.filter(t => t.template_type === 'followup').length

                  return (
                    <motion.div
                      key={category}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="card p-5 hover:shadow-md transition-all cursor-pointer"
                      onClick={() => setSelectedCategory(category)}
                    >
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-xl bg-purple-500/20 flex items-center justify-center">
                            <FileText className="w-5 h-5 text-purple-400" />
                          </div>
                          <div>
                            <h3 className="font-semibold text-gray-900">{category}</h3>
                            <p className="text-xs text-gray-500">
                              Click to manage templates in this category
                            </p>
                          </div>
                        </div>
                        <Badge variant="info">{inCategory.length} templates</Badge>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-xen-dark-400">
                        <span>Initial: {initialCount}</span>
                        <span>•</span>
                        <span>Follow-ups: {followupCount}</span>
                      </div>
                    </motion.div>
                  )
                })}
              </div>
            </motion.div>
          ) : (
            // Category detail view
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-6"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-xen-dark-500 mb-1">Template Category</p>
                  <h2 className="text-xl font-semibold text-gray-900">{selectedCategory}</h2>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setSelectedCategory(null)}
                  >
                    Back to Categories
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => {
                      setEditingId(null)
                      setFormData({
                        ...defaultFormData,
                        category: selectedCategory,
                      })
                      setShowModal(true)
                    }}
                  >
                    <Plus className="w-4 h-4 mr-1" />
                    Add New Template
                  </Button>
                </div>
              </div>

              {/* Initial templates */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-xen-dark-300">Initial Templates</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {templates
                    .filter(t => t.category === selectedCategory && t.template_type === 'initial')
                    .map((template, index) => (
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
                              <h3 className="font-semibold text-gray-900">{template.name}</h3>
                              <div className="mt-1">
                                <Badge variant="success">
                                  Main Email Template
                                </Badge>
                              </div>
                            </div>
                          </div>
                          <Badge variant={template.is_active ? 'success' : 'warning'}>
                            {template.is_active ? 'Active' : 'Draft'}
                          </Badge>
                        </div>
                        <div className="mb-4 p-3 rounded-lg bg-xen-dark-800/50">
                          <p className="text-xs text-xen-dark-500 mb-1">Subject</p>
                          <p className="text-sm text-gray-900 font-medium truncate">{template.subject}</p>
                        </div>
                        <div className="mb-4 p-3 rounded-lg bg-xen-dark-800/50">
                          <p className="text-xs text-xen-dark-500 mb-1">Preview</p>
                          <p className="text-sm text-xen-dark-300 line-clamp-3">
                            {template.body_text || generatePlainText(template.body_html)}
                          </p>
                        </div>
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
                  {templates.filter(t => t.category === selectedCategory && t.template_type === 'initial').length === 0 && (
                    <p className="text-xs text-xen-dark-500">
                      No initial templates in this category yet. Click &quot;Add New Template&quot; to create one.
                    </p>
                  )}
                </div>
              </div>

              {/* Follow-up templates */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-xen-dark-300">Follow-up Templates</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {templates
                    .filter(t => t.category === selectedCategory && t.template_type === 'followup')
                    .map((template, index) => (
                      <motion.div
                        key={template.id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.05 }}
                        className="glass rounded-2xl p-6 border border-xen-dark-700/50 hover:border-xen-dark-600/50 transition-colors"
                      >
                        <div className="flex items-start justify-between mb-4">
                          <div className="flex items-center gap-3">
                            <div className="w-12 h-12 rounded-xl bg-blue-500/20 flex items-center justify-center">
                              <FileText className="w-6 h-6 text-blue-400" />
                            </div>
                            <div>
                              <h3 className="font-semibold text-gray-900">{template.name}</h3>
                              <div className="mt-1">
                                <Badge variant="info">
                                  Follow-up Template
                                </Badge>
                              </div>
                            </div>
                          </div>
                          <Badge variant={template.is_active ? 'success' : 'warning'}>
                            {template.is_active ? 'Active' : 'Draft'}
                          </Badge>
                        </div>
                        <div className="mb-4 p-3 rounded-lg bg-xen-dark-800/50">
                          <p className="text-xs text-xen-dark-500 mb-1">Subject</p>
                          <p className="text-sm text-gray-900 font-medium truncate">{template.subject}</p>
                        </div>
                        <div className="mb-4 p-3 rounded-lg bg-xen-dark-800/50">
                          <p className="text-xs text-xen-dark-500 mb-1">Preview</p>
                          <p className="text-sm text-xen-dark-300 line-clamp-3">
                            {template.body_text || generatePlainText(template.body_html)}
                          </p>
                        </div>
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
                  {templates.filter(t => t.category === selectedCategory && t.template_type === 'followup').length === 0 && (
                    <p className="text-xs text-xen-dark-500">
                      No follow-up templates in this category yet. Create one to enable rotating follow-ups.
                    </p>
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </>
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
                <h2 className="text-xl font-semibold text-gray-900">
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
                      className="input"
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
                      className="input"
                    >
                      <option value="initial">Main Email</option>
                      <option value="followup">Follow-up</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                    Category *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className="input"
                    placeholder="e.g., Car Parts Companies, Real Estate, SaaS"
                  />
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
                    className="input"
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
                <h2 className="text-xl font-semibold text-gray-900">Preview: {showPreview.name}</h2>
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
                  <p className="text-gray-900 font-medium">{showPreview.subject}</p>
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
