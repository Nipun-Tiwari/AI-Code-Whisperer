import { AlertTriangle, RefreshCw } from 'lucide-react'
import { clsx } from 'clsx'

interface QuotaNoticeProps {
  serviceName: string
  message: string
  retryable: boolean
  retryAfter?: string | null
  onRetry?: () => void
  className?: string
}

export function QuotaNotice({
  serviceName,
  message,
  retryable,
  retryAfter,
  onRetry,
  className,
}: QuotaNoticeProps) {
  return (
    <div
      className={clsx(
        'flex gap-3 p-4 rounded-lg border',
        'bg-warning-subtle border-warning/30',
        className,
      )}
      role="alert"
    >
      <AlertTriangle
        size={15}
        className="shrink-0 mt-0.5 text-warning"
        aria-hidden="true"
      />
      <div className="flex-1 min-w-0 space-y-1">
        <p className="text-sm font-medium text-text-primary">
          {serviceName} unavailable
        </p>
        <p className="text-sm text-text-secondary">{message}</p>
        {retryAfter && (
          <p className="text-xs text-text-muted">
            Available after: {retryAfter}
          </p>
        )}
        {!retryAfter && (
          <p className="text-xs text-text-muted">
            Check the{' '}
            <a href="/usage" className="underline hover:text-text-secondary transition-colors">
              Usage &amp; Infrastructure
            </a>{' '}
            page for details.
          </p>
        )}
        {retryable && onRetry && (
          <button
            onClick={onRetry}
            className={clsx(
              'mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium',
              'border border-border bg-canvas text-text-secondary',
              'hover:bg-hover hover:text-text-primary transition-colors',
            )}
          >
            <RefreshCw size={11} />
            Retry
          </button>
        )}
      </div>
    </div>
  )
}
