import { apiClient } from './client'

export interface MCPToolInfo {
  name: string
  description: string
  required_permission: string
}

export interface MCPToolCallRecord {
  tool_name: string
  success: boolean
  duration_ms: number | null
  error_category: string | null
  created_at: string
}

export async function listMcpTools(): Promise<MCPToolInfo[]> {
  const { data } = await apiClient.get<MCPToolInfo[]>('/api/v1/mcp/tools')
  return data
}

export async function getMcpToolCalls(): Promise<MCPToolCallRecord[]> {
  const { data } = await apiClient.get<MCPToolCallRecord[]>('/api/v1/mcp/tool-calls')
  return data
}
