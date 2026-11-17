import { apiClient } from './client'
import { pollUntilDone, type TaskResponse } from './tasks'

export interface DocumentationCreate {
  repository_id: string
  doc_type: string
  module_path?: string
  branch?: string
}

export async function getDocumentation(taskId: string): Promise<TaskResponse> {
  const { data } = await apiClient.get<TaskResponse>(`/api/v1/documentation/${taskId}`)
  return data
}

export async function generateDocumentation(data: DocumentationCreate): Promise<TaskResponse> {
  const { data: res } = await apiClient.post<TaskResponse>('/api/v1/documentation/generate', data)
  return pollUntilDone(getDocumentation, res.taskId)
}
