import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store'

export function ProtectedRoute() {
  const { user, isLoading } = useAuthStore()

  if (isLoading) {
    return (
      <div className="min-h-screen bg-canvas flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-6 h-6 border-2 border-border border-t-text-primary rounded-full animate-spin" />
          <span className="text-xs text-text-muted">Loading CodeWhisperer...</span>
        </div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
