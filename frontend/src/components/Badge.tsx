import clsx from 'clsx'

interface BadgeProps {
  children: React.ReactNode
  variant?: 'success' | 'warning' | 'error' | 'info' | 'default'
  size?: 'sm' | 'md'
  pulse?: boolean
}

const variants = {
  success: 'bg-green-50 text-green-700 border-green-200',
  warning: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  error: 'bg-enterprise-red/10 text-enterprise-red border-enterprise-red/30',
  info: 'bg-gray-100 text-gray-700 border-gray-300',
  default: 'bg-gray-50 text-gray-700 border-gray-200',
}

const sizes = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
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
        'inline-flex items-center gap-1.5 font-medium rounded-md border',
        variants[variant],
        sizes[size]
      )}
    >
      {pulse && (
        <span className="relative flex h-2 w-2">
          <span
            className={clsx(
              'animate-ping absolute inline-flex h-full w-full rounded-full opacity-75',
              variant === 'success' && 'bg-green-600',
              variant === 'warning' && 'bg-yellow-600',
              variant === 'error' && 'bg-enterprise-red',
              variant === 'info' && 'bg-gray-600',
              variant === 'default' && 'bg-gray-600'
            )}
          />
          <span
            className={clsx(
              'relative inline-flex rounded-full h-2 w-2',
              variant === 'success' && 'bg-green-600',
              variant === 'warning' && 'bg-yellow-600',
              variant === 'error' && 'bg-enterprise-red',
              variant === 'info' && 'bg-gray-600',
              variant === 'default' && 'bg-gray-600'
            )}
          />
        </span>
      )}
      {children}
    </span>
  )
}
