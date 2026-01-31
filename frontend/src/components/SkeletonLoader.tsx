import { motion } from 'framer-motion'

interface SkeletonLoaderProps {
  lines?: number
  className?: string
  showAvatar?: boolean
}

export default function SkeletonLoader({ lines = 3, className = '', showAvatar = false }: SkeletonLoaderProps) {
  return (
    <div className={`space-y-3 ${className}`}>
      {showAvatar && (
        <div className="flex items-center gap-3">
          <div className="skeleton w-10 h-10 rounded-full" />
          <div className="flex-1 space-y-2">
            <div className="skeleton h-4 w-1/4 rounded" />
            <div className="skeleton h-3 w-1/3 rounded" />
          </div>
        </div>
      )}
      {Array.from({ length: lines }).map((_, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: i * 0.1 }}
          className="skeleton-shimmer h-4 rounded"
          style={{ width: i === lines - 1 ? '60%' : '100%' }}
        />
      ))}
    </div>
  )
}

export function SkeletonCard() {
  return (
    <div className="card p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1 space-y-3">
          <div className="skeleton-shimmer h-4 w-1/4 rounded" />
          <div className="skeleton-shimmer h-8 w-1/3 rounded" />
        </div>
        <div className="skeleton w-12 h-12 rounded-lg" />
      </div>
      <div className="space-y-2">
        <div className="skeleton-shimmer h-3 w-full rounded" />
        <div className="skeleton-shimmer h-3 w-3/4 rounded" />
      </div>
    </div>
  )
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="table-header">
              <th className="text-left px-6 py-4">
                <div className="skeleton-shimmer h-4 w-24 rounded" />
              </th>
              <th className="text-left px-6 py-4">
                <div className="skeleton-shimmer h-4 w-20 rounded" />
              </th>
              <th className="text-left px-6 py-4">
                <div className="skeleton-shimmer h-4 w-28 rounded" />
              </th>
              <th className="text-left px-6 py-4">
                <div className="skeleton-shimmer h-4 w-16 rounded" />
              </th>
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: rows }).map((_, i) => (
              <tr key={i} className="table-row">
                <td className="table-cell">
                  <div className="skeleton-shimmer h-4 w-48 rounded" />
                </td>
                <td className="table-cell">
                  <div className="skeleton-shimmer h-4 w-32 rounded" />
                </td>
                <td className="table-cell">
                  <div className="skeleton-shimmer h-4 w-36 rounded" />
                </td>
                <td className="table-cell">
                  <div className="skeleton-shimmer h-6 w-20 rounded-md" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
