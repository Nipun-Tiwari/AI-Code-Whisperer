import { Send, GitBranch } from 'lucide-react'
import { useState } from 'react'
import { PageHeader, EmptyState } from '@/components'
import { clsx } from 'clsx'

export function WorkspacePage() {
  const [question, setQuestion] = useState('')

  // TODO: load selected repository from query param or store
  const selectedRepo = null

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="AI Workspace"
        subtitle="Ask questions about your indexed repositories"
      />

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Main content area */}
        <div className="flex-1 overflow-y-auto p-6">
          {selectedRepo === null ? (
            <EmptyState
              icon={GitBranch}
              title="No repository selected"
              description="Select an indexed repository to start asking questions about the codebase."
              size="md"
            />
          ) : (
            /* TODO: render conversation messages here */
            <div className="max-w-3xl mx-auto space-y-4" />
          )}
        </div>

        {/* Input bar */}
        <div className="border-t border-border bg-canvas p-4">
          <div className="max-w-3xl mx-auto">
            {/* Repository context chip */}
            <div className="mb-2 flex items-center gap-2">
              <span className="text-xs text-text-muted">Repository:</span>
              <button
                className={clsx(
                  'inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-xs',
                  'border-border text-text-secondary hover:bg-surface transition-colors',
                )}
              >
                <GitBranch size={11} />
                Select repository
              </button>
            </div>

            <div className="flex items-end gap-2">
              <div className="flex-1 relative">
                <textarea
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="Ask a question about the repository… (e.g. 'How does the authentication middleware work?')"
                  className={clsx(
                    'w-full resize-none rounded-lg border border-border bg-canvas px-3 py-2.5 text-sm',
                    'text-text-primary placeholder:text-text-muted',
                    'focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent',
                    'min-h-[80px] max-h-[200px]',
                  )}
                  rows={3}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      // TODO: submit question
                    }
                  }}
                />
              </div>
              <button
                disabled={!question.trim() || selectedRepo === null}
                className={clsx(
                  'shrink-0 flex items-center justify-center w-10 h-10 rounded-lg transition-colors',
                  'bg-accent text-white hover:bg-accent-hover',
                  'disabled:opacity-40 disabled:cursor-not-allowed',
                )}
                title="Send question"
                onClick={() => {
                  // TODO: submit question to AI Workspace API
                }}
              >
                <Send size={16} />
              </button>
            </div>
            <p className="mt-1.5 text-xs text-text-muted">
              Press Enter to send, Shift+Enter for a new line.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

