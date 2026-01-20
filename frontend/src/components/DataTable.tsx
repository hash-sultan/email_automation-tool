import { motion } from 'framer-motion'
import clsx from 'clsx'

interface Column<T> {
  key: string
  header: string
  render?: (item: T) => React.ReactNode
  className?: string
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  loading?: boolean
  emptyMessage?: string
  onRowClick?: (item: T) => void
}

export default function DataTable<T extends { id: number | string }>({
  columns,
  data,
  loading = false,
  emptyMessage = 'No data found',
  onRowClick,
}: DataTableProps<T>) {
  if (loading) {
    return (
      <div className="glass rounded-2xl border border-xen-dark-700/50 overflow-hidden">
        <div className="p-8 text-center">
          <div className="w-8 h-8 border-2 border-xen-red-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xen-dark-400 mt-4">Loading...</p>
        </div>
      </div>
    )
  }

  if (data.length === 0) {
    return (
      <div className="glass rounded-2xl border border-xen-dark-700/50 overflow-hidden">
        <div className="p-8 text-center">
          <p className="text-xen-dark-400">{emptyMessage}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="glass rounded-2xl border border-xen-dark-700/50 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-xen-dark-700/50">
              {columns.map((column) => (
                <th
                  key={column.key}
                  className={clsx(
                    'px-6 py-4 text-left text-xs font-semibold text-xen-dark-400 uppercase tracking-wider',
                    column.className
                  )}
                >
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-xen-dark-800/50">
            {data.map((item, index) => (
              <motion.tr
                key={item.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                onClick={() => onRowClick?.(item)}
                className={clsx(
                  'hover:bg-xen-dark-800/30 transition-colors',
                  onRowClick && 'cursor-pointer'
                )}
              >
                {columns.map((column) => (
                  <td
                    key={column.key}
                    className={clsx(
                      'px-6 py-4 text-sm text-xen-dark-200',
                      column.className
                    )}
                  >
                    {column.render
                      ? column.render(item)
                      : (item as Record<string, unknown>)[column.key] as React.ReactNode}
                  </td>
                ))}
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

