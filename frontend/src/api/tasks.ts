import { apiClient, AppApiError } from './client'

export interface TaskResponse {
  taskId: string
  status: string
  taskType: string
  result: Record<string, unknown> | null
  tokensUsed: number | null
}

export interface TaskListItem {
  taskId: string
  taskType: string
  status: string
  repositoryId: string
  createdAt: string
  completedAt: string | null
  tokensUsed: number | null
}

const TERMINAL_STATUSES = new Set(['completed', 'partial', 'failed', 'paused'])

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

/** Poll a task GET until terminal status or timeout (default 3 minutes). */
export async function pollUntilDone(
  getter: (taskId: string) => Promise<TaskResponse>,
  taskId: string,
  options?: { intervalMs?: number; timeoutMs?: number },
): Promise<TaskResponse> {
  const intervalMs = options?.intervalMs ?? 2000
  const timeoutMs = options?.timeoutMs ?? 180_000
  const started = Date.now()

  // First poll after a short delay so the background worker can start.
  await new Promise((r) => setTimeout(r, Math.min(500, intervalMs)))

  while (true) {
    const task = await getter(taskId)
    if (TERMINAL_STATUSES.has(task.status)) {
      return task
    }
    if (Date.now() - started >= timeoutMs) {
      throw new AppApiError({
        code: 'REQUEST_TIMEOUT',
        message:
          'This AI task is still running after 3 minutes. Check Agent Activity for status, or try again later.',
        service: null,
        retryable: true,
        retryAfter: null,
        correlationId: '',
      })
    }
    await new Promise((r) => setTimeout(r, intervalMs))
  }
}
