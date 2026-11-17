import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Plus, RefreshCw, Trash2, ExternalLink, GitBranch } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { PageHeader, DataTable, StatusBadge, ConfirmationDialog } from '@/components'
import { GitHubConnectButton } from '@/components/integrations/GitHubConnectButton'
import {
  listRepositories,
  listGitHubConnections,
  listAccessibleRepos,
  addRepository,
  removeRepository,
  startIndexJob,
  type GitHubRepo,
} from '@/api/repositories'
import type { Repository } from '@/types'
import { clsx } from 'clsx'

// Job-stage statuses plus the repository-level 'indexing' status — a repo sits
// in 'indexing' for the lifetime of its active job, so both need to count as active.
const ACTIVE_STATUSES = new Set(['indexing', 'queued', 'fetching', 'classifying', 'parsing', 'summarizing', 'embedding', 'persisting'])

export default function RepositoriesPage() {
  const queryClient = useQueryClient()
  const [showAddModal, setShowAddModal] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<Repository | null>(null)
  const [githubError, setGithubError] = useState<string | null>(null)
  const [searchParams, setSearchParams] = useSearchParams()

  useEffect(() => {
    const result = searchParams.get('github')
    if (!result) return

    if (result === 'connected') {
      setShowAddModal(true)
      queryClient.invalidateQueries({ queryKey: ['github-connections'] })
      queryClient.invalidateQueries({ queryKey: ['accessible-repos'] })
    } else if (result === 'error') {
      const reason = searchParams.get('reason')
      setGithubError(
        reason === 'authorization_denied'
          ? 'GitHub authorization was cancelled.'
          : 'Unable to connect GitHub. Please try again.',
      )
    }

    const cleanedParams = new URLSearchParams(searchParams)
    cleanedParams.delete('github')
    cleanedParams.delete('reason')
    setSearchParams(cleanedParams, { replace: true })
  }, [queryClient, searchParams, setSearchParams])

  const hasActive = (repos: Repository[]) =>
    repos.some((r) => ACTIVE_STATUSES.has(r.status))

  const { data, isLoading, error } = useQuery({
    queryKey: ['repositories'],
    queryFn: () => listRepositories(),
    refetchInterval: (query) => {
      const repos = query.state.data?.items ?? []
      return hasActive(repos) ? 5000 : false
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => removeRepository(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repositories'] })
      setDeleteTarget(null)
    },
  })

  const indexMutation = useMutation({
    mutationFn: (id: string) => startIndexJob(id, 'full'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['repositories'] }),
  })

  const repos = data?.items ?? []

  const columns = [
    {
      key: 'name',
      header: 'Repository',
      render: (repo: Repository) => (
        <div className="flex flex-col gap-0.5">
          <Link
            to={`/repositories/${repo.id}`}
            className="font-medium text-text-primary hover:text-accent transition-colors"
          >
            {repo.owner}/{repo.name}
          </Link>
          {repo.description && (
            <span className="text-xs text-text-muted line-clamp-1">{repo.description}</span>
          )}
        </div>
      ),
    },
    {
      key: 'visibility',
      header: 'Visibility',
      render: (repo: Repository) => (
        <span className="text-xs text-text-secondary capitalize">{repo.visibility}</span>
      ),
    },
    {
      key: 'branch',
      header: 'Branch',
      render: (repo: Repository) => (
        <span className="flex items-center gap-1 text-sm text-text-secondary">
          <GitBranch size={12} />
          {repo.selectedBranch}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Index Status',
      render: (repo: Repository) => <StatusBadge status={repo.status} />,
    },
    {
      key: 'indexed',
      header: 'Last Indexed',
      render: (repo: Repository) =>
        repo.latestVersion ? (
          <span className="text-xs text-text-secondary">
            {new Date(repo.latestVersion.indexedAt).toLocaleDateString()}
          </span>
        ) : (
          <span className="text-xs text-text-muted">Never</span>
        ),
    },
    {
      key: 'actions',
      header: '',
      render: (repo: Repository) => (
        <div className="flex items-center gap-1 justify-end">
          <button
            onClick={() => indexMutation.mutate(repo.id)}
            disabled={ACTIVE_STATUSES.has(repo.status) || indexMutation.isPending}
            className="p-1.5 rounded hover:bg-surface text-text-secondary hover:text-accent transition-colors disabled:opacity-40"
            title="Start indexing"
          >
            <RefreshCw size={14} className={clsx(ACTIVE_STATUSES.has(repo.status) && 'animate-spin')} />
          </button>
          <button
            onClick={() => setDeleteTarget(repo)}
            className="p-1.5 rounded hover:bg-danger-subtle text-text-secondary hover:text-danger transition-colors"
            title="Remove repository"
          >
            <Trash2 size={14} />
          </button>
        </div>
      ),
    },
  ]

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Repositories"
        subtitle="Connect and manage your GitHub repositories for indexing and analysis."
        actions={
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-3 py-2 bg-accent text-white rounded-md text-sm font-medium hover:bg-accent-hover transition-colors"
          >
            <Plus size={16} />
            Add Repository
          </button>
        }
      />

      {githubError && (
        <p className="text-sm text-danger" role="alert">
          {githubError}
        </p>
      )}

      <DataTable
        columns={columns}
        data={repos}
        keyExtractor={(r) => r.id}
        isLoading={isLoading}
        error={error ? String(error) : undefined}
        emptyTitle="No repositories connected"
        emptyDescription="Connect a GitHub repository to start indexing and analyzing your code."
        emptyAction={
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-3 py-2 bg-accent text-white rounded-md text-sm font-medium hover:bg-accent-hover transition-colors"
          >
            <Plus size={16} />
            Add Repository
          </button>
        }
      />

      {showAddModal && (
        <AddRepositoryModal
          onClose={() => setShowAddModal(false)}
          onAdded={() => {
            setShowAddModal(false)
            queryClient.invalidateQueries({ queryKey: ['repositories'] })
          }}
        />
      )}

      <ConfirmationDialog
        open={!!deleteTarget}
        onOpenChange={(open) => { if (!open) setDeleteTarget(null) }}
        title="Remove Repository"
        description={`Remove "${deleteTarget?.owner}/${deleteTarget?.name}"? This will delete all indexed data for this repository.`}
        confirmLabel="Remove"
        variant="danger"
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        isLoading={deleteMutation.isPending}
      />
    </div>
  )
}

// ── Add Repository Modal ──────────────────────────────────────────────────────

function AddRepositoryModal({
  onClose,
  onAdded,
}: {
  onClose: () => void
  onAdded: () => void
}) {
  const [selectedRepo, setSelectedRepo] = useState<GitHubRepo | null>(null)
  const [branch, setBranch] = useState('')

  const {
    data: connections,
    isLoading: loadingConnections,
    error: connectionsError,
    refetch: refetchConnections,
  } = useQuery({
    queryKey: ['github-connections'],
    queryFn: listGitHubConnections,
  })

  const {
    data: accessibleRepos,
    isLoading: loadingRepos,
    error: accessibleReposError,
    refetch: refetchAccessibleRepos,
  } = useQuery({
    queryKey: ['accessible-repos'],
    queryFn: listAccessibleRepos,
    enabled: (connections?.length ?? 0) > 0,
  })

  const addMutation = useMutation({
    mutationFn: () =>
      addRepository({
        owner: selectedRepo!.owner,
        name: selectedRepo!.name,
        branch: branch || selectedRepo!.defaultBranch,
        github_connection_id: selectedRepo!.githubConnectionId,
      }),
    onSuccess: onAdded,
  })

  const hasConnections = (connections?.length ?? 0) > 0

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-canvas border border-border rounded-lg shadow-lg w-full max-w-lg mx-4">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-base font-semibold text-text-primary">Add Repository</h2>
          <button onClick={onClose} className="text-text-secondary hover:text-text-primary p-1">
            ×
          </button>
        </div>

        <div className="p-4 space-y-4">
          {loadingConnections ? (
            <p className="text-sm text-text-secondary text-center py-4">
              Checking GitHub connection…
            </p>
          ) : connectionsError ? (
            <div className="text-center py-6 space-y-3">
              <p className="text-sm text-danger" role="alert">
                Unable to load your GitHub connections.
              </p>
              <button
                onClick={() => refetchConnections()}
                className="text-sm text-accent hover:underline"
              >
                Try again
              </button>
            </div>
          ) : !hasConnections ? (
            <div className="text-center py-6 space-y-3">
              <p className="text-sm text-text-secondary">
                Connect your GitHub account to browse and add repositories.
              </p>
              <GitHubConnectButton
                className="inline-flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-md text-sm font-medium hover:bg-accent-hover transition-colors"
              >
                <ExternalLink size={14} />
                Connect GitHub
              </GitHubConnectButton>
            </div>
          ) : loadingRepos ? (
            <p className="text-sm text-text-secondary text-center py-4">Loading repositories…</p>
          ) : accessibleReposError ? (
            <div className="text-center py-6 space-y-3">
              <p className="text-sm text-danger" role="alert">
                Unable to load repositories from GitHub.
              </p>
              <button
                onClick={() => refetchAccessibleRepos()}
                className="text-sm text-accent hover:underline"
              >
                Try again
              </button>
              <GitHubConnectButton
                className="inline-flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-md text-sm font-medium hover:bg-accent-hover transition-colors"
              >
                <ExternalLink size={14} />
                Reconnect GitHub
              </GitHubConnectButton>
            </div>
          ) : (accessibleRepos?.length ?? 0) === 0 ? (
            <div className="text-center py-6 space-y-3">
              <p className="text-sm text-text-secondary">
                No repositories are available to this GitHub App installation. Update its
                repository access in GitHub settings, then reconnect.
              </p>
              <GitHubConnectButton
                className="inline-flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-md text-sm font-medium hover:bg-accent-hover transition-colors"
              >
                <ExternalLink size={14} />
                Update GitHub Access
              </GitHubConnectButton>
            </div>
          ) : (
            <>
              <div className="max-h-64 overflow-y-auto space-y-1 border border-border rounded-md p-2">
                {(accessibleRepos ?? []).map((repo) => (
                  <button
                    key={repo.id}
                    onClick={() => {
                      setSelectedRepo(repo)
                      setBranch(repo.defaultBranch)
                    }}
                    className={clsx(
                      'w-full text-left px-3 py-2 rounded text-sm transition-colors',
                      selectedRepo?.id === repo.id
                        ? 'bg-accent-subtle text-accent'
                        : 'hover:bg-surface text-text-primary',
                    )}
                  >
                    <span className="font-medium">{repo.fullName}</span>
                    <span className="ml-2 text-xs text-text-muted capitalize">{repo.visibility}</span>
                  </button>
                ))}
              </div>

              {selectedRepo && (
                <div className="space-y-2">
                  <label className="block text-xs font-medium text-text-secondary">Branch</label>
                  <input
                    type="text"
                    value={branch}
                    onChange={(e) => setBranch(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-border rounded-md focus:outline-none focus:ring-1 focus:ring-accent bg-canvas text-text-primary"
                    placeholder="main"
                  />
                </div>
              )}
            </>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 p-4 border-t border-border">
          <button
            onClick={onClose}
            className="px-3 py-2 text-sm text-text-secondary hover:text-text-primary transition-colors"
          >
            Cancel
          </button>
          {hasConnections && (
            <button
              onClick={() => addMutation.mutate()}
              disabled={!selectedRepo || addMutation.isPending}
              className="px-4 py-2 bg-accent text-white rounded-md text-sm font-medium hover:bg-accent-hover transition-colors disabled:opacity-50"
            >
              {addMutation.isPending ? 'Adding…' : 'Add Repository'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
