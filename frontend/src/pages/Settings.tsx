import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Save, Mail, Trash2, AlertTriangle, Settings as SettingsIcon } from 'lucide-react'
import Button from '../components/Button'
import { settingsApi } from '../api/client'
import toast from 'react-hot-toast'

interface SystemSettings {
  campaign_daily_limit: number
  sender_daily_limit: number
  reply_check_interval_minutes: number
  reply_look_back_hours: number
}

export default function Settings() {
  const [resetting, setResetting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)
  const [settings, setSettings] = useState<SystemSettings>({
    campaign_daily_limit: 500,
    sender_daily_limit: 200,
    reply_check_interval_minutes: 5,
    reply_look_back_hours: 24,
  })

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const data = await settingsApi.getSettings()
        setSettings(data)
      } catch (err) {
        console.error('Failed to load settings:', err)
        // Use defaults if API fails
      } finally {
        setLoading(false)
      }
    }
    fetchSettings()
  }, [])

  const handleResetAllData = async () => {
    const firstConfirm = confirm(
      '⚠️ DANGER ZONE ⚠️\n\n' +
      'This will PERMANENTLY DELETE:\n' +
      '• All campaigns\n' +
      '• All leads\n' +
      '• All email logs (including replies)\n' +
      '• All analytics data\n' +
      '• Reset all sender counters to 0\n\n' +
      'This will KEEP:\n' +
      '• All senders (intact)\n' +
      '• All templates (intact)\n\n' +
      'This action CANNOT be undone!\n\n' +
      'Are you absolutely sure?'
    )

    if (!firstConfirm) return

    const userInput = prompt('Type "RESET" (all caps) to confirm:')
    if (userInput !== 'RESET') {
      toast.error('Reset cancelled - confirmation text did not match')
      return
    }

    setResetting(true)
    try {
      const result = await settingsApi.resetAllData()
      toast.success(
        `Reset complete! Deleted ${result.deleted.campaigns} campaigns, ${result.deleted.email_logs} email logs, ${result.deleted.leads} leads.`,
        { duration: 6000 }
      )
      // Reload the page to refresh all data
      setTimeout(() => {
        window.location.reload()
      }, 2000)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to reset data'
      toast.error(errorMsg)
    } finally {
      setResetting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-enterprise-red"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div>
        <motion.h1
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-3xl font-semibold text-gray-900"
        >
          Settings
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-gray-500 mt-1"
        >
          Configure system settings and safety thresholds
        </motion.p>
      </div>

      {/* Daily Limits */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="card p-6"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-enterprise-red/10 flex items-center justify-center">
            <SettingsIcon className="w-5 h-5 text-enterprise-red" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Daily Limits</h2>
            <p className="text-sm text-gray-500">
              Configure sending limits for senders
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Sender Daily Limit
            </label>
            <input
              type="number"
              value={settings.sender_daily_limit}
              onChange={(e) => setSettings({ ...settings, sender_daily_limit: parseInt(e.target.value) || 200 })}
              min={1}
              max={500}
              className="input"
            />
            <p className="text-xs text-gray-500 mt-1">Maximum emails per sender per day (max: 500)</p>
          </div>
        </div>
      </motion.div>

      {/* IMAP Settings */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="card p-6"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-green-500/20 flex items-center justify-center">
            <Mail className="w-5 h-5 text-green-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Reply Detection</h2>
            <p className="text-sm text-gray-500">Configure IMAP monitoring settings</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Check Interval (minutes)
            </label>
            <input
              type="number"
              value={settings.reply_check_interval_minutes}
              onChange={(e) => setSettings({ ...settings, reply_check_interval_minutes: parseInt(e.target.value) || 5 })}
              min={1}
              max={60}
              className="input"
            />
            <p className="text-xs text-gray-500 mt-1">How often to check for replies</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Look Back (hours)
            </label>
            <input
              type="number"
              value={settings.reply_look_back_hours}
              onChange={(e) => setSettings({ ...settings, reply_look_back_hours: parseInt(e.target.value) || 24 })}
              min={1}
              max={168}
              className="input"
            />
            <p className="text-xs text-gray-500 mt-1">How far back to check for replies</p>
          </div>
        </div>
      </motion.div>

      {/* Reset All Data - Danger Zone */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="card p-6 border-2 border-red-500/30 bg-red-500/5"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-red-500/20 flex items-center justify-center">
            <AlertTriangle className="w-5 h-5 text-red-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Reset All Data</h2>
            <p className="text-sm text-gray-500">
              Start fresh by deleting all campaigns and activity data
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30">
            <p className="text-sm font-medium text-yellow-400 mb-2">⚠️ This will permanently delete:</p>
            <ul className="text-sm text-gray-600 space-y-1 list-disc list-inside">
              <li>All campaigns</li>
              <li>All leads</li>
              <li>All email logs (including replies)</li>
              <li>All analytics data</li>
              <li>All sender counters (reset to 0)</li>
            </ul>
          </div>

          <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/30">
            <p className="text-sm font-medium text-green-400 mb-2">✅ This will be preserved:</p>
            <ul className="text-sm text-gray-600 space-y-1 list-disc list-inside">
              <li>All senders (intact, counters reset)</li>
              <li>All templates (completely intact)</li>
            </ul>
          </div>

          <Button
            variant="danger"
            icon={Trash2}
            onClick={handleResetAllData}
            loading={resetting}
            disabled={resetting}
            className="w-full"
          >
            {resetting ? 'Resetting...' : 'Reset All Campaign & Activity Data'}
          </Button>
        </div>
      </motion.div>

      {/* Save Button */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="flex justify-end"
      >
        <Button 
          icon={Save} 
          onClick={async () => {
            setSaving(true)
            try {
              await settingsApi.updateSettings(settings)
              toast.success('Settings saved successfully!')
            } catch (err) {
              toast.error(err instanceof Error ? err.message : 'Failed to save settings')
            } finally {
              setSaving(false)
            }
          }}
          loading={saving}
        >
          Save Settings
        </Button>
      </motion.div>
    </div>
  )
}

