import axios, { type AxiosInstance, type AxiosError } from 'axios'
import type { ApiErrorResponse } from '@/types'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30_000,
})

// Attach Supabase access token from localStorage on every request
apiClient.interceptors.request.use((config) => {
  const token = getStoredAccessToken()
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

// Map API errors to a consistent shape
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorResponse>) => {
    if (error.response) {
      const apiError = error.response.data?.error
      if (apiError) {
        return Promise.reject(new AppApiError(apiError))
      }
    }
    if (error.code === 'ECONNABORTED') {
      return Promise.reject(new AppApiError({
        code: 'REQUEST_TIMEOUT',
        message: 'The request timed out. Please try again.',
        service: null,
        retryable: true,
        retryAfter: null,
        correlationId: '',
      }))
    }
    if (!error.response) {
      return Promise.reject(new AppApiError({
        code: 'NETWORK_ERROR',
        message: 'Unable to reach the server. Check your connection.',
        service: null,
        retryable: true,
        retryAfter: null,
        correlationId: '',
      }))
    }
    return Promise.reject(error)
  },
)

export class AppApiError extends Error {
  code: string
  service: string | null
  retryable: boolean
  retryAfter: string | null
  correlationId: string

  constructor(apiError: ApiErrorResponse['error']) {
    super(apiError.message)
    this.name = 'AppApiError'
    this.code = apiError.code
    this.service = apiError.service
    this.retryable = apiError.retryable
    this.retryAfter = apiError.retryAfter
    this.correlationId = apiError.correlationId
  }
}

function getStoredAccessToken(): string | null {
  // Supabase stores its session in localStorage under a project-specific key.
  // We read it here so we don't need to import the Supabase client everywhere.
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key?.startsWith('sb-') && key.endsWith('-auth-token')) {
        const raw = localStorage.getItem(key)
        if (raw) {
          const parsed = JSON.parse(raw) as { access_token?: string }
          return parsed.access_token ?? null
        }
      }
    }
  } catch {
    // ignore storage errors
  }
  return null
}
