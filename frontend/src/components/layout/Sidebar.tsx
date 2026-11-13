import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  GitBranch,
  Bot,
  Code2,
  Search,
  Shield,
  FileText,
  Activity,
  Wrench,
  BarChart3,
  Settings,
  ChevronLeft,
  ChevronRight,
  Zap,
  X,
  type LucideIcon,
} from 'lucide-react'
import { useSidebarStore } from '@/store'
import { clsx } from 'clsx'
import { useEffect } from 'react'

interface NavItem {
  label: string
  to: string
  icon: LucideIcon
}

interface NavSection {
  title: string
  items: NavItem[]
}

const NAV_SECTIONS: NavSection[] = [
  {
    title: 'Workspace',
    items: [
      { label: 'Dashboard',       to: '/dashboard',     icon: LayoutDashboard },
      { label: 'Repositories',    to: '/repositories',  icon: GitBranch },
      { label: 'AI Workspace',    to: '/workspace',     icon: Bot },
      { label: 'Code Explorer',   to: '/code-explorer', icon: Code2 },
    ],
  },
  {
    title: 'Analysis',
    items: [
      { label: 'Investigations',  to: '/investigation', icon: Search },
      { label: 'Security',        to: '/security',      icon: Shield },
      { label: 'Documentation',   to: '/documentation', icon: FileText },
    ],
  },
  {
    title: 'Operations',
    items: [
      { label: 'Agent Activity',           to: '/agent-activity', icon: Activity },
      { label: 'MCP Tools',                to: '/mcp-tools',      icon: Wrench },
      { label: 'Usage & Infrastructure',   to: '/usage',          icon: BarChart3 },
    ],
  },
  {
    title: 'Configuration',
    items: [{ label: 'Settings', to: '/settings', icon: Settings }],
  },
]

export function Sidebar() {
  const { collapsed, toggleCollapsed, setCollapsed } = useSidebarStore()
  const location = useLocation()

  // Auto-collapse on tablet breakpoint (768–1023px)
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 1024 && window.innerWidth >= 768) {
        setCollapsed(true)
      } else if (window.innerWidth >= 1024) {
        // restore to user preference — do nothing, let store state win
      }
    }
    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [setCollapsed])

  // Close drawer on route change (mobile)
  useEffect(() => {
    if (window.innerWidth < 768) {
      setCollapsed(true)
    }
  }, [location.pathname, setCollapsed])

  const isMobileOpen = !collapsed && window.innerWidth < 768

  return (
    <>
      {/* Mobile overlay backdrop */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-20 bg-text-primary/20 md:hidden"
          onClick={() => setCollapsed(true)}
          aria-hidden="true"
        />
      )}

      <aside
        id="sidebar"
        aria-label="Main navigation"
        className={clsx(
          'sidebar-transition flex flex-col bg-surface border-r border-border h-full overflow-hidden shrink-0',
          // Mobile: fixed overlay drawer
          'max-md:fixed max-md:inset-y-0 max-md:left-0 max-md:z-30',
          // Show/hide on mobile
          collapsed && 'max-md:hidden',
          // Width
          collapsed ? 'w-[var(--sidebar-collapsed-width)]' : 'w-[var(--sidebar-width)]',
        )}
      >
        {/* Logo */}
        <div
          className={clsx(
            'flex items-center border-b border-border shrink-0',
            collapsed ? 'justify-center px-0' : 'px-4',
          )}
          style={{ height: 'var(--header-height)' }}
        >
          <div className="flex items-center gap-2 min-w-0 flex-1">
            <div className="shrink-0 w-6 h-6 rounded-md bg-text-primary flex items-center justify-center">
              <Zap size={13} className="text-canvas" aria-hidden="true" />
            </div>
            {!collapsed && (
              <span className="font-medium text-sm tracking-tight text-text-primary truncate">
                CodeWhisperer
              </span>
            )}
          </div>
          {/* Close button on mobile when expanded */}
          {!collapsed && (
            <button
              className="md:hidden p-1 rounded text-text-muted hover:text-text-secondary hover:bg-hover transition-colors shrink-0"
              onClick={() => setCollapsed(true)}
              aria-label="Close navigation"
              title="Close navigation"
            >
              <X size={14} />
            </button>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-3 px-2" aria-label="Site navigation">
          {NAV_SECTIONS.map((section) => (
            <div key={section.title} className="mb-5">
              {!collapsed && (
                <p className="px-2 mb-1.5 text-[11px] font-medium uppercase tracking-widest text-text-muted select-none">
                  {section.title}
                </p>
              )}
              <ul className="space-y-0.5" role="list">
                {section.items.map((item) => {
                  const Icon = item.icon
                  const isActive =
                    item.to === '/dashboard'
                      ? location.pathname === '/' || location.pathname === '/dashboard'
                      : location.pathname.startsWith(item.to)

                  return (
                    <li key={item.to}>
                      <NavLink
                        to={item.to}
                        title={collapsed ? item.label : undefined}
                        aria-label={collapsed ? item.label : undefined}
                        className={clsx(
                          'flex items-center gap-2.5 rounded-md text-sm transition-colors duration-100',
                          collapsed ? 'justify-center px-0 py-2' : 'px-2 py-1.5',
                          isActive
                            ? 'bg-nav-active-bg text-nav-active-text font-medium'
                            : 'text-text-secondary hover:bg-hover hover:text-text-primary',
                        )}
                      >
                        <Icon size={14} className="shrink-0" aria-hidden="true" />
                        {!collapsed && <span className="truncate">{item.label}</span>}
                      </NavLink>
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}
        </nav>

        {/* Collapse toggle — hidden on mobile */}
        <div className="shrink-0 border-t border-border p-2 max-md:hidden">
          <button
            onClick={toggleCollapsed}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className={clsx(
              'flex items-center justify-center w-full rounded-md py-1.5 text-text-muted hover:bg-hover hover:text-text-secondary transition-colors duration-100',
              collapsed ? 'px-0' : 'px-2 gap-2',
            )}
          >
            {collapsed ? <ChevronRight size={14} aria-hidden="true" /> : <ChevronLeft size={14} aria-hidden="true" />}
            {!collapsed && <span className="text-xs">Collapse</span>}
          </button>
        </div>
      </aside>
    </>
  )
}
