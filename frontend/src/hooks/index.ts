export { useAuthStore, useSidebarStore, useNotificationStore } from '@/store'

import { useQuery } from '@tanstack/react-query'
import { listRepositories } from '@/api/repositories'
import { getSession } from '@/api/auth'

export function useSession() {
  return useQuery({
    queryKey: ['session'],
    queryFn: getSession,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
}

export function useRepositories(params?: { page?: number; pageSize?: number; search?: string }) {
  return useQuery({
    queryKey: ['repositories', params],
    queryFn: () => listRepositories(params),
    staleTime: 30 * 1000,
  })
}
