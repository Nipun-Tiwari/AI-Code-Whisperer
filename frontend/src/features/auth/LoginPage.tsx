import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { supabase } from '@/lib/supabase'
import { useAuthStore } from '@/store'
import { clsx } from 'clsx'

export function LoginPage() {
  const { user, isLoading } = useAuthStore()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [mode, setMode] = useState<'signin' | 'signup'>('signin')
  const [submitting, setSubmitting] = useState(false)
  const [githubLoading, setGithubLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  if (!isLoading && user) {
    return <Navigate to="/dashboard" replace />
  }

  async function handleEmailAuth(e: React.FormEvent) {
    e.preventDefault()
    setErrorMessage(null)
    setSuccessMessage(null)
    setSubmitting(true)

    try {
      if (mode === 'signup') {
        const { error, data } = await supabase.auth.signUp({
          email,
          password,
        })
        if (error) throw error
        if (data.session) {
          // Immediately signed in
          return
        }
        setSuccessMessage('Verification link sent! Check your email to confirm.')
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        })
        if (error) throw error
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Authentication failed.'
      setErrorMessage(msg)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleGitHubLogin() {
    setErrorMessage(null)
    setGithubLoading(true)
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'github',
        options: {
          redirectTo: `${window.location.origin}/dashboard`,
        },
      })
      if (error) throw error
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to connect to GitHub.'
      setErrorMessage(msg)
      setGithubLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-canvas flex flex-col justify-center items-center px-4 py-12 select-none">
      <div className="w-full max-w-[380px] space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-surface border border-border shadow-sm mb-1">
            <span className="font-mono text-sm font-semibold tracking-tighter text-text-primary">CW</span>
          </div>
          <h1 className="text-xl font-medium tracking-tight text-text-primary">
            CodeWhisperer
          </h1>
          <p className="text-xs text-text-muted">
            Codebase intelligence & agentic reasoning
          </p>
        </div>

        {/* Card */}
        <div className="bg-surface border border-border rounded-xl p-6 shadow-sm space-y-5">
          {/* GitHub OAuth Button */}
          <button
            type="button"
            onClick={handleGitHubLogin}
            disabled={githubLoading || submitting}
            className={clsx(
              'w-full flex items-center justify-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium',
              'bg-surface-elevated hover:bg-hover border border-border text-text-primary',
              'transition-colors duration-150 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-border',
              (githubLoading || submitting) && 'opacity-60 cursor-not-allowed',
            )}
          >
            <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24" aria-hidden="true">
              <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
            </svg>
            <span>{githubLoading ? 'Connecting...' : 'Continue with GitHub'}</span>
          </button>

          <div className="relative flex items-center justify-center">
            <div className="border-t border-border w-full" />
            <span className="bg-surface px-2 text-[11px] text-text-muted uppercase tracking-wider relative">
              or
            </span>
          </div>

          {/* Error & Success Alerts */}
          {errorMessage && (
            <div className="p-3 text-xs rounded-lg border border-red-500/30 bg-red-500/10 text-red-400">
              {errorMessage}
            </div>
          )}
          {successMessage && (
            <div className="p-3 text-xs rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
              {successMessage}
            </div>
          )}

          {/* Email / Password Form */}
          <form onSubmit={handleEmailAuth} className="space-y-3.5">
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">
                Email
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="developer@example.com"
                className={clsx(
                  'w-full px-3 py-1.5 rounded-lg text-sm bg-canvas border border-border text-text-primary',
                  'placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent',
                  'transition-colors duration-150',
                )}
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">
                Password
              </label>
              <input
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className={clsx(
                  'w-full px-3 py-1.5 rounded-lg text-sm bg-canvas border border-border text-text-primary',
                  'placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent',
                  'transition-colors duration-150',
                )}
              />
            </div>

            <button
              type="submit"
              disabled={submitting || githubLoading}
              className={clsx(
                'w-full py-2 px-3 rounded-lg text-sm font-medium transition-colors duration-150 mt-1',
                'bg-accent text-canvas hover:bg-accent-hover',
                'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-border',
                (submitting || githubLoading) && 'opacity-60 cursor-not-allowed',
              )}
            >
              {submitting
                ? 'Processing...'
                : mode === 'signin'
                  ? 'Sign In'
                  : 'Create Account'}
            </button>
          </form>

          {/* Toggle mode */}
          <div className="text-center text-xs text-text-muted pt-1">
            {mode === 'signin' ? (
              <>
                Don&apos;t have an account?{' '}
                <button
                  type="button"
                  onClick={() => {
                    setMode('signup')
                    setErrorMessage(null)
                    setSuccessMessage(null)
                  }}
                  className="text-text-primary hover:underline font-medium"
                >
                  Create one
                </button>
              </>
            ) : (
              <>
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => {
                    setMode('signin')
                    setErrorMessage(null)
                    setSuccessMessage(null)
                  }}
                  className="text-text-primary hover:underline font-medium"
                >
                  Sign in
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
