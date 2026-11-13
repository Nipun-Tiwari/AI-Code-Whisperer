import { clsx } from 'clsx'

export type StatusVariant =
  | 'operational'
  | 'degraded'
  | 'rate_limited'
  | 'quota_exhausted'
  | 'auth_error'
  | 'unavailable'
  | 'usage_unavailable'
  | 'unknown'
  | 'not_configured'
  | 'indexing'
  | 'completed'
  | 'failed'
  | 'queued'
  | 'partial'
  | 'paused'
  | 'active'
  | 'stale'
  | 'pending'

interface StatusConfig {
  label: string
  dotColor: string
  bgColor: string
  textColor: string
}

const STATUS_CONFIG: Record<StatusVariant, StatusConfig> = {
  operational: {
    label: 'Operational',
    dotColor: 'var(--color-success)',
    bgColor: 'var(--color-success-subtle)',
    textColor: 'var(--color-success)',
  },
  degraded: {
    label: 'Degraded',
    dotColor: 'var(--color-warning)',
    bgColor: 'var(--color-warning-subtle)',
    textColor: 'var(--color-warning)',
  },
  rate_limited: {
    label: 'Rate Limited',
    dotColor: 'var(--color-warning)',
    bgColor: 'var(--color-warning-subtle)',
    textColor: 'var(--color-warning)',
  },
  quota_exhausted: {
    label: 'Quota Exhausted',
    dotColor: 'var(--color-danger)',
    bgColor: 'var(--color-danger-subtle)',
    textColor: 'var(--color-danger)',
  },
  auth_error: {
    label: 'Auth Error',
    dotColor: 'var(--color-danger)',
    bgColor: 'var(--color-danger-subtle)',
    textColor: 'var(--color-danger)',
  },
  unavailable: {
    label: 'Unavailable',
    dotColor: 'var(--color-danger)',
    bgColor: 'var(--color-danger-subtle)',
    textColor: 'var(--color-danger)',
  },
  usage_unavailable: {
    label: 'Usage Unavailable',
    dotColor: 'var(--color-text-muted)',
    bgColor: 'var(--color-surface)',
    textColor: 'var(--color-text-secondary)',
  },
  unknown: {
    label: 'Unknown',
    dotColor: 'var(--color-text-muted)',
    bgColor: 'var(--color-surface)',
    textColor: 'var(--color-text-secondary)',
  },
  not_configured: {
    label: 'Not Configured',
    dotColor: 'var(--color-text-muted)',
    bgColor: 'var(--color-surface)',
    textColor: 'var(--color-text-secondary)',
  },
  indexing: {
    label: 'Indexing',
    dotColor: 'var(--color-info)',
    bgColor: 'var(--color-info-subtle)',
    textColor: 'var(--color-info)',
  },
  completed: {
    label: 'Completed',
    dotColor: 'var(--color-success)',
    bgColor: 'var(--color-success-subtle)',
    textColor: 'var(--color-success)',
  },
  failed: {
    label: 'Failed',
    dotColor: 'var(--color-danger)',
    bgColor: 'var(--color-danger-subtle)',
    textColor: 'var(--color-danger)',
  },
  queued: {
    label: 'Queued',
    dotColor: 'var(--color-text-muted)',
    bgColor: 'var(--color-surface)',
    textColor: 'var(--color-text-secondary)',
  },
  partial: {
    label: 'Partial',
    dotColor: 'var(--color-warning)',
    bgColor: 'var(--color-warning-subtle)',
    textColor: 'var(--color-warning)',
  },
  paused: {
    label: 'Paused',
    dotColor: 'var(--color-warning)',
    bgColor: 'var(--color-warning-subtle)',
    textColor: 'var(--color-warning)',
  },
  active: {
    label: 'Active',
    dotColor: 'var(--color-success)',
    bgColor: 'var(--color-success-subtle)',
    textColor: 'var(--color-success)',
  },
  stale: {
    label: 'Stale',
    dotColor: 'var(--color-warning)',
    bgColor: 'var(--color-warning-subtle)',
    textColor: 'var(--color-warning)',
  },
  pending: {
    label: 'Pending',
    dotColor: 'var(--color-text-muted)',
    bgColor: 'var(--color-surface)',
    textColor: 'var(--color-text-secondary)',
  },
}

interface StatusBadgeProps {
  status: StatusVariant
  label?: string
  size?: 'sm' | 'md'
  className?: string
}

export function StatusBadge({ status, label, size = 'md', className }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.unknown

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full font-medium whitespace-nowrap',
        size === 'sm' ? 'text-[11px] px-2 py-0.5' : 'text-xs px-2.5 py-1',
        className,
      )}
      style={{
        backgroundColor: config.bgColor,
        color: config.textColor,
      }}
    >
      <span
        className="shrink-0 rounded-full"
        style={{
          width: size === 'sm' ? '5px' : '6px',
          height: size === 'sm' ? '5px' : '6px',
          backgroundColor: config.dotColor,
        }}
        aria-hidden="true"
      />
      {label ?? config.label}
    </span>
  )
}
