import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  MessageSquare,
  Send,
  Mail,
  Calendar,
  X,
  RefreshCw,
  Filter,
  Reply as ReplyIcon,
} from 'lucide-react'
import Button from '../components/Button'
import Badge from '../components/Badge'
import { repliesApi, campaignsApi, sendersApi, type Reply, type Campaign, type Sender } from '../api/client'
import toast from 'react-hot-toast'

export default function Replies() {
  const [replies, setReplies] = useState<Reply[]>([])
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [senders, setSenders] = useState<Sender[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [selectedReply, setSelectedReply] = useState<Reply | null>(null)
  const [showReplyModal, setShowReplyModal] = useState(false)
  const [replyBody, setReplyBody] = useState('')
  const [replySubject, setReplySubject] = useState('')
  const [sending, setSending] = useState(false)
  const [filterSender, setFilterSender] = useState<number | undefined>()
  const [filterCampaign, setFilterCampaign] = useState<number | undefined>()

  const fetchData = async () => {
    setLoading(true)
    try {
      const [repliesData, campaignsData, sendersData] = await Promise.all([
        repliesApi.list(page, 20, filterSender, filterCampaign),
        campaignsApi.list(),
        sendersApi.list(),
      ])
      setReplies(repliesData.items)
      setTotalPages(repliesData.pages)
      setTotal(repliesData.total)
      setCampaigns(campaignsData)
      setSenders(sendersData)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load replies'
      toast.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [page, filterSender, filterCampaign])

  const handleReply = (reply: Reply) => {
    setSelectedReply(reply)
    setReplySubject(`Re: ${reply.subject}`)
    setReplyBody('')
    setShowReplyModal(true)
  }

  const handleSendReply = async () => {
    if (!selectedReply || !replyBody.trim()) {
      toast.error('Please enter a reply message')
      return
    }

    setSending(true)
    try {
      await repliesApi.send({
        email_log_id: selectedReply.id,
        body_html: replyBody.replace(/\n/g, '<br>'),
        body_text: replyBody,
        subject: replySubject,
      })
      toast.success('Reply sent successfully!')
      setShowReplyModal(false)
      setSelectedReply(null)
      setReplyBody('')
      setReplySubject('')
      fetchData() // Refresh replies
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to send reply')
    } finally {
      setSending(false)
    }
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
            Replies
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-gray-500 mt-1"
          >
            View and respond to email replies ({total} total)
          </motion.p>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="ghost" onClick={fetchData} disabled={loading}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Filters */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
          className="card p-4"
      >
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-500" />
            <span className="text-sm text-gray-600">Filter by:</span>
          </div>
          <select
            value={filterSender || ''}
            onChange={(e) => {
              setFilterSender(e.target.value ? Number(e.target.value) : undefined)
              setPage(1) // Reset to first page when filter changes
            }}
            className="input text-sm"
          >
            <option value="">All Senders</option>
            {senders.map(s => (
              <option key={s.id} value={s.id}>{s.email}</option>
            ))}
          </select>
          <select
            value={filterCampaign || ''}
            onChange={(e) => {
              setFilterCampaign(e.target.value ? Number(e.target.value) : undefined)
              setPage(1) // Reset to first page when filter changes
            }}
            className="input text-sm"
          >
            <option value="">All Campaigns</option>
            {campaigns.map(c => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
      </motion.div>

      {/* Replies List */}
      {loading && replies.length === 0 ? (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 text-enterprise-red animate-spin" />
        </div>
      ) : replies.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="card p-12 text-center"
        >
          <MessageSquare className="w-16 h-16 mx-auto text-gray-400 mb-4" />
          <h3 className="text-xl font-semibold text-gray-900 mb-2">No replies yet</h3>
          <p className="text-gray-500">
            Replies will appear here when leads respond to your emails
          </p>
        </motion.div>
      ) : (
        <div className="space-y-4">
          {replies.map((reply, index) => (
            <motion.div
              key={reply.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="card p-6 hover:shadow-md transition-all"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-12 h-12 rounded-xl bg-green-500/20 flex items-center justify-center">
                      <MessageSquare className="w-6 h-6 text-green-400" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-gray-900">
                          {reply.lead_name || reply.lead_email}
                        </h3>
                        <Badge variant="success">Replied</Badge>
                      </div>
                      <p className="text-sm text-gray-600">{reply.lead_email}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div className="flex items-center gap-2 text-sm">
                      <Mail className="w-4 h-4 text-gray-500" />
                      <span className="text-gray-600">Sender:</span>
                      <span className="text-gray-900 truncate">{reply.sender_email}</span>
                    </div>
                    {reply.campaign_name && (
                      <div className="flex items-center gap-2 text-sm">
                        <Send className="w-4 h-4 text-xen-dark-500" />
                        <span className="text-xen-dark-400">Campaign:</span>
                        <span className="text-gray-900 truncate">{reply.campaign_name}</span>
                      </div>
                    )}
                    <div className="flex items-center gap-2 text-sm">
                      <Calendar className="w-4 h-4 text-xen-dark-500" />
                      <span className="text-xen-dark-400">Replied:</span>
                      <span className="text-gray-900">
                        {reply.replied_at 
                          ? new Date(reply.replied_at).toLocaleDateString()
                          : 'N/A'}
                      </span>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="p-3 rounded-lg bg-xen-dark-800/50">
                      <p className="text-xs text-xen-dark-500 mb-1">Subject</p>
                      <p className="text-sm text-gray-900 font-medium">{reply.subject}</p>
                    </div>
                    {reply.body_preview && (
                      <div className="p-3 rounded-lg bg-gray-50 border border-gray-200">
                        <p className="text-xs text-gray-500 mb-1">Reply Preview</p>
                        <p className="text-sm text-gray-800 whitespace-pre-wrap line-clamp-3">
                          {reply.body_preview}
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                <div className="ml-4">
                  <Button
                    size="sm"
                    onClick={() => handleReply(reply)}
                  >
                    <ReplyIcon className="w-4 h-4 mr-2" />
                    Reply
                  </Button>
                </div>
              </div>
            </motion.div>
          ))}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                Previous
              </Button>
              <span className="text-sm text-xen-dark-400">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                Next
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Reply Modal */}
      <AnimatePresence>
        {showReplyModal && selectedReply && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setShowReplyModal(false)}
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
                  Reply to {selectedReply.lead_name || selectedReply.lead_email}
                </h2>
                <button
                  onClick={() => setShowReplyModal(false)}
                  className="p-2 rounded-lg hover:bg-xen-dark-800 transition-colors"
                >
                  <X className="w-5 h-5 text-xen-dark-400" />
                </button>
              </div>

              {/* Original reply content */}
              {selectedReply.body_text && (
                <div className="mb-4 p-3 rounded-lg bg-gray-50 border border-gray-200">
                  <p className="text-xs text-gray-500 mb-1">Original Message</p>
                  <div className="max-h-48 overflow-y-auto text-sm text-gray-800 whitespace-pre-wrap">
                    {selectedReply.body_text}
                  </div>
                </div>
              )}

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                    Subject
                  </label>
                  <input
                    type="text"
                    value={replySubject}
                    onChange={(e) => setReplySubject(e.target.value)}
                    className="input"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-xen-dark-300 mb-2">
                    Message
                  </label>
                  <textarea
                    value={replyBody}
                    onChange={(e) => setReplyBody(e.target.value)}
                    rows={8}
                    className="input"
                    placeholder="Type your reply here..."
                  />
                </div>

                <div className="flex items-center gap-3 pt-4">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => setShowReplyModal(false)}
                    className="flex-1"
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleSendReply}
                    disabled={sending || !replyBody.trim()}
                    className="flex-1"
                  >
                    {sending ? (
                      <>
                        <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                        Sending...
                      </>
                    ) : (
                      <>
                        <Send className="w-4 h-4 mr-2" />
                        Send Reply
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
