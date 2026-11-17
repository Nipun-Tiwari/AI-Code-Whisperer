import { apiClient } from './client'
import { pollUntilDone, type TaskResponse } from './tasks'
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
  fullName: string
  visibility: string
  defaultBranch: string
  description: string | null
  githubConnectionId: string
}

export interface ChatQueryRequest {
  repository_id: string
  question: string
}

export interface EvidenceItem {
  chunkId: string
  filePath: string
  lineStart: number
  lineEnd: number
  text: string
  symbolName: string | null
  language: string
  chunkType: string
  score: number
  retrievalMethod: string
}

export interface ChatQueryResponse {
  answer: string
  evidence: EvidenceItem[]
  repositoryId: string
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

export async function startGitHubConnection(): Promise<string> {
  const { data } = await apiClient.post<{ installUrl: string }>(
    '/api/v1/integrations/github/connect',
  )
  return data.installUrl
}

export async function listAccessibleRepos(): Promise<GitHubRepo[]> {
  const { data } = await apiClient.get<GitHubRepo[]>('/api/v1/integrations/github/repositories')
  return data
}

export async function getChatQuery(taskId: string): Promise<TaskResponse> {
  const { data } = await apiClient.get<TaskResponse>(`/api/v1/chat/query/${taskId}`)
  return data
}

export async function queryRepository(request: ChatQueryRequest): Promise<ChatQueryResponse> {
  const { data: created } = await apiClient.post<TaskResponse>('/api/v1/chat/query', request)
  const task = await pollUntilDone(getChatQuery, created.taskId)
  const result = (task.result ?? {}) as Record<string, unknown>
  const evidence = Array.isArray(result.evidence) ? (result.evidence as EvidenceItem[]) : []
  return {
    answer: typeof result.answer === 'string' ? result.answer : 'No answer returned.',
    evidence,
    repositoryId:
      typeof result.repositoryId === 'string'
        ? result.repositoryId
        : request.repository_id,
    question: typeof result.question === 'string' ? result.question : request.question,
  }
}
