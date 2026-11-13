import { clsx } from 'clsx'
import type { ReactNode } from 'react'

interface PageHeaderProps {
  title: string
  subtitle?: string
  actions?: ReactNode
  className?: string
}

export function PageHeader({ title, subtitle, actions, className }: PageHeaderProps) {
  return (
    <div
      className={clsx(
        'flex items-start justify-between gap-4 px-6 py-4 border-b border-border bg-canvas shrink-0',
        className,
      )}
    >
      <div className="min-w-0">
        <h1 className="text-lg font-semibold text-text-primary leading-tight">{title}</h1>
        {subtitle && (
          <p className="mt-0.5 text-sm text-text-secondary">{subtitle}</p>
        )}
      </div>
      {actions && (
        <div className="flex items-center gap-2 shrink-0 mt-0.5">{actions}</div>
      )}
    </div>
  )
}
