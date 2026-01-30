import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { FileText, Plus, Trash2 } from 'lucide-react'
import Button from '../../components/Button'
import Badge from '../../components/Badge'
import { templatesApi, type Template } from '../../api/client'
import toast from 'react-hot-toast'

export default function TemplatesCategoryList() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  // Derive template categories from existing templates
  // Group by case-insensitive category name, but preserve the original case for display
  const categoryMap = new Map<string, string>() // lowercase -> original case
  templates.forEach(t => {
    const lower = t.category.toLowerCase()
    if (!categoryMap.has(lower)) {
      // Use the first occurrence's case as the canonical version
      categoryMap.set(lower, t.category)
    }
  })
  
  // Get unique categories (case-insensitive) sorted
  const templateCategories = Array.from(categoryMap.values()).sort((a, b) => 
    a.toLowerCase().localeCompare(b.toLowerCase())
  )

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

  // Helper to encode category name for URL
  const encodeCategory = (category: string) => encodeURIComponent(category.toLowerCase().replace(/\s+/g, '-'))

  const handleDeleteCategory = async (category: string, e?: React.MouseEvent) => {
    e?.stopPropagation() // Prevent card click
    
    // Get all templates in this category (case-insensitive)
    const inCategory = templates.filter(t => t.category.toLowerCase() === category.toLowerCase())
    const templateCount = inCategory.length
    
    if (!confirm(
      `Are you sure you want to delete the category "${category}"?\n\n` +
      `This will delete ${templateCount} template(s) in this category.\n\n` +
      `This action cannot be undone.`
    )) {
      return
    }

    try {
      const result = await templatesApi.deleteCategory(category)
      toast.success(`Category "${category}" deleted (${result.templates_deleted} template(s) removed)`)
      fetchTemplates() // Refresh the list
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to delete category'
      toast.error(errorMsg)
      setError(errorMsg)
    }
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
      <div className="p-4 rounded-xl bg-enterprise-red/10 border border-enterprise-red/30">
        <p className="text-enterprise-red">{error}</p>
      </div>
    )
  }

  // If no categories yet: prompt to create first category
  if (templateCategories.length === 0) {
    return (
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
          onClick={() => navigate('/templates/categories/new')}
        >
          <Plus className="w-4 h-4 mr-2" />
          Create First Template Category
        </Button>
      </motion.div>
    )
  }

  // Category list view
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">Template Categories</h3>
        <Button
          size="sm"
          onClick={() => navigate('/templates/categories/new')}
        >
          <Plus className="w-4 h-4 mr-1" />
          New Category & Template
        </Button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {templateCategories.map((category, index) => {
          // Filter templates by case-insensitive category match
          const inCategory = templates.filter(t => t.category.toLowerCase() === category.toLowerCase())
          const initialCount = inCategory.filter(t => t.template_type === 'initial').length
          const followupCount = inCategory.filter(t => t.template_type === 'followup').length

          return (
            <motion.div
              key={category}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="card p-5 hover:shadow-md transition-all cursor-pointer relative group"
              onClick={() => navigate(`/templates/categories/${encodeCategory(category)}`)}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <div className="w-10 h-10 rounded-xl bg-purple-500/20 flex items-center justify-center flex-shrink-0">
                    <FileText className="w-5 h-5 text-purple-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-gray-900 truncate">{category}</h3>
                    <p className="text-xs text-gray-500">
                      Click to manage templates in this category
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <Badge variant="info">{inCategory.length} templates</Badge>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e?: React.MouseEvent<HTMLButtonElement>) => handleDeleteCategory(category, e)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity text-red-400 hover:text-red-300 hover:bg-red-500/10"
                    title="Delete category"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
              <div className="flex items-center gap-3 text-xs text-gray-600">
                <span>Initial: {initialCount}</span>
                <span>•</span>
                <span>Follow-ups: {followupCount}</span>
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
