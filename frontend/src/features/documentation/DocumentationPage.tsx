import { useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { FileText, Loader2, Copy, RefreshCw, Download } from 'lucide-react'
import html2pdf from 'html2pdf.js'
import { PageHeader, StatusBadge, EmptyState, MarkdownView } from '@/components'
import { AppApiError } from '@/api/client'
import { useRepositories } from '@/hooks'
import { generateDocumentation } from '@/api/documentation'
import type { TaskResponse } from '@/api/tasks'

type DocType = 'architecture' | 'module' | 'technical'

type DocumentationResult = {
  docType?: string
  title?: string
  content?: string
  citations?: Array<{ filePath: string; lineStart: number; lineEnd: number; symbolName?: string }>
  repositoryVersion?: string
  gaps?: string[]
  generatedAt?: string
  answer?: string
  errors?: string[]
}

const DOC_TYPES: { value: DocType; label: string; description: string }[] = [
  { value: 'architecture', label: 'Architecture Overview', description: 'High-level system design and component relationships' },
  { value: 'module', label: 'Module Explanation', description: 'Detailed explanation of a specific file or module' },
  { value: 'technical', label: 'Technical Reference', description: 'API and function-level documentation' },
]

function sanitizePdfFilename(title: string | undefined): string {
  const base = (title || 'documentation')
    .trim()
    .replace(/[<>:"/\\|?*\u0000-\u001f]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 80)
  return `${base || 'documentation'}.pdf`
}

export default function DocumentationPage() {
  const { data: repos } = useRepositories()
  const [selectedRepo, setSelectedRepo] = useState('')
  const [docType, setDocType] = useState<DocType>('architecture')
  const [modulePath, setModulePath] = useState('')
  const [result, setResult] = useState<TaskResponse | null>(null)
  const [copied, setCopied] = useState(false)
  const [pdfExporting, setPdfExporting] = useState(false)
  const pdfExportRef = useRef<HTMLDivElement>(null)

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
  const citations = docResult?.citations ?? []
  const gaps = docResult?.gaps ?? []
  const errors = docResult?.errors ?? []
  const content = docResult?.content || docResult?.answer || ''

  const errorMessage =
    mutation.error instanceof AppApiError
      ? mutation.error.message
      : mutation.error instanceof Error
        ? mutation.error.message
        : 'Documentation generation failed. Please try again.'

  const handleCopy = () => {
    if (content) {
      navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleDownloadPdf = async () => {
    const el = pdfExportRef.current
    if (!el || !content || pdfExporting) return

    setPdfExporting(true)
    const previousBg = el.style.backgroundColor
    const previousColor = el.style.color
    // Prefer light background for readable screenshots in dark theme.
    el.style.backgroundColor = '#ffffff'
    el.style.color = '#111827'

    try {
      await html2pdf()
        .set({
          margin: [10, 10, 10, 10],
          filename: sanitizePdfFilename(docResult?.title),
          image: { type: 'jpeg', quality: 0.98 },
          html2canvas: { scale: 2, useCORS: true, backgroundColor: '#ffffff' },
          jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
        })
        .from(el)
        .save()
    } catch (err) {
      console.error('PDF export failed', err)
    } finally {
      el.style.backgroundColor = previousBg
      el.style.color = previousColor
      setPdfExporting(false)
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
        {mutation.isError && (
          <p className="text-sm text-danger">{errorMessage}</p>
        )}
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
              <h2 className="text-base font-medium text-text-primary">{docResult.title || 'Documentation'}</h2>
              <StatusBadge status={(result?.status === 'completed' ? 'completed' : 'partial') as 'completed' | 'partial'} />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-muted">v: {docResult.repositoryVersion?.slice(0, 8) || 'unknown'}</span>
              <button
                className="flex items-center gap-1.5 px-3 py-1.5 border border-border text-sm text-text-secondary rounded-md hover:border-accent/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={handleCopy}
                disabled={!content}
              >
                <Copy size={12} />
                {copied ? 'Copied!' : 'Copy'}
              </button>
              <button
                className="flex items-center gap-1.5 px-3 py-1.5 border border-border text-sm text-text-secondary rounded-md hover:border-accent/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={handleDownloadPdf}
                disabled={!content || mutation.isPending || pdfExporting}
              >
                {pdfExporting ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />}
                {pdfExporting ? 'Preparing PDF...' : 'Download PDF'}
              </button>
            </div>
          </div>

          {errors.length > 0 && (
            <ul className="space-y-1">
              {errors.map((err, i) => (
                <li key={i} className="text-xs text-danger break-all">{err}</li>
              ))}
            </ul>
          )}

          <div className="grid grid-cols-3 gap-4">
            {/* Main content — PDF export target (title + body; not sources/gaps) */}
            <div className="col-span-2 border border-border rounded-lg p-5 bg-surface">
              <div ref={pdfExportRef} id="documentation-pdf-export" className="bg-surface p-1 rounded space-y-3">
                <h1 className="text-base font-semibold text-text-primary">
                  {docResult.title || 'Documentation'}
                </h1>
                <MarkdownView>{content || 'No documentation content was generated.'}</MarkdownView>
              </div>
            </div>

            {/* Citations panel */}
            <div className="space-y-3">
              {citations.length > 0 && (
                <div className="border border-border rounded-lg p-4 bg-surface">
                  <h4 className="text-xs font-medium text-text-secondary uppercase tracking-wide mb-2">Sources ({citations.length})</h4>
                  <ul className="space-y-1.5">
                    {citations.map((c, i) => (
                      <li key={i} className="text-xs font-mono text-text-secondary">
                        {c.filePath}
                        {c.lineStart ? `:${c.lineStart}` : ''}
                        {c.symbolName ? <span className="text-accent"> {c.symbolName}</span> : null}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {gaps.length > 0 && (
                <div className="border border-warning/30 rounded-lg p-4 bg-warning-subtle">
                  <h4 className="text-xs font-medium text-warning uppercase tracking-wide mb-2">Gaps</h4>
                  <ul className="space-y-1">
                    {gaps.map((g, i) => (
                      <li key={i} className="text-xs text-warning/80">{g}</li>
                    ))}
                  </ul>
                </div>
              )}

              {docResult.generatedAt && (
                <div className="text-xs text-text-muted">
                  Generated {new Date(docResult.generatedAt).toLocaleString()}
                </div>
              )}
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
