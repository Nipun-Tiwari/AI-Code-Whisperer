import { X, CheckCircle, AlertTriangle, XCircle, Info } from 'lucide-react'
import { useNotificationStore, type Notification } from '@/store'
import { clsx } from 'clsx'

const ICON_MAP = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
} as const

const STYLE_MAP = {
  success: 'border-success/30 bg-success-subtle text-success',
  error: 'border-danger/30 bg-danger-subtle text-danger',
  warning: 'border-warning/30 bg-warning-subtle text-warning',
  info: 'border-info/30 bg-info-subtle text-info',
} as const

function ToastItem({ notification }: { notification: Notification }) {
  const { dismissNotification } = useNotificationStore()
  const Icon = ICON_MAP[notification.type]

  return (
    <div
      className={clsx(
        'flex items-start gap-3 p-3 rounded-lg border shadow-md w-80',
        STYLE_MAP[notification.type],
      )}
      role="alert"
    >
      <Icon size={16} className="shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium leading-tight">{notification.title}</p>
        {notification.message && (
          <p className="mt-0.5 text-xs opacity-80">{notification.message}</p>
        )}
      </div>
      <button
        onClick={() => dismissNotification(notification.id)}
        className="shrink-0 opacity-60 hover:opacity-100 transition-opacity"
        aria-label="Dismiss notification"
      >
        <X size={14} />
      </button>
    </div>
  )
}

export function ToastContainer() {
  const { notifications } = useNotificationStore()

  if (notifications.length === 0) return null

  return (
    <div
      className="fixed bottom-5 right-5 z-50 flex flex-col gap-2"
      aria-live="polite"
      aria-label="Notifications"
    >
      {notifications.map((n) => (
        <ToastItem key={n.id} notification={n} />
      ))}
    </div>
  )
}
