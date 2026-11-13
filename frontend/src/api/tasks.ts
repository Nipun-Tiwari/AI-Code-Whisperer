import { apiClient } from './client'

export interface TaskResponse {
  task_id: string
  status: string
  task_type: string
  result: Record<string, unknown> | null
  tokens_used: number | null
}

export interface TaskListItem {
  task_id: string
  task_type: string
  status: string
  repository_id: string
  created_at: string
  completed_at: string | null
  tokens_used: number | null
}

export async function getTask(taskId: string): Promise<TaskResponse> {
  const { data } = await apiClient.get<TaskResponse>(`/api/v1/agent-activity/${taskId}`)
  return data
}

export async function listAgentActivity(limit = 20): Promise<TaskListItem[]> {
  const { data } = await apiClient.get<TaskListItem[]>('/api/v1/agent-activity', {
    params: { limit },
  })
  return data
}

export async function retryTask(taskId: string): Promise<TaskResponse> {
  const { data } = await apiClient.post<TaskResponse>(`/api/v1/tasks/${taskId}/retry`)
  return data
}
