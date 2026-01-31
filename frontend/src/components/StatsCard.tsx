import { motion } from 'framer-motion'
import { LucideIcon } from 'lucide-react'
import clsx from 'clsx'

interface StatsCardProps {
  title: string
  value: string | number
  change?: number
  changeLabel?: string
  icon: LucideIcon
  color?: 'red' | 'green' | 'blue' | 'purple'
  delay?: number
}

const colorClasses = {
  red: {
    icon: 'text-enterprise-red',
    change: 'text-enterprise-red',
  },
  green: {
    icon: 'text-green-600',
    change: 'text-green-600',
  },
  blue: {
    icon: 'text-enterprise-red',
    change: 'text-enterprise-red',
  },
  purple: {
    icon: 'text-purple-600',
    change: 'text-purple-600',
  },
}

export default function StatsCard({
  title,
  value,
  change,
  changeLabel,
  icon: Icon,
  color = 'red',
  delay = 0,
}: StatsCardProps) {
  const colors = colorClasses[color]

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay }}
      whileHover={{ y: -2 }}
      className="card card-hover p-6"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-500 mb-1">{title}</p>
          <motion.p
            initial={{ scale: 0.95 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.3, delay: delay + 0.1 }}
            className="text-3xl font-semibold text-gray-900 mt-2"
          >
            {typeof value === 'number' ? value.toLocaleString() : value}
          </motion.p>
          {change !== undefined && (
            <p className={clsx('text-sm mt-2 font-medium', colors.change)}>
              {change >= 0 ? '↑' : '↓'} {Math.abs(change)}%
              {changeLabel && (
                <span className="text-gray-400 ml-1 font-normal">{changeLabel}</span>
              )}
            </p>
          )}
        </div>
        <div className={clsx('p-3 rounded-md bg-gray-50', colors.icon)}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </motion.div>
  )
}
