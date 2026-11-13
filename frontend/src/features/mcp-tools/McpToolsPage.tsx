import { Wrench } from 'lucide-react'
import { PageHeader, DataTable, StatusBadge, EmptyState } from '@/components'
import type { MCPTool } from '@/types'
import type { ColumnDef } from '@/components'

export function McpToolsPage() {
  // TODO: load tools from /api/v1/mcp/tools
  const tools: MCPTool[] = []
  const isLoading = false

  const columns: ColumnDef<MCPTool>[] = [
    {
      key: 'name',
      header: 'Tool',
      render: (t) => (
        <div>
          <p className="text-sm font-medium text-text-primary font-mono">{t.name}</p>
          <p className="text-xs text-text-muted mt-0.5">{t.description}</p>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      width: '150px',
      render: (t) => <StatusBadge status={t.status as never} size="sm" />,
    },
    {
      key: 'permission',
      header: 'Required Permission',
      width: '180px',
      render: (t) => (
        <span className="text-xs text-text-secondary font-mono">{t.requiredPermission}</span>
      ),
    },
    {
      key: 'lastUsed',
      header: 'Last Used',
      width: '160px',
      render: (t) => (
        <span className="text-sm text-text-muted">
          {t.lastUsedAt ? new Date(t.lastUsedAt).toLocaleString() : 'Never'}
        </span>
      ),
    },
  ]

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="MCP Tools"
        subtitle="Available Model Context Protocol tools and their authorization status"
      />

      <div className="flex-1 p-6 overflow-y-auto space-y-4">
        {/* Info notice */}
        <div className="flex items-start gap-3 p-3 rounded-lg border border-info/30 bg-info-subtle">
          <Wrench size={14} className="shrink-0 text-info mt-0.5" />
          <p className="text-xs text-info">
            MCP tools are read-only by default. Write-capable tools require explicit approval and
            narrow permission scopes before they can be enabled. Tool arguments and repository
            content are treated as untrusted data.
          </p>
        </div>

        <DataTable
          columns={columns}
          data={tools}
          keyExtractor={(t) => t.id}
          isLoading={isLoading}
          emptyTitle="No MCP tools configured"
          emptyDescription="MCP tools become available after the backend MCP server is deployed and connected."
          emptyAction={
            <EmptyState
              icon={Wrench}
              title=""
              description="Tool configuration is managed in the backend settings."
              size="sm"
            />
          }
        />
      </div>
    </div>
  )
}
