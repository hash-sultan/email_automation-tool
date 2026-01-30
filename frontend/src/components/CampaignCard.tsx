import { memo } from 'react'
import { motion } from 'framer-motion'
import {
  Send,
  Play,
  Pause,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Clock,
  Trash2,
  Pencil,
  Zap,
} from 'lucide-react'
import Button from './Button'
import Badge from './Badge'
import { type Campaign } from '../api/client'

const statusConfig: Record<string, { color: string; icon: typeof Play; label: string }> = {
  draft: { color: 'gray', icon: Clock, label: 'Draft' },
  active: { color: 'green', icon: Play, label: 'Active' },
  paused: { color: 'yellow', icon: Pause, label: 'Paused' },
  completed: { color: 'blue', icon: CheckCircle, label: 'Completed' },
  cancelled: { color: 'red', icon: Clock, label: 'Cancelled' },
}

interface CampaignCardProps {
  campaign: Campaign
  index: number
  actionLoading: number | null
  onStart: (id: number) => void
  onPause: (id: number) => void
  onResume: (id: number) => void
  onDelete: (id: number) => void
  onEdit: (campaign: Campaign) => void
  onTriggerFollowups: (campaignId: number) => void
}

const CampaignCard = ({
  campaign,
  index,
  actionLoading,
  onStart,
  onPause,
  onResume,
  onDelete,
  onEdit,
  onTriggerFollowups,
}: CampaignCardProps) => {
  const status = statusConfig[campaign.status] || statusConfig.draft
  const replyRate = campaign.emails_sent > 0 
    ? ((campaign.replies_count / campaign.emails_sent) * 100).toFixed(1)
    : '0.0'
  const leadsContacted = campaign.leads_contacted ?? campaign.emails_sent
  // Enable trigger follow-ups only when all leads have been contacted
  const canTriggerFollowups = campaign.status === 'active' && 
    campaign.followup_enabled && 
    leadsContacted === campaign.total_leads && 
    campaign.total_leads > 0

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.15, delay: index * 0.03 }}
      className="card p-6 hover:shadow-md transition-all"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
            campaign.status === 'active' ? 'bg-green-500/20' : 'bg-enterprise-red/20'
          }`}>
            <Send className={`w-6 h-6 ${
              campaign.status === 'active' ? 'text-green-400' : 'text-enterprise-red'
            }`} />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">{campaign.name}</h3>
            <p className="text-xs text-gray-500">
              Created {new Date(campaign.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>
        <Badge 
          variant={
            campaign.status === 'active' ? 'success' : 
            campaign.status === 'paused' ? 'warning' : 
            campaign.status === 'completed' ? 'info' : 'default'
          }
          pulse={campaign.status === 'active'}
        >
          {status.label}
        </Badge>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
        <div className="p-2 rounded-lg bg-gray-50 text-center">
          <p className="text-lg font-semibold text-gray-900">{campaign.total_leads}</p>
          <p className="text-xs text-gray-500">Leads</p>
        </div>
        <div className="p-2 rounded-lg bg-gray-50 text-center">
          <p className="text-lg font-semibold text-enterprise-red">{leadsContacted}</p>
          <p className="text-xs text-gray-500">Contacted</p>
        </div>
        <div className="p-2 rounded-lg bg-gray-50 text-center">
          <p className="text-lg font-semibold text-blue-600">{campaign.followups_sent || 0}</p>
          <p className="text-xs text-gray-500">Follow-ups</p>
        </div>
        <div className="p-2 rounded-lg bg-gray-50 text-center">
          <p className="text-lg font-semibold text-green-600">{campaign.replies_count}</p>
          <p className="text-xs text-gray-500">Replies</p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="flex items-center justify-between text-xs mb-1">
          <span className="text-gray-500">Reply Rate</span>
          <span className="text-green-600 font-medium">{replyRate}%</span>
        </div>
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-green-500 to-green-400 rounded-full transition-all"
            style={{ width: `${Math.min(parseFloat(replyRate), 100)}%` }}
          />
        </div>
      </div>

      {/* Bounce indicator */}
      {campaign.bounces_count > 0 && (
        <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/30 mb-4">
          <div className="flex items-center gap-2 text-sm text-red-400">
            <AlertCircle className="w-4 h-4" />
            <span>{campaign.bounces_count} bounces</span>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          {campaign.status === 'draft' && (
            <Button
              size="sm"
              onClick={() => onStart(campaign.id)}
              disabled={actionLoading === campaign.id || campaign.total_leads === 0}
              className="flex-1"
            >
              {actionLoading === campaign.id ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <Play className="w-4 h-4 mr-1" />
                  Start
                </>
              )}
            </Button>
          )}
          {campaign.status === 'active' && (
            <Button
              size="sm"
              variant="secondary"
              onClick={() => onPause(campaign.id)}
              disabled={actionLoading === campaign.id}
              className="flex-1"
            >
              {actionLoading === campaign.id ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <Pause className="w-4 h-4 mr-1" />
                  Pause
                </>
              )}
            </Button>
          )}
          {campaign.status === 'paused' && (
            <Button
              size="sm"
              onClick={() => onResume(campaign.id)}
              disabled={actionLoading === campaign.id}
              className="flex-1"
            >
              {actionLoading === campaign.id ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <Play className="w-4 h-4 mr-1" />
                  Resume
                </>
              )}
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onEdit(campaign)}
            className="text-gray-400 hover:text-gray-300"
            disabled={campaign.status === 'active'}
            title="Edit campaign"
          >
            <Pencil className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(campaign.id)}
            className="text-red-400 hover:text-red-300"
            disabled={campaign.status === 'active'}
            title="Delete campaign"
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
        <Button
          variant={canTriggerFollowups ? "secondary" : "ghost"}
          size="sm"
          onClick={() => onTriggerFollowups(campaign.id)}
          disabled={!canTriggerFollowups || actionLoading === campaign.id}
          className={`w-full text-xs ${!canTriggerFollowups ? 'opacity-50 cursor-not-allowed' : ''}`}
          title={canTriggerFollowups ? "Manually trigger follow-ups for this campaign" : "All leads must be contacted first"}
        >
          {actionLoading === campaign.id ? (
            <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
          ) : (
            <Zap className={`w-3 h-3 mr-1 ${canTriggerFollowups ? 'text-enterprise-red' : ''}`} />
          )}
          Trigger Follow-ups
        </Button>
      </div>
    </motion.div>
  )
}

CampaignCard.displayName = 'CampaignCard'

// Custom comparison function to ensure re-render when status or key props change
export default memo(CampaignCard, (prevProps, nextProps) => {
  // Always re-render if campaign status changes (this is the key fix!)
  if (prevProps.campaign.status !== nextProps.campaign.status) {
    return false // false means "should re-render"
  }
  // Always re-render if actionLoading changes for this campaign
  if (prevProps.actionLoading !== nextProps.actionLoading) {
    return false
  }
  // Re-render if campaign data changes (shallow comparison of key fields)
  if (
    prevProps.campaign.id !== nextProps.campaign.id ||
    prevProps.campaign.emails_sent !== nextProps.campaign.emails_sent ||
    prevProps.campaign.followups_sent !== nextProps.campaign.followups_sent ||
    prevProps.campaign.replies_count !== nextProps.campaign.replies_count ||
    prevProps.campaign.total_leads !== nextProps.campaign.total_leads ||
    prevProps.campaign.bounces_count !== nextProps.campaign.bounces_count
  ) {
    return false
  }
  // Otherwise, skip re-render (return true means "props are equal, skip render")
  return true
})
