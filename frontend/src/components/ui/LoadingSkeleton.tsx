import type { CSSProperties } from 'react'
import { clsx } from 'clsx'

interface SkeletonProps {
  className?: string
  width?: string | number
  height?: string | number
  style?: CSSProperties
}

export function Skeleton({ className, width, height, style }: SkeletonProps) {
  return (
    <div
      className={clsx('skeleton-animate rounded bg-border', className)}
      style={{ width, height, ...style }}
      aria-hidden="true"
    />
  )
}

interface LoadingSkeletonProps {
  rows?: number
  className?: string
}

export function LoadingSkeleton({ rows = 3, className }: LoadingSkeletonProps) {
  return (
    <div className={clsx('space-y-3 p-6', className)} aria-label="Loading" role="status">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-3">
          <Skeleton className="h-8 w-8 rounded-md shrink-0" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3.5" style={{ width: `${60 + (i % 3) * 15}%` }} />
            <Skeleton className="h-3" style={{ width: `${40 + (i % 2) * 20}%` }} />
          </div>
        </div>
      ))}
    </div>
  )
}

export function TableLoadingSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="space-y-0" role="status" aria-label="Loading table">
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div
          key={rowIdx}
          className="flex items-center gap-4 px-4 py-3 border-b border-border-subtle"
        >
          {Array.from({ length: cols }).map((_, colIdx) => (
            <Skeleton
              key={colIdx}
              className="h-3.5"
              style={{ flex: colIdx === 0 ? 2 : 1, width: undefined }}
            />
          ))}
        </div>
      ))}
    </div>
  )
}
