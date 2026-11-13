import { ChevronRight, LogOut, Settings, Sun, Moon, Monitor, Menu } from 'lucide-react'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { useLocation, Link } from 'react-router-dom'
import { useAuthStore, useThemeStore, useSidebarStore } from '@/store'
import type { ThemePreference } from '@/store'
import { clsx } from 'clsx'

const ROUTE_LABELS: Record<string, string> = {
  '/dashboard':     'Dashboard',
  '/repositories':  'Repositories',
  '/workspace':     'AI Workspace',
  '/code-explorer': 'Code Explorer',
  '/investigation': 'Investigations',
  '/security':      'Security',
  '/documentation': 'Documentation',
  '/agent-activity':'Agent Activity',
  '/mcp-tools':     'MCP Tools',
  '/usage':         'Usage & Infrastructure',
  '/settings':      'Settings',
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

const THEME_OPTIONS: { value: ThemePreference; label: string; Icon: typeof Sun }[] = [
  { value: 'light',  label: 'Light',  Icon: Sun },
  { value: 'dark',   label: 'Dark',   Icon: Moon },
  { value: 'system', label: 'System', Icon: Monitor },
]

function ThemeToggle() {
  const { preference, setPreference } = useThemeStore()

  const CurrentIcon =
    preference === 'light' ? Sun : preference === 'dark' ? Moon : Monitor

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button
          className={clsx(
            'flex items-center justify-center w-7 h-7 rounded-md',
            'text-text-muted hover:text-text-secondary hover:bg-hover',
            'transition-colors duration-100',
            'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-border',
          )}
          aria-label="Toggle theme"
          title="Theme"
        >
          <CurrentIcon size={14} />
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={6}
          className={clsx(
            'z-50 min-w-[130px] rounded-md bg-surface border border-border shadow-md',
            'py-1 text-sm',
            'data-[state=open]:animate-in data-[state=closed]:animate-out',
            'data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0',
            'data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95',
          )}
        >
          {THEME_OPTIONS.map(({ value, label, Icon }) => (
            <DropdownMenu.Item
              key={value}
              onSelect={() => setPreference(value)}
              className={clsx(
                'flex items-center gap-2.5 px-3 py-1.5 cursor-pointer outline-none transition-colors',
                preference === value
                  ? 'text-text-primary bg-nav-active-bg'
                  : 'text-text-secondary hover:text-text-primary hover:bg-hover',
              )}
            >
              <Icon size={13} />
              <span>{label}</span>
              {preference === value && (
                <span className="ml-auto w-1.5 h-1.5 rounded-full bg-text-primary" />
              )}
            </DropdownMenu.Item>
          ))}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  )
}

export function TopBar() {
  const location = useLocation()
  const { user } = useAuthStore()
  const { setCollapsed } = useSidebarStore()
  const breadcrumbs = getBreadcrumbs(location.pathname)

  const initials = user?.displayName
    ? user.displayName.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)
    : user?.email?.slice(0, 2).toUpperCase() ?? 'CW'

  return (
    <header
      className="shrink-0 flex items-center justify-between px-4 bg-canvas border-b border-border"
      style={{ height: 'var(--header-height)' }}
    >
      {/* Hamburger — mobile only */}
      <button
        className="md:hidden mr-2 p-1.5 rounded text-text-muted hover:text-text-secondary hover:bg-hover transition-colors shrink-0"
        onClick={() => setCollapsed(false)}
        aria-label="Open navigation"
        aria-controls="sidebar"
        title="Open navigation"
      >
        <Menu size={16} aria-hidden="true" />
      </button>

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

      {/* Right side: theme toggle + user menu */}
      <div className="flex items-center gap-1.5 shrink-0">
        <ThemeToggle />

        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <button
              className={clsx(
                'flex items-center justify-center w-7 h-7 rounded-full text-xs font-medium',
                'bg-surface-elevated text-text-secondary border border-border',
                'hover:bg-hover hover:text-text-primary transition-colors duration-100',
                'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-border',
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
                'z-50 min-w-[160px] rounded-md bg-surface border border-border shadow-md',
                'py-1 text-sm',
                'data-[state=open]:animate-in data-[state=closed]:animate-out',
                'data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0',
                'data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95',
              )}
            >
              {user && (
                <div className="px-3 py-2 border-b border-border">
                  <p className="font-medium text-text-primary truncate text-sm">
                    {user.displayName ?? user.email}
                  </p>
                  {user.displayName && (
                    <p className="text-xs text-text-muted truncate">{user.email}</p>
                  )}
                </div>
              )}
              <DropdownMenu.Item asChild>
                <Link
                  to="/settings"
                  className="flex items-center gap-2 px-3 py-1.5 text-text-secondary hover:text-text-primary hover:bg-hover cursor-pointer outline-none transition-colors"
                >
                  <Settings size={13} />
                  Settings
                </Link>
              </DropdownMenu.Item>
              <DropdownMenu.Separator className="h-px bg-border my-1" />
              <DropdownMenu.Item
                className="flex items-center gap-2 px-3 py-1.5 text-danger hover:bg-danger-subtle cursor-pointer outline-none transition-colors"
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
