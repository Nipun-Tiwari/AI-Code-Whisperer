import { apiClient } from './client'

export interface MetricValue {
  key: string
  label: string
  value: number | null
  unit: string
  sourceType: string
}

export interface ServiceStatus {
  serviceKey: string
  name: string
  category: string
  configured: boolean
  status: string
  metrics: MetricValue[]
  lastChecked: string | null
  sourceType: string
  dependentFeatures: string[]
  errorMessage: string | null
}

export interface DashboardSummary {
  totalServices: number
  operational: number
  degraded: number
  quotaExhausted: number
  notConfigured: number
  unknown: number
  services: ServiceStatus[]
  generatedAt: string
}

export interface UsagePoint {
  recordedAt: string
  metric: string
  quantity: number
  unit: string
  sourceType: string
}

export async function getUsageOverview(): Promise<DashboardSummary> {
  const { data } = await apiClient.get<DashboardSummary>('/api/v1/usage/overview')
  return data
}

export async function getServices(): Promise<ServiceStatus[]> {
  const { data } = await apiClient.get<ServiceStatus[]>('/api/v1/usage/services')
  return data
}

export async function getService(serviceKey: string): Promise<ServiceStatus> {
  const { data } = await apiClient.get<ServiceStatus>(`/api/v1/usage/services/${serviceKey}`)
  return data
}

export async function refreshService(serviceKey: string): Promise<ServiceStatus> {
  const { data } = await apiClient.post<ServiceStatus>(`/api/v1/usage/services/${serviceKey}/refresh`)
  return data
}

export async function getUsageHistory(serviceKey: string, hours = 24): Promise<UsagePoint[]> {
  const { data } = await apiClient.get<UsagePoint[]>('/api/v1/usage/history', {
    params: { service_key: serviceKey, hours },
  })
  return data
}
