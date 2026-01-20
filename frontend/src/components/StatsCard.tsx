import { motion } from 'framer-motion'
import { LucideIcon } from 'lucide-react'
import clsx from 'clsx'

interface StatsCardProps {
  title: string
  value: string | number
  change?: number
  changeLabel?: string
  icon: LucideIcon
  color?: 'red' | 'green' | 'blue' | 'yellow' | 'purple'
  delay?: number
}

const colorClasses = {
  red: {
    bg: 'bg-xen-red-500/10',
    border: 'border-xen-red-500/30',
    icon: 'bg-xen-red-500/20 text-xen-red-400',
    glow: 'glow-red-sm',
  },
  green: {
    bg: 'bg-green-500/10',
    border: 'border-green-500/30',
    icon: 'bg-green-500/20 text-green-400',
    glow: '',
  },
  blue: {
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    icon: 'bg-blue-500/20 text-blue-400',
    glow: '',
  },
  yellow: {
    bg: 'bg-yellow-500/10',
    border: 'border-yellow-500/30',
    icon: 'bg-yellow-500/20 text-yellow-400',
    glow: '',
  },
  purple: {
    bg: 'bg-purple-500/10',
    border: 'border-purple-500/30',
    icon: 'bg-purple-500/20 text-purple-400',
    glow: '',
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
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      whileHover={{ scale: 1.02, y: -2 }}
      className={clsx(
        'glass rounded-2xl p-6 border transition-all duration-300',
        colors.bg,
        colors.border,
        colors.glow
      )}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-xen-dark-400">{title}</p>
          <motion.p
            initial={{ scale: 0.5 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.5, delay: delay + 0.2, type: 'spring' }}
            className="text-3xl font-bold text-white mt-2"
          >
            {typeof value === 'number' ? value.toLocaleString() : value}
          </motion.p>
          {change !== undefined && (
            <p
              className={clsx(
                'text-sm mt-2',
                change >= 0 ? 'text-green-400' : 'text-red-400'
              )}
            >
              {change >= 0 ? '↑' : '↓'} {Math.abs(change)}%
              {changeLabel && (
                <span className="text-xen-dark-500 ml-1">{changeLabel}</span>
              )}
            </p>
          )}
        </div>
        <div className={clsx('p-3 rounded-xl', colors.icon)}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </motion.div>
  )
}

