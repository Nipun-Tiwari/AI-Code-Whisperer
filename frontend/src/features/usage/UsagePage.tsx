import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  RefreshCw,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
} from 'lucide-react'
import { PageHeader, StatusBadge, ErrorState, LoadingSkeleton } from '@/components'
import type { StatusVariant } from '@/components'
import {
  getUsageOverview,
  refreshService,
  getUsageHistory,
  type ServiceStatus,
  type DashboardSummary,
} from '@/api/usage'
import { clsx } from 'clsx'

const CATEGORY_ORDER = ['ai', 'data', 'integration', 'platform']
const CATEGORY_LABELS: Record<string, string> = {
  ai: 'AI Services',
  data: 'Data & Storage',
  integration: 'Integrations',
  platform: 'Platform',
}

const SOURCE_LABELS: Record<string, string> = {
  provider_reported: 'Provider reported',
  codewhisperer_tracked: 'Tracked',
  not_available: 'N/A',
  unavailable: 'Unavailable',
}

const AUTO_REFRESH_OPTIONS = [
  { label: 'Off', value: 0 },
  { label: '30s', value: 30 },
  { label: '1m', value: 60 },
  { label: '5m', value: 300 },
]

function formatRelativeTime(isoString: string | null): string {
  if (!isoString) return '—'
  const diff = Date.now() - new Date(isoString).getTime()
  const seconds = Math.floor(diff / 1000)
  if (seconds < 10) return 'just now'
  if (seconds < 60) return `${seconds}s ago`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  return `${Math.floor(seconds / 3600)}h ago`
}

function formatMetricValue(value: number | null, unit: string): string {
  if (value === null || value === undefined) return '—'
  if (unit === 'MB') return `${value.toLocaleString()} MB`
  if (unit === 'bytes') {
    const mb = value / (1024 * 1024)
    return `${mb.toFixed(1)} MB`
  }
  return `${value.toLocaleString()} ${unit}`
}

function OverviewTile({
  label,
  count,
  icon: Icon,
  colorClass,
}: {
  label: string
  count: number
  icon: typeof CheckCircle2
  colorClass: string
}) {
  return (
    <div className="border border-border rounded-lg p-4 bg-canvas">
      <div className="flex items-center gap-2 mb-2">
        <Icon size={14} className={colorClass} aria-hidden="true" />
        <span className="text-xs text-text-muted">{label}</span>
      </div>
      <p className="text-3xl font-normal tabular-nums tracking-tight text-text-primary">
        {count}
      </p>
    </div>
  )
}

function ServiceRow({
  svc,
  isRefreshing,
  onRefresh,
}: {
  svc: ServiceStatus
  isRefreshing: boolean
  onRefresh: (key: string) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const { data: history } = useQuery({
    queryKey: ['usage-history', svc.serviceKey],
    queryFn: () => getUsageHistory(svc.serviceKey, 1),
    enabled: expanded,
    staleTime: 60_000,
  })

  const primaryMetric = svc.metrics[0] ?? null
  const badgeStatus = (svc.configured ? svc.status : 'not_configured') as StatusVariant

  return (
    <>
      <tr
        className={clsx(
          'cursor-pointer hover:bg-hover transition-colors',
          expanded && 'bg-hover',
        )}
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="w-4 shrink-0 text-text-muted">
              {expanded
                ? <ChevronDown size={12} aria-hidden="true" />
                : <ChevronRight size={12} aria-hidden="true" />}
            </span>
            <span className="text-sm font-medium text-text-primary">{svc.name}</span>
          </div>
        </td>
        <td className="px-4 py-3">
          <StatusBadge status={badgeStatus} size="sm" />
        </td>
        <td className="px-4 py-3">
          {primaryMetric ? (
            <div>
              <span className="text-sm text-text-primary font-mono tabular-nums">
                {primaryMetric.value !== null
                  ? formatMetricValue(primaryMetric.value, primaryMetric.unit)
                  : <span className="text-text-muted text-xs">Unavailable</span>
                }
              </span>
              {primaryMetric.value !== null && (
                <span className="ml-1.5 text-[11px] text-text-muted">
                  {SOURCE_LABELS[primaryMetric.sourceType] ?? primaryMetric.sourceType}
                </span>
              )}
            </div>
          ) : (
            <span className="text-xs text-text-muted">—</span>
          )}
        </td>
        <td className="px-4 py-3 text-xs text-text-muted">
          {formatRelativeTime(svc.lastChecked)}
        </td>
        <td className="px-4 py-3">
          <button
            onClick={(e) => { e.stopPropagation(); onRefresh(svc.serviceKey) }}
            disabled={isRefreshing}
            aria-label={`Refresh ${svc.name}`}
            title={`Refresh ${svc.name}`}
            className={clsx(
              'p-1.5 rounded hover:bg-surface transition-colors text-text-muted hover:text-text-secondary',
              'disabled:opacity-40 disabled:cursor-not-allowed',
            )}
          >
            <RefreshCw size={12} className={isRefreshing ? 'animate-spin' : ''} aria-hidden="true" />
          </button>
        </td>
      </tr>

      {expanded && (
        <tr className="bg-surface">
          <td colSpan={5} className="px-10 py-4 border-t border-border-subtle">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* All metrics */}
              <div>
                <h4 className="text-xs font-medium text-text-muted uppercase tracking-wider mb-2">Metrics</h4>
                <div className="space-y-1.5">
                  {svc.metrics.map((m) => (
                    <div key={m.key} className="flex items-center justify-between text-sm">
                      <span className="text-text-secondary">{m.label}</span>
                      <div className="flex items-center gap-2">
                        <span className="font-mono tabular-nums text-text-primary">
                          {m.value !== null ? formatMetricValue(m.value, m.unit) : <span className="text-text-muted text-xs">Unavailable</span>}
                        </span>
                        <span className="text-[11px] text-text-muted">
                          {SOURCE_LABELS[m.sourceType] ?? m.sourceType}
                        </span>
                      </div>
                    </div>
                  ))}
                  {svc.metrics.length === 0 && (
                    <p className="text-xs text-text-muted">No metrics available</p>
                  )}
                </div>
              </div>

              {/* Dependent features */}
              <div>
                <h4 className="text-xs font-medium text-text-muted uppercase tracking-wider mb-2">Dependent Features</h4>
                <div className="flex flex-wrap gap-1">
                  {(svc.dependentFeatures ?? []).map((f) => (
                    <span key={f} className="text-xs px-2 py-0.5 rounded border border-border bg-canvas text-text-secondary">
                      {f}
                    </span>
                  ))}
                </div>

                {/* Recent events */}
                {history && history.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-xs font-medium text-text-muted uppercase tracking-wider mb-2">Recent Activity (24h)</h4>
                    <div className="space-y-1">
                      {history.slice(0, 5).map((pt, i) => (
                        <div key={i} className="flex items-center justify-between text-xs">
                          <span className="text-text-muted">
                            {new Date(pt.recordedAt).toLocaleTimeString()}
                          </span>
                          <span className="text-text-secondary font-mono">
                            {pt.quantity.toLocaleString()} {pt.unit}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {svc.errorMessage && (
                  <p className="mt-3 text-xs text-danger">{svc.errorMessage}</p>
                )}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

export function UsagePage() {
  const qc = useQueryClient()
  const [autoRefreshSeconds, setAutoRefreshSeconds] = useState(0)
  const [refreshingKey, setRefreshingKey] = useState<string | null>(null)

  const { data, isLoading, isError, refetch } = useQuery<DashboardSummary>({
    queryKey: ['usage-overview'],
    queryFn: getUsageOverview,
    refetchInterval: autoRefreshSeconds > 0 ? autoRefreshSeconds * 1000 : false,
    staleTime: 10_000,
  })

  const refreshMutation = useMutation({
    mutationFn: refreshService,
    onMutate: (key) => setRefreshingKey(key),
    onSettled: () => {
      setRefreshingKey(null)
      qc.invalidateQueries({ queryKey: ['usage-overview'] })
    },
  })

  if (isLoading) {
    return (
      <div className="flex flex-col h-full">
        <PageHeader title="Usage & Infrastructure" subtitle="Service health, quota status and usage metrics" />
        <div className="p-6"><LoadingSkeleton rows={6} /></div>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex flex-col h-full">
        <PageHeader title="Usage & Infrastructure" subtitle="Service health, quota status and usage metrics" />
        <div className="p-6">
          <ErrorState
            title="Failed to load usage data"
            message="Could not reach the usage service. Check the backend is running."
            onRetry={() => refetch()}
          />
        </div>
      </div>
    )
  }

  const summary = data!
  const servicesByCategory: Record<string, ServiceStatus[]> = {}
  for (const svc of summary.services) {
    if (!servicesByCategory[svc.category]) servicesByCategory[svc.category] = []
    servicesByCategory[svc.category].push(svc)
  }

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Usage & Infrastructure"
        subtitle="Service health, quota status and usage metrics for CodeWhisperer"
        actions={
          <div className="flex items-center gap-3">
            {/* Auto-refresh selector */}
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-text-muted">Auto-refresh:</span>
              <div className="flex border border-border rounded-md overflow-hidden">
                {AUTO_REFRESH_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setAutoRefreshSeconds(opt.value)}
                    className={clsx(
                      'px-2.5 py-1 text-xs transition-colors',
                      autoRefreshSeconds === opt.value
                        ? 'bg-nav-active-bg text-nav-active-text font-medium'
                        : 'text-text-muted hover:bg-hover hover:text-text-secondary',
                    )}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
            <button
              onClick={() => refetch()}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm border border-border text-text-secondary hover:bg-hover transition-colors"
              aria-label="Refresh all services"
            >
              <RefreshCw size={13} aria-hidden="true" />
              Refresh all
            </button>
          </div>
        }
      />

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Overview strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <OverviewTile label="Operational" count={summary.operational} icon={CheckCircle2} colorClass="text-success" />
          <OverviewTile label="Degraded" count={summary.degraded} icon={AlertTriangle} colorClass="text-warning" />
          <OverviewTile label="Quota Exhausted" count={summary.quotaExhausted} icon={XCircle} colorClass="text-danger" />
          <OverviewTile label="Not Configured" count={summary.notConfigured} icon={HelpCircle} colorClass="text-text-muted" />
        </div>

        {/* Service groups */}
        {CATEGORY_ORDER.filter((cat) => servicesByCategory[cat]?.length).map((cat) => (
          <section key={cat}>
            <h2 className="text-xs font-medium text-text-muted uppercase tracking-wider mb-3">
              {CATEGORY_LABELS[cat] ?? cat}
            </h2>
            <div className="border border-border rounded-lg overflow-hidden bg-canvas">
              <table className="w-full text-sm" role="table">
                <thead>
                  <tr className="bg-surface border-b border-border">
                    <th scope="col" className="text-left px-4 py-2.5 text-xs font-medium text-text-secondary">Service</th>
                    <th scope="col" className="text-left px-4 py-2.5 text-xs font-medium text-text-secondary w-36">Status</th>
                    <th scope="col" className="text-left px-4 py-2.5 text-xs font-medium text-text-secondary">Usage</th>
                    <th scope="col" className="text-left px-4 py-2.5 text-xs font-medium text-text-secondary w-24">Last checked</th>
                    <th scope="col" className="px-4 py-2.5 w-12" aria-label="Actions"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {servicesByCategory[cat].map((svc) => (
                    <ServiceRow
                      key={svc.serviceKey}
                      svc={svc}
                      isRefreshing={refreshingKey === svc.serviceKey}
                      onRefresh={(key) => refreshMutation.mutate(key)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ))}

        {/* Attribution note */}
        <div className="flex items-start gap-2 p-3 rounded-lg bg-surface border border-border-subtle text-xs text-text-muted">
          <span className="shrink-0 mt-0.5" aria-hidden="true">ⓘ</span>
          <span>
            <strong className="text-text-secondary">Provider reported</strong> values come from the provider API.{' '}
            <strong className="text-text-secondary">Tracked</strong> values are CodeWhisperer internal counters.
            Unknown or unavailable metrics are never shown as zero.
          </span>
        </div>
      </div>
    </div>
  )
}
