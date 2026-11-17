import { useState } from 'react'
import { Search, ChevronDown, ChevronRight, FileCode } from 'lucide-react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { PageHeader, LoadingSkeleton, QuotaNotice } from '@/components'
import { AppApiError } from '@/api/client'
import { listRepositories, queryRepository, type ChatQueryResponse, type EvidenceItem } from '@/api/repositories'

export default function WorkspacePage() {
  const [selectedRepoId, setSelectedRepoId] = useState<string>('')
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState<ChatQueryResponse | null>(null)

  const { data: reposData, isLoading: loadingRepos } = useQuery({
    queryKey: ['repositories'],
    queryFn: () => listRepositories(),
  })

  const repos = reposData?.items ?? []
  const indexedRepos = repos.filter((r) => r.status === 'indexed' || r.status === 'stale')

  const queryMutation = useMutation({
    mutationFn: () =>
      queryRepository({ repository_id: selectedRepoId, question }),
    onSuccess: (data) => setResult(data),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedRepoId || !question.trim()) return
    setResult(null)
    queryMutation.mutate()
  }

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="AI Workspace"
        subtitle="Ask questions about your indexed repositories and explore code with AI assistance."
      />

      <div className="max-w-3xl space-y-4">
        {/* Repository selector */}
        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-text-secondary">Repository</label>
          {loadingRepos ? (
            <div className="h-9 bg-surface rounded-md animate-pulse" />
          ) : indexedRepos.length === 0 ? (
            <div className="p-3 border border-border rounded-md bg-surface text-sm text-text-secondary">
              No indexed repositories found. Index a repository from the{' '}
              <a href="/repositories" className="text-accent hover:underline">Repositories</a> page first.
            </div>
          ) : (
            <select
              value={selectedRepoId}
              onChange={(e) => {
                setSelectedRepoId(e.target.value)
                setResult(null)
              }}
              className="w-full px-3 py-2 text-sm border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-accent bg-canvas text-text-primary"
            >
              <option value="">Select a repository…</option>
              {indexedRepos.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.owner}/{r.name} ({r.selectedBranch})
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Question input */}
        <form onSubmit={handleSubmit} className="space-y-2">
          <label className="block text-xs font-medium text-text-secondary">Question</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. How does authentication work in this codebase?"
              disabled={!selectedRepoId}
              className="flex-1 px-3 py-2 text-sm border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-accent bg-canvas text-text-primary placeholder-text-muted disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!selectedRepoId || !question.trim() || queryMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-md text-sm font-medium hover:bg-accent-hover transition-colors disabled:opacity-50"
            >
              <Search size={14} />
              {queryMutation.isPending ? 'Working…' : 'Ask'}
            </button>
          </div>
        </form>

        {/* Suggested questions */}
        {selectedRepoId && !result && !queryMutation.isPending && (
          <div className="space-y-1.5">
            <p className="text-xs text-text-muted">Suggested questions</p>
            <div className="flex flex-wrap gap-2">
              {[
                'What is the main entry point?',
                'How is authentication implemented?',
                'What database models exist?',
                'How are API routes organized?',
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => setQuestion(q)}
                  className="px-2.5 py-1 text-xs border border-border rounded-full text-text-secondary hover:border-accent hover:text-accent transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Loading state */}
      {queryMutation.isPending && (
        <div className="max-w-3xl space-y-3">
          <LoadingSkeleton rows={4} />
        </div>
      )}

      {/* Error — distinguish quota exhaustion from generic errors */}
      {queryMutation.isError && (() => {
        const err = queryMutation.error
        const isQuota = err instanceof AppApiError && err.code === 'PROVIDER_QUOTA_EXHAUSTED'
        if (isQuota) {
          return (
            <div className="max-w-3xl">
              <QuotaNotice
                serviceName={(err as AppApiError).service ?? 'LLM service'}
                message={(err as AppApiError).message}
                retryable={false}
                onRetry={() => queryMutation.reset()}
              />
            </div>
          )
        }
        const message =
          err instanceof AppApiError
            ? err.message
            : err instanceof Error
              ? err.message
              : 'Query failed. Please try again.'
        return (
          <div className="max-w-3xl p-4 border border-danger/30 bg-danger-subtle rounded-md text-sm text-danger">
            {message}
          </div>
        )
      })()}

      {/* Results */}
      {result && !queryMutation.isPending && (
        <div className="max-w-3xl space-y-4">
          {/* Answer */}
          <div className="p-4 border border-border rounded-lg bg-surface space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-text-primary">Answer</h3>
              <span className="text-xs text-text-muted">
                {result.evidence.length} evidence item{result.evidence.length !== 1 ? 's' : ''}
              </span>
            </div>
            <p className="text-sm text-text-primary whitespace-pre-wrap leading-relaxed">
              {result.answer}
            </p>
          </div>

          {/* Evidence */}
          {result.evidence.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
                Retrieved Evidence
              </h3>
              <div className="space-y-2">
                {result.evidence.map((item) => (
                  <EvidenceCard key={item.chunkId} item={item} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function EvidenceCard({ item }: { item: EvidenceItem }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-surface transition-colors text-left"
      >
        <div className="flex items-center gap-2 min-w-0">
          <FileCode size={14} className="text-text-muted shrink-0" />
          <span className="text-xs font-medium text-text-primary truncate">{item.filePath}</span>
          <span className="text-xs text-text-muted shrink-0">
            L{item.lineStart}–{item.lineEnd}
          </span>
          {item.symbolName && (
            <span className="text-xs bg-accent-subtle text-accent px-1.5 py-0.5 rounded shrink-0">
              {item.symbolName.split('.').pop()}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0 ml-2">
          <span className="text-xs text-text-muted capitalize">{item.retrievalMethod}</span>
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </div>
      </button>
      {expanded && (
        <div className="border-t border-border">
          <pre className="p-3 text-xs font-mono text-text-primary bg-surface-elevated overflow-x-auto whitespace-pre-wrap">
            {item.text}
          </pre>
        </div>
      )}
    </div>
  )
}
