import clsx from 'clsx'

interface BadgeProps {
  children: React.ReactNode
  variant?: 'success' | 'warning' | 'error' | 'info' | 'default'
  size?: 'sm' | 'md'
  pulse?: boolean
}

const variants = {
  success: 'bg-green-500/20 text-green-400 border-green-500/30',
  warning: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  error: 'bg-red-500/20 text-red-400 border-red-500/30',
  info: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  default: 'bg-xen-dark-700/50 text-xen-dark-300 border-xen-dark-600/50',
}

const sizes = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-3 py-1 text-sm',
}

export default function Badge({
  children,
  variant = 'default',
  size = 'sm',
  pulse = false,
}: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 font-medium rounded-full border',
        variants[variant],
        sizes[size]
      )}
    >
      {pulse && (
        <span className="relative flex h-2 w-2">
          <span
            className={clsx(
              'animate-ping absolute inline-flex h-full w-full rounded-full opacity-75',
              variant === 'success' && 'bg-green-400',
              variant === 'warning' && 'bg-yellow-400',
              variant === 'error' && 'bg-red-400',
              variant === 'info' && 'bg-blue-400',
              variant === 'default' && 'bg-xen-dark-400'
            )}
          />
          <span
            className={clsx(
              'relative inline-flex rounded-full h-2 w-2',
              variant === 'success' && 'bg-green-400',
              variant === 'warning' && 'bg-yellow-400',
              variant === 'error' && 'bg-red-400',
              variant === 'info' && 'bg-blue-400',
              variant === 'default' && 'bg-xen-dark-400'
            )}
          />
        </span>
      )}
      {children}
    </span>
  )
}

