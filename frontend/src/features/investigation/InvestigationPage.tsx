import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Search, AlertCircle, ChevronDown, ChevronRight, Loader2 } from 'lucide-react'
import { PageHeader, StatusBadge, EmptyState } from '@/components'
import { AppApiError } from '@/api/client'
import { useRepositories } from '@/hooks'
import { startInvestigation } from '@/api/investigations'
import type { TaskResponse } from '@/api/tasks'
import { clsx } from 'clsx'

type Hypothesis = {
  rank: number
  description: string
  supportingEvidence: string[]
  confidence: 'high' | 'medium' | 'low'
}

type ExecutionStep = {
  step: number
  location: string
  description: string
  evidence: 'source_fact' | 'inferred'
}

type InvestigationResult = {
  symptomSummary?: string
  affectedFiles?: string[]
  executionPath?: ExecutionStep[]
  hypotheses?: Hypothesis[]
  suggestedRemediation?: string
  limitations?: string
  followUpChecks?: string[]
  answer?: string
  errors?: string[]
}

export default function InvestigationPage() {
  const { data: repos } = useRepositories()
  const [selectedRepo, setSelectedRepo] = useState('')
  const [description, setDescription] = useState('')
  const [expandedHypothesis, setExpandedHypothesis] = useState<number | null>(0)
  const [result, setResult] = useState<TaskResponse | null>(null)

  const mutation = useMutation({
    mutationFn: () =>
      startInvestigation({
        repository_id: selectedRepo,
        description,
      }),
    onSuccess: (data) => setResult(data),
  })

  const investigationResult = result?.result as InvestigationResult | undefined
  const affectedFiles = investigationResult?.affectedFiles ?? []
  const executionPath = investigationResult?.executionPath ?? []
  const hypotheses = investigationResult?.hypotheses ?? []
  const errors = investigationResult?.errors ?? []

  const confidenceColor: Record<string, string> = {
    high: 'text-danger',
    medium: 'text-warning',
    low: 'text-text-secondary',
  }

  const errorMessage =
    mutation.error instanceof AppApiError
      ? mutation.error.message
      : mutation.error instanceof Error
        ? mutation.error.message
        : 'Investigation failed. Please try again.'

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <PageHeader
        title="Code Investigation"
        subtitle="Trace likely root causes of reported defects using indexed repository evidence."
      />

      <div className="border border-border rounded-lg p-5 space-y-4 bg-surface">
        <div className="space-y-1">
          <label className="text-sm font-medium text-text-primary">Repository</label>
          <select
            className="w-full border border-border rounded-md px-3 py-2 text-sm bg-canvas focus:outline-none focus:ring-1 focus:ring-accent"
            value={selectedRepo}
            onChange={(e) => setSelectedRepo(e.target.value)}
          >
            <option value="">Select a repository...</option>
            {repos?.items?.map((r) => (
              <option key={r.id} value={r.id}>
                {r.owner}/{r.name}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1">
          <label className="text-sm font-medium text-text-primary">Issue description</label>
          <textarea
            className="w-full border border-border rounded-md px-3 py-2 text-sm bg-canvas focus:outline-none focus:ring-1 focus:ring-accent min-h-[120px] resize-y"
            placeholder="Describe the error or unexpected behaviour. Include error messages, affected features, or reproduction steps."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        <button
          className="flex items-center gap-2 px-4 py-2 bg-accent text-white text-sm font-medium rounded-md hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          disabled={!selectedRepo || !description.trim() || mutation.isPending}
          onClick={() => mutation.mutate()}
        >
          {mutation.isPending ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <Search size={14} />
          )}
          {mutation.isPending ? 'Investigating...' : 'Start Investigation'}
        </button>

        {mutation.isError && (
          <p className="text-sm text-danger">{errorMessage}</p>
        )}
      </div>

      {mutation.isPending && (
        <div className="border border-border rounded-lg p-6 space-y-3 bg-surface">
          <div className="flex items-center gap-2 text-text-secondary text-sm">
            <Loader2 size={14} className="animate-spin" />
            <span>Running investigation...</span>
          </div>
          <div className="text-xs text-text-muted">Retrieving evidence and tracing code paths</div>
        </div>
      )}

      {investigationResult && (
        <div className="space-y-4">
          {(investigationResult.symptomSummary || investigationResult.answer || errors.length > 0) && (
            <div className="border border-border rounded-lg p-5 bg-surface space-y-2">
              <div className="flex items-center gap-2">
                <AlertCircle size={14} className="text-warning" />
                <span className="text-sm font-medium text-text-primary">Symptom</span>
                <StatusBadge status={(result?.status === 'completed' ? 'completed' : 'partial') as 'completed' | 'partial'} />
              </div>
              <p className="text-sm text-text-secondary">
                {investigationResult.symptomSummary || investigationResult.answer || 'Investigation finished with limited output.'}
              </p>
              {affectedFiles.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {affectedFiles.map((f) => (
                    <span key={f} className="text-xs font-mono bg-surface-elevated border border-border px-2 py-0.5 rounded text-text-secondary">
                      {f}
                    </span>
                  ))}
                </div>
              )}
              {errors.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {errors.map((err, i) => (
                    <li key={i} className="text-xs text-danger break-all">{err}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {executionPath.length > 0 && (
            <div className="border border-border rounded-lg p-5 bg-surface space-y-3">
              <h3 className="text-sm font-medium text-text-primary">Execution Path</h3>
              <div className="space-y-2">
                {executionPath.map((step) => (
                  <div key={step.step} className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <div className="w-5 h-5 rounded-full bg-accent-subtle border border-accent text-accent text-xs flex items-center justify-center font-mono shrink-0">
                        {step.step}
                      </div>
                      <div className="w-px flex-1 bg-border mt-1" />
                    </div>
                    <div className="pb-3 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-accent">{step.location}</span>
                        <span className={clsx(
                          'text-xs px-1.5 py-0.5 rounded border',
                          step.evidence === 'source_fact'
                            ? 'bg-success-subtle border-success/30 text-success'
                            : 'bg-warning-subtle border-warning/30 text-warning'
                        )}>
                          {step.evidence === 'source_fact' ? 'Source fact' : 'Inferred'}
                        </span>
                      </div>
                      <p className="text-sm text-text-secondary mt-0.5">{step.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {hypotheses.length > 0 && (
            <div className="border border-border rounded-lg p-5 bg-surface space-y-3">
              <h3 className="text-sm font-medium text-text-primary">Root Cause Hypotheses</h3>
              <div className="space-y-2">
                {hypotheses.map((h) => (
                  <div key={h.rank} className="border border-border rounded-md overflow-hidden">
                    <button
                      className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-surface-elevated transition-colors"
                      onClick={() => setExpandedHypothesis(expandedHypothesis === h.rank ? null : h.rank)}
                    >
                      <span className="text-xs font-medium text-text-muted w-5">#{h.rank}</span>
                      <span className="flex-1 text-sm text-text-primary">{h.description}</span>
                      <span className={clsx('text-xs font-medium', confidenceColor[h.confidence])}>
                        {h.confidence}
                      </span>
                      {expandedHypothesis === h.rank ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    </button>
                    {expandedHypothesis === h.rank && (h.supportingEvidence?.length ?? 0) > 0 && (
                      <div className="px-4 pb-3 border-t border-border bg-surface-elevated">
                        <ul className="mt-2 space-y-1">
                          {(h.supportingEvidence ?? []).map((e, i) => (
                            <li key={i} className="text-xs text-text-secondary font-mono">{e}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {investigationResult.suggestedRemediation && (
            <div className="border border-border rounded-lg p-5 bg-surface space-y-2">
              <h3 className="text-sm font-medium text-text-primary">Suggested Remediation</h3>
              <p className="text-sm text-text-secondary whitespace-pre-wrap">{investigationResult.suggestedRemediation}</p>
            </div>
          )}

          {investigationResult.limitations && (
            <div className="border border-border/50 rounded-lg p-4 bg-warning-subtle text-warning text-xs">
              <span className="font-medium">Limitations: </span>
              {investigationResult.limitations}
            </div>
          )}
        </div>
      )}

      {!investigationResult && !mutation.isPending && !mutation.isError && (
        <EmptyState
          icon={Search}
          title="No investigation yet"
          description="Select a repository, describe the issue, and start an investigation."
        />
      )}
    </div>
  )
}
