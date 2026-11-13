import { apiClient } from './client'
import type { Repository, IndexJob, PaginatedResponse } from '@/types'

export interface AddRepositoryRequest {
  owner: string
  name: string
  branch: string
  githubConnectionId: string
}

export async function listRepositories(params?: {
  page?: number
  pageSize?: number
  search?: string
}): Promise<PaginatedResponse<Repository>> {
  const { data } = await apiClient.get<PaginatedResponse<Repository>>('/api/v1/repositories', {
    params,
  })
  return data
}

export async function getRepository(id: string): Promise<Repository> {
  const { data } = await apiClient.get<Repository>(`/api/v1/repositories/${id}`)
  return data
}

export async function addRepository(request: AddRepositoryRequest): Promise<Repository> {
  const { data } = await apiClient.post<Repository>('/api/v1/repositories', request)
  return data
}

export async function removeRepository(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/repositories/${id}`)
}

export async function startIndexJob(
  repositoryId: string,
  mode: 'full' | 'incremental' = 'full',
): Promise<IndexJob> {
  const { data } = await apiClient.post<IndexJob>(
    `/api/v1/repositories/${repositoryId}/index-jobs`,
    { mode },
  )
  return data
}

export async function getIndexJob(jobId: string): Promise<IndexJob> {
  const { data } = await apiClient.get<IndexJob>(`/api/v1/index-jobs/${jobId}`)
  return data
}

export async function listBranches(repositoryId: string): Promise<string[]> {
  const { data } = await apiClient.get<{ branches: string[] }>(
    `/api/v1/repositories/${repositoryId}/branches`,
  )
  return data.branches
}
