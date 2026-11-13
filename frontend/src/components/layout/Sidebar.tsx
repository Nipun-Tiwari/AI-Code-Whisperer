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
  type LucideIcon,
} from 'lucide-react'
import { useSidebarStore } from '@/store'
import { clsx } from 'clsx'

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
      { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
      { label: 'Repositories', to: '/repositories', icon: GitBranch },
      { label: 'AI Workspace', to: '/workspace', icon: Bot },
      { label: 'Code Explorer', to: '/code-explorer', icon: Code2 },
    ],
  },
  {
    title: 'Analysis',
    items: [
      { label: 'Investigations', to: '/investigation', icon: Search },
      { label: 'Security', to: '/security', icon: Shield },
      { label: 'Documentation', to: '/documentation', icon: FileText },
    ],
  },
  {
    title: 'Operations',
    items: [
      { label: 'Agent Activity', to: '/agent-activity', icon: Activity },
      { label: 'MCP Tools', to: '/mcp-tools', icon: Wrench },
      { label: 'Usage & Infrastructure', to: '/usage', icon: BarChart3 },
    ],
  },
  {
    title: 'Configuration',
    items: [{ label: 'Settings', to: '/settings', icon: Settings }],
  },
]

export function Sidebar() {
  const { collapsed, toggleCollapsed } = useSidebarStore()
  const location = useLocation()

  return (
    <aside
      className={clsx(
        'sidebar-transition flex flex-col bg-surface border-r border-border h-full overflow-hidden shrink-0',
        collapsed ? 'w-[var(--sidebar-collapsed-width)]' : 'w-[var(--sidebar-width)]',
      )}
    >
      {/* Logo */}
      <div
        className={clsx(
          'flex items-center border-b border-border shrink-0',
          collapsed ? 'justify-center px-0 h-[var(--header-height)]' : 'px-4 h-[var(--header-height)]',
        )}
      >
        <div className="flex items-center gap-2 min-w-0">
          <div className="shrink-0 w-7 h-7 rounded-md bg-accent flex items-center justify-center">
            <Zap size={14} className="text-white" />
          </div>
          {!collapsed && (
            <span className="font-semibold text-text-primary text-sm tracking-tight truncate">
              CodeWhisperer
            </span>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3 px-2">
        {NAV_SECTIONS.map((section) => (
          <div key={section.title} className="mb-4">
            {!collapsed && (
              <p className="px-2 mb-1 text-[11px] font-semibold uppercase tracking-widest text-text-muted select-none">
                {section.title}
              </p>
            )}
            <ul className="space-y-0.5">
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
                      className={clsx(
                        'flex items-center gap-2.5 rounded-md text-sm transition-colors duration-100',
                        collapsed ? 'justify-center px-0 py-2' : 'px-2 py-1.5',
                        isActive
                          ? 'bg-accent-subtle text-accent font-medium'
                          : 'text-text-secondary hover:bg-border-subtle hover:text-text-primary',
                      )}
                    >
                      <Icon size={15} className="shrink-0" />
                      {!collapsed && <span className="truncate">{item.label}</span>}
                    </NavLink>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Collapse toggle */}
      <div className="shrink-0 border-t border-border p-2">
        <button
          onClick={toggleCollapsed}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className={clsx(
            'flex items-center justify-center w-full rounded-md py-1.5 text-text-secondary hover:bg-border-subtle hover:text-text-primary transition-colors duration-100',
            collapsed ? 'px-0' : 'px-2 gap-2',
          )}
        >
          {collapsed ? <ChevronRight size={15} /> : <ChevronLeft size={15} />}
          {!collapsed && <span className="text-sm">Collapse</span>}
        </button>
      </div>
    </aside>
  )
}
