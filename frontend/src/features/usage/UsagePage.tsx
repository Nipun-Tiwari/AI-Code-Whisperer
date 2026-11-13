import { BarChart3, RefreshCw } from 'lucide-react'
import { PageHeader, StatusBadge } from '@/components'
import type { ServiceCategory } from '@/types'
import { clsx } from 'clsx'

// Static service registry — populated from backend in Phase 4
// For now shows "Not configured" for all services to satisfy the PRD requirement
// that unconfigured services show "Not configured", not zero or operational.
const SERVICE_REGISTRY: Array<{
  key: string
  name: string
  category: ServiceCategory
  provider: string
  dependentFeatures: string[]
}> = [
  {
    key: 'llm_provider',
    name: 'LLM Provider',
    category: 'ai',
    provider: 'Google Gemini',
    dependentFeatures: ['All agent workflows', 'Q&A', 'Investigation', 'Documentation'],
  },
  {
    key: 'embedding_provider',
    name: 'Embedding Provider',
    category: 'ai',
    provider: 'Google Gemini',
    dependentFeatures: ['Repository indexing', 'Code search'],
  },
  {
    key: 'qdrant',
    name: 'Qdrant',
    category: 'data',
    provider: 'Qdrant Cloud',
    dependentFeatures: ['Vector search', 'Code retrieval'],
  },
  {
    key: 'postgresql',
    name: 'PostgreSQL',
    category: 'data',
    provider: 'Neon',
    dependentFeatures: ['All data persistence'],
  },
  {
    key: 'object_storage',
    name: 'Object Storage',
    category: 'data',
    provider: 'Cloudflare R2',
    dependentFeatures: ['Generated documents', 'Repository artifacts'],
  },
  {
    key: 'cloud_run',
    name: 'Cloud Run',
    category: 'platform',
    provider: 'Google Cloud',
    dependentFeatures: ['API server', 'Indexing workers', 'MCP server'],
  },
  {
    key: 'github_api',
    name: 'GitHub API',
    category: 'integration',
    provider: 'GitHub',
    dependentFeatures: ['Repository access', 'File retrieval', 'Commit history'],
  },
  {
    key: 'redis',
    name: 'Redis (optional)',
    category: 'data',
    provider: 'Upstash',
    dependentFeatures: ['Caching (optional)'],
  },
]

const CATEGORY_LABELS: Record<ServiceCategory, string> = {
  ai: 'AI',
  data: 'Data',
  platform: 'Platform',
  integration: 'Integration',
}

export function UsagePage() {
  // TODO: in Phase 4, load real quota snapshots from /api/v1/usage/services
  // For now all services show as not_configured until credentials are wired up

  const lastRefreshed: string | null = null
  const isRefreshing = false

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Usage & Infrastructure"
        subtitle="Service health, quota status and usage metrics for CodeWhisperer"
        actions={
          <div className="flex items-center gap-2">
            {lastRefreshed && (
              <span className="text-xs text-text-muted">
                Last updated: {new Date(lastRefreshed).toLocaleTimeString()}
              </span>
            )}
            <button
              disabled={isRefreshing}
              className={clsx(
                'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium',
                'border border-border text-text-secondary hover:bg-surface transition-colors',
                'disabled:opacity-50 disabled:cursor-not-allowed',
              )}
              onClick={() => {
                // TODO: call /api/v1/usage/services/*/refresh
              }}
            >
              <RefreshCw size={13} className={isRefreshing ? 'animate-spin' : ''} />
              Refresh
            </button>
          </div>
        }
      />

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Overview strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {(['Configured', 'Operational', 'Degraded', 'Not Configured'] as const).map((label) => (
            <div
              key={label}
              className="border border-border rounded-lg p-3 bg-canvas"
            >
              <p className="text-2xl font-semibold tabular-nums text-text-primary">
                {label === 'Not Configured' ? SERVICE_REGISTRY.length : 0}
              </p>
              <p className="text-xs text-text-muted mt-0.5">{label}</p>
            </div>
          ))}
        </div>

        {/* Service groups */}
        {(['ai', 'data', 'platform', 'integration'] as ServiceCategory[]).map((cat) => {
          const services = SERVICE_REGISTRY.filter((s) => s.category === cat)
          return (
            <section key={cat}>
              <h2 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
                {CATEGORY_LABELS[cat]}
              </h2>
              <div className="border border-border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-surface border-b border-border">
                      <th className="text-left px-4 py-2.5 text-xs font-semibold text-text-secondary">
                        Service
                      </th>
                      <th className="text-left px-4 py-2.5 text-xs font-semibold text-text-secondary">
                        Provider
                      </th>
                      <th className="text-left px-4 py-2.5 text-xs font-semibold text-text-secondary w-32">
                        Status
                      </th>
                      <th className="text-left px-4 py-2.5 text-xs font-semibold text-text-secondary">
                        Usage
                      </th>
                      <th className="text-left px-4 py-2.5 text-xs font-semibold text-text-secondary">
                        Dependent Features
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-subtle">
                    {services.map((svc) => (
                      <tr key={svc.key} className="hover:bg-surface transition-colors">
                        <td className="px-4 py-3 font-medium text-text-primary">{svc.name}</td>
                        <td className="px-4 py-3 text-text-secondary">{svc.provider}</td>
                        <td className="px-4 py-3">
                          <StatusBadge status="not_configured" size="sm" />
                        </td>
                        <td className="px-4 py-3 text-text-muted text-xs">
                          {/* Not configured: do not show zero */}
                          Usage unavailable
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-1">
                            {svc.dependentFeatures.map((f) => (
                              <span
                                key={f}
                                className="text-xs px-1.5 py-0.5 rounded bg-surface border border-border text-text-muted"
                              >
                                {f}
                              </span>
                            ))}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )
        })}

        {/* Data attribution note */}
        <div className="flex items-start gap-2 p-3 rounded-lg bg-surface border border-border-subtle">
          <BarChart3 size={13} className="shrink-0 text-text-muted mt-0.5" />
          <p className="text-xs text-text-muted">
            Usage data labeled <strong className="text-text-secondary">Provider-reported</strong>{' '}
            comes directly from the provider API.{' '}
            <strong className="text-text-secondary">CodeWhisperer-tracked</strong> values are
            internal estimates. Unknown or unavailable values are never shown as zero.
          </p>
        </div>
      </div>
    </div>
  )
}
