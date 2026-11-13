import { ChevronRight, LogOut, Settings } from 'lucide-react'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { useLocation, Link } from 'react-router-dom'
import { useAuthStore } from '@/store'
import { clsx } from 'clsx'

const ROUTE_LABELS: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/repositories': 'Repositories',
  '/workspace': 'AI Workspace',
  '/code-explorer': 'Code Explorer',
  '/investigation': 'Investigations',
  '/security': 'Security',
  '/documentation': 'Documentation',
  '/agent-activity': 'Agent Activity',
  '/mcp-tools': 'MCP Tools',
  '/usage': 'Usage & Infrastructure',
  '/settings': 'Settings',
}

function getBreadcrumbs(pathname: string): Array<{ label: string; to: string }> {
  const segments = pathname.split('/').filter(Boolean)
  const crumbs: Array<{ label: string; to: string }> = []
  let path = ''
  for (const segment of segments) {
    path += `/${segment}`
    const label = ROUTE_LABELS[path]
    if (label) crumbs.push({ label, to: path })
    else crumbs.push({ label: segment, to: path })
  }
  return crumbs
}

export function TopBar() {
  const location = useLocation()
  const { user } = useAuthStore()
  const breadcrumbs = getBreadcrumbs(location.pathname)

  const initials = user?.displayName
    ? user.displayName
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : user?.email?.slice(0, 2).toUpperCase() ?? 'CW'

  return (
    <header
      className="shrink-0 flex items-center justify-between px-4 bg-canvas border-b border-border"
      style={{ height: 'var(--header-height)' }}
    >
      {/* Breadcrumb */}
      <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-sm min-w-0">
        {breadcrumbs.length === 0 ? (
          <span className="font-medium text-text-primary">Dashboard</span>
        ) : (
          breadcrumbs.map((crumb, i) => (
            <span key={crumb.to} className="flex items-center gap-1 min-w-0">
              {i > 0 && <ChevronRight size={12} className="text-text-muted shrink-0" />}
              {i === breadcrumbs.length - 1 ? (
                <span className="font-medium text-text-primary truncate">{crumb.label}</span>
              ) : (
                <Link
                  to={crumb.to}
                  className="text-text-secondary hover:text-text-primary transition-colors truncate"
                >
                  {crumb.label}
                </Link>
              )}
            </span>
          ))
        )}
      </nav>

      {/* Right side: user menu */}
      <div className="flex items-center gap-2 shrink-0">
        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <button
              className={clsx(
                'flex items-center justify-center w-7 h-7 rounded-full text-xs font-semibold',
                'bg-accent-subtle text-accent border border-accent/20',
                'hover:bg-accent hover:text-white transition-colors duration-100',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-1',
              )}
              aria-label="User menu"
            >
              {initials}
            </button>
          </DropdownMenu.Trigger>
          <DropdownMenu.Portal>
            <DropdownMenu.Content
              align="end"
              sideOffset={6}
              className={clsx(
                'z-50 min-w-[160px] rounded-md bg-canvas border border-border shadow-md',
                'py-1 text-sm',
                'data-[state=open]:animate-in data-[state=closed]:animate-out',
                'data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0',
                'data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95',
              )}
            >
              {user && (
                <>
                  <div className="px-3 py-2 border-b border-border">
                    <p className="font-medium text-text-primary truncate">
                      {user.displayName ?? user.email}
                    </p>
                    {user.displayName && (
                      <p className="text-xs text-text-muted truncate">{user.email}</p>
                    )}
                  </div>
                </>
              )}
              <DropdownMenu.Item asChild>
                <Link
                  to="/settings"
                  className="flex items-center gap-2 px-3 py-1.5 text-text-secondary hover:text-text-primary hover:bg-surface cursor-pointer outline-none"
                >
                  <Settings size={13} />
                  Settings
                </Link>
              </DropdownMenu.Item>
              <DropdownMenu.Separator className="h-px bg-border my-1" />
              <DropdownMenu.Item
                className="flex items-center gap-2 px-3 py-1.5 text-danger hover:bg-danger-subtle cursor-pointer outline-none"
                onSelect={() => {
                  // TODO: implement sign-out via Supabase client
                }}
              >
                <LogOut size={13} />
                Sign out
              </DropdownMenu.Item>
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root>
      </div>
    </header>
  )
}

