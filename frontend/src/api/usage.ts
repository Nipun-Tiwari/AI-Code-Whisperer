import { apiClient } from './client'

export interface MetricValue {
  key: string
  label: string
  value: number | null
  unit: string
  source_type: string
}

export interface ServiceStatus {
  service_key: string
  name: string
  category: string
  configured: boolean
  status: string
  metrics: MetricValue[]
  last_checked: string | null
  source_type: string
  dependent_features: string[]
  error_message: string | null
}

export interface DashboardSummary {
  total_services: number
  operational: number
  degraded: number
  quota_exhausted: number
  not_configured: number
  unknown: number
  services: ServiceStatus[]
  generated_at: string
}

export interface UsagePoint {
  recorded_at: string
  metric: string
  quantity: number
  unit: string
  source_type: string
}

export async function getUsageOverview(): Promise<DashboardSummary> {
  const { data } = await apiClient.get<DashboardSummary>('/api/v1/usage/overview')
  return data
}

export async function listServices(): Promise<ServiceStatus[]> {
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

export async function getUsageHistory(serviceKey: string, days = 7): Promise<UsagePoint[]> {
  const { data } = await apiClient.get<UsagePoint[]>('/api/v1/usage/history', {
    params: { service: serviceKey, days },
  })
  return data
}
