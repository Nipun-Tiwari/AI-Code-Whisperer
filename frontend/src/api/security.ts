import { apiClient } from './client'
import { pollUntilDone, type TaskResponse } from './tasks'

export interface SecurityScanCreate {
  repository_id: string
  branch?: string
}

export async function getSecurityScan(scanId: string): Promise<TaskResponse> {
  const { data } = await apiClient.get<TaskResponse>(`/api/v1/security/scans/${scanId}`)
  return data
}

export async function startSecurityScan(data: SecurityScanCreate): Promise<TaskResponse> {
  const { data: res } = await apiClient.post<TaskResponse>('/api/v1/security/scans', data)
  return pollUntilDone(getSecurityScan, res.taskId)
}
