import { apiClient } from './client'
import type { TaskResponse } from './tasks'

export interface InvestigationCreate {
  repository_id: string
  description: string
  branch?: string
}

export async function startInvestigation(data: InvestigationCreate): Promise<TaskResponse> {
  const { data: res } = await apiClient.post<TaskResponse>('/api/v1/investigations', data)
  return res
}

export async function getInvestigation(taskId: string): Promise<TaskResponse> {
  const { data } = await apiClient.get<TaskResponse>(`/api/v1/investigations/${taskId}`)
  return data
}
