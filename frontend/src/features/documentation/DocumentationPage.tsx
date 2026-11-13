import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { FileText, Loader2, Copy, RefreshCw } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { PageHeader, StatusBadge, EmptyState } from '@/components'
import { useRepositories } from '@/hooks'
import { generateDocumentation } from '@/api/documentation'
import type { TaskResponse } from '@/api/tasks'

type DocType = 'architecture' | 'module' | 'technical'

type DocumentationResult = {
  doc_type: string
  title: string
  content: string
  citations: Array<{ file_path: string; line_start: number; line_end: number; symbol_name?: string }>
  repository_version: string
  gaps: string[]
  generated_at: string
}

const DOC_TYPES: { value: DocType; label: string; description: string }[] = [
  { value: 'architecture', label: 'Architecture Overview', description: 'High-level system design and component relationships' },
  { value: 'module', label: 'Module Explanation', description: 'Detailed explanation of a specific file or module' },
  { value: 'technical', label: 'Technical Reference', description: 'API and function-level documentation' },
]

export default function DocumentationPage() {
  const { data: repos } = useRepositories()
  const [selectedRepo, setSelectedRepo] = useState('')
  const [docType, setDocType] = useState<DocType>('architecture')
  const [modulePath, setModulePath] = useState('')
  const [result, setResult] = useState<TaskResponse | null>(null)
  const [copied, setCopied] = useState(false)

  const mutation = useMutation({
    mutationFn: () =>
      generateDocumentation({
        repository_id: selectedRepo,
        doc_type: docType,
        module_path: modulePath,
      }),
    onSuccess: (data) => setResult(data),
  })

  const docResult = result?.result as DocumentationResult | undefined

  const handleCopy = () => {
    if (docResult?.content) {
      navigator.clipboard.writeText(docResult.content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <PageHeader
        title="Documentation"
        subtitle="Generate technical documentation grounded in repository evidence."
      />

      {/* Controls */}
      <div className="border border-border rounded-lg p-5 bg-surface space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <label className="text-sm font-medium text-text-primary">Repository</label>
            <select
              className="w-full border border-border rounded-md px-3 py-2 text-sm bg-canvas focus:outline-none focus:ring-1 focus:ring-accent"
              value={selectedRepo}
              onChange={(e) => setSelectedRepo(e.target.value)}
            >
              <option value="">Select a repository...</option>
              {repos?.items?.map((r) => (
                <option key={r.id} value={r.id}>{r.owner}/{r.name}</option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium text-text-primary">Documentation type</label>
            <select
              className="w-full border border-border rounded-md px-3 py-2 text-sm bg-canvas focus:outline-none focus:ring-1 focus:ring-accent"
              value={docType}
              onChange={(e) => setDocType(e.target.value as DocType)}
            >
              {DOC_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
        </div>

        {(docType === 'module' || docType === 'technical') && (
          <div className="space-y-1">
            <label className="text-sm font-medium text-text-primary">Module path (optional)</label>
            <input
              type="text"
              className="w-full border border-border rounded-md px-3 py-2 text-sm bg-canvas focus:outline-none focus:ring-1 focus:ring-accent font-mono"
              placeholder="e.g. src/services/auth.py"
              value={modulePath}
              onChange={(e) => setModulePath(e.target.value)}
            />
          </div>
        )}

        <div className="flex gap-2">
          <button
            className="flex items-center gap-2 px-4 py-2 bg-accent text-white text-sm font-medium rounded-md hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            disabled={!selectedRepo || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14} />}
            {mutation.isPending ? 'Generating...' : 'Generate'}
          </button>

          {docResult && (
            <button
              className="flex items-center gap-2 px-4 py-2 border border-border text-sm text-text-secondary rounded-md hover:border-accent/50 transition-colors"
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
            >
              <RefreshCw size={14} />
              Regenerate
            </button>
          )}
        </div>
      </div>

      {/* Loading */}
      {mutation.isPending && (
        <div className="border border-border rounded-lg p-6 flex items-center gap-3 text-text-secondary text-sm bg-surface">
          <Loader2 size={14} className="animate-spin" />
          Retrieving evidence and generating documentation...
        </div>
      )}

      {/* Result */}
      {docResult && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h2 className="text-base font-medium text-text-primary">{docResult.title}</h2>
              <StatusBadge status={(result?.status === 'completed' ? 'completed' : 'partial') as 'completed' | 'partial'} />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-muted">v: {docResult.repository_version?.slice(0, 8) || 'unknown'}</span>
              <button
                className="flex items-center gap-1.5 px-3 py-1.5 border border-border text-sm text-text-secondary rounded-md hover:border-accent/50 transition-colors"
                onClick={handleCopy}
              >
                <Copy size={12} />
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            {/* Main content */}
            <div className="col-span-2 border border-border rounded-lg p-5 bg-surface">
              <div className="prose prose-sm max-w-none text-text-primary [&>h1]:text-base [&>h1]:font-semibold [&>h2]:text-sm [&>h2]:font-semibold [&>h3]:text-sm [&>h3]:font-medium [&>p]:text-sm [&>p]:text-text-secondary [&>ul]:text-sm [&>ul]:text-text-secondary [&>code]:text-xs [&>pre]:text-xs [&>pre]:bg-surface-elevated [&>pre]:p-3 [&>pre]:rounded">
                <ReactMarkdown>{docResult.content}</ReactMarkdown>
              </div>
            </div>

            {/* Citations panel */}
            <div className="space-y-3">
              {docResult.citations.length > 0 && (
                <div className="border border-border rounded-lg p-4 bg-surface">
                  <h4 className="text-xs font-medium text-text-secondary uppercase tracking-wide mb-2">Sources ({docResult.citations.length})</h4>
                  <ul className="space-y-1.5">
                    {docResult.citations.map((c, i) => (
                      <li key={i} className="text-xs font-mono text-text-secondary">
                        {c.file_path}
                        {c.line_start ? `:${c.line_start}` : ''}
                        {c.symbol_name ? <span className="text-accent"> {c.symbol_name}</span> : null}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {docResult.gaps.length > 0 && (
                <div className="border border-warning/30 rounded-lg p-4 bg-warning-subtle">
                  <h4 className="text-xs font-medium text-warning uppercase tracking-wide mb-2">Gaps</h4>
                  <ul className="space-y-1">
                    {docResult.gaps.map((g, i) => (
                      <li key={i} className="text-xs text-warning/80">{g}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="text-xs text-text-muted">
                Generated {new Date(docResult.generated_at).toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      )}

      {!docResult && !mutation.isPending && (
        <EmptyState
          icon={FileText}
          title="No documentation yet"
          description="Select a repository and documentation type, then click Generate."
        />
      )}
    </div>
  )
}
