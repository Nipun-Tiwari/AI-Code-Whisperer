import { useState } from 'react'
import { Search, ChevronDown, ChevronRight, FileCode } from 'lucide-react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { PageHeader, LoadingSkeleton } from '@/components'
import { AppApiError } from '@/api/client'
import { listRepositories, queryRepository, type EvidenceItem } from '@/api/repositories'
import { clsx } from 'clsx'

export default function CodeExplorerPage() {
  const [selectedRepoId, setSelectedRepoId] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')
  const [results, setResults] = useState<EvidenceItem[]>([])
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const { data: reposData, isLoading: loadingRepos } = useQuery({
    queryKey: ['repositories'],
    queryFn: () => listRepositories(),
  })

  const repos = reposData?.items ?? []
  const indexedRepos = repos.filter((r) => r.status === 'indexed' || r.status === 'stale')

  const searchMutation = useMutation({
    mutationFn: () =>
      queryRepository({ repository_id: selectedRepoId, question: searchQuery }),
    onSuccess: (data) => setResults(data.evidence),
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedRepoId || !searchQuery.trim()) return
    setResults([])
    searchMutation.mutate()
  }

  const errorMessage =
    searchMutation.error instanceof AppApiError
      ? searchMutation.error.message
      : searchMutation.error instanceof Error
        ? searchMutation.error.message
        : 'Search failed. Please try again.'

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Code Explorer"
        subtitle="Search your repository code using natural language and explore retrieved code snippets."
      />

      <div className="max-w-3xl space-y-4">
        <div className="flex gap-3">
          <select
            value={selectedRepoId}
            onChange={(e) => {
              setSelectedRepoId(e.target.value)
              setResults([])
            }}
            className="px-3 py-2 text-sm border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-accent bg-canvas text-text-primary w-56"
          >
            <option value="">Select repository…</option>
            {indexedRepos.map((r) => (
              <option key={r.id} value={r.id}>
                {r.owner}/{r.name}
              </option>
            ))}
          </select>

          <form onSubmit={handleSearch} className="flex-1 flex gap-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search code, functions, classes…"
              disabled={!selectedRepoId}
              className="flex-1 px-3 py-2 text-sm border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-accent bg-canvas text-text-primary placeholder-text-muted disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!selectedRepoId || !searchQuery.trim() || searchMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-md text-sm font-medium hover:bg-accent-hover transition-colors disabled:opacity-50"
            >
              <Search size={14} />
              {searchMutation.isPending ? 'Searching…' : 'Search'}
            </button>
          </form>
        </div>

        {!selectedRepoId && indexedRepos.length === 0 && !loadingRepos && (
          <p className="text-sm text-text-secondary">
            No indexed repositories found. Index a repository first.
          </p>
        )}
      </div>

      {searchMutation.isPending && (
        <div className="max-w-3xl space-y-2">
          <p className="text-xs text-text-muted">Retrieving evidence and generating an answer…</p>
          <LoadingSkeleton rows={5} />
        </div>
      )}

      {searchMutation.isError && (
        <div className="max-w-3xl p-4 border border-danger/30 bg-danger-subtle rounded-md text-sm text-danger">
          {errorMessage}
        </div>
      )}

      {results.length > 0 && !searchMutation.isPending && (
        <div className="max-w-3xl space-y-2">
          <p className="text-xs text-text-muted">
            {results.length} result{results.length !== 1 ? 's' : ''} for "{searchQuery}"
          </p>
          {results.map((item) => (
            <div key={item.chunkId} className="border border-border rounded-lg overflow-hidden">
              <button
                onClick={() => setExpandedId(expandedId === item.chunkId ? null : item.chunkId)}
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
                  <span className={clsx(
                    'text-xs px-1.5 py-0.5 rounded shrink-0',
                    item.language === 'python' ? 'bg-info-subtle text-info' :
                    item.language === 'typescript' ? 'bg-accent-subtle text-accent' :
                    'bg-surface text-text-muted'
                  )}>
                    {item.language}
                  </span>
                </div>
                <div className="shrink-0 ml-2 text-text-muted">
                  {expandedId === item.chunkId ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </div>
              </button>
              {expandedId === item.chunkId && (
                <div className="border-t border-border">
                  <pre className="p-3 text-xs font-mono text-text-primary bg-surface-elevated overflow-x-auto whitespace-pre-wrap max-h-80">
                    {item.text}
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {results.length === 0 && searchMutation.isSuccess && !searchMutation.isPending && (
        <p className="text-sm text-text-secondary max-w-3xl">
          No matching code found for "{searchQuery}". Try different keywords.
        </p>
      )}
    </div>
  )
}
