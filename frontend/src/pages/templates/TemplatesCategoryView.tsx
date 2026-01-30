import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FileText, Plus, Trash2, Edit2, Copy, Eye, ArrowLeft, X } from 'lucide-react'
import Button from '../../components/Button'
import Badge from '../../components/Badge'
import { templatesApi, type Template } from '../../api/client'

export default function TemplatesCategoryView() {
  const { categoryId } = useParams<{ categoryId: string }>()
  const navigate = useNavigate()
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showPreview, setShowPreview] = useState<Template | null>(null)

  // Helper to encode category names
  const encodeCategory = (cat: string) => cat.toLowerCase().replace(/\s+/g, '-')
  
  // Get category name from URL by finding matching template
  const categoryName = categoryId && templates.length > 0
    ? templates.find(t => encodeCategory(t.category) === categoryId.toLowerCase())?.category || categoryId.replace(/-/g, ' ')
    : categoryId?.replace(/-/g, ' ') || null

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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-enterprise-red"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30">
        <p className="text-red-400">{error}</p>
      </div>
    )
  }

  if (!categoryName) {
    return (
      <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30">
        <p className="text-red-400">Invalid category</p>
      </div>
    )
  }

  // Filter templates for this category (match by encoded name)
  const categoryTemplates = templates.filter(t => 
    encodeCategory(t.category) === categoryId?.toLowerCase()
  )

  const initialTemplates = categoryTemplates.filter(t => t.template_type === 'initial')
  const followupTemplates = categoryTemplates.filter(t => t.template_type === 'followup')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-gray-500 mb-1">Template Category</p>
          <h2 className="text-xl font-semibold text-gray-900">{categoryName}</h2>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/templates')}
          >
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back to Categories
          </Button>
          <Button
            size="sm"
            onClick={() => navigate(`/templates/categories/${categoryId}/new`)}
          >
            <Plus className="w-4 h-4 mr-1" />
            Add New Template
          </Button>
        </div>
      </div>

      {/* Initial templates */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-gray-700">Initial Templates</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {initialTemplates.map((template, index) => (
            <motion.div
              key={template.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="card p-6 hover:shadow-md transition-all"
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
              <div className="mb-4 p-3 rounded-lg bg-gray-50">
                <p className="text-xs text-gray-500 mb-1">Subject</p>
                <p className="text-sm text-gray-900 font-medium truncate">{template.subject}</p>
              </div>
              <div className="mb-4 p-3 rounded-lg bg-gray-50">
                <p className="text-xs text-gray-500 mb-1">Preview</p>
                <p className="text-sm text-gray-700 line-clamp-3">
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
                  onClick={() => navigate(`/templates/categories/${categoryId}/${template.id}/edit`)}
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
          {initialTemplates.length === 0 && (
            <p className="text-xs text-gray-500">
              No initial templates in this category yet. Click &quot;Add New Template&quot; to create one.
            </p>
          )}
        </div>
      </div>

      {/* Follow-up templates */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-gray-700">Follow-up Templates</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {followupTemplates.map((template, index) => (
            <motion.div
              key={template.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="card p-6 hover:shadow-md transition-all"
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
              <div className="mb-4 p-3 rounded-lg bg-gray-50">
                <p className="text-xs text-gray-500 mb-1">Subject</p>
                <p className="text-sm text-gray-900 font-medium truncate">{template.subject}</p>
              </div>
              <div className="mb-4 p-3 rounded-lg bg-gray-50">
                <p className="text-xs text-gray-500 mb-1">Preview</p>
                <p className="text-sm text-gray-700 line-clamp-3">
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
                  onClick={() => navigate(`/templates/categories/${categoryId}/${template.id}/edit`)}
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
          {followupTemplates.length === 0 && (
            <p className="text-xs text-gray-500">
              No follow-up templates in this category yet. Create one to enable rotating follow-ups.
            </p>
          )}
        </div>
      </div>

      {/* Preview Modal */}
      {showPreview && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="card p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-900">Preview: {showPreview.name}</h2>
              <button
                onClick={() => setShowPreview(null)}
                className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-gray-50 border border-gray-200">
                <p className="text-xs text-gray-500 mb-1">Subject</p>
                <p className="text-gray-900 font-medium">{showPreview.subject}</p>
              </div>
              <div className="p-4 rounded-xl bg-white">
                <div 
                  className="prose prose-sm max-w-none text-gray-800"
                  dangerouslySetInnerHTML={{ __html: showPreview.body_html }}
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
