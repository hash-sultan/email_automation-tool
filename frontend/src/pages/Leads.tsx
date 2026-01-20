import { useEffect, useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Users,
  Plus,
  Trash2,
  Upload,
  RefreshCw,
  AlertTriangle,
  X,
  Search,
  CheckCircle,
  Mail,
} from 'lucide-react'
import Button from '../components/Button'
import { leadsApi, campaignsApi, type Lead, type Campaign } from '../api/client'

interface LeadFormData {
  email: string
  name: string
  company: string
  industry: string
  title: string
  campaign_id?: number
}

const defaultFormData: LeadFormData = {
  email: '',
  name: '',
  company: '',
  industry: '',
  title: '',
}

const statusColors: Record<string, { bg: string; text: string }> = {
  new: { bg: 'bg-blue-500/20', text: 'text-blue-400' },
  contacted: { bg: 'bg-yellow-500/20', text: 'text-yellow-400' },
  replied: { bg: 'bg-green-500/20', text: 'text-green-400' },
  bounced: { bg: 'bg-red-500/20', text: 'text-red-400' },
  unsubscribed: { bg: 'bg-gray-500/20', text: 'text-gray-400' },
  converted: { bg: 'bg-purple-500/20', text: 'text-purple-400' },
}

export default function Leads() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [showImportModal, setShowImportModal] = useState(false)
  const [formData, setFormData] = useState<LeadFormData>(defaultFormData)
  const [submitting, setSubmitting] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [selectedCampaign, setSelectedCampaign] = useState<number | undefined>(undefined)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [leadsData, campaignsData] = await Promise.all([
        leadsApi.list(selectedCampaign),
        campaignsApi.list(),
      ])
      setLeads(leadsData)
      setCampaigns(campaignsData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [selectedCampaign])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)

    try {
      await leadsApi.create(formData)
      setShowModal(false)
      setFormData(defaultFormData)
      setSuccess('Lead added successfully!')
      fetchData()
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create lead')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this lead?')) return

    try {
      await leadsApi.delete(id)
      fetchData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete lead')
    }
  }

  const handleFileImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setSubmitting(true)
    setError(null)

    try {
      const result = await leadsApi.import(file, selectedCampaign)
      setShowImportModal(false)
      setSuccess(`Imported ${result.success} leads! (${result.duplicates} duplicates, ${result.failed} failed)`)
      fetchData()
      setTimeout(() => setSuccess(null), 5000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed')
    } finally {
      setSubmitting(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  // Filter leads
  const filteredLeads = leads.filter(lead => {
    const matchesSearch = 
      lead.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (lead.name?.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (lead.company?.toLowerCase().includes(searchQuery.toLowerCase()))
    
    const matchesStatus = statusFilter === 'all' || lead.status === statusFilter
    
    return matchesSearch && matchesStatus
  })

  // Stats
  const stats = {
    total: leads.length,
    new: leads.filter(l => l.status === 'new').length,
    contacted: leads.filter(l => l.status === 'contacted').length,
    replied: leads.filter(l => l.status === 'replied').length,
    bounced: leads.filter(l => l.status === 'bounced').length,
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
            Leads
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-xen-dark-400 mt-1"
          >
            Manage your contacts and import leads
          </motion.p>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="ghost" onClick={fetchData} disabled={loading}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          <Button variant="secondary" onClick={() => setShowImportModal(true)}>
            <Upload className="w-4 h-4 mr-2" />
            Import CSV
          </Button>
          <Button onClick={() => setShowModal(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Add Lead
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
          { label: 'Total', value: stats.total, color: 'text-white' },
          { label: 'New', value: stats.new, color: 'text-blue-400' },
          { label: 'Contacted', value: stats.contacted, color: 'text-yellow-400' },
          { label: 'Replied', value: stats.replied, color: 'text-green-400' },
          { label: 'Bounced', value: stats.bounced, color: 'text-red-400' },
        ].map((stat) => (
          <div key={stat.label} className="glass rounded-xl p-4 border border-xen-dark-700/50">
            <p className="text-xs text-xen-dark-500">{stat.label}</p>
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

      {/* Filters */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex-1 min-w-[200px] relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-xen-dark-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search leads..."
            className="w-full pl-10 pr-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white placeholder-xen-dark-500 focus:outline-none focus:border-xen-red-500"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white focus:outline-none focus:border-xen-red-500"
        >
          <option value="all">All Status</option>
          <option value="new">New</option>
          <option value="contacted">Contacted</option>
          <option value="replied">Replied</option>
          <option value="bounced">Bounced</option>
          <option value="unsubscribed">Unsubscribed</option>
        </select>

        <select
          value={selectedCampaign || ''}
          onChange={(e) => setSelectedCampaign(e.target.value ? parseInt(e.target.value) : undefined)}
          className="px-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white focus:outline-none focus:border-xen-red-500"
        >
          <option value="">All Campaigns</option>
          {campaigns.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>

      {/* Leads Table */}
      {loading && leads.length === 0 ? (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 text-xen-red-400 animate-spin" />
        </div>
      ) : filteredLeads.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass rounded-2xl p-12 border border-xen-dark-700/50 text-center"
        >
          <Users className="w-16 h-16 mx-auto text-xen-dark-600 mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">
            {leads.length === 0 ? 'No leads yet' : 'No matching leads'}
          </h3>
          <p className="text-xen-dark-400 mb-6">
            {leads.length === 0 
              ? 'Import a CSV file or add leads manually to get started'
              : 'Try adjusting your search or filters'}
          </p>
          {leads.length === 0 && (
            <div className="flex items-center justify-center gap-3">
              <Button variant="secondary" onClick={() => setShowImportModal(true)}>
                <Upload className="w-4 h-4 mr-2" />
                Import CSV
              </Button>
              <Button onClick={() => setShowModal(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Add Lead
              </Button>
            </div>
          )}
        </motion.div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass rounded-2xl border border-xen-dark-700/50 overflow-hidden"
        >
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-xen-dark-700/50">
                  <th className="text-left p-4 text-xen-dark-400 font-medium">Email</th>
                  <th className="text-left p-4 text-xen-dark-400 font-medium">Name</th>
                  <th className="text-left p-4 text-xen-dark-400 font-medium">Company</th>
                  <th className="text-left p-4 text-xen-dark-400 font-medium">Status</th>
                  <th className="text-left p-4 text-xen-dark-400 font-medium">Added</th>
                  <th className="text-right p-4 text-xen-dark-400 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredLeads.map((lead, index) => (
                  <motion.tr
                    key={lead.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.02 }}
                    className="border-b border-xen-dark-700/30 hover:bg-xen-dark-800/30 transition-colors"
                  >
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-xen-red-500/20 flex items-center justify-center">
                          <Mail className="w-4 h-4 text-xen-red-400" />
                        </div>
                        <span className="text-white">{lead.email}</span>
                      </div>
                    </td>
                    <td className="p-4 text-xen-dark-300">{lead.name || '-'}</td>
                    <td className="p-4 text-xen-dark-300">{lead.company || '-'}</td>
                    <td className="p-4">
                      <span className={`px-2 py-1 rounded-lg text-xs font-medium ${statusColors[lead.status]?.bg} ${statusColors[lead.status]?.text}`}>
                        {lead.status}
                      </span>
                    </td>
                    <td className="p-4 text-xen-dark-400 text-sm">
                      {new Date(lead.created_at).toLocaleDateString()}
                    </td>
                    <td className="p-4 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(lead.id)}
                        className="text-red-400 hover:text-red-300"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
          
          <div className="p-4 border-t border-xen-dark-700/50 text-sm text-xen-dark-400">
            Showing {filteredLeads.length} of {leads.length} leads
          </div>
        </motion.div>
      )}

      {/* Add Lead Modal */}
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
              className="glass rounded-2xl p-6 border border-xen-dark-700/50 w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-white">Add Lead</h2>
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
                    Email *
                  </label>
                  <input
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white placeholder-xen-dark-500 focus:outline-none focus:border-xen-red-500"
                    placeholder="email@example.com"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                    Name
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
                    Company
                  </label>
                  <input
                    type="text"
                    value={formData.company}
                    onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white placeholder-xen-dark-500 focus:outline-none focus:border-xen-red-500"
                    placeholder="Acme Corp"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                      Industry
                    </label>
                    <input
                      type="text"
                      value={formData.industry}
                      onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
                      className="w-full px-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white placeholder-xen-dark-500 focus:outline-none focus:border-xen-red-500"
                      placeholder="Technology"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                      Title
                    </label>
                    <input
                      type="text"
                      value={formData.title}
                      onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                      className="w-full px-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white placeholder-xen-dark-500 focus:outline-none focus:border-xen-red-500"
                      placeholder="CEO"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                    Campaign (optional)
                  </label>
                  <select
                    value={formData.campaign_id || ''}
                    onChange={(e) => setFormData({ ...formData, campaign_id: e.target.value ? parseInt(e.target.value) : undefined })}
                    className="w-full px-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white focus:outline-none focus:border-xen-red-500"
                  >
                    <option value="">No campaign</option>
                    {campaigns.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
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
                        Adding...
                      </>
                    ) : (
                      'Add Lead'
                    )}
                  </Button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Import CSV Modal */}
      <AnimatePresence>
        {showImportModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setShowImportModal(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="glass rounded-2xl p-6 border border-xen-dark-700/50 w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-white">Import Leads from CSV</h2>
                <button
                  onClick={() => setShowImportModal(false)}
                  className="p-2 rounded-lg hover:bg-xen-dark-800 transition-colors"
                >
                  <X className="w-5 h-5 text-xen-dark-400" />
                </button>
              </div>

              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-xen-dark-800/50 border border-xen-dark-700">
                  <h4 className="text-sm font-medium text-xen-dark-300 mb-2">CSV Format</h4>
                  <p className="text-xs text-xen-dark-400 mb-2">
                    Your CSV should have these columns:
                  </p>
                  <code className="text-xs text-xen-red-400 block">
                    email,name,company,industry,title
                  </code>
                </div>

                <div>
                  <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                    Assign to Campaign (optional)
                  </label>
                  <select
                    value={selectedCampaign || ''}
                    onChange={(e) => setSelectedCampaign(e.target.value ? parseInt(e.target.value) : undefined)}
                    className="w-full px-4 py-3 rounded-xl bg-xen-dark-800 border border-xen-dark-700 text-white focus:outline-none focus:border-xen-red-500"
                  >
                    <option value="">No campaign</option>
                    {campaigns.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv"
                  onChange={handleFileImport}
                  className="hidden"
                />

                <Button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={submitting}
                  className="w-full"
                >
                  {submitting ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      Importing...
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4 mr-2" />
                      Select CSV File
                    </>
                  )}
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
