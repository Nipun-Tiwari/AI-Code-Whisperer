import { Settings, Github, User, Trash2 } from 'lucide-react'
import { PageHeader, StatusBadge } from '@/components'
import { useAuthStore } from '@/store'
import { clsx } from 'clsx'

export function SettingsPage() {
  const { user } = useAuthStore()

  return (
    <div className="flex flex-col h-full">
      <PageHeader
        title="Settings"
        subtitle="Manage your profile, integrations and data"
      />

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl mx-auto space-y-6">
          {/* Profile section */}
          <section className="border border-border rounded-lg">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-surface rounded-t-lg">
              <User size={14} className="text-text-secondary" />
              <h2 className="text-sm font-semibold text-text-primary">Profile</h2>
            </div>
            <div className="p-4 space-y-3">
              <InfoRow label="Email" value={user?.email ?? '—'} />
              <InfoRow label="Display name" value={user?.displayName ?? '—'} />
              <InfoRow
                label="Member since"
                value={user?.createdAt ? new Date(user.createdAt).toLocaleDateString() : '—'}
              />
            </div>
          </section>

          {/* GitHub connection section */}
          <section className="border border-border rounded-lg">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-surface rounded-t-lg">
              <Github size={14} className="text-text-secondary" />
              <h2 className="text-sm font-semibold text-text-primary">GitHub Connection</h2>
            </div>
            <div className="p-4 space-y-3">
              {/* TODO: show connected GitHub App installations */}
              <div className="flex items-center gap-3 py-2">
                <div className="flex-1">
                  <p className="text-sm text-text-secondary">No GitHub App installed</p>
                  <p className="text-xs text-text-muted mt-0.5">
                    Connect a GitHub App installation to access your repositories.
                  </p>
                </div>
                <StatusBadge status="not_configured" size="sm" />
              </div>
              <button
                className={clsx(
                  'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium',
                  'border border-border text-text-secondary hover:bg-surface transition-colors',
                )}
                onClick={() => {
                  // TODO: initiate GitHub App installation flow
                  // GET /api/v1/integrations/github/connect
                }}
              >
                <Github size={13} />
                Install GitHub App
              </button>
            </div>
          </section>

          {/* Data management */}
          <section className="border border-border rounded-lg">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-surface rounded-t-lg">
              <Settings size={14} className="text-text-secondary" />
              <h2 className="text-sm font-semibold text-text-primary">Data Management</h2>
            </div>
            <div className="p-4 space-y-3">
              <div>
                <p className="text-sm text-text-primary font-medium">Delete account data</p>
                <p className="text-xs text-text-muted mt-0.5">
                  Removes all indexed repositories, conversations, findings and generated
                  documents. This action cannot be undone.
                </p>
              </div>
              <button
                className={clsx(
                  'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium',
                  'border border-danger/30 text-danger hover:bg-danger-subtle transition-colors',
                  'disabled:opacity-50 disabled:cursor-not-allowed',
                )}
                disabled
                title="Data deletion is available once you have indexed repositories"
              >
                <Trash2 size={13} />
                Delete all data
              </button>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-1 border-b border-border-subtle last:border-0">
      <span className="text-xs text-text-muted">{label}</span>
      <span className="text-sm text-text-primary">{value}</span>
    </div>
  )
}
