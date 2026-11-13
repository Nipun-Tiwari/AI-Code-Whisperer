import { useParams, Link } from 'react-router-dom'
import { GitBranch, RefreshCw, Bot, Shield, FileText, Search, type LucideIcon } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { PageHeader, StatusBadge, ErrorState, LoadingSkeleton } from '@/components'
import { getRepository, listRepositoryJobs, startIndexJob } from '@/api/repositories'
import type { IndexJob } from '@/types'
import { clsx } from 'clsx'

const ACTIVE_STATUSES = new Set(['queued', 'fetching', 'classifying', 'parsing', 'summarizing', 'embedding', 'persisting'])

export default function RepositoryDetailPage() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()

  const isActive = (jobs: IndexJob[]) => jobs.some((j) => ACTIVE_STATUSES.has(j.status))

  const { data: repo, isLoading, error } = useQuery({
    queryKey: ['repository', id],
    queryFn: () => getRepository(id!),
    enabled: !!id,
    refetchInterval: (query) => ACTIVE_STATUSES.has(query.state.data?.status ?? '') ? 3000 : false,
  })

  const { data: jobs } = useQuery({
    queryKey: ['repository-jobs', id],
    queryFn: () => listRepositoryJobs(id!),
    enabled: !!id,
    refetchInterval: (query) => isActive(query.state.data ?? []) ? 3000 : false,
  })

  const indexMutation = useMutation({
    mutationFn: () => startIndexJob(id!, 'full'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repository', id] })
      queryClient.invalidateQueries({ queryKey: ['repository-jobs', id] })
    },
  })

  if (isLoading) return <div className="p-6"><LoadingSkeleton rows={6} /></div>
  if (error || !repo) return (
    <div className="p-6">
      <ErrorState title="Repository not found" message="This repository could not be loaded." />
    </div>
  )

  const latestJob = jobs?.[0]
  const isIndexing = ACTIVE_STATUSES.has(repo.status)

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title={`${repo.owner}/${repo.name}`}
        subtitle={repo.description || undefined}
        actions={
          <div className="flex items-center gap-2">
            <StatusBadge status={repo.status} />
            <button
              onClick={() => indexMutation.mutate()}
              disabled={isIndexing || indexMutation.isPending}
              className="flex items-center gap-2 px-3 py-2 border border-border rounded-md text-sm text-text-secondary hover:border-accent hover:text-accent transition-colors disabled:opacity-50"
            >
              <RefreshCw size={14} className={clsx(isIndexing && 'animate-spin')} />
              {repo.latestVersion ? 'Refresh Index' : 'Start Indexing'}
            </button>
          </div>
        }
      />

      {/* Index info */}
      <div className="grid grid-cols-3 gap-4">
        <InfoCard label="Branch" value={
          <span className="flex items-center gap-1.5 text-sm text-text-primary">
            <GitBranch size={14} className="text-text-muted" />
            {repo.selectedBranch}
          </span>
        } />
        <InfoCard label="Last Indexed" value={
          repo.latestVersion
            ? new Date(repo.latestVersion.indexedAt).toLocaleString()
            : 'Not yet indexed'
        } />
        <InfoCard label="Commit" value={
          repo.latestVersion ? (
            <span className="font-mono text-xs">{repo.latestVersion.commitSha.slice(0, 8)}</span>
          ) : '—'
        } />
      </div>

      {/* Active job progress */}
      {latestJob && ACTIVE_STATUSES.has(latestJob.status) && (
        <div className="p-4 border border-accent/30 bg-accent-subtle rounded-lg space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-accent">
              Indexing in progress — {latestJob.stage || latestJob.status}
            </span>
            <span className="text-xs text-text-secondary">
              {latestJob.filesProcessed}/{latestJob.filesTotal ?? '?'} files
            </span>
          </div>
          {latestJob.filesTotal && latestJob.filesTotal > 0 && (
            <div className="h-1.5 bg-accent/20 rounded-full overflow-hidden">
              <div
                className="h-full bg-accent rounded-full transition-all"
                style={{ width: `${Math.min(100, (latestJob.filesProcessed / latestJob.filesTotal) * 100)}%` }}
              />
            </div>
          )}
        </div>
      )}

      {/* Quick navigation */}
      <div className="space-y-2">
        <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">Analysis</h2>
        <div className="grid grid-cols-2 gap-3">
          <QuickLink to={`/workspace?repo=${id}`} icon={Bot} label="AI Workspace" description="Ask questions about this repository" />
          <QuickLink to={`/code-explorer?repo=${id}`} icon={Search} label="Code Explorer" description="Search and browse code" />
          <QuickLink to={`/security?repo=${id}`} icon={Shield} label="Security" description="Scan for vulnerabilities" />
          <QuickLink to={`/documentation?repo=${id}`} icon={FileText} label="Documentation" description="Generate technical docs" />
        </div>
      </div>

      {/* Recent jobs */}
      {jobs && jobs.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">Recent Jobs</h2>
          <div className="border border-border rounded-lg divide-y divide-border">
            {jobs.slice(0, 5).map((job) => (
              <div key={job.id} className="flex items-center justify-between p-3">
                <div className="flex items-center gap-3">
                  <StatusBadge status={job.status} />
                  <span className="text-xs text-text-secondary capitalize">{job.mode}</span>
                  {job.stage && (
                    <span className="text-xs text-text-muted">— {job.stage}</span>
                  )}
                </div>
                <div className="flex items-center gap-4 text-xs text-text-muted">
                  {job.filesTotal && (
                    <span>{job.filesProcessed}/{job.filesTotal} files</span>
                  )}
                  {job.filesFailed > 0 && (
                    <span className="text-warning">{job.filesFailed} failed</span>
                  )}
                  <span>{new Date(job.createdAt).toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function InfoCard({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="p-3 border border-border rounded-lg bg-surface">
      <p className="text-xs text-text-muted mb-1">{label}</p>
      <div className="text-sm text-text-primary">{value}</div>
    </div>
  )
}

function QuickLink({
  to,
  icon: Icon,
  label,
  description,
}: {
  to: string
  icon: LucideIcon
  label: string
  description: string
}) {
  return (
    <Link
      to={to}
      className="flex flex-col gap-1.5 p-3 border border-border rounded-lg hover:bg-surface hover:border-accent/30 transition-colors"
    >
      <Icon size={16} className="text-text-secondary" />
      <span className="text-sm font-medium text-text-primary">{label}</span>
      <span className="text-xs text-text-muted">{description}</span>
    </Link>
  )
}
