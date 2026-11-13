import { Plus, GitBranch, RefreshCw, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { PageHeader, DataTable, StatusBadge, ConfirmationDialog } from '@/components'
import { useRepositories } from '@/hooks'
import { useState } from 'react'
import type { Repository } from '@/types'
import type { ColumnDef } from '@/components'
import { clsx } from 'clsx'

export function RepositoriesPage() {
  const { data, isLoading, error, refetch } = useRepositories()
  const repos = data?.items ?? []
  const [repoToDelete, setRepoToDelete] = useState<Repository | null>(null)

  const columns: ColumnDef<Repository>[] = [
    {
      key: 'name',
      header: 'Repository',
      render: (repo) => (
        <Link
          to={`/repositories/${repo.id}`}
          className="flex items-center gap-2.5 hover:text-accent transition-colors min-w-0"
        >
          <GitBranch size={14} className="shrink-0 text-text-muted" />
          <div className="min-w-0">
            <p className="font-medium text-text-primary truncate">
              {repo.owner}/{repo.name}
            </p>
            {repo.description && (
              <p className="text-xs text-text-muted truncate">{repo.description}</p>
            )}
          </div>
        </Link>
      ),
    },
    {
      key: 'visibility',
      header: 'Visibility',
      width: '100px',
      render: (repo) => (
        <span className="text-xs text-text-secondary capitalize">{repo.visibility}</span>
      ),
    },
    {
      key: 'branch',
      header: 'Branch',
      width: '140px',
      render: (repo) => (
        <span className="font-mono text-xs text-text-secondary">{repo.selectedBranch}</span>
      ),
    },
    {
      key: 'status',
      header: 'Index Status',
      width: '140px',
      render: (repo) => <StatusBadge status={repo.status as never} size="sm" />,
    },
    {
      key: 'lastIndexed',
      header: 'Last Indexed',
      width: '160px',
      render: (repo) =>
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
      width: '80px',
      align: 'right',
      render: (repo) => (
        <div className="flex items-center justify-end gap-1">
          <button
            title="Refresh index"
            className="p-1.5 rounded text-text-muted hover:text-text-primary hover:bg-surface transition-colors"
            onClick={(e) => {
              e.preventDefault()
              // TODO: trigger index job
            }}
          >
            <RefreshCw size={13} />
          </button>
          <button
            title="Remove repository"
            className="p-1.5 rounded text-text-muted hover:text-danger hover:bg-danger-subtle transition-colors"
            onClick={(e) => {
              e.preventDefault()
              setRepoToDelete(repo)
            }}
          >
            <Trash2 size={13} />
          </button>
        </div>
      ),
    },
  ]

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Repositories"
        subtitle="Manage connected repositories and indexing"
        actions={
          <button
            className={clsx(
              'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium',
              'bg-accent text-white hover:bg-accent-hover transition-colors',
            )}
            onClick={() => {
              // TODO: open Add Repository dialog (Phase 1 completion after credentials)
            }}
          >
            <Plus size={14} />
            Add Repository
          </button>
        }
      />

      <div className="flex-1 p-6 overflow-y-auto">
        <DataTable
          columns={columns}
          data={repos}
          keyExtractor={(r) => r.id}
          isLoading={isLoading}
          error={error ? 'Failed to load repositories' : null}
          onRetry={() => refetch()}
          emptyTitle="No repositories connected"
          emptyDescription="Connect a GitHub repository to start indexing and analyzing your code."
          emptyAction={
            <button
              className={clsx(
                'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium',
                'bg-accent text-white hover:bg-accent-hover transition-colors',
              )}
            >
              <Plus size={14} />
              Add Repository
            </button>
          }
        />
      </div>

      <ConfirmationDialog
        open={repoToDelete !== null}
        onOpenChange={(open) => !open && setRepoToDelete(null)}
        title="Remove repository"
        description={
          repoToDelete
            ? `Remove ${repoToDelete.owner}/${repoToDelete.name}? This will delete all indexed data, vectors, summaries and job history associated with this repository.`
            : ''
        }
        confirmLabel="Remove repository"
        variant="danger"
        onConfirm={() => {
          // TODO: call removeRepository(repoToDelete.id)
          setRepoToDelete(null)
        }}
      />
    </div>
  )
}
