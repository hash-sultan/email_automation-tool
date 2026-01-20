import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard,
  Send,
  Users,
  FileText,
  Mail,
  BarChart3,
  Settings,
  Zap,
  Shield,
  Bell,
} from 'lucide-react'
import clsx from 'clsx'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Campaigns', href: '/campaigns', icon: Send },
  { name: 'Leads', href: '/leads', icon: Users },
  { name: 'Templates', href: '/templates', icon: FileText },
  { name: 'Senders', href: '/senders', icon: Mail },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export default function Layout() {
  const location = useLocation()

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <motion.aside
        initial={{ x: -280 }}
        animate={{ x: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="fixed left-0 top-0 h-screen w-64 glass border-r border-xen-dark-700/50 z-50"
      >
        {/* Logo */}
        <div className="h-16 flex items-center px-6 border-b border-xen-dark-700/50">
          <motion.div
            className="flex items-center gap-3"
            whileHover={{ scale: 1.02 }}
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-xen-red-500 to-xen-red-700 flex items-center justify-center glow-red-sm">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-lg text-white">XenFlow</h1>
              <p className="text-xs text-xen-dark-400">Email Automation</p>
            </div>
          </motion.div>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-1">
          {navigation.map((item, index) => (
            <motion.div
              key={item.name}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 + 0.2 }}
            >
              <NavLink
                to={item.href}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 group',
                    isActive
                      ? 'bg-gradient-to-r from-xen-red-600/20 to-xen-red-500/10 text-xen-red-400 border border-xen-red-500/30'
                      : 'text-xen-dark-300 hover:text-white hover:bg-xen-dark-800/50'
                  )
                }
              >
                <item.icon
                  className={clsx(
                    'w-5 h-5 transition-transform duration-300 group-hover:scale-110'
                  )}
                />
                <span className="font-medium">{item.name}</span>
              </NavLink>
            </motion.div>
          ))}
        </nav>

        {/* Safety Status */}
        <div className="absolute bottom-0 left-0 right-0 p-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="glass rounded-xl p-4 border border-green-500/30 bg-green-500/5"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-green-500/20 flex items-center justify-center">
                <Shield className="w-4 h-4 text-green-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-green-400">System Safe</p>
                <p className="text-xs text-xen-dark-400">All checks passed</p>
              </div>
            </div>
          </motion.div>
        </div>
      </motion.aside>

      {/* Main Content */}
      <div className="flex-1 ml-64">
        {/* Header */}
        <motion.header
          initial={{ y: -60 }}
          animate={{ y: 0 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="h-16 glass border-b border-xen-dark-700/50 flex items-center justify-between px-6 sticky top-0 z-40"
        >
          <div>
            <h2 className="text-lg font-semibold text-white">
              {navigation.find((n) => n.href === location.pathname)?.name || 'Dashboard'}
            </h2>
          </div>

          <div className="flex items-center gap-4">
            {/* Notifications */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="relative p-2 rounded-xl hover:bg-xen-dark-800/50 transition-colors"
            >
              <Bell className="w-5 h-5 text-xen-dark-400" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-xen-red-500 rounded-full" />
            </motion.button>

            {/* User Menu */}
            <motion.div
              whileHover={{ scale: 1.02 }}
              className="flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-xen-dark-800/50 transition-colors cursor-pointer"
            >
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-xen-red-500 to-xen-red-700 flex items-center justify-center">
                <span className="text-sm font-bold text-white">A</span>
              </div>
              <span className="text-sm font-medium text-xen-dark-200">Admin</span>
            </motion.div>
          </div>
        </motion.header>

        {/* Page Content */}
        <main className="p-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}

