import { Shield, GitBranch, Play } from 'lucide-react'
import { PageHeader, DataTable, StatusBadge } from '@/components'
import type { SecurityFinding } from '@/types'
import type { ColumnDef } from '@/components'
import { clsx } from 'clsx'

export function SecurityPage() {
  // TODO: load scans from /api/v1/security/scans
  const scans: SecurityFinding[] = []
  const isLoading = false

  const columns: ColumnDef<SecurityFinding>[] = [
    {
      key: 'severity',
      header: 'Severity',
      width: '100px',
      render: (f) => {
        const variantMap: Record<string, 'failed' | 'degraded' | 'partial' | 'unknown'> = {
          critical: 'failed',
          high: 'failed',
          medium: 'degraded',
          low: 'partial',
          unknown: 'unknown',
        }
        return (
          <StatusBadge
            status={variantMap[f.severity] ?? 'unknown'}
            label={f.severity.charAt(0).toUpperCase() + f.severity.slice(1)}
            size="sm"
          />
        )
      },
    },
    {
      key: 'title',
      header: 'Finding',
      render: (f) => (
        <div className="min-w-0">
          <p className="text-sm font-medium text-text-primary truncate">{f.title}</p>
          <p className="text-xs text-text-muted truncate">
            {f.category.replace(/_/g, ' ')}
          </p>
        </div>
      ),
    },
    {
      key: 'location',
      header: 'Package / File',
      width: '180px',
      render: (f) => (
        <span className="font-mono text-xs text-text-secondary truncate">
          {f.packageName ?? f.filePath ?? '—'}
        </span>
      ),
    },
    {
      key: 'version',
      header: 'Version',
      width: '130px',
      render: (f) => (
        <div>
          {f.installedVersion && (
            <p className="font-mono text-xs text-text-primary">{f.installedVersion}</p>
          )}
          {f.fixedVersion && (
            <p className="font-mono text-xs text-success">Fix: {f.fixedVersion}</p>
          )}
        </div>
      ),
    },
    {
      key: 'advisory',
      header: 'Advisory / Rule',
      width: '130px',
      render: (f) => (
        <span className="font-mono text-xs text-text-muted">
          {f.advisoryId ?? f.ruleId ?? '—'}
        </span>
      ),
    },
  ]

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Security"
        subtitle="Dependency vulnerabilities and selected insecure code patterns"
        actions={
          <div className="flex items-center gap-2">
            <button
              className={clsx(
                'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium',
                'border border-border text-text-secondary hover:bg-surface transition-colors',
              )}
            >
              <GitBranch size={13} />
              Select repository
            </button>
            <button
              className={clsx(
                'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium',
                'bg-accent text-white hover:bg-accent-hover transition-colors',
              )}
              onClick={() => {
                // TODO: start security scan via POST /api/v1/security/scans
              }}
            >
              <Play size={13} />
              Start Scan
            </button>
          </div>
        }
      />

      <div className="flex-1 p-6 overflow-y-auto space-y-4">
        {/* Scan status info area */}
        {/* TODO: show active scan progress or last scan summary */}

        <DataTable
          columns={columns}
          data={scans}
          keyExtractor={(f) => f.id}
          isLoading={isLoading}
          emptyTitle="No security scan run yet"
          emptyDescription="Select a repository and start a scan to check for dependency vulnerabilities and insecure code patterns."
          emptyAction={
            <div className="flex items-center gap-2">
              <Shield size={14} className="text-text-muted" />
              <span className="text-sm text-text-muted">
                Security scans are read-only and do not modify your code.
              </span>
            </div>
          }
        />
      </div>
    </div>
  )
}
