import { Activity, ChevronRight } from 'lucide-react'
import { PageHeader, DataTable, StatusBadge } from '@/components'
import type { AgentTask } from '@/types'
import type { ColumnDef } from '@/components'

const TASK_TYPE_LABELS: Record<string, string> = {
  repository_qa: 'Repository Q&A',
  investigation: 'Investigation',
  security_scan: 'Security Scan',
  documentation: 'Documentation',
}

export function AgentActivityPage() {
  // TODO: load tasks from /api/v1/agent-activity
  const tasks: AgentTask[] = []
  const isLoading = false

  const columns: ColumnDef<AgentTask>[] = [
    {
      key: 'type',
      header: 'Task Type',
      width: '160px',
      render: (t) => (
        <span className="text-sm text-text-primary">
          {TASK_TYPE_LABELS[t.taskType] ?? t.taskType}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      width: '130px',
      render: (t) => <StatusBadge status={t.status as never} size="sm" />,
    },
    {
      key: 'repository',
      header: 'Repository',
      render: (t) => (
        <span className="text-sm text-text-secondary font-mono">{t.repositoryId}</span>
      ),
    },
    {
      key: 'tokens',
      header: 'Tokens Used',
      width: '120px',
      align: 'right',
      render: (t) => (
        <span className="text-sm tabular-nums text-text-secondary">
          {t.tokensUsed !== null ? t.tokensUsed.toLocaleString() : '—'}
        </span>
      ),
    },
    {
      key: 'created',
      header: 'Started',
      width: '160px',
      render: (t) => (
        <span className="text-sm text-text-muted">
          {new Date(t.createdAt).toLocaleString()}
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      width: '40px',
      align: 'right',
      render: () => (
        <button
          title="View details"
          className="p-1 rounded text-text-muted hover:text-text-primary hover:bg-surface transition-colors"
          onClick={() => {
            // TODO: open task detail panel
          }}
        >
          <ChevronRight size={14} />
        </button>
      ),
    },
  ]

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Agent Activity"
        subtitle="Inspect recent tasks, agent steps and tool call history"
      />

      <div className="flex-1 p-6 overflow-y-auto">
        {/* TODO: add filter bar for task type, status, repository */}
        <DataTable
          columns={columns}
          data={tasks}
          keyExtractor={(t) => t.id}
          isLoading={isLoading}
          emptyTitle="No agent tasks yet"
          emptyDescription="Tasks appear here once you submit a question, investigation, security scan or documentation request."
          emptyAction={
            <div className="flex items-center gap-2">
              <Activity size={14} className="text-text-muted" />
              <span className="text-sm text-text-muted">
                All task traces are retained for inspection.
              </span>
            </div>
          }
        />
      </div>
    </div>
  )
}
