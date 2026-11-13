import * as Dialog from '@radix-ui/react-dialog'
import { AlertTriangle, X } from 'lucide-react'
import { clsx } from 'clsx'
import type { ReactNode } from 'react'

interface ConfirmationDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description: string
  confirmLabel?: string
  cancelLabel?: string
  onConfirm: () => void
  isLoading?: boolean
  variant?: 'danger' | 'default'
  children?: ReactNode
}

export function ConfirmationDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  onConfirm,
  isLoading = false,
  variant = 'default',
}: ConfirmationDialogProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/30 z-40 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <Dialog.Content
          className={clsx(
            'fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50',
            'bg-canvas border border-border rounded-lg shadow-lg',
            'w-full max-w-md p-6',
            'data-[state=open]:animate-in data-[state=closed]:animate-out',
            'data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0',
            'data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95',
          )}
        >
          <div className="flex items-start gap-4">
            {variant === 'danger' && (
              <div className="shrink-0 w-10 h-10 rounded-full bg-danger-subtle flex items-center justify-center">
                <AlertTriangle size={18} className="text-danger" />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <Dialog.Title className="text-base font-semibold text-text-primary">
                {title}
              </Dialog.Title>
              <Dialog.Description className="mt-1.5 text-sm text-text-secondary">
                {description}
              </Dialog.Description>
            </div>
          </div>

          <div className="mt-6 flex justify-end gap-2">
            <Dialog.Close asChild>
              <button
                className={clsx(
                  'px-3 py-1.5 rounded-md text-sm font-medium border border-border',
                  'text-text-secondary bg-canvas hover:bg-surface transition-colors',
                )}
                disabled={isLoading}
              >
                {cancelLabel}
              </button>
            </Dialog.Close>
            <button
              onClick={onConfirm}
              disabled={isLoading}
              className={clsx(
                'px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                variant === 'danger'
                  ? 'bg-danger text-white hover:bg-danger/90'
                  : 'bg-accent text-white hover:bg-accent-hover',
              )}
            >
              {isLoading ? 'Please wait...' : confirmLabel}
            </button>
          </div>

          <Dialog.Close asChild>
            <button
              className="absolute right-4 top-4 text-text-muted hover:text-text-primary transition-colors"
              aria-label="Close"
            >
              <X size={16} />
            </button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
