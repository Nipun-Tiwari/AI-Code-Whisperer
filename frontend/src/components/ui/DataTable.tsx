import type { ReactNode } from 'react'
import { clsx } from 'clsx'
import { TableLoadingSkeleton } from './LoadingSkeleton'
import { EmptyState } from './EmptyState'
import { ErrorState } from './ErrorState'

export interface ColumnDef<T> {
  key: string
  header: string
  width?: string
  align?: 'left' | 'right' | 'center'
  render: (row: T) => ReactNode
}

interface DataTableProps<T> {
  columns: ColumnDef<T>[]
  data: T[]
  keyExtractor: (row: T) => string
  isLoading?: boolean
  error?: string | null
  onRetry?: () => void
  emptyTitle?: string
  emptyDescription?: string
  emptyAction?: ReactNode
  className?: string
}

export function DataTable<T>({
  columns,
  data,
  keyExtractor,
  isLoading,
  error,
  onRetry,
  emptyTitle = 'No data',
  emptyDescription,
  emptyAction,
  className,
}: DataTableProps<T>) {
  return (
    <div className={clsx('border border-border rounded-lg overflow-hidden', className)}>
      <div className="overflow-x-auto">
        <table className="w-full text-sm" role="table">
          <thead>
            <tr className="bg-surface border-b border-border" role="row">
              {columns.map((col) => (
                <th
                  key={col.key}
                  scope="col"
                  className={clsx(
                    'px-4 py-2.5 text-xs font-semibold text-text-secondary whitespace-nowrap',
                    col.align === 'right' && 'text-right',
                    col.align === 'center' && 'text-center',
                    col.align !== 'right' && col.align !== 'center' && 'text-left',
                  )}
                  style={{ width: col.width }}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          {!isLoading && !error && data.length > 0 && (
            <tbody className="divide-y divide-border-subtle">
              {data.map((row) => (
                <tr
                  key={keyExtractor(row)}
                  role="row"
                  className="hover:bg-hover transition-colors duration-100"
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={clsx(
                        'px-4 py-3 text-text-primary',
                        col.align === 'right' && 'text-right',
                        col.align === 'center' && 'text-center',
                      )}
                    >
                      {col.render(row)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          )}
        </table>
      </div>
      {isLoading && <TableLoadingSkeleton cols={columns.length} />}
      {!isLoading && error && (
        <ErrorState message={error} onRetry={onRetry} />
      )}
      {!isLoading && !error && data.length === 0 && (
        <EmptyState
          title={emptyTitle}
          description={emptyDescription}
          action={emptyAction}
          size="sm"
        />
      )}
    </div>
  )
}
