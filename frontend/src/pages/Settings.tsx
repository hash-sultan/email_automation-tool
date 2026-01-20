import { motion } from 'framer-motion'
import { Save, Shield, Clock, Mail } from 'lucide-react'
import Button from '../components/Button'

export default function Settings() {
  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div>
        <motion.h1
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-2xl font-bold text-white"
        >
          Settings
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-xen-dark-400 mt-1"
        >
          Configure system settings and safety thresholds
        </motion.p>
      </div>

      {/* Safety Settings */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="glass rounded-2xl p-6 border border-xen-dark-700/50"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-xen-red-500/20 flex items-center justify-center">
            <Shield className="w-5 h-5 text-xen-red-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Safety Thresholds</h2>
            <p className="text-sm text-xen-dark-400">
              Configure limits to protect sender reputation
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-xen-dark-300 mb-2">
              Max Emails Per Day
            </label>
            <input
              type="number"
              defaultValue={200}
              className="w-full px-4 py-2.5 bg-xen-dark-800/50 border border-xen-dark-700 rounded-xl text-white focus:border-xen-red-500 focus:ring-1 focus:ring-xen-red-500 transition-colors"
            />
            <p className="text-xs text-xen-dark-500 mt-1">Hard limit: 500</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-xen-dark-300 mb-2">
              Max Emails Per Hour
            </label>
            <input
              type="number"
              defaultValue={20}
              className="w-full px-4 py-2.5 bg-xen-dark-800/50 border border-xen-dark-700 rounded-xl text-white focus:border-xen-red-500 focus:ring-1 focus:ring-xen-red-500 transition-colors"
            />
            <p className="text-xs text-xen-dark-500 mt-1">Hard limit: 50</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-xen-dark-300 mb-2">
              Max Bounce Rate (%)
            </label>
            <input
              type="number"
              defaultValue={5}
              step={0.1}
              className="w-full px-4 py-2.5 bg-xen-dark-800/50 border border-xen-dark-700 rounded-xl text-white focus:border-xen-red-500 focus:ring-1 focus:ring-xen-red-500 transition-colors"
            />
            <p className="text-xs text-xen-dark-500 mt-1">System stops at 10%</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-xen-dark-300 mb-2">
              Max Complaint Rate (%)
            </label>
            <input
              type="number"
              defaultValue={0.1}
              step={0.01}
              className="w-full px-4 py-2.5 bg-xen-dark-800/50 border border-xen-dark-700 rounded-xl text-white focus:border-xen-red-500 focus:ring-1 focus:ring-xen-red-500 transition-colors"
            />
            <p className="text-xs text-xen-dark-500 mt-1">System stops at 0.5%</p>
          </div>
        </div>
      </motion.div>

      {/* Send Window */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="glass rounded-2xl p-6 border border-xen-dark-700/50"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-blue-500/20 flex items-center justify-center">
            <Clock className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Send Window</h2>
            <p className="text-sm text-xen-dark-400">Configure when emails can be sent</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-xen-dark-300 mb-2">
              Start Time
            </label>
            <input
              type="time"
              defaultValue="09:00"
              className="w-full px-4 py-2.5 bg-xen-dark-800/50 border border-xen-dark-700 rounded-xl text-white focus:border-xen-red-500 focus:ring-1 focus:ring-xen-red-500 transition-colors"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-xen-dark-300 mb-2">
              End Time
            </label>
            <input
              type="time"
              defaultValue="17:00"
              className="w-full px-4 py-2.5 bg-xen-dark-800/50 border border-xen-dark-700 rounded-xl text-white focus:border-xen-red-500 focus:ring-1 focus:ring-xen-red-500 transition-colors"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-xen-dark-300 mb-2">Timezone</label>
            <select className="w-full px-4 py-2.5 bg-xen-dark-800/50 border border-xen-dark-700 rounded-xl text-white focus:border-xen-red-500 focus:ring-1 focus:ring-xen-red-500 transition-colors">
              <option value="America/New_York">Eastern Time (ET)</option>
              <option value="America/Chicago">Central Time (CT)</option>
              <option value="America/Denver">Mountain Time (MT)</option>
              <option value="America/Los_Angeles">Pacific Time (PT)</option>
              <option value="UTC">UTC</option>
            </select>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="weekdaysOnly"
              defaultChecked
              className="w-5 h-5 rounded bg-xen-dark-800 border-xen-dark-600 text-xen-red-500 focus:ring-xen-red-500"
            />
            <label htmlFor="weekdaysOnly" className="text-sm text-xen-dark-300">
              Send on weekdays only
            </label>
          </div>
        </div>
      </motion.div>

      {/* IMAP Settings */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="glass rounded-2xl p-6 border border-xen-dark-700/50"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-green-500/20 flex items-center justify-center">
            <Mail className="w-5 h-5 text-green-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Reply Detection</h2>
            <p className="text-sm text-xen-dark-400">Configure IMAP monitoring settings</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-xen-dark-300 mb-2">
              Check Interval (minutes)
            </label>
            <input
              type="number"
              defaultValue={5}
              className="w-full px-4 py-2.5 bg-xen-dark-800/50 border border-xen-dark-700 rounded-xl text-white focus:border-xen-red-500 focus:ring-1 focus:ring-xen-red-500 transition-colors"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-xen-dark-300 mb-2">
              Look Back (hours)
            </label>
            <input
              type="number"
              defaultValue={24}
              className="w-full px-4 py-2.5 bg-xen-dark-800/50 border border-xen-dark-700 rounded-xl text-white focus:border-xen-red-500 focus:ring-1 focus:ring-xen-red-500 transition-colors"
            />
          </div>
        </div>
      </motion.div>

      {/* Save Button */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="flex justify-end"
      >
        <Button icon={Save}>Save Settings</Button>
      </motion.div>
    </div>
  )
}

