import { Outlet } from 'react-router-dom'
import { motion } from 'framer-motion'

export default function TemplatesIndex() {
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
            Email Templates
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-gray-500 mt-1"
          >
            Create and manage your email templates
          </motion.p>
        </div>
      </div>

      {/* Placeholders Info */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-4 rounded-xl bg-gray-50 border border-gray-200"
      >
        <h3 className="text-sm font-medium text-gray-700 mb-2">Available Placeholders</h3>
        <div className="flex flex-wrap gap-2">
          {['{{name}}', '{{first_name}}', '{{last_name}}', '{{company}}', '{{industry}}', '{{title}}'].map((placeholder) => (
            <code key={placeholder} className="px-2 py-1 rounded bg-gray-200 text-enterprise-red text-xs">
              {placeholder}
            </code>
          ))}
        </div>
      </motion.div>

      {/* Nested Routes */}
      <Outlet />
    </div>
  )
}
