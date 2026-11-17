import { GitBranch, Plus, ArrowRight, AlertCircle, Activity, CheckCircle2, type LucideIcon } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { PageHeader, EmptyState, StatusBadge, LoadingSkeleton } from '@/components'
import { useRepositories } from '@/hooks'
import { listAgentActivity } from '@/api/tasks'
import { getUsageOverview } from '@/api/usage'
import { clsx } from 'clsx'

function StatTile({ label, value, icon: Icon, isLoading }: {
  label: string
  value: number | null
  icon: LucideIcon
  isLoading: boolean
}) {
  return (
    <div className="border border-border rounded-lg p-4 bg-canvas">
      <div className="flex items-center gap-2 mb-2">
        <Icon size={13} className="text-text-muted" aria-hidden="true" />
        <span className="text-xs text-text-muted">{label}</span>
      </div>
      {isLoading ? (
        <div className="skeleton-animate h-8 w-12 rounded bg-border" />
      ) : (
        <p className="text-3xl font-normal tabular-nums tracking-tight text-text-primary">
          {value ?? '—'}
        </p>
      )}
    </div>
  )
}

export function DashboardPage() {
  const { data: reposData, isLoading: reposLoading } = useRepositories({ pageSize: 5 })
  const repos = reposData?.items ?? []
  const hasRepos = repos.length > 0

  const { data: tasksData, isLoading: tasksLoading } = useQuery({
    queryKey: ['agent-activity-recent'],
    queryFn: () => listAgentActivity(20),
    staleTime: 30_000,
  })

  const { data: usageSummary, isLoading: usageLoading } = useQuery({
    queryKey: ['usage-overview'],
    queryFn: getUsageOverview,
    staleTime: 60_000,
  })

  // Count tasks created today
  const todayStart = new Date()
  todayStart.setHours(0, 0, 0, 0)
  const tasksToday = tasksData?.filter(
    (t) => t.createdAt && new Date(t.createdAt) >= todayStart
  ).length ?? null

  const recentTasks = tasksData?.slice(0, 5) ?? []

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
              'bg-accent text-canvas hover:bg-accent-hover transition-colors',
            )}
          >
            <Plus size={14} />
            Add Repository
          </Link>
        }
      />

      <div className="flex-1 p-6 space-y-6 overflow-y-auto">
        {/* Stat tiles */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <StatTile
            label="Repositories"
            value={reposData?.total ?? null}
            icon={GitBranch}
            isLoading={reposLoading}
          />
          <StatTile
            label="Tasks today"
            value={tasksToday}
            icon={Activity}
            isLoading={tasksLoading}
          />
          <StatTile
            label="Services OK"
            value={usageSummary?.operational ?? null}
            icon={CheckCircle2}
            isLoading={usageLoading}
          />
          <StatTile
            label="Total services"
            value={usageSummary?.totalServices ?? null}
            icon={ArrowRight}
            isLoading={usageLoading}
          />
        </div>

        {/* Two-column main content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: repos + tasks */}
          <div className="lg:col-span-2 space-y-6">
            {/* Recent Repositories */}
            <section>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-medium text-text-primary">Recent Repositories</h2>
                <Link to="/repositories" className="text-xs text-text-secondary hover:text-text-primary flex items-center gap-1 transition-colors">
                  View all <ArrowRight size={11} />
                </Link>
              </div>

              {reposLoading && <LoadingSkeleton rows={3} />}

              {!reposLoading && !hasRepos && (
                <div className="border border-border border-dashed rounded-lg">
                  <EmptyState
                    icon={GitBranch}
                    title="No repositories connected"
                    description="Connect a GitHub repository to get started with code analysis."
                    action={
                      <Link
                        to="/repositories"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium bg-accent text-canvas hover:bg-accent-hover transition-colors"
                      >
                        <Plus size={14} />
                        Add Repository
                      </Link>
                    }
                    size="md"
                  />
                </div>
              )}

              {!reposLoading && hasRepos && (
                <div className="border border-border rounded-lg divide-y divide-border-subtle">
                  {repos.map((repo) => (
                    <Link
                      key={repo.id}
                      to={`/repositories/${repo.id}`}
                      className="flex items-center gap-3 px-4 py-3 hover:bg-hover transition-colors"
                    >
                      <div className="shrink-0 w-7 h-7 rounded-md bg-accent-subtle flex items-center justify-center">
                        <GitBranch size={13} className="text-text-secondary" aria-hidden="true" />
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

            {/* Recent Tasks */}
            <section>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-medium text-text-primary">Recent Tasks</h2>
                <Link to="/agent-activity" className="text-xs text-text-secondary hover:text-text-primary flex items-center gap-1 transition-colors">
                  View all <ArrowRight size={11} />
                </Link>
              </div>

              {tasksLoading && <LoadingSkeleton rows={3} />}

              {!tasksLoading && recentTasks.length === 0 && (
                <div className="border border-border border-dashed rounded-lg p-4 text-center">
                  <p className="text-sm text-text-muted">No tasks yet. Use the AI Workspace to get started.</p>
                </div>
              )}

              {!tasksLoading && recentTasks.length > 0 && (
                <div className="border border-border rounded-lg divide-y divide-border-subtle">
                  {recentTasks.map((task) => (
                    <Link
                      key={task.taskId}
                      to="/agent-activity"
                      className="flex items-center gap-3 px-4 py-2.5 hover:bg-hover transition-colors"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-text-primary capitalize truncate">
                          {task.taskType?.replace('_', ' ')}
                        </p>
                        <p className="text-xs text-text-muted">
                          {task.createdAt ? new Date(task.createdAt).toLocaleString() : '—'}
                        </p>
                      </div>
                      <StatusBadge status={(task.status || 'unknown') as never} size="sm" />
                    </Link>
                  ))}
                </div>
              )}
            </section>
          </div>

          {/* Right: service health + quick actions */}
          <div className="space-y-6">
            {/* Service health mini */}
            <section>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-medium text-text-primary">Service Health</h2>
                <Link to="/usage" className="text-xs text-text-secondary hover:text-text-primary transition-colors">
                  Details
                </Link>
              </div>
              <div className="border border-border rounded-lg divide-y divide-border-subtle">
                {usageLoading && <div className="p-3"><LoadingSkeleton rows={4} /></div>}
                {!usageLoading && usageSummary?.services.slice(0, 4).map((svc) => (
                  <div key={svc.serviceKey} className="flex items-center gap-3 px-3 py-2.5">
                    <span
                      className="w-2 h-2 rounded-full shrink-0"
                      style={{
                        backgroundColor:
                          svc.status === 'operational' ? 'var(--color-success)' :
                          svc.status === 'degraded' || svc.status === 'rate_limited' ? 'var(--color-warning)' :
                          svc.status === 'quota_exhausted' || svc.status === 'unavailable' ? 'var(--color-danger)' :
                          'var(--color-text-muted)',
                      }}
                      aria-hidden="true"
                    />
                    <span className="text-sm text-text-secondary truncate flex-1">{svc.name}</span>
                    <span className="text-xs text-text-muted capitalize">{svc.status.replace('_', ' ')}</span>
                  </div>
                ))}
                {!usageLoading && !usageSummary && (
                  <div className="p-3 text-xs text-text-muted">Service data unavailable</div>
                )}
              </div>
            </section>

            {/* Quick actions */}
            <section>
              <h2 className="text-sm font-medium text-text-primary mb-3">Quick Actions</h2>
              <div className="space-y-2">
                <QuickActionCard to="/workspace" icon={Activity} title="AI Workspace" description="Ask questions about your code" />
                <QuickActionCard to="/investigation" icon={AlertCircle} title="Investigate issue" description="Trace code-level root causes" />
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  )
}

interface QuickActionCardProps {
  to: string
  icon: LucideIcon
  title: string
  description: string
}

function QuickActionCard({ to, icon: Icon, title, description }: QuickActionCardProps) {
  return (
    <Link
      to={to}
      className="flex items-center gap-3 p-3 rounded-lg border border-border bg-canvas hover:bg-hover transition-colors"
    >
      <Icon size={14} className="shrink-0 text-text-secondary" aria-hidden="true" />
      <div className="min-w-0">
        <p className="text-sm font-medium text-text-primary">{title}</p>
        <p className="text-xs text-text-muted truncate">{description}</p>
      </div>
    </Link>
  )
}
