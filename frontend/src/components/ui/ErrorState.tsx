import { AlertTriangle, RefreshCw } from 'lucide-react'
import { clsx } from 'clsx'

interface ErrorStateProps {
  title?: string
  message: string
  onRetry?: () => void
  retryLabel?: string
  className?: string
}

export function ErrorState({
  title = 'Something went wrong',
  message,
  onRetry,
  retryLabel = 'Try again',
  className,
}: ErrorStateProps) {
  return (
    <div
      className={clsx(
        'flex flex-col items-center justify-center text-center py-16 px-6',
        className,
      )}
    >
      <div className="mb-4 w-12 h-12 rounded-xl bg-danger-subtle flex items-center justify-center border border-danger/20">
        <AlertTriangle size={22} className="text-danger" />
      </div>
      <h3 className="font-semibold text-text-primary text-base">{title}</h3>
      <p className="mt-1 text-sm text-text-secondary max-w-sm">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className={clsx(
            'mt-5 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium',
            'border border-border text-text-secondary bg-canvas',
            'hover:bg-surface hover:text-text-primary transition-colors',
          )}
        >
          <RefreshCw size={13} />
          {retryLabel}
        </button>
      )}
    </div>
  )
}
