import { Search, Code2, GitBranch } from 'lucide-react'
import { useState } from 'react'
import { PageHeader, EmptyState } from '@/components'
import { clsx } from 'clsx'

export function CodeExplorerPage() {
  const [query, setQuery] = useState('')

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Code Explorer"
        subtitle="Search and browse indexed repository files and symbols"
      />

      <div className="flex-1 flex overflow-hidden">
        {/* Left: file browser pane */}
        <div className="w-64 border-r border-border flex flex-col shrink-0">
          <div className="p-3 border-b border-border">
            <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
              Repository
            </p>
            <button
              className={clsx(
                'w-full flex items-center gap-1.5 px-2 py-1.5 rounded border text-xs text-left',
                'border-border text-text-secondary hover:bg-surface transition-colors',
              )}
            >
              <GitBranch size={11} />
              Select repository
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-3">
            {/* TODO: render repository file tree here */}
            <EmptyState
              icon={Code2}
              title="No repository selected"
              description="Select a repository to browse its files."
              size="sm"
            />
          </div>
        </div>

        {/* Right: search + viewer */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {/* Search bar */}
          <div className="border-b border-border p-3">
            <div className="relative">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
              />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search code, symbols or file paths…"
                className={clsx(
                  'w-full pl-9 pr-3 py-2 text-sm rounded-md border border-border bg-canvas',
                  'text-text-primary placeholder:text-text-muted',
                  'focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent',
                )}
              />
            </div>
          </div>

          {/* Code viewer area */}
          <div className="flex-1 overflow-auto">
            {!query ? (
              <EmptyState
                icon={Search}
                title="Search the codebase"
                description="Enter a search query to find relevant files, symbols and code snippets."
                size="md"
              />
            ) : (
              /* TODO: render search results and code viewer */
              <div className="p-6">
                <p className="text-sm text-text-muted">
                  Search results for &ldquo;{query}&rdquo; will appear here.
                </p>
                {/* TODO: implement code search via /api/v1/chat/query or MCP search tools */}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
