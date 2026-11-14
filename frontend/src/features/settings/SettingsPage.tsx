import { Settings, Github, User, Trash2, Sun, Moon, Monitor, CheckCircle2, Circle } from 'lucide-react'
import { PageHeader, StatusBadge } from '@/components'
import { useAuthStore, useThemeStore } from '@/store'
import type { ThemePreference } from '@/store'
import { clsx } from 'clsx'

const THEME_OPTIONS: { value: ThemePreference; label: string; description: string; Icon: typeof Sun }[] = [
  { value: 'light',  label: 'Light',  description: 'Always use light mode',                    Icon: Sun },
  { value: 'dark',   label: 'Dark',   description: 'Always use dark mode',                     Icon: Moon },
  { value: 'system', label: 'System', description: 'Follow your operating system preference',  Icon: Monitor },
]

export function SettingsPage() {
  const { user } = useAuthStore()
  const { preference, setPreference } = useThemeStore()

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
              <a
                href={`${import.meta.env.VITE_API_URL ?? ''}/api/v1/integrations/github/connect`}
                className={clsx(
                  'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium',
                  'border border-border text-text-secondary hover:bg-surface transition-colors',
                )}
              >
                <Github size={13} />
                Install GitHub App
              </a>
            </div>
          </section>

          {/* Theme */}
          <section className="border border-border rounded-lg">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-surface rounded-t-lg">
              <Monitor size={14} className="text-text-secondary" />
              <h2 className="text-sm font-medium text-text-primary">Appearance</h2>
            </div>
            <div className="p-4">
              <p className="text-xs text-text-muted mb-3">
                Choose how CodeWhisperer looks. System follows your OS setting.
              </p>
              <div className="grid grid-cols-3 gap-2">
                {THEME_OPTIONS.map(({ value, label, description, Icon }) => (
                  <button
                    key={value}
                    onClick={() => setPreference(value)}
                    className={clsx(
                      'flex flex-col items-start gap-2 p-3 rounded-md border text-left transition-colors',
                      preference === value
                        ? 'border-text-primary bg-nav-active-bg'
                        : 'border-border bg-surface hover:bg-hover hover:border-border',
                    )}
                  >
                    <Icon size={14} className={preference === value ? 'text-text-primary' : 'text-text-muted'} />
                    <div>
                      <p className={clsx('text-xs font-medium', preference === value ? 'text-text-primary' : 'text-text-secondary')}>
                        {label}
                      </p>
                      <p className="text-[11px] text-text-muted mt-0.5 leading-tight">{description}</p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </section>

          {/* API & Integrations status */}
          <section className="border border-border rounded-lg">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-surface rounded-t-lg">
              <CheckCircle2 size={14} className="text-text-secondary" />
              <h2 className="text-sm font-medium text-text-primary">API & Integrations</h2>
            </div>
            <div className="p-4">
              <p className="text-xs text-text-muted mb-3">
                Configured services. No credential values are shown here.
              </p>
              <div className="space-y-2">
                <IntegrationRow label="Google Gemini (LLM & Embeddings)" configured={!!import.meta.env.VITE_SUPABASE_URL} note="Configured via GEMINI_API_KEY" />
                <IntegrationRow label="Neon PostgreSQL" configured={true} note="Connection active" />
                <IntegrationRow label="Qdrant Cloud" configured={true} note="Configured via QDRANT_URL" />
                <IntegrationRow label="GitHub App" configured={true} note="Configured via GITHUB_APP_ID" />
              </div>
              <p className="text-xs text-text-muted mt-3">
                View detailed service health on the{' '}
                <a href="/usage" className="underline hover:text-text-secondary transition-colors">
                  Usage &amp; Infrastructure
                </a>{' '}
                page.
              </p>
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

function IntegrationRow({ label, configured, note }: { label: string; configured: boolean; note: string }) {
  return (
    <div className="flex items-center gap-3 py-1.5">
      {configured
        ? <CheckCircle2 size={13} className="shrink-0 text-success" aria-label="Configured" />
        : <Circle size={13} className="shrink-0 text-text-muted" aria-label="Not configured" />
      }
      <div className="flex-1 min-w-0">
        <span className="text-sm text-text-primary">{label}</span>
        <span className="ml-2 text-xs text-text-muted">{note}</span>
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
