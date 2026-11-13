import { apiClient } from './client'
import type { Repository, IndexJob, PaginatedResponse } from '@/types'

export interface AddRepositoryRequest {
  owner: string
  name: string
  branch: string
  github_connection_id: string
}

export interface GitHubConnection {
  id: string
  github_account_login: string
  github_account_type: string
  installation_id: string | null
  status: string
  connected_at: string | null
}

export interface GitHubRepo {
  id: string
  owner: string
  name: string
  full_name: string
  visibility: string
  default_branch: string
  description: string | null
  github_connection_id: string
}

export interface ChatQueryRequest {
  repository_id: string
  question: string
}

export interface EvidenceItem {
  chunk_id: string
  file_path: string
  line_start: number
  line_end: number
  text: string
  symbol_name: string | null
  language: string
  chunk_type: string
  score: number
  retrieval_method: string
}

export interface ChatQueryResponse {
  answer: string
  evidence: EvidenceItem[]
  repository_id: string
  question: string
}

export async function listRepositories(params?: {
  page?: number
  page_size?: number
  search?: string
}): Promise<PaginatedResponse<Repository>> {
  const { data } = await apiClient.get<PaginatedResponse<Repository>>('/api/v1/repositories', { params })
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

export async function listRepositoryJobs(repositoryId: string): Promise<IndexJob[]> {
  const { data } = await apiClient.get<IndexJob[]>(`/api/v1/repositories/${repositoryId}/index-jobs`)
  return data
}

export async function listBranches(repositoryId: string): Promise<string[]> {
  const { data } = await apiClient.get<string[]>(`/api/v1/repositories/${repositoryId}/branches`)
  return Array.isArray(data) ? data : []
}

export async function listGitHubConnections(): Promise<GitHubConnection[]> {
  const { data } = await apiClient.get<GitHubConnection[]>('/api/v1/integrations/github')
  return data
}

export async function listAccessibleRepos(): Promise<GitHubRepo[]> {
  const { data } = await apiClient.get<GitHubRepo[]>('/api/v1/integrations/github/repositories')
  return data
}

export async function queryRepository(request: ChatQueryRequest): Promise<ChatQueryResponse> {
  const { data } = await apiClient.post<ChatQueryResponse>('/api/v1/chat/query', request)
  return data
}
