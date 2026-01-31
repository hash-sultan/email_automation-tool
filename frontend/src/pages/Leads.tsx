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
  queued: { bg: 'bg-orange-500/20', text: 'text-orange-400' },
  contacted: { bg: 'bg-green-500/20', text: 'text-green-400' },
  replied: { bg: 'bg-green-500/20', text: 'text-green-400' },
  bounced: { bg: 'bg-enterprise-red/20', text: 'text-enterprise-red' },
  unsubscribed: { bg: 'bg-gray-500/20', text: 'text-gray-400' },
  converted: { bg: 'bg-purple-500/20', text: 'text-purple-400' },
}

// Map backend status to display name
const getStatusDisplayName = (status: string): string => {
  const statusMap: Record<string, string> = {
    new: 'new',
    queued: 'queued',
    contacted: 'sent',
    replied: 'replied',
    bounced: 'bounced',
    unsubscribed: 'unsubscribed',
    converted: 'converted',
  }
  return statusMap[status] || status
}

export default function Leads() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [page, setPage] = useState(1)
  const pageSize = 100
  const [totalPages, setTotalPages] = useState(1)
  const [totalLeads, setTotalLeads] = useState(0)
  const [stats, setStats] = useState({
    total: 0,
    new: 0,
    queued: 0,
    contacted: 0,
    replied: 0,
    bounced: 0,
    unsubscribed: 0,
    converted: 0,
  })
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
      const [leadsResponse, campaignsData, statsData] = await Promise.all([
        leadsApi.list(selectedCampaign, page, pageSize),
        campaignsApi.list(),
        leadsApi.stats(selectedCampaign), // Get accurate stats from API
      ])
      setLeads(leadsResponse.items)
      setTotalLeads(leadsResponse.total)
      setTotalPages(leadsResponse.pages || 1)
      setStats(statsData)
      setCampaigns(campaignsData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [selectedCampaign, page])

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

  // Stats are now fetched from API, so they're accurate

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
            Leads
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-gray-500 mt-1"
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
          { label: 'Total', value: stats.total, color: 'text-gray-900' },
          { label: 'New', value: stats.new, color: 'text-enterprise-red' },
          { label: 'Queued', value: stats.queued, color: 'text-orange-600' },
          { label: 'Sent', value: stats.contacted, color: 'text-green-600' },
          { label: 'Replied', value: stats.replied, color: 'text-green-600' },
          { label: 'Bounced', value: stats.bounced, color: 'text-enterprise-red' },
        ].map((stat) => (
          <div key={stat.label} className="card p-4">
            <p className="text-xs text-gray-500">{stat.label}</p>
            <p className={`text-2xl font-semibold ${stat.color}`}>{stat.value}</p>
          </div>
        ))}
      </motion.div>

      {/* Messages */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-xl bg-enterprise-red/10 border border-enterprise-red/30 flex items-center gap-3"
        >
          <AlertTriangle className="w-5 h-5 text-enterprise-red" />
          <p className="text-enterprise-red">{error}</p>
          <button onClick={() => setError(null)} className="ml-auto">
            <X className="w-4 h-4 text-enterprise-red" />
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
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search leads..."
            className="input pl-10"
          />
        </div>

        {/* Delete all leads button - left of status filter */}
        {selectedCampaign && stats.total > 0 && (
          <Button
            variant="ghost"
            onClick={async () => {
              const campaignName = campaigns.find(c => c.id === selectedCampaign)?.name || 'this campaign'
              if (
                !confirm(
                  `Are you sure you want to delete ALL ${stats.total} leads in "${campaignName}"? This cannot be undone.`
                )
              ) {
                return
              }
              try {
                setLoading(true)
                await leadsApi.deleteByCampaign(selectedCampaign)
                setSuccess(`All ${stats.total} leads for "${campaignName}" have been deleted.`)
                // Reset to first page and refresh
                setPage(1)
                fetchData()
                setTimeout(() => setSuccess(null), 4000)
              } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to delete leads')
              } finally {
                setLoading(false)
              }
            }}
            className="text-enterprise-red hover:text-enterprise-red/80 hover:bg-enterprise-red/10 border border-enterprise-red/30 px-3 py-2 text-xs whitespace-nowrap"
            disabled={loading}
          >
            <Trash2 className="w-3 h-3 mr-1" />
            Delete All ({stats.total})
          </Button>
        )}

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="input"
        >
          <option value="all">All Status</option>
          <option value="new">New</option>
          <option value="queued">Queued</option>
          <option value="contacted">Sent</option>
          <option value="replied">Replied</option>
          <option value="bounced">Bounced</option>
          <option value="unsubscribed">Unsubscribed</option>
        </select>

        <select
          value={selectedCampaign || ''}
          onChange={(e) => setSelectedCampaign(e.target.value ? parseInt(e.target.value) : undefined)}
          className="input"
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
          <RefreshCw className="w-8 h-8 text-enterprise-red animate-spin" />
        </div>
      ) : filteredLeads.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="card p-12 text-center"
        >
          <Users className="w-16 h-16 mx-auto text-gray-400 mb-4" />
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            {leads.length === 0 ? 'No leads yet' : 'No matching leads'}
          </h3>
          <p className="text-gray-500 mb-6">
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
          className="card overflow-hidden"
        >
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="table-header">
                  <th className="text-left px-6 py-4">Email</th>
                  <th className="text-left px-6 py-4">Name</th>
                  <th className="text-left px-6 py-4">Company</th>
                  <th className="text-left px-6 py-4">Status</th>
                  <th className="text-left px-6 py-4">Added</th>
                  <th className="text-right px-6 py-4">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredLeads.map((lead, index) => (
                  <motion.tr
                    key={lead.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.02 }}
                    className="table-row"
                  >
                    <td className="table-cell">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-enterprise-red/10 flex items-center justify-center">
                          <Mail className="w-4 h-4 text-enterprise-red" />
                        </div>
                        <span className="text-gray-900 font-medium">{lead.email}</span>
                      </div>
                    </td>
                    <td className="table-cell">{lead.name || '-'}</td>
                    <td className="table-cell">{lead.company || '-'}</td>
                    <td className="table-cell">
                      <span className={`px-2.5 py-1 rounded-md text-xs font-medium ${statusColors[lead.status]?.bg || 'bg-gray-500/20'} ${statusColors[lead.status]?.text || 'text-gray-400'}`}>
                        {getStatusDisplayName(lead.status)}
                      </span>
                    </td>
                    <td className="table-cell text-gray-500">
                      {new Date(lead.created_at).toLocaleDateString()}
                    </td>
                    <td className="table-cell text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(lead.id)}
                        className="text-enterprise-red hover:text-enterprise-red/80"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
          
          <div className="p-4 border-t border-gray-200 text-sm text-gray-600 flex items-center justify-between gap-4">
            <div>
              Showing {filteredLeads.length} of {totalLeads} leads
              {stats.total > totalLeads && ` (${stats.total} total${selectedCampaign ? ' in this campaign' : ''})`}
              {totalPages > 1 && ` • Page ${page} of ${totalPages}`}
            </div>
            {totalPages > 1 && (
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  Prev
                </Button>
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                  <button
                    key={p}
                    onClick={() => setPage(p)}
                    className={`px-2 py-1 rounded-lg text-xs font-medium ${
                      p === page
                        ? 'bg-enterprise-red text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {p}
                  </button>
                ))}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                >
                  Next
                </Button>
              </div>
            )}
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
            className="modal-overlay"
            onClick={() => setShowModal(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="modal-content p-8 w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-8">
                <h2 className="heading-2">Add Lead</h2>
                <button
                  onClick={() => setShowModal(false)}
                  className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <X className="w-5 h-5 text-gray-500" />
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2.5">
                    Email *
                  </label>
                  <input
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="input"
                    placeholder="email@example.com"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2.5">
                    Name
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="input"
                    placeholder="John Smith"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Company
                  </label>
                  <input
                    type="text"
                    value={formData.company}
                    onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                    className="input"
                    placeholder="Acme Corp"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Industry
                    </label>
                    <input
                      type="text"
                      value={formData.industry}
                      onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
                      className="input"
                      placeholder="Technology"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Title
                    </label>
                    <input
                      type="text"
                      value={formData.title}
                      onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                      className="input"
                      placeholder="CEO"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Campaign (optional)
                  </label>
                  <select
                    value={formData.campaign_id || ''}
                    onChange={(e) => setFormData({ ...formData, campaign_id: e.target.value ? parseInt(e.target.value) : undefined })}
                    className="input"
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
            className="modal-overlay"
            onClick={() => setShowImportModal(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="modal-content p-8 w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-8">
                <h2 className="heading-2">Import Leads from CSV</h2>
                <button
                  onClick={() => setShowImportModal(false)}
                  className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <X className="w-5 h-5 text-gray-500" />
                </button>
              </div>

              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-gray-50 border border-gray-200">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">CSV Format</h4>
                  <p className="text-xs text-gray-600 mb-2">
                    Your CSV should have these columns:
                  </p>
                  <code className="text-xs text-enterprise-red block">
                    email,name,company,industry,title
                  </code>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Assign to Campaign (optional)
                  </label>
                  <select
                    value={selectedCampaign || ''}
                    onChange={(e) => setSelectedCampaign(e.target.value ? parseInt(e.target.value) : undefined)}
                    className="input"
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
