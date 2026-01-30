import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { X, RefreshCw } from 'lucide-react'
import Button from '../../components/Button'
import { templatesApi } from '../../api/client'

interface TemplateFormData {
  name: string
  subject: string
  body_html: string
  body_text: string
  template_type: 'initial' | 'followup'
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

export default function TemplateForm() {
  const { categoryId, templateId } = useParams<{ categoryId?: string; templateId?: string }>()
  const navigate = useNavigate()
  const [formData, setFormData] = useState<TemplateFormData>(defaultFormData)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  // Decode category name from URL if present
  const categoryName = categoryId ? decodeURIComponent(categoryId.replace(/-/g, ' ')) : null

  // If we're editing, fetch the template
  useEffect(() => {
    if (templateId) {
      setLoading(true)
      templatesApi.get(parseInt(templateId))
        .then((template) => {
          setFormData({
            name: template.name,
            subject: template.subject,
            body_html: template.body_html,
            body_text: template.body_text,
            template_type: template.template_type,
            category: template.category || 'General',
          })
        })
        .catch((err) => {
          setError(err instanceof Error ? err.message : 'Failed to load template')
        })
        .finally(() => {
          setLoading(false)
        })
    } else if (categoryName) {
      // If creating new template in a category, pre-fill category
      setFormData(prev => ({ ...prev, category: categoryName }))
    }
  }, [templateId, categoryId, categoryName])

  // Generate plain text from HTML
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
      if (templateId) {
        await templatesApi.update(parseInt(templateId), formData)
        // Navigate back to category view
        if (categoryId) {
          navigate(`/templates/categories/${categoryId}`)
        } else {
          navigate('/templates')
        }
      } else {
        await templatesApi.create(formData)
        // Navigate back to category view if we have categoryId, otherwise to list
        if (categoryId) {
          navigate(`/templates/categories/${categoryId}`)
        } else {
          navigate('/templates')
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save template')
    } finally {
      setSubmitting(false)
    }
  }

  // Determine back navigation path
  const getBackPath = () => {
    if (templateId && categoryId) {
      return `/templates/categories/${categoryId}`
    } else if (categoryId) {
      return `/templates/categories/${categoryId}`
    }
    return '/templates'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-enterprise-red"></div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
            className="card p-6"
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900">
            {templateId ? 'Edit Template' : 'Create Template'}
          </h2>
          <button
            onClick={() => navigate(getBackPath())}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 mb-4">
            <p className="text-red-400">{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
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
              <label className="block text-sm font-medium text-gray-700 mb-2">
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
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Category *
            </label>
            <input
              type="text"
              required
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              disabled={!!categoryId} // Disable if category is set from URL
              className="input disabled:opacity-50 disabled:cursor-not-allowed"
              placeholder="e.g., Car Parts Companies, Real Estate, SaaS"
            />
            {categoryId && (
              <p className="text-xs text-gray-500 mt-1">
                Category is set from the URL and cannot be changed
              </p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
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
            <label className="block text-sm font-medium text-gray-700 mb-2">
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
              className="input font-mono text-sm"
              placeholder="<p>Hi {{name}},</p><p>I noticed {{company}} is doing great work...</p>"
            />
            <p className="text-xs text-xen-dark-500 mt-1">
              Use HTML tags for formatting. Placeholders like {'{{name}}'} will be replaced.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Plain Text Version (auto-generated)
            </label>
            <textarea
              value={formData.body_text}
              onChange={(e) => setFormData({ ...formData, body_text: e.target.value })}
              rows={4}
              className="input font-mono text-sm"
              placeholder="Plain text version..."
            />
          </div>

          {/* Submit */}
          <div className="flex items-center gap-3 pt-4">
            <Button
              type="button"
              variant="ghost"
              onClick={() => navigate(getBackPath())}
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
                  {templateId ? 'Update Template' : 'Create Template'}
                </>
              )}
            </Button>
          </div>
        </form>
      </motion.div>
    </div>
  )
}
