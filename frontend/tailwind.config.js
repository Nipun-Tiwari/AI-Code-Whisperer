/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  // Theme is controlled via data-theme attribute on <html>, not Tailwind's dark class
  theme: {
    extend: {
      colors: {
        // Surfaces
        canvas:            'var(--color-canvas)',
        surface:           'var(--color-surface)',
        'surface-elevated':'var(--color-surface-elevated)',
        hover:             'var(--color-hover)',

        // Text
        'text-primary':   'var(--color-text-primary)',
        'text-secondary': 'var(--color-text-secondary)',
        'text-muted':     'var(--color-text-muted)',

        // Borders
        border:          'var(--color-border)',
        'border-subtle': 'var(--color-border-subtle)',

        // Navigation active
        'nav-active-bg':   'var(--color-nav-active-bg)',
        'nav-active-text': 'var(--color-nav-active-text)',

        // Accent (neutral)
        accent:         'var(--color-accent)',
        'accent-hover': 'var(--color-accent-hover)',
        'accent-subtle':'var(--color-accent-subtle)',

        // Inputs
        'input-bg': 'var(--color-input-bg)',

        // Status
        success:         'var(--color-success)',
        'success-subtle':'var(--color-success-subtle)',
        warning:         'var(--color-warning)',
        'warning-subtle':'var(--color-warning-subtle)',
        danger:          'var(--color-danger)',
        'danger-subtle': 'var(--color-danger-subtle)',
        info:            'var(--color-info)',
        'info-subtle':   'var(--color-info-subtle)',
      },
      fontFamily: {
        sans: ['Satoshi', 'Arial', 'sans-serif'],
      },
      fontSize: {
        '2xs': '11px',
        xs:    '12px',
        sm:    '13px',
        base:  '14px',
        md:    '15px',
        lg:    '16px',
        xl:    '18px',
        '2xl': '20px',
        '3xl': '24px',
        '4xl': '28px',
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
      },
      height: {
        header: 'var(--header-height)',
      },
      width: {
        sidebar:           'var(--sidebar-width)',
        'sidebar-collapsed':'var(--sidebar-collapsed-width)',
      },
      boxShadow: {
        // Minimal shadows — dark-mode-safe (no white in shadow)
        sm:  '0 1px 2px 0 rgb(0 0 0 / 0.08)',
        md:  '0 1px 4px 0 rgb(0 0 0 / 0.10)',
        lg:  '0 4px 12px 0 rgb(0 0 0 / 0.12)',
        none:'none',
      },
      letterSpacing: {
        tight:  '-0.02em',
        tighter:'-0.03em',
      },
    },
  },
  plugins: [],
}
