import { forwardRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { clsx } from 'clsx'

type MarkdownViewProps = {
  children: string
  className?: string
  id?: string
}

const proseClasses = clsx(
  'prose prose-sm max-w-none',
  'prose-headings:text-text-primary prose-headings:font-semibold',
  'prose-h1:text-base prose-h2:text-sm prose-h3:text-sm',
  'prose-p:text-sm prose-p:text-text-secondary',
  'prose-li:text-sm prose-li:text-text-secondary',
  'prose-strong:text-text-primary',
  'prose-a:text-accent prose-a:no-underline hover:prose-a:underline',
  'prose-code:text-xs prose-code:before:content-none prose-code:after:content-none',
  'prose-code:bg-surface-elevated prose-code:px-1 prose-code:py-0.5 prose-code:rounded',
  'prose-pre:text-xs prose-pre:bg-surface-elevated prose-pre:p-3 prose-pre:rounded',
  'prose-blockquote:border-border prose-blockquote:text-text-secondary',
  'prose-hr:border-border',
  'prose-th:text-text-primary prose-td:text-text-secondary',
  'prose-table:text-sm',
)

/**
 * Renders Markdown as styled HTML. Does not enable raw HTML plugins.
 */
export const MarkdownView = forwardRef<HTMLDivElement, MarkdownViewProps>(
  function MarkdownView({ children, className, id }, ref) {
    return (
      <div ref={ref} id={id} className={clsx(proseClasses, className)}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
      </div>
    )
  },
)
