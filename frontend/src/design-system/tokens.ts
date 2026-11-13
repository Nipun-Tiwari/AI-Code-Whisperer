// Design tokens — mirrors the CSS custom properties in index.css.
// Use CSS variables in components (Tailwind aliases) rather than these constants
// directly; these exist for reference and non-Tailwind usage.

export const colors = {
  canvas:           'var(--color-canvas)',
  surface:          'var(--color-surface)',
  surfaceElevated:  'var(--color-surface-elevated)',
  hover:            'var(--color-hover)',
  textPrimary:      'var(--color-text-primary)',
  textSecondary:    'var(--color-text-secondary)',
  textMuted:        'var(--color-text-muted)',
  border:           'var(--color-border)',
  borderSubtle:     'var(--color-border-subtle)',
  navActiveBg:      'var(--color-nav-active-bg)',
  navActiveText:    'var(--color-nav-active-text)',
  accent:           'var(--color-accent)',
  accentHover:      'var(--color-accent-hover)',
  accentSubtle:     'var(--color-accent-subtle)',
  inputBg:          'var(--color-input-bg)',
  success:          'var(--color-success)',
  successSubtle:    'var(--color-success-subtle)',
  warning:          'var(--color-warning)',
  warningSubtle:    'var(--color-warning-subtle)',
  danger:           'var(--color-danger)',
  dangerSubtle:     'var(--color-danger-subtle)',
  info:             'var(--color-info)',
  infoSubtle:       'var(--color-info-subtle)',
} as const

export const typography = {
  fontSans: 'var(--font-sans)',
  sizes: {
    '2xs': '11px',
    xs:    '12px',
    sm:    '13px',
    base:  '14px',
    md:    '15px',
    lg:    '16px',
    xl:    '18px',
    '2xl': '20px',
    '3xl': '24px',   // metric
    '4xl': '28px',   // page heading
  },
  weights: {
    normal:  '400',
    medium:  '500',
    semibold:'600',
    bold:    '700',
  },
  letterSpacing: {
    tight:  '-0.02em',
    tighter:'-0.03em',
    normal: '0em',
  },
  lineHeights: {
    tight:   '1.2',
    normal:  '1.5',
    relaxed: '1.75',
  },
} as const

export const spacing = {
  0:   '0px',
  0.5: '2px',
  1:   '4px',
  1.5: '6px',
  2:   '8px',
  2.5: '10px',
  3:   '12px',
  3.5: '14px',
  4:   '16px',
  5:   '20px',
  6:   '24px',
  7:   '28px',
  8:   '32px',
  10:  '40px',
  12:  '48px',
  16:  '64px',
  20:  '80px',
} as const

export const radius = {
  sm: 'var(--radius-sm)',  // 4px
  md: 'var(--radius-md)',  // 6px
  lg: 'var(--radius-lg)',  // 8px
} as const

export const layout = {
  sidebarWidth:          'var(--sidebar-width)',           // 224px
  sidebarCollapsedWidth: 'var(--sidebar-collapsed-width)', // 48px
  headerHeight:          'var(--header-height)',           // 56px
} as const

export const shadows = {
  sm:  '0 1px 2px 0 rgb(0 0 0 / 0.08)',
  md:  '0 1px 4px 0 rgb(0 0 0 / 0.10)',
  lg:  '0 4px 12px 0 rgb(0 0 0 / 0.12)',
  none:'none',
} as const
