import { motion } from 'framer-motion'
import { LucideIcon, Loader2 } from 'lucide-react'
import clsx from 'clsx'

interface ButtonProps {
  children: React.ReactNode
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  icon?: LucideIcon
  iconPosition?: 'left' | 'right'
  loading?: boolean
  disabled?: boolean
  onClick?: () => void
  type?: 'button' | 'submit'
  className?: string
}

const variants = {
  primary: 'bg-gradient-to-r from-xen-red-600 to-xen-red-500 hover:from-xen-red-500 hover:to-xen-red-400 text-white glow-red-sm',
  secondary: 'bg-xen-dark-800 hover:bg-xen-dark-700 text-xen-dark-200 border border-xen-dark-600',
  danger: 'bg-red-600/20 hover:bg-red-600/30 text-red-400 border border-red-500/30',
  ghost: 'bg-transparent hover:bg-xen-dark-800/50 text-xen-dark-300 hover:text-white',
}

const sizes = {
  sm: 'px-3 py-1.5 text-sm gap-1.5',
  md: 'px-4 py-2 text-sm gap-2',
  lg: 'px-6 py-3 text-base gap-2',
}

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  icon: Icon,
  iconPosition = 'left',
  loading = false,
  disabled = false,
  onClick,
  type = 'button',
  className,
}: ButtonProps) {
  return (
    <motion.button
      whileHover={{ scale: disabled ? 1 : 1.02 }}
      whileTap={{ scale: disabled ? 1 : 0.98 }}
      type={type}
      disabled={disabled || loading}
      onClick={onClick}
      className={clsx(
        'inline-flex items-center justify-center font-medium rounded-xl transition-all duration-300',
        variants[variant],
        sizes[size],
        (disabled || loading) && 'opacity-50 cursor-not-allowed',
        className
      )}
    >
      {loading ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        <>
          {Icon && iconPosition === 'left' && <Icon className="w-4 h-4" />}
          {children}
          {Icon && iconPosition === 'right' && <Icon className="w-4 h-4" />}
        </>
      )}
    </motion.button>
  )
}

