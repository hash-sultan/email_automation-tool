import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Send,
  Users,
  MessageSquare,
  AlertTriangle,
  Activity,
  Shield,
  CheckCircle,
  RefreshCw,
} from 'lucide-react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts'
import StatsCard from '../components/StatsCard'
import Badge from '../components/Badge'
import { dashboardApi, campaignsApi, type DashboardStats, type Campaign } from '../api/client'

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [statsData, campaignsData] = await Promise.all([
        dashboardApi.getStats(),
        campaignsApi.list(),
      ])
      setStats(statsData)
      setCampaigns(campaignsData.filter(c => c.status === 'active' || c.status === 'paused').slice(0, 3))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])

  // Transform emails_by_day to chart format
  const chartData = stats?.emails_by_day?.map(day => ({
    name: new Date(day.date).toLocaleDateString('en-US', { weekday: 'short' }),
    sent: day.sent,
    replies: day.replies,
  })) || []

  // Calculate reply rate
  const replyRate = stats?.total_emails_sent 
    ? ((stats.total_replies / stats.total_emails_sent) * 100).toFixed(1)
    : '0.0'

  // Calculate bounce rate
  const bounceRate = stats?.overall_bounce_rate 
    ? (stats.overall_bounce_rate * 100).toFixed(1)
    : '0.0'

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="w-8 h-8 text-xen-red-400 animate-spin" />
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
            className="text-2xl font-bold text-white"
          >
            Welcome back! 👋
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-xen-dark-400 mt-1"
          >
            Here's what's happening with your campaigns today.
          </motion.p>
        </div>

        <div className="flex items-center gap-4">
          {/* Refresh Button */}
          <motion.button
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            onClick={fetchData}
            disabled={loading}
            className="p-2 rounded-lg bg-xen-dark-800 hover:bg-xen-dark-700 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-5 h-5 text-xen-dark-400 ${loading ? 'animate-spin' : ''}`} />
          </motion.button>

          {/* Safety Status Indicator */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
            className={`glass rounded-xl px-4 py-2 border flex items-center gap-3 ${
              error 
                ? 'border-red-500/30' 
                : 'border-green-500/30'
            }`}
          >
            <div className={`w-3 h-3 rounded-full animate-pulse ${
              error ? 'bg-red-500' : 'bg-green-500'
            }`} />
            <div>
              <p className={`text-sm font-medium ${error ? 'text-red-400' : 'text-green-400'}`}>
                {error ? 'Connection Error' : 'All Systems Operational'}
              </p>
              <p className="text-xs text-xen-dark-500">
                {error || 'Deliverability: Excellent'}
              </p>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Emails Sent Today"
          value={stats?.emails_sent_today ?? 0}
          change={0}
          changeLabel="today"
          icon={Send}
          color="red"
          delay={0}
        />
        <StatsCard
          title="Total Leads"
          value={stats?.total_leads ?? 0}
          change={0}
          changeLabel="total"
          icon={Users}
          color="blue"
          delay={0.1}
        />
        <StatsCard
          title="Reply Rate"
          value={`${replyRate}%`}
          change={0}
          changeLabel="overall"
          icon={MessageSquare}
          color="green"
          delay={0.2}
        />
        <StatsCard
          title="Active Campaigns"
          value={stats?.active_campaigns ?? 0}
          icon={Activity}
          color="purple"
          delay={0.3}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sending Activity Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="glass rounded-2xl p-6 border border-xen-dark-700/50"
        >
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-white">Sending Activity</h3>
            <Badge variant="info">Last 7 days</Badge>
          </div>
          <div className="h-64">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="colorSent" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
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
                    stroke="#ef4444"
                    strokeWidth={2}
                    fill="url(#colorSent)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xen-dark-500">
                No sending data yet. Start a campaign to see activity.
              </div>
            )}
          </div>
        </motion.div>

        {/* Replies Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="glass rounded-2xl p-6 border border-xen-dark-700/50"
        >
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-white">Replies Received</h3>
            <Badge variant="success">{stats?.replies_today ?? 0} today</Badge>
          </div>
          <div className="h-64">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
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
                  <Bar dataKey="replies" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xen-dark-500">
                No reply data yet. Replies will appear here.
              </div>
            )}
          </div>
        </motion.div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active Campaigns */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="lg:col-span-2 glass rounded-2xl p-6 border border-xen-dark-700/50"
        >
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-white">Active Campaigns</h3>
            <a
              href="/campaigns"
              className="text-sm text-xen-red-400 hover:text-xen-red-300 transition-colors"
            >
              View all →
            </a>
          </div>
          <div className="space-y-4">
            {campaigns.length > 0 ? (
              campaigns.map((campaign, index) => (
                <motion.div
                  key={campaign.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.7 + index * 0.1 }}
                  className="flex items-center justify-between p-4 rounded-xl bg-xen-dark-800/30 hover:bg-xen-dark-800/50 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-lg bg-xen-red-500/20 flex items-center justify-center">
                      <Send className="w-5 h-5 text-xen-red-400" />
                    </div>
                    <div>
                      <p className="font-medium text-white">{campaign.name}</p>
                      <p className="text-sm text-xen-dark-400">
                        {campaign.emails_sent} sent • {campaign.emails_replied} replies
                      </p>
                    </div>
                  </div>
                  <Badge
                    variant={campaign.status === 'active' ? 'success' : 'warning'}
                    pulse={campaign.status === 'active'}
                  >
                    {campaign.status}
                  </Badge>
                </motion.div>
              ))
            ) : (
              <div className="text-center py-8 text-xen-dark-500">
                <Activity className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No campaigns yet</p>
                <a href="/campaigns" className="text-xen-red-400 hover:text-xen-red-300 text-sm">
                  Create your first campaign →
                </a>
              </div>
            )}
          </div>
        </motion.div>

        {/* Quick Stats */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="glass rounded-2xl p-6 border border-xen-dark-700/50"
        >
          <h3 className="text-lg font-semibold text-white mb-6">Quick Stats</h3>
          <div className="space-y-4">
            <div className="flex items-center gap-3 p-3 rounded-lg bg-xen-dark-800/30">
              <div className="w-8 h-8 rounded-lg bg-green-500/20 flex items-center justify-center">
                <MessageSquare className="w-4 h-4 text-green-400" />
              </div>
              <div className="flex-1">
                <p className="text-sm text-xen-dark-400">Total Replies</p>
                <p className="font-semibold text-white">{stats?.total_replies ?? 0}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-lg bg-xen-dark-800/30">
              <div className="w-8 h-8 rounded-lg bg-red-500/20 flex items-center justify-center">
                <AlertTriangle className="w-4 h-4 text-red-400" />
              </div>
              <div className="flex-1">
                <p className="text-sm text-xen-dark-400">Bounces Today</p>
                <p className="font-semibold text-white">{stats?.bounces_today ?? 0}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-lg bg-xen-dark-800/30">
              <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <CheckCircle className="w-4 h-4 text-blue-400" />
              </div>
              <div className="flex-1">
                <p className="text-sm text-xen-dark-400">Total Emails Sent</p>
                <p className="font-semibold text-white">{stats?.total_emails_sent ?? 0}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-lg bg-xen-dark-800/30">
              <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center">
                <Users className="w-4 h-4 text-purple-400" />
              </div>
              <div className="flex-1">
                <p className="text-sm text-xen-dark-400">Active Senders</p>
                <p className="font-semibold text-white">{stats?.total_senders ?? 0}</p>
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Safety Metrics */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.9 }}
        className="glass rounded-2xl p-6 border border-xen-dark-700/50"
      >
        <div className="flex items-center gap-3 mb-6">
          <Shield className="w-6 h-6 text-xen-red-400" />
          <h3 className="text-lg font-semibold text-white">Deliverability Health</h3>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className={`p-4 rounded-xl border ${
            parseFloat(bounceRate) < 5 
              ? 'bg-green-500/10 border-green-500/30' 
              : 'bg-red-500/10 border-red-500/30'
          }`}>
            <p className="text-sm text-xen-dark-400">Bounce Rate</p>
            <p className={`text-2xl font-bold mt-1 ${
              parseFloat(bounceRate) < 5 ? 'text-green-400' : 'text-red-400'
            }`}>{bounceRate}%</p>
            <p className={`text-xs mt-1 ${
              parseFloat(bounceRate) < 5 ? 'text-green-500/70' : 'text-red-500/70'
            }`}>
              {parseFloat(bounceRate) < 5 ? 'Below 5% threshold' : 'Above 5% threshold!'}
            </p>
          </div>
          <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/30">
            <p className="text-sm text-xen-dark-400">Reply Rate</p>
            <p className="text-2xl font-bold text-green-400 mt-1">{replyRate}%</p>
            <p className="text-xs text-green-500/70 mt-1">Overall performance</p>
          </div>
          <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/30">
            <p className="text-sm text-xen-dark-400">Active Senders</p>
            <p className="text-2xl font-bold text-blue-400 mt-1">{stats?.total_senders ?? 0}</p>
            <p className="text-xs text-blue-500/70 mt-1">Configured accounts</p>
          </div>
          <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/30">
            <p className="text-sm text-xen-dark-400">Campaigns</p>
            <p className="text-2xl font-bold text-purple-400 mt-1">{stats?.active_campaigns ?? 0}</p>
            <p className="text-xs text-purple-500/70 mt-1">Currently active</p>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
