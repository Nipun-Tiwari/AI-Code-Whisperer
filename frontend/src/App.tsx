import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppShell } from '@/components/layout/AppShell'
import { ToastContainer } from '@/components/ui/Toast'
import { DashboardPage } from '@/features/dashboard/DashboardPage'
import { RepositoriesPage } from '@/features/repositories/RepositoriesPage'
import { RepositoryDetailPage } from '@/features/repositories/RepositoryDetailPage'
import { WorkspacePage } from '@/features/workspace/WorkspacePage'
import { CodeExplorerPage } from '@/features/code-explorer/CodeExplorerPage'
import { InvestigationPage } from '@/features/investigation/InvestigationPage'
import { SecurityPage } from '@/features/security/SecurityPage'
import { DocumentationPage } from '@/features/documentation/DocumentationPage'
import { AgentActivityPage } from '@/features/agent-activity/AgentActivityPage'
import { McpToolsPage } from '@/features/mcp-tools/McpToolsPage'
import { UsagePage } from '@/features/usage/UsagePage'
import { SettingsPage } from '@/features/settings/SettingsPage'

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
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* All authenticated routes share the AppShell layout */}
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

          {/* Catch-all: redirect to dashboard */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>

        {/* Global toast notifications */}
        <ToastContainer />
      </BrowserRouter>
    </QueryClientProvider>
  )
}
