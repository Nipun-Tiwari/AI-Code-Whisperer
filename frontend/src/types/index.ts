// ─── Identity & Auth ────────────────────────────────────────────────────────

export interface User {
  id: string
  email: string
  displayName: string | null
  createdAt: string
}

export interface Session {
  user: User
  accessToken: string
}

// ─── GitHub ─────────────────────────────────────────────────────────────────

export type GitHubConnectionStatus = 'active' | 'revoked' | 'expired'
export type GitHubAccountType = 'User' | 'Organization'

export interface GitHubConnection {
  id: string
  userId: string
  githubAppInstallationId: string | null
  githubAccountLogin: string
  githubAccountType: GitHubAccountType
  status: GitHubConnectionStatus
  connectedAt: string
}

// ─── Repository ──────────────────────────────────────────────────────────────

export type RepositoryVisibility = 'public' | 'private'
export type RepositoryStatus =
  | 'pending'
  | 'indexing'
  | 'indexed'
  | 'failed'
  | 'stale'
  | 'removed'

export interface Repository {
  id: string
  userId: string
  githubConnectionId: string
  owner: string
  name: string
  fullName: string
  githubRepoId: string
  visibility: RepositoryVisibility
  defaultBranch: string
  selectedBranch: string
  description: string | null
  status: RepositoryStatus
  createdAt: string
  updatedAt: string
  latestVersion: RepositoryVersion | null
}

export interface RepositoryVersion {
  id: string
  repositoryId: string
  branch: string
  commitSha: string
  indexedAt: string
  indexVersion: number
}

// ─── Index Jobs ───────────────────────────────────────────────────────────────

export type IndexJobMode = 'full' | 'incremental'
export type IndexJobStatus =
  | 'queued'
  | 'fetching'
  | 'classifying'
  | 'parsing'
  | 'summarizing'
  | 'embedding'
  | 'persisting'
  | 'completed'
  | 'partial'
  | 'failed'
  | 'paused'

export interface IndexJob {
  id: string
  repositoryId: string
  versionId: string | null
  mode: IndexJobMode
  status: IndexJobStatus
  stage: string | null
  checkpoint: string | null
  filesTotal: number | null
  filesProcessed: number
  filesFailed: number
  filesSkipped: number
  errorCategory: string | null
  startedAt: string | null
  completedAt: string | null
  createdAt: string
}

// ─── File / Symbol Records ────────────────────────────────────────────────────

export type ParseStatus = 'parsed' | 'partial' | 'unsupported' | 'failed'
export type SymbolKind = 'class' | 'function' | 'method' | 'module' | 'import'

export interface FileRecord {
  id: string
  repositoryId: string
  versionId: string
  path: string
  language: string | null
  sizeBytes: number
  contentHash: string
  parseStatus: ParseStatus
}

export interface SymbolRecord {
  id: string
  fileId: string
  symbolKind: SymbolKind
  name: string
  qualifiedName: string
  lineStart: number
  lineEnd: number
}

// ─── Conversations & Tasks ────────────────────────────────────────────────────

export type TaskType =
  | 'repository_qa'
  | 'investigation'
  | 'security_scan'
  | 'documentation'

export type TaskStatus =
  | 'queued'
  | 'planning'
  | 'running'
  | 'completed'
  | 'partial'
  | 'failed'
  | 'paused'

export interface Conversation {
  id: string
  userId: string
  repositoryId: string
  title: string | null
  createdAt: string
}

export interface AgentTask {
  id: string
  conversationId: string | null
  userId: string
  repositoryId: string
  taskType: TaskType
  status: TaskStatus
  plan: TaskPlan | null
  result: TaskResult | null
  tokenBudget: number | null
  tokensUsed: number | null
  createdAt: string
  completedAt: string | null
}

export interface TaskPlan {
  steps: TaskStep[]
  estimatedTokens: number | null
}

export interface TaskStep {
  id: string
  agentRole: string
  description: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  startedAt: string | null
  completedAt: string | null
}

export interface TaskResult {
  summary: string
  evidence: EvidenceItem[]
  citations: Citation[]
  limitations: string[]
  status: 'complete' | 'partial'
}

export interface EvidenceItem {
  evidenceId: string
  sourceType: string
  repositoryId: string
  commitSha: string
  filePath: string
  lineStart: number | null
  lineEnd: number | null
  excerpt: string
  retrievalMethod: string
}

export interface Citation {
  id: string
  filePath: string
  lineStart: number | null
  lineEnd: number | null
  commitSha: string
}

// ─── Security ─────────────────────────────────────────────────────────────────

export type SecurityScanStatus =
  | 'queued'
  | 'scanning'
  | 'completed'
  | 'incomplete'
  | 'failed'

export type FindingSeverity = 'critical' | 'high' | 'medium' | 'low' | 'unknown'
export type FindingCategory = 'dependency_vulnerability' | 'insecure_pattern' | 'hardcoded_secret'

export interface SecurityScan {
  id: string
  repositoryId: string
  versionId: string
  status: SecurityScanStatus
  scannerVersions: Record<string, string>
  createdAt: string
  completedAt: string | null
}

export interface SecurityFinding {
  id: string
  scanId: string
  category: FindingCategory
  severity: FindingSeverity
  title: string
  packageName: string | null
  filePath: string | null
  installedVersion: string | null
  fixedVersion: string | null
  advisoryId: string | null
  ruleId: string | null
  evidence: string
  remediationGuidance: string | null
  createdAt: string
}

// ─── Documentation ────────────────────────────────────────────────────────────

export type DocumentationType = 'architecture' | 'module' | 'technical'
export type DocumentationStatus = 'generating' | 'generated' | 'partial' | 'failed'

export interface GeneratedDocument {
  id: string
  repositoryId: string
  versionId: string
  documentationType: DocumentationType
  status: DocumentationStatus
  title: string
  content: string | null
  citations: Citation[]
  knownGaps: string[]
  createdAt: string
}

// ─── MCP Tools ───────────────────────────────────────────────────────────────

export type MCPToolStatus = 'available' | 'unavailable' | 'permission_missing' | 'degraded'

export interface MCPTool {
  id: string
  name: string
  description: string
  requiredPermission: string
  status: MCPToolStatus
  lastUsedAt: string | null
  inputSchema: Record<string, unknown>
}

export interface MCPToolCall {
  id: string
  taskId: string
  toolName: string
  safeArgumentsSummary: string
  durationMs: number | null
  outcome: 'success' | 'failure' | 'timeout' | 'permission_denied'
  errorCategory: string | null
  createdAt: string
}

// ─── Usage & Infrastructure ───────────────────────────────────────────────────

export type ServiceStatus =
  | 'operational'
  | 'degraded'
  | 'rate_limited'
  | 'quota_exhausted'
  | 'auth_error'
  | 'unavailable'
  | 'usage_unavailable'
  | 'unknown'
  | 'not_configured'

export type UsageSourceType = 'provider_reported' | 'codewhisperer_tracked' | 'estimated'
export type ServiceCategory = 'ai' | 'data' | 'platform' | 'integration'

export interface ServiceDefinition {
  key: string
  name: string
  category: ServiceCategory
  provider: string
  configured: boolean
  capabilities: string[]
  dependentFeatures: string[]
}

export interface QuotaSnapshot {
  id: string
  serviceKey: string
  status: ServiceStatus
  usageValue: number | null
  usageUnit: string | null
  limitValue: number | null
  remaining: number | null
  resetAt: string | null
  sourceType: UsageSourceType
  measuredAt: string
  freshness: 'current' | 'stale' | 'unknown'
}

export interface ServiceUsageSummary {
  service: ServiceDefinition
  quota: QuotaSnapshot | null
  recentEvents: ServiceStatusEvent[]
}

export interface ServiceStatusEvent {
  id: string
  serviceKey: string
  status: ServiceStatus
  category: string
  observedAt: string
  correlationId: string | null
}

export interface UsageOverview {
  totalConfigured: number
  operational: number
  degraded: number
  exhausted: number
  unknown: number
  notConfigured: number
  services: ServiceUsageSummary[]
}

// ─── Shared / API ─────────────────────────────────────────────────────────────

export interface ApiError {
  code: string
  message: string
  service: string | null
  retryable: boolean
  retryAfter: string | null
  correlationId: string
}

export interface ApiErrorResponse {
  error: ApiError
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  hasMore: boolean
}

// ─── GitHub Repository (from GitHub API) ─────────────────────────────────────

export interface GitHubRepo {
  id: number
  name: string
  fullName: string
  description: string | null
  private: boolean
  defaultBranch: string
  language: string | null
  stargazersCount: number
  updatedAt: string
}
