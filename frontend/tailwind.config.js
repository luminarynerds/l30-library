/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import typography from "@tailwindcss/typography";
import scrollbar from "tailwind-scrollbar";
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      // Text-only override: rose family text utilities use the lifted
      // `--accent-rose-text-rgb` variable (set by BrandingContext in dark
      // mode), while bg/border/ring/etc. continue to use the unlifted
      // `--accent-rose-rgb`. This split keeps `text-lsc-rose` on dark
      // surfaces legible without crushing white-text-on-bg contrast for
      // `bg-lsc-rose` callouts. See PR #677 regression notes.
      textColor: {
        'lsc-rose': 'rgb(var(--accent-rose-text-rgb) / <alpha-value>)',
        'lsc-rose-light': 'rgb(var(--accent-rose-light-text-rgb) / <alpha-value>)',
        'lsc-primary': 'rgb(var(--accent-rose-text-rgb) / <alpha-value>)',
        'lsc-accent': 'rgb(var(--accent-rose-text-rgb) / <alpha-value>)',
        'brand-accent': 'rgb(var(--accent-rose-text-rgb) / <alpha-value>)',
        'brand-accent-light': 'rgb(var(--accent-rose-light-text-rgb) / <alpha-value>)',
        brand: {
          DEFAULT: 'rgb(var(--accent-rose-text-rgb) / <alpha-value>)',
          500: 'rgb(var(--accent-rose-text-rgb) / <alpha-value>)',
        },
      },
      colors: {
        // L30 — Nordic Cultural Institution palette
        // Deep plum base with dusty rose accent
        'lsc-cream': 'rgb(var(--brand-surface-rgb, 240 236 240) / <alpha-value>)',   // Warm white (light mode base / dark text)
        'lsc-dark': 'rgb(var(--brand-secondary-rgb, 30 26 36) / <alpha-value>)',     // Deep plum (dark base)
        'lsc-brown': 'rgb(42 37 48 / <alpha-value>)',    // Surface plum
        'lsc-rose': 'rgb(var(--accent-rose-rgb) / <alpha-value>)',         // Dusty rose brand accent (WCAG AA)
        'lsc-rose-light': 'rgb(var(--accent-rose-light-rgb) / <alpha-value>)', // Lighter dusty rose (WCAG AA)
        'lsc-rose-dark': '#5C2E2E',                                        // Darkened rose hover/fill state (WCAG AA, ~11:1 with white text)
        'lsc-white': 'rgb(var(--card-white-rgb, 255 255 255) / <alpha-value>)',     // Card surface (theme-aware)
        'lsc-border': 'rgb(var(--border-light-rgb, 224 220 228) / <alpha-value>)', // Subtle border (theme-aware)
        'lsc-header': 'rgb(var(--brand-secondary-rgb, 30 26 36) / <alpha-value>)',       // Deep plum heading text (#1E1A24)
        'lsc-blue': '#4A6E66',                             // Sage-teal (links, icons)
        'lsc-blue-light': '#7BA098',                       // Lighter sage for dark mode
        'lsc-green': '#7BA098',                            // Sage green (success states, buttons)
        'lsc-gold': '#B8860B',                             // Dark goldenrod (staff message board)
        'lsc-primary': 'rgb(var(--accent-rose-rgb) / <alpha-value>)', // Theme-aware primary action
        'lsc-accent': 'rgb(var(--accent-rose-rgb) / <alpha-value>)',  // Theme-aware accent
        'lsc-600': 'rgb(var(--accent-600-rgb) / <alpha-value>)',       // Mid-dark rose
        'lsc-cream0': 'rgb(240 236 240 / 0)',              // Transparent cream (ring-lsc-cream0)
        'lsc-foundation-green': '#7BA098',  // Muted sage
        // Platform-neutral aliases (new code should use these)
        'brand-cream': 'rgb(var(--brand-surface-rgb, 240 236 240) / <alpha-value>)',
        'brand-dark': 'rgb(var(--brand-secondary-rgb, 30 26 36) / <alpha-value>)',
        'brand-surface': 'rgb(42 37 48 / <alpha-value>)',
        'brand-accent': 'rgb(var(--accent-rose-rgb) / <alpha-value>)',
        'brand-accent-light': 'rgb(var(--accent-rose-light-rgb) / <alpha-value>)',
        'brand-white': 'rgb(var(--card-white-rgb, 255 255 255) / <alpha-value>)',
        'brand-border': 'rgb(var(--border-light-rgb, 224 220 228) / <alpha-value>)',
        'brand-green': '#7BA098',
        // Semantic status colors (use instead of raw red/green/amber/blue/purple/orange/yellow)
        "status-success": {
          50: "#f0fdf4", 100: "#dcfce7", 200: "#bbf7d0", 300: "#86efac",
          400: "#4ade80", 500: "#22c55e", 600: "#15803d", 700: "#166534",
          800: "#14532d", 900: "#0d3b1f",
        },
        "status-danger": {
          50: "#fef2f2", 100: "#fee2e2", 200: "#fecaca", 300: "#fca5a5",
          400: "#f87171", 500: "#ef4444", 600: "#dc2626", 700: "#b91c1c",
          800: "#991b1b", 900: "#7f1d1d",
        },
        "status-warning": {
          50: "#fffbeb", 100: "#fef3c7", 200: "#fde68a", 300: "#fcd34d",
          400: "#fbbf24", 500: "#f59e0b", 600: "#d97706", 700: "#b45309",
          800: "#92400e", 900: "#78350f",
        },
        "status-info": {
          50: "#eff6ff", 100: "#dbeafe", 200: "#bfdbfe", 300: "#93c5fd",
          400: "#60a5fa", 500: "#3b82f6", 600: "#2563eb", 700: "#1d4ed8",
          800: "#1e40af", 900: "#1e3a5f",
        },
        category: {
          50: "#faf5ff", 100: "#f3e8ff", 200: "#e9d5ff", 300: "#d8b4fe",
          400: "#c084fc", 500: "#a855f7", 600: "#9333ea", 700: "#7e22ce",
          800: "#6b21a8", 900: "#581c87", 950: "#3b0764",
        },
        brand: {
          DEFAULT: 'rgb(var(--accent-rose-rgb) / <alpha-value>)',
          50: 'rgb(var(--accent-50-rgb) / <alpha-value>)',
          200: 'rgb(var(--accent-200-rgb) / <alpha-value>)',
          300: 'rgb(var(--accent-300-rgb) / <alpha-value>)',
          400: 'rgb(var(--accent-400-rgb) / <alpha-value>)',
          500: 'rgb(var(--accent-rose-rgb) / <alpha-value>)',
          600: 'rgb(var(--accent-600-rgb) / <alpha-value>)',
          700: 'rgb(var(--accent-700-rgb) / <alpha-value>)',
          800: 'rgb(var(--accent-800-rgb) / <alpha-value>)',
          900: 'rgb(var(--accent-900-rgb) / <alpha-value>)',
        },
        library: {
          50: 'rgb(var(--accent-50-rgb) / <alpha-value>)',
          100: 'rgb(var(--accent-100-rgb) / <alpha-value>)',
          200: 'rgb(var(--accent-200-rgb) / <alpha-value>)',
          300: 'rgb(var(--accent-300-rgb) / <alpha-value>)',
          400: 'rgb(var(--accent-400-rgb) / <alpha-value>)',
          500: 'rgb(var(--accent-500-rgb) / <alpha-value>)',
          600: 'rgb(var(--accent-600-rgb) / <alpha-value>)',
          700: 'rgb(var(--accent-700-rgb) / <alpha-value>)',
          800: 'rgb(var(--accent-800-rgb) / <alpha-value>)',
          900: 'rgb(var(--accent-900-rgb) / <alpha-value>)',
        },
        sage: {
          DEFAULT: 'rgb(var(--accent-400-rgb) / <alpha-value>)',
          50: 'rgb(var(--accent-50-rgb) / <alpha-value>)',
          100: 'rgb(var(--accent-100-rgb) / <alpha-value>)',
          200: 'rgb(var(--accent-200-rgb) / <alpha-value>)',
          300: 'rgb(var(--accent-300-rgb) / <alpha-value>)',
          400: 'rgb(var(--accent-400-rgb) / <alpha-value>)',
          500: 'rgb(var(--accent-500-rgb) / <alpha-value>)',
          600: 'rgb(var(--accent-600-rgb) / <alpha-value>)',
          700: 'rgb(var(--accent-700-rgb) / <alpha-value>)',
          800: 'rgb(var(--accent-800-rgb) / <alpha-value>)',
          900: 'rgb(var(--accent-900-rgb) / <alpha-value>)',
        },
        earth: {
          DEFAULT: '#8A8690',
          50: '#F0ECF0',
          100: '#E0DCE4',
          200: '#C0BCC8',
          300: '#B8B4BC',
          400: '#9E9AA6',
          500: '#6E6A76',
          600: '#54505C',
          650: '#47424E',
          700: '#3A3540',
          750: '#322D38',
          800: '#2A2530',
          900: '#1E1A24',
          950: '#14111A',
        },
        cream: {
          DEFAULT: '#F0ECF0',
          50: '#FAF8FA',
          100: '#F0ECF0',
          200: '#E0DCE4',
          300: '#C8C4CE',
          400: '#A8A4B0',
          500: '#8A8690',
          600: '#6E6A76',
          700: '#54505C',
          800: '#3A3540',
          900: '#2A2530',
        },
        forest: {
          50: '#F1F6F4',
          100: '#E1EDE9',
          200: '#C4D8D1',
          300: '#A0BEB5',
          400: '#89ADA4',
          500: '#7BA098',
          600: '#6B9088',
          700: '#5B8078',
          800: '#4B7068',
          900: '#3B6058',
        },
        // Mood-browse pastel tints (catalog MoodBrowseRow): six cycling
        // light-mode card tones, each with a slightly deeper hover shade.
        // Deliberate exception to the earth/rose system; named so they stay
        // one palette instead of arbitrary per-file hex.
        mood: {
          'rose': '#ffe3e7', 'rose-hover': '#ffd1d8',
          'lime': '#f1f6c5', 'lime-hover': '#e7efaa',
          'lilac': '#ece1ff', 'lilac-hover': '#dccaff',
          'gold': '#feeac1', 'gold-hover': '#fcdba0',
          'mint': '#d6f0df', 'mint-hover': '#bee5cd',
          'sky': '#d6e8ff', 'sky-hover': '#bcd8ff',
        },
        education: {
          primary: '#7BA098',
          secondary: 'rgb(var(--accent-400-rgb) / <alpha-value>)',
        },
        kids: {
          DEFAULT: 'rgb(var(--accent-300-rgb) / <alpha-value>)',
          light: 'rgb(var(--accent-50-rgb) / <alpha-value>)',
          accent: 'rgb(var(--accent-400-rgb) / <alpha-value>)',
          dark: 'rgb(var(--accent-600-rgb) / <alpha-value>)',
        },
        teen: {
          DEFAULT: 'rgb(var(--accent-400-rgb) / <alpha-value>)',
          light: 'rgb(var(--accent-50-rgb) / <alpha-value>)',
          accent: '#7BA098',
          dark: 'rgb(var(--accent-700-rgb) / <alpha-value>)',
        },
        staff: {
          DEFAULT: '#7BA098',
          light: '#F0FAF6',
          accent: '#6B9088',
          dark: '#5B8078',
        },
        resources: {
          DEFAULT: 'rgb(var(--accent-400-rgb) / <alpha-value>)',
          light: 'rgb(var(--accent-50-rgb) / <alpha-value>)',
          accent: 'rgb(var(--accent-300-rgb) / <alpha-value>)',
          dark: 'rgb(var(--accent-600-rgb) / <alpha-value>)',
        },
      },
      fontFamily: {
        'sans': ['"Instrument Sans"', 'system-ui', '-apple-system', 'sans-serif'],
        'serif': ['var(--display, "DM Serif Display")', 'Georgia', 'serif'],
        'mono': ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        'sm': '4px',
        DEFAULT: '6px',
        'md': '8px',
        'lg': '12px',
        'xl': '16px',
        '2xl': '20px',
        '3xl': '24px',
      },
      boxShadow: {
        'soft-sm': '0 1px 3px 0 rgba(0, 0, 0, 0.12)',
        'soft-md': '0 2px 6px -1px rgba(0, 0, 0, 0.16)',
        'soft-lg': '0 4px 12px -2px rgba(0, 0, 0, 0.2)',
        'soft-xl': '0 8px 24px -4px rgba(0, 0, 0, 0.24)',
      },
      keyframes: {
        'slide-up': {
          '0%': { transform: 'translateY(100%)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'slide-up-half': {
          '0%': { transform: 'translateY(100%)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'slide-down': {
          '0%': { transform: 'translateY(0)', opacity: '1' },
          '100%': { transform: 'translateY(100%)', opacity: '0' },
        },
        'backdrop-fade': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'menu-enter': {
          '0%': { transform: 'translateY(-4px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'scale-in': {
          '0%': { transform: 'scale(0.98)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        'hero-fade-up': {
          '0%': { transform: 'translateY(16px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'slide-in-right': {
          '0%': { transform: 'translateX(100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        'slide-up-fade': {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'dashboard-enter': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        breathe: {
          '0%, 100%': { opacity: '0.4', transform: 'scale(0.95)' },
          '50%': { opacity: '1', transform: 'scale(1.05)' },
        },
        'glow-breathe': {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(139, 94, 94, 0)' },
          '50%': { boxShadow: '0 0 20px 2px rgba(139, 94, 94, 0.15)' },
        },
      },
      animation: {
        'slide-up': 'slide-up 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-up-half': 'slide-up-half 0.25s cubic-bezier(0, 0, 0.2, 1)',
        'slide-down': 'slide-down 0.25s ease-in',
        'backdrop-fade': 'backdrop-fade 0.15s cubic-bezier(0.16, 1, 0.3, 1)',
        'menu-enter': 'menu-enter 0.12s cubic-bezier(0.16, 1, 0.3, 1)',
        'fade-in': 'fade-in 0.15s cubic-bezier(0.16, 1, 0.3, 1)',
        'scale-in': 'scale-in 0.15s cubic-bezier(0.16, 1, 0.3, 1)',
        'hero-fade-up-0': 'hero-fade-up 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0s both',
        'hero-fade-up-1': 'hero-fade-up 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.08s both',
        'hero-fade-up-2': 'hero-fade-up 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.16s both',
        'hero-fade-up-3': 'hero-fade-up 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.24s both',
        'slide-in-right': 'slide-in-right 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-up-fade': 'slide-up-fade 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'glow-breathe': 'glow-breathe 4s ease-in-out infinite',
        'dashboard-enter-0': 'dashboard-enter 0.4s cubic-bezier(0.16, 1, 0.3, 1) 0.05s both',
        'dashboard-enter-1': 'dashboard-enter 0.4s cubic-bezier(0.16, 1, 0.3, 1) 0.1s both',
        'dashboard-enter-2': 'dashboard-enter 0.4s cubic-bezier(0.16, 1, 0.3, 1) 0.15s both',
        'dashboard-enter-3': 'dashboard-enter 0.4s cubic-bezier(0.16, 1, 0.3, 1) 0.2s both',
        'dashboard-enter-4': 'dashboard-enter 0.4s cubic-bezier(0.16, 1, 0.3, 1) 0.25s both',
        breathe: 'breathe 2.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      typography: {
        DEFAULT: {
          css: {
            "--tw-prose-body": "rgb(30 26 36)",
            "--tw-prose-headings": "rgb(30 26 36)",
            "--tw-prose-links": "rgb(var(--accent-rose-rgb))",
            "--tw-prose-bold": "rgb(30 26 36)",
            "--tw-prose-quotes": "rgb(30 26 36 / 0.8)",
            "--tw-prose-quote-borders": "rgb(var(--accent-rose-rgb))",
            "--tw-prose-counters": "rgb(30 26 36 / 0.6)",
            "--tw-prose-bullets": "rgb(var(--accent-rose-rgb) / 0.6)",
            "--tw-prose-hr": "rgb(30 26 36 / 0.1)",
            "--tw-prose-th-borders": "rgb(30 26 36 / 0.2)",
            "--tw-prose-td-borders": "rgb(30 26 36 / 0.1)",
          },
        },
      },
    },
  },
  plugins: [
    typography,
    function ({ addUtilities }) {
      const focusUtilities = {
        '.focus-ring': {
          '&:focus-visible': {
            outline: '2px solid var(--focus-ring-color, #C88080)',
            'outline-offset': '2px',
          },
        },
        '.focus-ring-strong': {
          '&:focus-visible': {
            outline: '3px solid var(--focus-ring-color, #C88080)',
            'outline-offset': '2px',
          },
        },
        '.focus-ring-inset': {
          '&:focus-visible': {
            outline: '2px solid var(--focus-ring-color, #C88080)',
            'outline-offset': '-2px',
          },
        },
        '.focus-ring-dark': {
          '&:focus-visible': {
            outline: '3px solid var(--focus-ring-color, #C88080)',
            'outline-offset': '2px',
          },
        },
        // Keep glass classes as no-ops so existing code doesn't break
        '.glass': {},
        '.glass-strong': {},
      }
      addUtilities(focusUtilities)
    },
    scrollbar,
  ],
}
