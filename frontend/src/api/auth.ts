import { apiClient } from './client'
import type { User } from '@/types'

export interface SessionResponse {
  user: User
}

export async function getSession(): Promise<SessionResponse> {
  const { data } = await apiClient.get<SessionResponse>('/api/v1/auth/session')
  return data
}
