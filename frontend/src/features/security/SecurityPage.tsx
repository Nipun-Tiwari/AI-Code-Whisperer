import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Shield, Loader2, AlertTriangle, Info } from 'lucide-react'
import { PageHeader, StatusBadge, EmptyState, DataTable } from '@/components'
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
  advisory_id?: string
  description: string
  fixed_version?: string | null
  source?: string
  rule?: string
  file_path?: string
  line?: number
  masked_evidence?: string
}

type SecurityResult = {
  scan_summary: { manifests_scanned: number; total_findings: number; by_severity: Record<string, number> }
  dependency_findings: SecurityFinding[]
  code_findings: SecurityFinding[]
  scan_incomplete: boolean
  unsupported_manifests: string[]
  manifests_scanned: string[]
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
  { key: 'fixed_version', header: 'Fix', render: (row) => row.fixed_version ? <span className="font-mono text-xs text-success">{row.fixed_version}</span> : <span className="text-text-muted text-xs">—</span> },
  { key: 'advisory_id', header: 'Advisory', render: (row) => <span className="text-xs text-text-secondary">{row.advisory_id}</span> },
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
  { key: 'file_path', header: 'File', render: (row) => <span className="font-mono text-xs text-text-secondary">{row.file_path}:{row.line}</span> },
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

  const filteredDepFindings = (scanResult?.dependency_findings || []).filter(
    (f) => severityFilter === 'all' || f.severity === severityFilter
  )
  const filteredCodeFindings = (scanResult?.code_findings || []).filter(
    (f) => severityFilter === 'all' || f.severity === severityFilter
  )

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <PageHeader
        title="Security Center"
        subtitle="Scan repositories for dependency vulnerabilities and insecure code patterns."
      />

      {/* Scan controls */}
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
      </div>

      {/* Scan results */}
      {mutation.isPending && (
        <div className="border border-border rounded-lg p-6 flex items-center gap-3 text-text-secondary text-sm bg-surface">
          <Loader2 size={14} className="animate-spin" />
          Scanning dependencies and code patterns...
        </div>
      )}

      {scanResult && (
        <div className="space-y-4">
          {/* Summary row */}
          <div className="border border-border rounded-lg p-5 bg-surface">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <StatusBadge status={(scanResult.scan_incomplete ? 'partial' : 'completed') as 'partial' | 'completed'} />
                <span className="text-sm text-text-secondary">
                  {scanResult.manifests_scanned.length > 0
                    ? `Scanned: ${scanResult.manifests_scanned.join(', ')}`
                    : 'No manifests scanned'}
                </span>
              </div>
              <span className="text-sm font-medium text-text-primary">
                {scanResult.scan_summary.total_findings} finding{scanResult.scan_summary.total_findings !== 1 ? 's' : ''}
              </span>
            </div>
            <div className="flex gap-3 flex-wrap">
              {Object.entries(scanResult.scan_summary.by_severity)
                .filter(([, count]) => count > 0)
                .map(([sev, count]) => (
                  <span key={sev} className={clsx('text-xs font-medium px-2 py-1 rounded border', SEVERITY_COLORS[sev] || SEVERITY_COLORS.unknown)}>
                    {count} {sev}
                  </span>
                ))}
            </div>
            {scanResult.scan_incomplete && (
              <div className="mt-3 flex items-center gap-2 text-xs text-warning">
                <AlertTriangle size={12} />
                Scan incomplete. Some manifests could not be analyzed: {scanResult.unsupported_manifests.join(', ')}
              </div>
            )}
          </div>

          {/* Severity filter */}
          {scanResult.scan_summary.total_findings > 0 && (
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

          {/* Dependency findings */}
          {filteredDepFindings.length > 0 && (
            <div className="border border-border rounded-lg overflow-hidden bg-surface">
              <div className="px-4 py-3 border-b border-border">
                <h3 className="text-sm font-medium text-text-primary">Dependency Vulnerabilities ({filteredDepFindings.length})</h3>
              </div>
              <DataTable columns={depColumns} data={filteredDepFindings} keyExtractor={(r) => `${r.advisory_id}-${r.package}`} />
            </div>
          )}

          {/* Code findings */}
          {filteredCodeFindings.length > 0 && (
            <div className="border border-border rounded-lg overflow-hidden bg-surface">
              <div className="px-4 py-3 border-b border-border">
                <h3 className="text-sm font-medium text-text-primary">Code Pattern Findings ({filteredCodeFindings.length})</h3>
              </div>
              <DataTable columns={codeColumns} data={filteredCodeFindings} keyExtractor={(r) => `${r.rule}-${r.file_path}-${r.line}`} />
            </div>
          )}

          {scanResult.scan_summary.total_findings === 0 && !scanResult.scan_incomplete && (
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
