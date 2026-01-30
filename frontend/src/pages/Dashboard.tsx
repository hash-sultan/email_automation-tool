import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Send,
  Users,
  MessageSquare,
  AlertTriangle,
  Activity,
  RefreshCw,
  TrendingUp,
} from 'lucide-react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import StatsCard from '../components/StatsCard'
import Badge from '../components/Badge'
import Button from '../components/Button'
import { SkeletonCard } from '../components/SkeletonLoader'
import { dashboardApi, campaignsApi, type DashboardStats, type Campaign } from '../api/client'

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(true)
  const [timePeriod, setTimePeriod] = useState<number>(7)

  const fetchData = async () => {
    setLoading(true)
    try {
      const [statsData, campaignsData] = await Promise.all([
        dashboardApi.getStats(timePeriod),
        campaignsApi.list(),
      ])
      setStats(statsData)
      setCampaigns(campaignsData.filter(c => c.status === 'active' || c.status === 'paused').slice(0, 3))
    } catch (err) {
      console.error('Failed to load dashboard:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [timePeriod])

  const chartData = stats?.emails_by_day?.map(day => {
    const date = new Date(day.date)
    const label = timePeriod <= 7 
      ? date.toLocaleDateString('en-US', { weekday: 'short' })
      : date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    return {
      name: label,
      sent: day.sent,
      replies: day.replies,
    }
  }) || []

  const replyRate = stats?.total_emails_sent 
    ? ((stats.total_replies / stats.total_emails_sent) * 100).toFixed(1)
    : '0.0'

  const bounceRate = stats?.overall_bounce_rate 
    ? (stats.overall_bounce_rate * 100).toFixed(1)
    : '0.0'

  if (loading && !stats) {
    return (
      <div className="space-y-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
        <SkeletonCard />
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <motion.h1
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-3xl font-semibold text-gray-900"
          >
            Dashboard
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-gray-500 mt-1"
          >
            Overview of your email automation performance
          </motion.p>
        </div>

        <Button
          variant="secondary"
          icon={RefreshCw}
          onClick={fetchData}
          disabled={loading}
          className={loading ? 'opacity-50' : ''}
        >
          Refresh
        </Button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
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
          title="Follow-ups Sent Today"
          value={stats?.followups_sent_today ?? 0}
          change={0}
          changeLabel="today"
          icon={Send}
          color="blue"
          delay={0.05}
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
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="card p-6"
        >
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900">Sending Activity</h3>
            <select
              value={timePeriod}
              onChange={(e) => setTimePeriod(Number(e.target.value))}
              className="input text-sm py-1.5 px-3 w-auto"
            >
              <option value={1}>Last 1 day</option>
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
          </div>
          <div className="h-64">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="colorSent" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#991b1b" stopOpacity={0.15} />
                      <stop offset="95%" stopColor="#991b1b" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" strokeOpacity={0.5} />
                  <XAxis 
                    dataKey="name" 
                    stroke="#737373" 
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis 
                    stroke="#737373" 
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#ffffff',
                      border: '1px solid #e5e5e5',
                      borderRadius: '8px',
                      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
                      padding: '8px 12px',
                    }}
                    labelStyle={{ color: '#404040', fontWeight: 600, fontSize: '12px' }}
                    itemStyle={{ color: '#737373', fontSize: '12px' }}
                  />
                  <Area
                    type="monotone"
                    dataKey="sent"
                    stroke="#991b1b"
                    strokeWidth={2.5}
                    fill="url(#colorSent)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-gray-400">
                No sending data yet. Start a campaign to see activity.
              </div>
            )}
          </div>
        </motion.div>

        {/* Replies List */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="card p-6"
        >
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900">Recent Replies</h3>
            <Badge variant="success">{stats?.replies_today ?? 0} today</Badge>
          </div>
          <div className="h-64 max-h-96 overflow-y-auto space-y-3">
            {stats?.recent_replies && stats.recent_replies.length > 0 ? (
              stats.recent_replies.map((reply, index) => (
                <motion.div
                  key={reply.lead_id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.03 }}
                  className="p-3 rounded-md border border-gray-200 hover:border-gray-300 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <MessageSquare className="w-4 h-4 text-green-600 flex-shrink-0" />
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {reply.name || reply.email}
                        </p>
                      </div>
                      <p className="text-xs text-gray-500 mb-1 truncate">{reply.email}</p>
                      <p className="text-xs text-gray-400 truncate">{reply.subject}</p>
                    </div>
                    <div className="text-right ml-4 flex-shrink-0">
                      <p className="text-xs text-gray-400 mb-1">
                        {reply.replied_at ? new Date(reply.replied_at).toLocaleDateString() : 'N/A'}
                      </p>
                      <div className="flex items-center gap-1 justify-end">
                        <div className="w-2 h-2 rounded-full bg-green-600"></div>
                        <p className="text-xs text-gray-500 truncate max-w-[100px]">
                          {reply.sender_email}
                        </p>
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))
            ) : (
              <div className="h-full flex items-center justify-center text-gray-400">
                No replies yet. Replies will appear here.
              </div>
            )}
          </div>
        </motion.div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active Campaigns */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="lg:col-span-2 card p-6"
        >
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900">Active Campaigns</h3>
            <a
              href="/campaigns"
              className="text-sm text-enterprise-red hover:text-enterprise-red-dark transition-colors font-medium"
            >
              View all →
            </a>
          </div>
          <div className="space-y-3">
            {campaigns.length > 0 ? (
              campaigns.map((campaign, index) => (
                <motion.div
                  key={campaign.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.7 + index * 0.05 }}
                  className="flex items-center justify-between p-4 rounded-md border border-gray-200 hover:border-gray-300 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-md bg-enterprise-red/10 flex items-center justify-center">
                      <Send className="w-5 h-5 text-enterprise-red" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">{campaign.name}</p>
                      <p className="text-sm text-gray-500">
                        {campaign.emails_sent} sent • {campaign.replies_count} replies
                      </p>
                    </div>
                  </div>
                  <Badge
                    variant={campaign.status === 'active' ? 'success' : 'warning'}
                  >
                    {campaign.status}
                  </Badge>
                </motion.div>
              ))
            ) : (
              <div className="text-center py-12 text-gray-400">
                <Activity className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p className="mb-2">No campaigns yet</p>
                <a href="/campaigns" className="text-enterprise-red hover:text-enterprise-red-dark text-sm font-medium">
                  Create your first campaign →
                </a>
              </div>
            )}
          </div>
        </motion.div>

        {/* Quick Stats */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="card p-6"
        >
          <h3 className="text-lg font-semibold text-gray-900 mb-6">Performance</h3>
          <div className="space-y-4">
            <div className="flex items-center gap-3 p-3 rounded-md bg-gray-50">
              <div className="w-8 h-8 rounded-md bg-green-100 flex items-center justify-center">
                <MessageSquare className="w-4 h-4 text-green-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm text-gray-500">Total Replies</p>
                <p className="font-semibold text-gray-900">{stats?.total_replies ?? 0}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-md bg-gray-50">
              <div className="w-8 h-8 rounded-md bg-red-100 flex items-center justify-center">
                <AlertTriangle className="w-4 h-4 text-red-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm text-gray-500">Bounces Today</p>
                <p className="font-semibold text-gray-900">{stats?.bounces_today ?? 0}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-md bg-gray-50">
              <div className="w-8 h-8 rounded-md bg-enterprise-red/10 flex items-center justify-center">
                <TrendingUp className="w-4 h-4 text-enterprise-red" />
              </div>
              <div className="flex-1">
                <p className="text-sm text-gray-500">Total Sent</p>
                <p className="font-semibold text-gray-900">{stats?.total_emails_sent ?? 0}</p>
              </div>
            </div>
            <div className="p-3 rounded-md border border-gray-200">
              <p className="text-sm text-gray-500 mb-1">Bounce Rate</p>
              <p className={`text-2xl font-semibold ${
                parseFloat(bounceRate) < 5 ? 'text-green-600' : 'text-red-600'
              }`}>
                {bounceRate}%
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {parseFloat(bounceRate) < 5 ? 'Healthy' : 'Above threshold'}
              </p>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

