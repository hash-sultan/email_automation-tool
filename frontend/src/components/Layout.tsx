import { useState } from 'react'
import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard,
  Send,
  Users,
  FileText,
  Mail,
  MessageSquare,
  BarChart3,
  Settings,
  Shield,
  ChevronLeft,
} from 'lucide-react'
import clsx from 'clsx'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Campaigns', href: '/campaigns', icon: Send },
  { name: 'Leads', href: '/leads', icon: Users },
  { name: 'Templates', href: '/templates', icon: FileText },
  { name: 'Senders', href: '/senders', icon: Mail },
  { name: 'Replies', href: '/replies', icon: MessageSquare },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export default function Layout() {
  const location = useLocation()
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* Sidebar */}
      <motion.aside
        animate={{ width: sidebarCollapsed ? 80 : 280 }}
        transition={{ duration: 0.25, ease: 'easeInOut' }}
        className="fixed left-0 top-0 h-screen bg-black z-50 border-r border-gray-900"
      >
        {/* Logo */}
        <div className="h-20 flex items-center px-4 border-b border-gray-900 relative">
          <AnimatePresence mode="wait">
            {!sidebarCollapsed ? (
              <motion.div
                key="expanded"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="flex items-center gap-4 flex-1 min-w-0"
              >
                <img 
                  src="/xenflow.png" 
                  alt="XenFlow Logo" 
                  className="h-16 w-auto object-contain flex-shrink-0"
                />
                <div className="min-w-0">
                  <h1 className="font-semibold text-lg text-white">XenFlow</h1>
                  <p className="text-xs text-gray-400">Email Automation</p>
                </div>
              </motion.div>
            ) : (
              <motion.img
                key="collapsed"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                src="/xenflow.png" 
                alt="XenFlow" 
                className="h-16 w-auto mx-auto"
              />
            )}
          </AnimatePresence>
          
          <motion.button
            whileTap={{ scale: 0.95 }}
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-md hover:bg-gray-900 transition-colors z-10"
            aria-label="Toggle sidebar"
          >
            {sidebarCollapsed ? (
              <ChevronLeft className="w-4 h-4 text-gray-400 rotate-180" />
            ) : (
              <ChevronLeft className="w-4 h-4 text-gray-400" />
            )}
          </motion.button>
        </div>

        {/* Navigation */}
        <nav className="p-3 space-y-1 overflow-y-auto h-[calc(100vh-5rem)]">
          {navigation.map((item, index) => (
            <motion.div
              key={item.name}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.15, delay: index * 0.02 }}
            >
              <NavLink
                to={item.href}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-3 px-3 py-2.5 rounded-md transition-all duration-200 group relative',
                    isActive
                      ? 'bg-enterprise-red text-white'
                      : 'text-gray-400 hover:text-white hover:bg-gray-900'
                  )
                }
              >
                <item.icon className="w-5 h-5 flex-shrink-0" />
                <AnimatePresence>
                  {!sidebarCollapsed && (
                    <motion.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.15 }}
                      className="font-medium text-sm whitespace-nowrap"
                    >
                      {item.name}
                    </motion.span>
                  )}
                </AnimatePresence>
                {sidebarCollapsed && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 0 }}
                    whileHover={{ opacity: 1 }}
                    transition={{ duration: 0.15 }}
                    className="absolute left-full ml-2 px-2 py-1 bg-gray-900 text-white text-sm rounded-md whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none z-50 border border-gray-800"
                  >
                    {item.name}
                  </motion.div>
                )}
              </NavLink>
            </motion.div>
          ))}
        </nav>

        {/* Safety Status */}
        <div className="absolute bottom-0 left-0 right-0 p-3 border-t border-gray-900">
          <AnimatePresence>
            {!sidebarCollapsed ? (
              <motion.div
                key="expanded"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="bg-gray-900 rounded-md p-3 border border-gray-800"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-md bg-green-500/20 flex items-center justify-center flex-shrink-0">
                    <Shield className="w-4 h-4 text-green-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white">System Safe</p>
                    <p className="text-xs text-gray-400 truncate">All checks passed</p>
                  </div>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="collapsed"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="flex justify-center"
              >
                <div className="w-10 h-10 rounded-md bg-green-500/20 flex items-center justify-center">
                  <Shield className="w-4 h-4 text-green-400" />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.aside>

      {/* Main Content */}
      <div 
        className="flex-1 transition-all duration-300"
        style={{ marginLeft: sidebarCollapsed ? 80 : 280 }}
      >
        {/* Header */}
        <motion.header
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.2 }}
          className="h-16 bg-gray-50 border-b border-gray-200 flex items-center justify-between px-6 sticky top-0 z-40"
        >
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              {navigation.find((n) => n.href === location.pathname)?.name || 'Dashboard'}
            </h2>
          </div>

          <div className="flex items-center gap-3">
            {/* User Menu */}
            <motion.div
              whileHover={{ scale: 1.02 }}
              className="flex items-center gap-3 px-3 py-1.5 rounded-md hover:bg-gray-100 transition-colors cursor-pointer"
            >
              <div className="w-8 h-8 rounded-md bg-enterprise-red flex items-center justify-center">
                <span className="text-sm font-semibold text-white">A</span>
              </div>
              <span className="text-sm font-medium text-gray-900">Admin</span>
            </motion.div>
          </div>
        </motion.header>

        {/* Page Content */}
        <main className="p-6 bg-gray-50 min-h-[calc(100vh-4rem)]">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}
