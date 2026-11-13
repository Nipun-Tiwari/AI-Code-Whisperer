import { Search, GitBranch, Send } from 'lucide-react'
import { useState } from 'react'
import { PageHeader, EmptyState } from '@/components'
import { clsx } from 'clsx'

export function InvestigationPage() {
  const [description, setDescription] = useState('')

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Investigations"
        subtitle="Submit a defect description to trace code-level root causes"
      />

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {/* Investigation form */}
          <div className="border border-border rounded-lg p-5 space-y-4">
            <h2 className="text-sm font-semibold text-text-primary">Start an Investigation</h2>

            {/* Repository selector */}
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1.5">
                Repository
              </label>
              <button
                className={clsx(
                  'w-full flex items-center gap-1.5 px-3 py-2 rounded-md border text-sm text-left',
                  'border-border text-text-secondary hover:bg-surface transition-colors',
                )}
              >
                <GitBranch size={13} />
                Select repository
                <span className="ml-auto text-xs text-text-muted">required</span>
              </button>
            </div>

            {/* Issue description */}
            <div>
              <label
                htmlFor="issue-description"
                className="block text-xs font-medium text-text-secondary mb-1.5"
              >
                Defect or issue description
              </label>
              <textarea
                id="issue-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder={`Describe the defect or unexpected behaviour you're investigating.\n\nExample: "API endpoint /users/profile returns a 500 error when the user has no profile photo set. The error message shows NullPointerException in UserService.getProfile()."`}
                className={clsx(
                  'w-full resize-none rounded-lg border border-border bg-canvas px-3 py-2.5 text-sm',
                  'text-text-primary placeholder:text-text-muted',
                  'focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent',
                  'min-h-[140px]',
                )}
                rows={6}
              />
              <p className="mt-1 text-xs text-text-muted">
                Include error messages, affected endpoints, or observed symptoms. CodeWhisperer will
                trace code-level causes from repository evidence only — not runtime data.
              </p>
            </div>

            <div className="flex justify-end">
              <button
                disabled={!description.trim()}
                className={clsx(
                  'inline-flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium',
                  'bg-accent text-white hover:bg-accent-hover transition-colors',
                  'disabled:opacity-40 disabled:cursor-not-allowed',
                )}
                onClick={() => {
                  // TODO: call POST /api/v1/investigations
                }}
              >
                <Send size={13} />
                Start Investigation
              </button>
            </div>
          </div>

          {/* Results area */}
          <div className="border border-border border-dashed rounded-lg">
            <EmptyState
              icon={Search}
              title="No investigation started"
              description="Submit a defect description above to begin code-level root-cause analysis."
              size="md"
            />
          </div>

          {/* TODO: render investigation report when task completes */}
          {/* TODO: show task progress stages: Planning, Retrieving evidence, Tracing code, Analyzing hypotheses, Synthesizing */}
        </div>
      </div>
    </div>
  )
}
