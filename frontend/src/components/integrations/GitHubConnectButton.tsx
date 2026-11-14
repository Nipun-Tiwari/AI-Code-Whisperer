import type { ReactNode } from 'react'
import { useMutation } from '@tanstack/react-query'
import { startGitHubConnection } from '@/api/repositories'

export function GitHubConnectButton({
  children,
  className,
}: {
  children: ReactNode
  className: string
}) {
  const mutation = useMutation({
    mutationFn: startGitHubConnection,
    onSuccess: (installUrl) => window.location.assign(installUrl),
  })

  return (
    <div>
      <button
        type="button"
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        className={`${className} disabled:opacity-50`}
      >
        {mutation.isPending ? 'Preparing GitHub connection…' : children}
      </button>
      {mutation.error && (
        <p className="mt-2 text-xs text-danger" role="alert">
          {mutation.error.message || 'Unable to start the GitHub connection. Please try again.'}
        </p>
      )}
    </div>
  )
}
