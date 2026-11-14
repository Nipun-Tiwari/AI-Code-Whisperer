import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@/components/theme/ThemeProvider'
import { AppShell } from '@/components/layout/AppShell'
import { ToastContainer } from '@/components/ui/Toast'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { LoginPage } from '@/features/auth/LoginPage'
import { DashboardPage } from '@/features/dashboard/DashboardPage'
import RepositoriesPage from '@/features/repositories/RepositoriesPage'
import RepositoryDetailPage from '@/features/repositories/RepositoryDetailPage'
import WorkspacePage from '@/features/workspace/WorkspacePage'
import CodeExplorerPage from '@/features/code-explorer/CodeExplorerPage'
import InvestigationPage from '@/features/investigation/InvestigationPage'
import SecurityPage from '@/features/security/SecurityPage'
import DocumentationPage from '@/features/documentation/DocumentationPage'
import AgentActivityPage from '@/features/agent-activity/AgentActivityPage'
import McpToolsPage from '@/features/mcp-tools/McpToolsPage'
import { UsagePage } from '@/features/usage/UsagePage'
import { SettingsPage } from '@/features/settings/SettingsPage'
import { supabase } from '@/lib/supabase'
import { useAuthStore } from '@/store'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
})

export function App() {
  const { setUser, setLoading } = useAuthStore()

  useEffect(() => {
    // 1. Check existing session on load
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) {
        setUser({
          id: session.user.id,
          email: session.user.email ?? '',
          displayName: session.user.user_metadata?.full_name ?? session.user.user_metadata?.user_name ?? null,
          createdAt: session.user.created_at,
        })
      } else {
        setUser(null)
      }
      setLoading(false)
    })

    // 2. Listen for auth changes (sign in, sign out, OAuth callback)
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        setUser({
          id: session.user.id,
          email: session.user.email ?? '',
          displayName: session.user.user_metadata?.full_name ?? session.user.user_metadata?.user_name ?? null,
          createdAt: session.user.created_at,
        })
      } else {
        setUser(null)
      }
      setLoading(false)
    })

    return () => {
      subscription.unsubscribe()
    }
  }, [setUser, setLoading])

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <BrowserRouter>
          <Routes>
            {/* Public route */}
            <Route path="/login" element={<LoginPage />} />

            {/* Protected routes wrapped in ProtectedRoute and AppShell */}
            <Route element={<ProtectedRoute />}>
              <Route element={<AppShell />}>
                <Route index element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/repositories" element={<RepositoriesPage />} />
                <Route path="/repositories/:id" element={<RepositoryDetailPage />} />
                <Route path="/workspace" element={<WorkspacePage />} />
                <Route path="/code-explorer" element={<CodeExplorerPage />} />
                <Route path="/investigation" element={<InvestigationPage />} />
                <Route path="/security" element={<SecurityPage />} />
                <Route path="/documentation" element={<DocumentationPage />} />
                <Route path="/agent-activity" element={<AgentActivityPage />} />
                <Route path="/mcp-tools" element={<McpToolsPage />} />
                <Route path="/usage" element={<UsagePage />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Route>
            </Route>

            {/* Catch-all: redirect to dashboard (which redirects to login if unauthenticated) */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>

          {/* Global toast notifications */}
          <ToastContainer />
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
