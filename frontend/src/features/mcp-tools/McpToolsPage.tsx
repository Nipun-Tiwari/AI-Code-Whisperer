import { useQuery } from '@tanstack/react-query'
import { Wrench, CheckCircle, XCircle } from 'lucide-react'
import { PageHeader, EmptyState, ErrorState, LoadingSkeleton, DataTable } from '@/components'
import { listMcpTools, getMcpToolCalls } from '@/api/mcp'
import type { MCPToolCallRecord } from '@/api/mcp'
import type { ColumnDef } from '@/components/ui/DataTable'
import { clsx } from 'clsx'

const callColumns: ColumnDef<MCPToolCallRecord>[] = [
  {
    key: 'tool_name',
    header: 'Tool',
    render: (row) => <span className="font-mono text-xs">{row.tool_name}</span>,
  },
  {
    key: 'success',
    header: 'Result',
    render: (row) => (
      <span className={clsx('flex items-center gap-1 text-xs', row.success ? 'text-success' : 'text-danger')}>
        {row.success ? <CheckCircle size={12} /> : <XCircle size={12} />}
        {row.success ? 'Success' : row.error_category || 'Failed'}
      </span>
    ),
  },
  {
    key: 'duration_ms',
    header: 'Duration',
    render: (row) => (
      <span className="text-xs text-text-secondary font-mono">
        {row.duration_ms != null ? `${row.duration_ms}ms` : '—'}
      </span>
    ),
  },
  {
    key: 'created_at',
    header: 'Time',
    render: (row) => (
      <span className="text-xs text-text-muted">
        {row.created_at ? new Date(row.created_at).toLocaleString() : '—'}
      </span>
    ),
  },
]

export default function McpToolsPage() {
  const { data: tools, isLoading: toolsLoading, isError: toolsError } = useQuery({
    queryKey: ['mcp-tools'],
    queryFn: listMcpTools,
  })

  const { data: calls, isLoading: callsLoading } = useQuery({
    queryKey: ['mcp-tool-calls'],
    queryFn: getMcpToolCalls,
    refetchInterval: 15000,
  })

  if (toolsLoading) return (
    <div className="p-6"><PageHeader title="MCP Tools" subtitle="Available integrations and tool call history." /><LoadingSkeleton rows={4} /></div>
  )
  if (toolsError) return (
    <div className="p-6"><PageHeader title="MCP Tools" subtitle="Available integrations and tool call history." /><ErrorState title="Failed to load tools" message="Could not retrieve MCP tool registry." /></div>
  )

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <PageHeader
        title="MCP Tools"
        subtitle="Read-only repository intelligence tools available to agents via Model Context Protocol."
      />

      {/* Tool registry */}
      <div className="border border-border rounded-lg overflow-hidden bg-surface">
        <div className="px-4 py-3 border-b border-border">
          <h3 className="text-sm font-medium text-text-primary">Available Tools ({tools?.length || 0})</h3>
        </div>
        {!tools?.length ? (
          <EmptyState icon={Wrench} title="No tools configured" description="MCP tools will appear here when the server is running." />
        ) : (
          <div className="divide-y divide-border">
            {tools.map((tool) => (
              <div key={tool.name} className="px-4 py-3 flex items-start gap-4">
                <div className="w-6 h-6 rounded bg-accent-subtle flex items-center justify-center shrink-0 mt-0.5">
                  <Wrench size={12} className="text-accent" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-mono font-medium text-text-primary">{tool.name}</span>
                    <span className="text-xs px-1.5 py-0.5 bg-surface-elevated border border-border rounded text-text-muted">
                      {tool.required_permission}
                    </span>
                  </div>
                  <p className="text-xs text-text-secondary mt-0.5">{tool.description}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent calls */}
      <div className="border border-border rounded-lg overflow-hidden bg-surface">
        <div className="px-4 py-3 border-b border-border">
          <h3 className="text-sm font-medium text-text-primary">Recent Tool Calls</h3>
        </div>
        {callsLoading ? (
          <LoadingSkeleton rows={3} />
        ) : !calls?.length ? (
          <EmptyState icon={Wrench} title="No tool calls yet" description="Tool calls will appear here when agents run." />
        ) : (
          <DataTable columns={callColumns} data={calls} keyExtractor={(r) => `${r.tool_name}-${r.created_at}`} />
        )}
      </div>
    </div>
  )
}
