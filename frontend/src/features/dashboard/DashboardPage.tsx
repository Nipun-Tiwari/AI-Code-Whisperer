import { GitBranch, Plus, ArrowRight, AlertCircle, type LucideIcon } from 'lucide-react'
import { Link } from 'react-router-dom'
import { PageHeader, EmptyState, StatusBadge } from '@/components'
import { useRepositories } from '@/hooks'
import { clsx } from 'clsx'

export function DashboardPage() {
  const { data, isLoading } = useRepositories({ pageSize: 5 })
  const repos = data?.items ?? []
  const hasRepos = repos.length > 0

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Dashboard"
        subtitle="Overview of your repositories and recent activity"
        actions={
          <Link
            to="/repositories"
            className={clsx(
              'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium',
              'bg-accent text-white hover:bg-accent-hover transition-colors',
            )}
          >
            <Plus size={14} />
            Add Repository
          </Link>
        }
      />

      <div className="flex-1 p-6 space-y-6 overflow-y-auto">
        {/* Quick actions — always visible */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <QuickActionCard
            to="/repositories"
            icon={GitBranch}
            title="Connect a repository"
            description="Add a GitHub repository to start analyzing your codebase"
            primary
          />
          <QuickActionCard
            to="/workspace"
            icon={ArrowRight}
            title="Ask a question"
            description="Query an indexed repository with natural language"
          />
          <QuickActionCard
            to="/investigation"
            icon={AlertCircle}
            title="Investigate an issue"
            description="Trace code-level root causes from a defect description"
          />
        </div>

        {/* Recent repositories */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-text-primary">Recent Repositories</h2>
            <Link
              to="/repositories"
              className="text-xs text-accent hover:text-accent-hover flex items-center gap-1"
            >
              View all <ArrowRight size={12} />
            </Link>
          </div>

          {isLoading && (
            <div className="border border-border rounded-lg p-4 space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className="skeleton-animate h-8 w-8 rounded-md bg-border" />
                  <div className="flex-1 space-y-1.5">
                    <div className="skeleton-animate h-3 w-40 rounded bg-border" />
                    <div className="skeleton-animate h-2.5 w-24 rounded bg-border" />
                  </div>
                </div>
              ))}
            </div>
          )}

          {!isLoading && !hasRepos && (
            <div className="border border-border border-dashed rounded-lg">
              <EmptyState
                icon={GitBranch}
                title="No repositories connected"
                description="Connect a GitHub repository to get started with code analysis."
                action={
                  <Link
                    to="/repositories"
                    className={clsx(
                      'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium',
                      'bg-accent text-white hover:bg-accent-hover transition-colors',
                    )}
                  >
                    <Plus size={14} />
                    Connect GitHub &amp; Add Repository
                  </Link>
                }
                size="md"
              />
            </div>
          )}

          {!isLoading && hasRepos && (
            <div className="border border-border rounded-lg divide-y divide-border-subtle">
              {repos.map((repo) => (
                <Link
                  key={repo.id}
                  to={`/repositories/${repo.id}`}
                  className="flex items-center gap-3 px-4 py-3 hover:bg-surface transition-colors"
                >
                  <div className="shrink-0 w-8 h-8 rounded-md bg-accent-subtle flex items-center justify-center">
                    <GitBranch size={14} className="text-accent" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-text-primary truncate">
                      {repo.owner}/{repo.name}
                    </p>
                    <p className="text-xs text-text-muted truncate">
                      {repo.selectedBranch}
                      {repo.latestVersion && ` · ${repo.latestVersion.commitSha.slice(0, 7)}`}
                    </p>
                  </div>
                  <StatusBadge status={repo.status as never} size="sm" />
                </Link>
              ))}
            </div>
          )}
        </section>

        {/* Service health summary — placeholder, populated in Phase 4 */}
        {/* TODO: wire up UsageOverview summary cards here once usage service is implemented */}
      </div>
    </div>
  )
}

interface QuickActionCardProps {
  to: string
  icon: LucideIcon
  title: string
  description: string
  primary?: boolean
}

function QuickActionCard({ to, icon: Icon, title, description, primary }: QuickActionCardProps) {
  return (
    <Link
      to={to}
      className={clsx(
        'group flex flex-col gap-2 p-4 rounded-lg border transition-colors',
        primary
          ? 'border-accent/30 bg-accent-subtle hover:bg-accent hover:border-accent hover:text-white'
          : 'border-border bg-canvas hover:bg-surface',
      )}
    >
      <Icon
        size={18}
        className={clsx(
          'shrink-0',
          primary ? 'text-accent group-hover:text-white' : 'text-text-secondary',
        )}
      />
      <div>
        <p
          className={clsx(
            'text-sm font-medium',
            primary ? 'text-accent group-hover:text-white' : 'text-text-primary',
          )}
        >
          {title}
        </p>
        <p
          className={clsx(
            'text-xs mt-0.5',
            primary ? 'text-accent/80 group-hover:text-white/80' : 'text-text-secondary',
          )}
        >
          {description}
        </p>
      </div>
    </Link>
  )
}
