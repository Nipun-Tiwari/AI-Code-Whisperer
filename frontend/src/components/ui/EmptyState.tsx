import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import { clsx } from 'clsx'

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description?: string
  action?: ReactNode
  className?: string
  size?: 'sm' | 'md' | 'lg'
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
  size = 'md',
}: EmptyStateProps) {
  return (
    <div
      role="status"
      aria-label={title}
      className={clsx(
        'flex flex-col items-center justify-center text-center',
        size === 'sm' && 'py-8 px-4',
        size === 'md' && 'py-16 px-6',
        size === 'lg' && 'py-24 px-8',
        className,
      )}
    >
      {Icon && (
        <div className="mb-4 w-12 h-12 rounded-xl bg-surface flex items-center justify-center border border-border">
          <Icon
            size={size === 'sm' ? 18 : 22}
            className="text-text-muted"
            aria-hidden="true"
          />
        </div>
      )}
      <h3
        className={clsx(
          'font-semibold text-text-primary',
          size === 'sm' ? 'text-sm' : 'text-base',
        )}
      >
        {title}
      </h3>
      {description && (
        <p
          className={clsx(
            'mt-1 text-text-secondary max-w-sm',
            size === 'sm' ? 'text-xs' : 'text-sm',
          )}
        >
          {description}
        </p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
