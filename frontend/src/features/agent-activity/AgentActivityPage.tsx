import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Activity, RefreshCw, ChevronDown, ChevronRight, Copy } from 'lucide-react'
import { PageHeader, StatusBadge, EmptyState, ErrorState, LoadingSkeleton } from '@/components'
import { listAgentActivity, retryTask } from '@/api/tasks'
import { clsx } from 'clsx'

const TASK_TYPE_LABELS: Record<string, string> = {
  repository_qa: 'Repository Q&A',
  investigation: 'Investigation',
  security_scan: 'Security Scan',
  documentation: 'Documentation',
}

export default function AgentActivityPage() {
  const qc = useQueryClient()
  const [expandedTask, setExpandedTask] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const { data: tasks, isLoading, isError, refetch } = useQuery({
    queryKey: ['agent-activity'],
    queryFn: () => listAgentActivity(50),
    refetchInterval: 10000,
  })

  const retryMutation = useMutation({
    mutationFn: retryTask,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agent-activity'] }),
  })

  const handleCopyId = (id: string) => {
    navigator.clipboard.writeText(id)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const isRetryable = (status: string) => ['failed', 'partial', 'paused'].includes(status)

  if (isLoading) return (
    <div className="p-6"><PageHeader title="Agent Activity" subtitle="Track agent task execution and results." /><LoadingSkeleton rows={5} /></div>
  )
  if (isError) return (
    <div className="p-6"><PageHeader title="Agent Activity" subtitle="Track agent task execution and results." /><ErrorState title="Failed to load activity" message="Could not retrieve task history." onRetry={() => refetch()} /></div>
  )

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-start justify-between">
        <PageHeader title="Agent Activity" subtitle="Track agent task execution, results, and token usage." />
        <button
          className="flex items-center gap-1.5 px-3 py-2 border border-border text-sm text-text-secondary rounded-md hover:border-accent/50 transition-colors"
          onClick={() => refetch()}
        >
          <RefreshCw size={13} />
          Refresh
        </button>
      </div>

      {!tasks?.length ? (
        <EmptyState
          icon={Activity}
          title="No tasks yet"
          description="Agent tasks will appear here when you run investigations, security scans, or generate documentation."
        />
      ) : (
        <div className="border border-border rounded-lg overflow-hidden bg-surface">
          {tasks.map((task) => (
            <div key={task.taskId} className={clsx('border-b border-border last:border-b-0', expandedTask === task.taskId && 'bg-surface-elevated')}>
              <div
                className="flex items-center gap-4 px-4 py-3 cursor-pointer hover:bg-surface-elevated transition-colors"
                onClick={() => setExpandedTask(expandedTask === task.taskId ? null : task.taskId)}
              >
                <div className="w-4">
                  {expandedTask === task.taskId ? <ChevronDown size={13} className="text-text-muted" /> : <ChevronRight size={13} className="text-text-muted" />}
                </div>

                <StatusBadge status={(task.status || 'unknown') as 'completed' | 'failed' | 'partial' | 'paused' | 'queued' | 'unknown'} />

                <span className="text-sm text-text-primary flex-1 min-w-0 truncate">
                  {TASK_TYPE_LABELS[task.taskType] || task.taskType}
                </span>

                <span className="text-xs text-text-muted w-32 truncate">
                  {task.createdAt ? new Date(task.createdAt).toLocaleString() : '—'}
                </span>

                {task.completedAt && task.createdAt && (
                  <span className="text-xs text-text-muted w-20 text-right">
                    {Math.round((new Date(task.completedAt).getTime() - new Date(task.createdAt).getTime()) / 1000)}s
                  </span>
                )}

                {task.tokensUsed != null && (
                  <span className="text-xs text-text-muted w-20 text-right font-mono">
                    {task.tokensUsed.toLocaleString()} tok
                  </span>
                )}

                <div className="flex items-center gap-1">
                  <button
                    className="p-1 rounded hover:bg-surface transition-colors text-text-muted hover:text-text-secondary"
                    title="Copy task ID"
                    onClick={(e) => { e.stopPropagation(); handleCopyId(task.taskId) }}
                  >
                    <Copy size={12} />
                  </button>

                  {isRetryable(task.status) && (
                    <button
                      className="px-2 py-1 text-xs border border-border rounded hover:border-accent/50 text-text-secondary transition-colors"
                      onClick={(e) => { e.stopPropagation(); retryMutation.mutate(task.taskId) }}
                      disabled={retryMutation.isPending}
                    >
                      Retry
                    </button>
                  )}
                </div>
              </div>

              {expandedTask === task.taskId && (
                <div className="px-10 pb-4 space-y-3 border-t border-border">
                  <div className="grid grid-cols-2 gap-4 pt-3">
                    <div className="space-y-1">
                      <span className="text-xs text-text-muted uppercase tracking-wide">Task ID</span>
                      <div className="font-mono text-xs text-text-secondary">{task.taskId}</div>
                    </div>
                    <div className="space-y-1">
                      <span className="text-xs text-text-muted uppercase tracking-wide">Repository</span>
                      <div className="font-mono text-xs text-text-secondary">{task.repositoryId}</div>
                    </div>
                  </div>

                  {copiedId === task.taskId && (
                    <span className="text-xs text-success">Task ID copied</span>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
