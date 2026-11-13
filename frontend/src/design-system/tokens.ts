export const colors = {
  canvas: 'var(--color-canvas)',
  surface: 'var(--color-surface)',
  surfaceElevated: 'var(--color-surface-elevated)',
  textPrimary: 'var(--color-text-primary)',
  textSecondary: 'var(--color-text-secondary)',
  textMuted: 'var(--color-text-muted)',
  border: 'var(--color-border)',
  borderSubtle: 'var(--color-border-subtle)',
  accent: 'var(--color-accent)',
  accentHover: 'var(--color-accent-hover)',
  accentSubtle: 'var(--color-accent-subtle)',
  success: 'var(--color-success)',
  successSubtle: 'var(--color-success-subtle)',
  warning: 'var(--color-warning)',
  warningSubtle: 'var(--color-warning-subtle)',
  danger: 'var(--color-danger)',
  dangerSubtle: 'var(--color-danger-subtle)',
  info: 'var(--color-info)',
  infoSubtle: 'var(--color-info-subtle)',
} as const

export const typography = {
  fontSans: 'var(--font-sans)',
  sizes: {
    xs: '11px',
    sm: '12px',
    base: '14px',
    md: '15px',
    lg: '16px',
    xl: '18px',
    '2xl': '20px',
    '3xl': '24px',
  },
  weights: {
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },
  lineHeights: {
    tight: '1.25',
    normal: '1.5',
    relaxed: '1.75',
  },
} as const

export const spacing = {
  0: '0px',
  0.5: '2px',
  1: '4px',
  1.5: '6px',
  2: '8px',
  2.5: '10px',
  3: '12px',
  3.5: '14px',
  4: '16px',
  5: '20px',
  6: '24px',
  7: '28px',
  8: '32px',
  10: '40px',
  12: '48px',
  16: '64px',
  20: '80px',
} as const

export const radius = {
  sm: 'var(--radius-sm)',
  md: 'var(--radius-md)',
  lg: 'var(--radius-lg)',
} as const

export const layout = {
  sidebarWidth: 'var(--sidebar-width)',
  sidebarCollapsedWidth: 'var(--sidebar-collapsed-width)',
  headerHeight: 'var(--header-height)',
} as const

export const shadows = {
  sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  md: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
  lg: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
} as const
