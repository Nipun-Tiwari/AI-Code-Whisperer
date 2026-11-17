import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Shield, Loader2, AlertTriangle, Info } from 'lucide-react'
import { PageHeader, StatusBadge, EmptyState, DataTable } from '@/components'
import { AppApiError } from '@/api/client'
import { useRepositories } from '@/hooks'
import { startSecurityScan } from '@/api/security'
import type { TaskResponse } from '@/api/tasks'
import { clsx } from 'clsx'
import type { ColumnDef } from '@/components/ui/DataTable'

type SecurityFinding = {
  package?: string
  version?: string
  ecosystem?: string
  severity: string
  advisoryId?: string
  description: string
  fixedVersion?: string | null
  source?: string
  rule?: string
  filePath?: string
  line?: number
  maskedEvidence?: string
}

type SecurityResult = {
  scanSummary?: { manifestsScanned: number; totalFindings: number; bySeverity: Record<string, number> }
  dependencyFindings?: SecurityFinding[]
  codeFindings?: SecurityFinding[]
  scanIncomplete?: boolean
  unsupportedManifests?: string[]
  manifestsScanned?: string[]
  answer?: string
  errors?: string[]
  warnings?: string[]
  requestType?: string
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'text-danger bg-danger-subtle border-danger/30',
  high: 'text-danger bg-danger-subtle border-danger/30',
  medium: 'text-warning bg-warning-subtle border-warning/30',
  low: 'text-info bg-info-subtle border-info/30',
  unknown: 'text-text-secondary bg-surface border-border',
}

const SEVERITIES = ['critical', 'high', 'medium', 'low', 'unknown']

const depColumns: ColumnDef<SecurityFinding>[] = [
  {
    key: 'severity',
    header: 'Severity',
    render: (row) => (
      <span className={clsx('text-xs font-medium px-2 py-0.5 rounded border', SEVERITY_COLORS[row.severity] || SEVERITY_COLORS.unknown)}>
        {row.severity}
      </span>
    ),
  },
  { key: 'package', header: 'Package', render: (row) => <span className="font-mono text-xs">{row.package}</span> },
  { key: 'version', header: 'Version', render: (row) => <span className="font-mono text-xs">{row.version}</span> },
  { key: 'description', header: 'Issue', render: (row) => <span className="text-sm">{row.description}</span> },
  { key: 'fixedVersion', header: 'Fix', render: (row) => row.fixedVersion ? <span className="font-mono text-xs text-success">{row.fixedVersion}</span> : <span className="text-text-muted text-xs">—</span> },
  { key: 'advisoryId', header: 'Advisory', render: (row) => <span className="text-xs text-text-secondary">{row.advisoryId}</span> },
]

const codeColumns: ColumnDef<SecurityFinding>[] = [
  {
    key: 'severity',
    header: 'Severity',
    render: (row) => (
      <span className={clsx('text-xs font-medium px-2 py-0.5 rounded border', SEVERITY_COLORS[row.severity] || SEVERITY_COLORS.unknown)}>
        {row.severity}
      </span>
    ),
  },
  { key: 'rule', header: 'Rule', render: (row) => <span className="font-mono text-xs">{row.rule}</span> },
  { key: 'filePath', header: 'File', render: (row) => <span className="font-mono text-xs text-text-secondary">{row.filePath}:{row.line}</span> },
  { key: 'description', header: 'Issue', render: (row) => <span className="text-sm">{row.description}</span> },
]

export default function SecurityPage() {
  const { data: repos } = useRepositories()
  const [selectedRepo, setSelectedRepo] = useState('')
  const [severityFilter, setSeverityFilter] = useState<string>('all')
  const [result, setResult] = useState<TaskResponse | null>(null)

  const mutation = useMutation({
    mutationFn: () => startSecurityScan({ repository_id: selectedRepo }),
    onSuccess: (data) => setResult(data),
  })

  const scanResult = result?.result as SecurityResult | undefined
  const summary = scanResult?.scanSummary
  const errors = scanResult?.errors ?? []
  const hasScanShape = Boolean(summary)

  const filteredDepFindings = (scanResult?.dependencyFindings || []).filter(
    (f) => severityFilter === 'all' || f.severity === severityFilter
  )
  const filteredCodeFindings = (scanResult?.codeFindings || []).filter(
    (f) => severityFilter === 'all' || f.severity === severityFilter
  )

  const errorMessage =
    mutation.error instanceof AppApiError
      ? mutation.error.message
      : mutation.error instanceof Error
        ? mutation.error.message
        : 'Security scan failed. Please try again.'

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <PageHeader
        title="Security Center"
        subtitle="Scan repositories for dependency vulnerabilities and insecure code patterns."
      />

      <div className="border border-border rounded-lg p-5 bg-surface space-y-4">
        <div className="flex items-end gap-3">
          <div className="flex-1 space-y-1">
            <label className="text-sm font-medium text-text-primary">Repository</label>
            <select
              className="w-full border border-border rounded-md px-3 py-2 text-sm bg-canvas focus:outline-none focus:ring-1 focus:ring-accent"
              value={selectedRepo}
              onChange={(e) => setSelectedRepo(e.target.value)}
            >
              <option value="">Select a repository...</option>
              {repos?.items?.map((r) => (
                <option key={r.id} value={r.id}>{r.owner}/{r.name}</option>
              ))}
            </select>
          </div>
          <button
            className="flex items-center gap-2 px-4 py-2 bg-accent text-white text-sm font-medium rounded-md hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            disabled={!selectedRepo || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Shield size={14} />}
            {mutation.isPending ? 'Scanning...' : 'Start Scan'}
          </button>
        </div>
        {mutation.isError && (
          <p className="text-sm text-danger">{errorMessage}</p>
        )}
      </div>

      {mutation.isPending && (
        <div className="border border-border rounded-lg p-6 flex items-center gap-3 text-text-secondary text-sm bg-surface">
          <Loader2 size={14} className="animate-spin" />
          Scanning dependencies and code patterns...
        </div>
      )}

      {scanResult && !hasScanShape && (
        <div className="border border-warning/30 rounded-lg p-5 bg-warning-subtle space-y-2">
          <div className="flex items-center gap-2 text-warning text-sm font-medium">
            <AlertTriangle size={14} />
            Scan did not return security findings
          </div>
          <p className="text-sm text-text-secondary">
            {scanResult.answer || 'The task finished without a security scan summary.'}
          </p>
          {errors.length > 0 && (
            <ul className="space-y-1">
              {errors.map((err, i) => (
                <li key={i} className="text-xs text-danger font-mono break-all">{err}</li>
              ))}
            </ul>
          )}
          <p className="text-xs text-text-muted">
            Status: {result?.status}
            {scanResult.requestType ? ` · type: ${scanResult.requestType}` : ''}
          </p>
        </div>
      )}

      {scanResult && hasScanShape && summary && (
        <div className="space-y-4">
          <div className="border border-border rounded-lg p-5 bg-surface">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <StatusBadge status={(scanResult.scanIncomplete ? 'partial' : 'completed') as 'partial' | 'completed'} />
                <span className="text-sm text-text-secondary">
                  {(scanResult.manifestsScanned?.length ?? 0) > 0
                    ? `Scanned: ${scanResult.manifestsScanned!.join(', ')}`
                    : 'No manifests scanned'}
                </span>
              </div>
              <span className="text-sm font-medium text-text-primary">
                {summary.totalFindings} finding{summary.totalFindings !== 1 ? 's' : ''}
              </span>
            </div>
            <div className="flex gap-3 flex-wrap">
              {Object.entries(summary.bySeverity || {})
                .filter(([, count]) => count > 0)
                .map(([sev, count]) => (
                  <span key={sev} className={clsx('text-xs font-medium px-2 py-1 rounded border', SEVERITY_COLORS[sev] || SEVERITY_COLORS.unknown)}>
                    {count} {sev}
                  </span>
                ))}
            </div>
            {scanResult.scanIncomplete && (
              <div className="mt-3 flex items-center gap-2 text-xs text-warning">
                <AlertTriangle size={12} />
                Scan incomplete. Some manifests could not be analyzed: {(scanResult.unsupportedManifests || []).join(', ')}
              </div>
            )}
            {errors.length > 0 && (
              <div className="mt-3 space-y-1">
                {errors.map((err, i) => (
                  <p key={i} className="text-xs text-danger break-all">{err}</p>
                ))}
              </div>
            )}
          </div>

          {summary.totalFindings > 0 && (
            <div className="flex gap-2">
              {['all', ...SEVERITIES].map((sev) => (
                <button
                  key={sev}
                  className={clsx(
                    'text-xs px-3 py-1 rounded border transition-colors',
                    severityFilter === sev
                      ? 'bg-accent text-white border-accent'
                      : 'border-border text-text-secondary hover:border-accent/50'
                  )}
                  onClick={() => setSeverityFilter(sev)}
                >
                  {sev === 'all' ? 'All' : sev}
                </button>
              ))}
            </div>
          )}

          {filteredDepFindings.length > 0 && (
            <div className="border border-border rounded-lg overflow-hidden bg-surface">
              <div className="px-4 py-3 border-b border-border">
                <h3 className="text-sm font-medium text-text-primary">Dependency Vulnerabilities ({filteredDepFindings.length})</h3>
              </div>
              <DataTable columns={depColumns} data={filteredDepFindings} keyExtractor={(r) => `${r.advisoryId}-${r.package}`} />
            </div>
          )}

          {filteredCodeFindings.length > 0 && (
            <div className="border border-border rounded-lg overflow-hidden bg-surface">
              <div className="px-4 py-3 border-b border-border">
                <h3 className="text-sm font-medium text-text-primary">Code Pattern Findings ({filteredCodeFindings.length})</h3>
              </div>
              <DataTable columns={codeColumns} data={filteredCodeFindings} keyExtractor={(r) => `${r.rule}-${r.filePath}-${r.line}`} />
            </div>
          )}

          {summary.totalFindings === 0 && !scanResult.scanIncomplete && (
            <div className="border border-border rounded-lg p-6 flex items-center gap-3 text-success text-sm bg-success-subtle">
              <Info size={14} />
              No vulnerabilities found in scanned manifests and code.
            </div>
          )}
        </div>
      )}

      {!scanResult && !mutation.isPending && (
        <EmptyState
          icon={Shield}
          title="No scan results"
          description="Select a repository and start a security scan to check for vulnerabilities."
        />
      )}
    </div>
  )
}
