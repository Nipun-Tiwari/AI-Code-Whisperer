import { FileText, GitBranch, Sparkles, Copy } from 'lucide-react'
import { useState } from 'react'
import { PageHeader, EmptyState } from '@/components'
import { clsx } from 'clsx'

type DocType = 'architecture' | 'module' | 'technical'

const DOC_TYPES: Array<{ value: DocType; label: string; description: string }> = [
  {
    value: 'architecture',
    label: 'Architecture Overview',
    description: 'High-level structure, key modules and their relationships',
  },
  {
    value: 'module',
    label: 'Module Explanation',
    description: 'Detailed explanation of a specific module or component',
  },
  {
    value: 'technical',
    label: 'Technical Reference',
    description: 'API surfaces, data models and integration points',
  },
]

export function DocumentationPage() {
  const [docType, setDocType] = useState<DocType>('architecture')
  const [scope, setScope] = useState('')

  // TODO: load generated document when task completes
  const generatedDoc = null

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Documentation"
        subtitle="Generate technical documentation grounded in repository evidence"
      />

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Configuration panel */}
          <div className="border border-border rounded-lg p-5 space-y-4">
            <h2 className="text-sm font-semibold text-text-primary">Documentation Request</h2>

            {/* Repository */}
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

            {/* Document type */}
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1.5">
                Document type
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {DOC_TYPES.map((dt) => (
                  <button
                    key={dt.value}
                    onClick={() => setDocType(dt.value)}
                    className={clsx(
                      'flex flex-col items-start gap-1 p-3 rounded-md border text-left transition-colors',
                      docType === dt.value
                        ? 'border-accent bg-accent-subtle'
                        : 'border-border hover:bg-surface',
                    )}
                  >
                    <span
                      className={clsx(
                        'text-sm font-medium',
                        docType === dt.value ? 'text-accent' : 'text-text-primary',
                      )}
                    >
                      {dt.label}
                    </span>
                    <span
                      className={clsx(
                        'text-xs',
                        docType === dt.value ? 'text-accent/80' : 'text-text-muted',
                      )}
                    >
                      {dt.description}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Optional scope */}
            <div>
              <label
                htmlFor="doc-scope"
                className="block text-xs font-medium text-text-secondary mb-1.5"
              >
                Scope <span className="text-text-muted font-normal">(optional)</span>
              </label>
              <input
                id="doc-scope"
                type="text"
                value={scope}
                onChange={(e) => setScope(e.target.value)}
                placeholder="e.g. src/services/auth or the entire repository"
                className={clsx(
                  'w-full px-3 py-2 text-sm rounded-md border border-border bg-canvas',
                  'text-text-primary placeholder:text-text-muted',
                  'focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent',
                )}
              />
            </div>

            <div className="flex justify-end">
              <button
                className={clsx(
                  'inline-flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium',
                  'bg-accent text-white hover:bg-accent-hover transition-colors',
                )}
                onClick={() => {
                  // TODO: call POST /api/v1/documentation/generate
                }}
              >
                <Sparkles size={13} />
                Generate Documentation
              </button>
            </div>
          </div>

          {/* Document preview */}
          {generatedDoc === null ? (
            <div className="border border-border border-dashed rounded-lg">
              <EmptyState
                icon={FileText}
                title="No document generated yet"
                description="Configure the options above and generate documentation grounded in your repository's indexed evidence."
                size="md"
              />
            </div>
          ) : (
            /* TODO: render generated document with citations */
            <div className="border border-border rounded-lg">
              <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-surface">
                <h3 className="text-sm font-semibold text-text-primary">Generated Document</h3>
                <button
                  className={clsx(
                    'inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium',
                    'border border-border text-text-secondary hover:bg-canvas transition-colors',
                  )}
                  onClick={() => {
                    // TODO: copy document to clipboard
                  }}
                >
                  <Copy size={12} />
                  Copy
                </button>
              </div>
              <div className="p-5 prose prose-sm max-w-none" />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
