import { Component, type ErrorInfo, type ReactNode } from 'react'

type Props = {
  children: ReactNode
  fallbackTitle?: string
}

type State = {
  hasError: boolean
  message: string
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: '' }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      message: error.message || 'Something went wrong while rendering this page.',
    }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('UI ErrorBoundary caught render error', error, info.componentStack)
  }

  private handleRetry = () => {
    this.setState({ hasError: false, message: '' })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-6 max-w-xl mx-auto space-y-3">
          <h2 className="text-base font-medium text-text-primary">
            {this.props.fallbackTitle ?? 'This page crashed'}
          </h2>
          <p className="text-sm text-text-secondary">
            A rendering error occurred. You can retry without leaving the app.
          </p>
          <p className="text-xs font-mono text-danger break-all">{this.state.message}</p>
          <button
            type="button"
            onClick={this.handleRetry}
            className="px-3 py-1.5 text-sm rounded-md border border-border text-text-secondary hover:bg-hover transition-colors"
          >
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
