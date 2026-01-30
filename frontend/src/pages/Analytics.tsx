import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Send,
  MessageSquare,
  AlertTriangle,
  Users,
  RefreshCw,
  Calendar,
} from 'lucide-react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import { dashboardApi, campaignsApi, analyticsApi, type DashboardStats, type Campaign } from '../api/client'

const COLORS = ['#ef4444', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6']

export default function Analytics() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [selectedCampaignId, setSelectedCampaignId] = useState<number | null>(null)
  const [campaignAnalytics, setCampaignAnalytics] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [campaignLoading, setCampaignLoading] = useState(false)
  const [, setError] = useState<string | null>(null)

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [data, campaignsData] = await Promise.all([
        dashboardApi.getStats(),
        campaignsApi.list(),
      ])
      setStats(data)
      setCampaigns(campaignsData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics')
    } finally {
      setLoading(false)
    }
  }

  const fetchCampaignAnalytics = async (campaignId: number) => {
    setCampaignLoading(true)
    try {
      const data = await analyticsApi.campaign(campaignId)
      setCampaignAnalytics(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load campaign analytics')
      setCampaignAnalytics(null)
    } finally {
      setCampaignLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  useEffect(() => {
    if (selectedCampaignId) {
      fetchCampaignAnalytics(selectedCampaignId)
    } else {
      setCampaignAnalytics(null)
    }
  }, [selectedCampaignId])

  // Transform data for charts
  const chartData = stats?.emails_by_day?.map(day => ({
    name: new Date(day.date).toLocaleDateString('en-US', { weekday: 'short' }),
    sent: day.sent,
    replies: day.replies,
    bounces: day.bounces,
  })) || []

  // Calculate metrics
  const replyRate = stats?.total_emails_sent 
    ? ((stats.total_replies / stats.total_emails_sent) * 100).toFixed(1)
    : '0.0'
  
  const bounceRate = stats?.overall_bounce_rate 
    ? (stats.overall_bounce_rate * 100).toFixed(1)
    : '0.0'

  // Pie chart data
  const pieData = [
    { name: 'Sent', value: stats?.total_emails_sent || 0 },
    { name: 'Replies', value: stats?.total_replies || 0 },
    { name: 'Bounces', value: stats?.bounces_today || 0 },
  ].filter(d => d.value > 0)

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="w-8 h-8 text-enterprise-red animate-spin" />
      </div>
    )
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
            Analytics
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-gray-500 mt-1"
          >
            Track your email performance and deliverability
          </motion.p>
        </div>

        <button
          onClick={fetchData}
          disabled={loading}
          className="p-2 rounded-lg bg-gray-100 hover:bg-gray-200 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-5 h-5 text-gray-600 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Key Metrics */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="grid grid-cols-2 md:grid-cols-4 gap-4"
      >
        <div className="card p-6">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-enterprise-red/10 flex items-center justify-center">
              <Send className="w-5 h-5 text-enterprise-red" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Total Sent</p>
              <p className="text-2xl font-semibold text-gray-900">{stats?.total_emails_sent || 0}</p>
            </div>
          </div>
          <div className="flex items-center gap-1 text-xs text-gray-500">
            <Calendar className="w-3 h-3" />
            <span>{stats?.emails_sent_today || 0} today</span>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-green-500/20 flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Reply Rate</p>
              <p className="text-2xl font-bold text-green-400">{replyRate}%</p>
            </div>
          </div>
          <div className="flex items-center gap-1 text-xs text-green-400">
            <TrendingUp className="w-3 h-3" />
            <span>{stats?.total_replies || 0} total replies</span>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center gap-3 mb-3">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
              parseFloat(bounceRate) > 5 ? 'bg-red-500/20' : 'bg-green-500/20'
            }`}>
              <AlertTriangle className={`w-5 h-5 ${
                parseFloat(bounceRate) > 5 ? 'text-red-400' : 'text-green-400'
              }`} />
            </div>
            <div>
              <p className="text-xs text-xen-dark-500">Bounce Rate</p>
              <p className={`text-2xl font-bold ${
                parseFloat(bounceRate) > 5 ? 'text-red-400' : 'text-green-400'
              }`}>{bounceRate}%</p>
            </div>
          </div>
          <div className={`flex items-center gap-1 text-xs ${
            parseFloat(bounceRate) > 5 ? 'text-red-400' : 'text-green-400'
          }`}>
            {parseFloat(bounceRate) > 5 ? (
              <>
                <TrendingDown className="w-3 h-3" />
                <span>Above threshold!</span>
              </>
            ) : (
              <>
                <TrendingUp className="w-3 h-3" />
                <span>Healthy</span>
              </>
            )}
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/20 flex items-center justify-center">
              <Users className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <p className="text-xs text-xen-dark-500">Total Leads</p>
              <p className="text-2xl font-bold text-purple-400">{stats?.total_leads || 0}</p>
            </div>
          </div>
          <div className="flex items-center gap-1 text-xs text-gray-500">
            <BarChart3 className="w-3 h-3" />
            <span>{stats?.active_campaigns || 0} active campaigns</span>
          </div>
        </div>
      </motion.div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sending Trend */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass rounded-2xl p-6 border border-xen-dark-700/50"
        >
          <h3 className="text-lg font-semibold text-gray-900 mb-6">Email Activity (Last 7 Days)</h3>
          <div className="h-64">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="colorSentAnalytics" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorRepliesAnalytics" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="name" stroke="#6b7280" />
                  <YAxis stroke="#6b7280" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1f2937',
                      border: '1px solid #374151',
                      borderRadius: '8px',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="sent"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    fill="url(#colorSentAnalytics)"
                    name="Sent"
                  />
                  <Area
                    type="monotone"
                    dataKey="replies"
                    stroke="#10b981"
                    strokeWidth={2}
                    fill="url(#colorRepliesAnalytics)"
                    name="Replies"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-gray-400">
                No data yet. Start sending emails to see analytics.
              </div>
            )}
          </div>
        </motion.div>

        {/* Distribution Pie */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="glass rounded-2xl p-6 border border-xen-dark-700/50"
        >
          <h3 className="text-lg font-semibold text-gray-900 mb-6">Email Distribution</h3>
          <div className="h-64">
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {pieData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1f2937',
                      border: '1px solid #374151',
                      borderRadius: '8px',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-gray-400">
                No data to display yet.
              </div>
            )}
          </div>
        </motion.div>
      </div>

      {/* Campaign Performance */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="glass rounded-2xl p-6 border border-xen-dark-700/50"
      >
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-gray-900">Campaign Performance</h3>
          <select
            value={selectedCampaignId || ''}
            onChange={(e) => setSelectedCampaignId(e.target.value ? Number(e.target.value) : null)}
            className="input text-sm"
          >
            <option value="">Select a campaign...</option>
            {campaigns.map(campaign => (
              <option key={campaign.id} value={campaign.id}>{campaign.name}</option>
            ))}
          </select>
        </div>

        {campaignLoading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-8 h-8 text-enterprise-red animate-spin" />
          </div>
        ) : campaignAnalytics ? (
          <div className="space-y-6">
            {/* Campaign Overview */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl bg-gray-50 border border-gray-200">
                <p className="text-xs text-gray-500 mb-1">Total Leads</p>
                <p className="text-2xl font-semibold text-gray-900">{campaignAnalytics.overview?.total_leads || 0}</p>
              </div>
              <div className="p-4 rounded-xl bg-gray-50 border border-gray-200">
                <p className="text-xs text-gray-500 mb-1">Emails Sent</p>
                <p className="text-2xl font-semibold text-enterprise-red">{campaignAnalytics.overview?.emails_sent || 0}</p>
              </div>
              <div className="p-4 rounded-xl bg-gray-50 border border-gray-200">
                <p className="text-xs text-gray-500 mb-1">Replies</p>
                <p className="text-2xl font-bold text-green-400">{campaignAnalytics.overview?.replies || 0}</p>
              </div>
              <div className="p-4 rounded-xl bg-xen-dark-800/50 border border-xen-dark-700">
                <p className="text-xs text-xen-dark-500 mb-1">Bounces</p>
                <p className="text-2xl font-bold text-red-400">{campaignAnalytics.overview?.bounces || 0}</p>
              </div>
            </div>

            {/* Performance Rates */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/30">
                <p className="text-xs text-xen-dark-400 mb-1">Reply Rate</p>
                <p className="text-2xl font-bold text-green-400">
                  {campaignAnalytics.rates?.reply_rate?.toFixed(1) || '0.0'}%
                </p>
              </div>
              <div className={`p-4 rounded-xl border ${
                (campaignAnalytics.rates?.bounce_rate || 0) > 5 
                  ? 'bg-red-500/10 border-red-500/30' 
                  : 'bg-green-500/10 border-green-500/30'
              }`}>
                <p className="text-xs text-xen-dark-400 mb-1">Bounce Rate</p>
                <p className={`text-2xl font-bold ${
                  (campaignAnalytics.rates?.bounce_rate || 0) > 5 ? 'text-red-400' : 'text-green-400'
                }`}>
                  {campaignAnalytics.rates?.bounce_rate?.toFixed(1) || '0.0'}%
                </p>
              </div>
              <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/30">
                <p className="text-xs text-xen-dark-400 mb-1">Click Rate</p>
                <p className="text-2xl font-bold text-purple-400">
                  {campaignAnalytics.rates?.click_rate?.toFixed(1) || '0.0'}%
                </p>
              </div>
            </div>

            {/* Lead Status Breakdown */}
            {campaignAnalytics.lead_statuses && Object.keys(campaignAnalytics.lead_statuses).length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-gray-900 mb-3">Lead Status Breakdown</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {Object.entries(campaignAnalytics.lead_statuses).map(([status, count]: [string, any]) => (
                    <div key={status} className="p-3 rounded-lg bg-xen-dark-800/50 border border-xen-dark-700">
                      <p className="text-xs text-xen-dark-400 capitalize">{status.replace('_', ' ')}</p>
                      <p className="text-lg font-semibold text-gray-900">{count}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Email Status Breakdown */}
            {campaignAnalytics.email_statuses && Object.keys(campaignAnalytics.email_statuses).length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-gray-900 mb-3">Email Status Breakdown</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {Object.entries(campaignAnalytics.email_statuses).map(([status, count]: [string, any]) => (
                    <div key={status} className="p-3 rounded-lg bg-xen-dark-800/50 border border-xen-dark-700">
                      <p className="text-xs text-xen-dark-400 capitalize">{status}</p>
                      <p className="text-lg font-semibold text-gray-900">{count}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-8 text-xen-dark-500">
            {campaigns.length > 0 
              ? "Select a campaign from the dropdown to see its performance."
              : "No campaign data yet. Create and run campaigns to see performance."}
          </div>
        )}
      </motion.div>

      {/* Sender Health */}
      {stats?.sender_health && stats.sender_health.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="glass rounded-2xl p-6 border border-xen-dark-700/50"
        >
          <h3 className="text-lg font-semibold text-gray-900 mb-6">Sender Health</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {stats.sender_health.map((sender) => (
              <div 
                key={sender.id} 
                className={`p-4 rounded-xl border ${
                  sender.bounce_rate > 0.05 
                    ? 'bg-red-500/10 border-red-500/30' 
                    : 'bg-green-500/10 border-green-500/30'
                }`}
              >
                <p className="font-medium text-gray-900 truncate">{sender.email}</p>
                <div className="flex items-center justify-between mt-2">
                  <span className={`text-sm ${
                    sender.bounce_rate > 0.05 ? 'text-red-400' : 'text-green-400'
                  }`}>
                    {(sender.bounce_rate * 100).toFixed(1)}% bounce
                  </span>
                  <span className="text-sm text-xen-dark-400">
                    {(sender.daily_usage * 100).toFixed(0)}% daily usage
                  </span>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  )
}
