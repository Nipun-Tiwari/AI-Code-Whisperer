import { useParams, Link } from 'react-router-dom'
import { GitBranch, RefreshCw, Bot, Shield, FileText, Search, type LucideIcon } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { PageHeader, StatusBadge, ErrorState, LoadingSkeleton, EmptyState } from '@/components'
import { getRepository } from '@/api/repositories'
import { clsx } from 'clsx'

export function RepositoryDetailPage() {
  const { id } = useParams<{ id: string }>()

  const { data: repo, isLoading, error } = useQuery({
    queryKey: ['repository', id],
    queryFn: () => getRepository(id!),
    enabled: Boolean(id),
  })

  if (isLoading) return <LoadingSkeleton rows={4} className="p-6" />

  if (error || !repo) {
    return (
      <ErrorState
        message="Failed to load repository details."
        onRetry={() => window.location.reload()}
      />
    )
  }

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title={`${repo.owner}/${repo.name}`}
        subtitle={repo.description ?? `${repo.selectedBranch} · ${repo.latestVersion?.commitSha?.slice(0, 7) ?? 'not indexed'}`}
        actions={
          <div className="flex items-center gap-2">
            <StatusBadge status={repo.status as never} />
            <button
              className={clsx(
                'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium',
                'border border-border text-text-secondary hover:bg-surface transition-colors',
              )}
            >
              <RefreshCw size={13} />
              Re-index
            </button>
          </div>
        }
      />

      <div className="flex-1 p-6 space-y-6 overflow-y-auto">
        {/* Index status panel */}
        <div className="border border-border rounded-lg p-4">
          <h2 className="text-sm font-semibold text-text-primary mb-3">Index Status</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <InfoItem label="Branch" value={repo.selectedBranch} mono />
            <InfoItem
              label="Commit"
              value={repo.latestVersion?.commitSha?.slice(0, 7) ?? '—'}
              mono
            />
            <InfoItem
              label="Last indexed"
              value={
                repo.latestVersion
                  ? new Date(repo.latestVersion.indexedAt).toLocaleString()
                  : 'Never'
              }
            />
            <InfoItem label="Visibility" value={repo.visibility} />
          </div>
        </div>

        {/* Quick links to analysis workflows */}
        {repo.status === 'indexed' || repo.status === 'stale' ? (
          <div>
            <h2 className="text-sm font-semibold text-text-primary mb-3">Analysis Workflows</h2>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <WorkflowCard
                to={`/workspace?repo=${repo.id}`}
                icon={Bot}
                label="Ask a question"
                description="Repository Q&A"
              />
              <WorkflowCard
                to={`/code-explorer?repo=${repo.id}`}
                icon={Search}
                label="Explore code"
                description="Browse and search"
              />
              <WorkflowCard
                to={`/investigation?repo=${repo.id}`}
                icon={GitBranch}
                label="Investigate issue"
                description="Root-cause analysis"
              />
              <WorkflowCard
                to={`/security?repo=${repo.id}`}
                icon={Shield}
                label="Security scan"
                description="Dependency &amp; patterns"
              />
              <WorkflowCard
                to={`/documentation?repo=${repo.id}`}
                icon={FileText}
                label="Generate docs"
                description="Architecture &amp; modules"
              />
            </div>
          </div>
        ) : (
          <EmptyState
            icon={GitBranch}
            title={
              repo.status === 'pending' || repo.status === 'indexing'
                ? 'Indexing in progress'
                : 'Repository not indexed'
            }
            description={
              repo.status === 'failed'
                ? 'Indexing failed. Check the job details and retry.'
                : 'Start indexing to enable Q&A, investigation, security analysis and documentation workflows.'
            }
            action={
              <button
                className={clsx(
                  'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium',
                  'bg-accent text-white hover:bg-accent-hover transition-colors',
                )}
              >
                <RefreshCw size={13} />
                Start Indexing
              </button>
            }
          />
        )}

        {/* TODO: recent tasks for this repository */}
        {/* TODO: index job history */}
      </div>
    </div>
  )
}

function InfoItem({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <p className="text-xs text-text-muted mb-0.5">{label}</p>
      <p className={clsx('text-sm text-text-primary', mono && 'font-mono')}>{value}</p>
    </div>
  )
}

function WorkflowCard({
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
      className="flex flex-col gap-2 p-3 border border-border rounded-lg hover:bg-surface hover:border-accent/30 transition-colors"
    >
      <Icon size={16} className="text-text-secondary" />
      <div>
        <p className="text-sm font-medium text-text-primary">{label}</p>
        <p className="text-xs text-text-muted">{description}</p>
      </div>
    </Link>
  )
}
