/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect } from 'react'
import { Link, Outlet } from 'react-router-dom'

// Minimal platform-framed shell for L30 vendor/marketing pages (e.g. /for-libraries).
// Deliberately NOT the patron Layout: no catalog nav, no "Get a Library Card", no
// library address/hours footer. Just the L30 platform mark and a route back to the
// live demo. Styled to match the Card Catalog Modern look of the pages it wraps.
// Global providers (Branding, i18n, react-query) and ErrorBoundary/ScrollToTop sit
// above this in App/AppRoutes, so this only owns the frame.

const C = {
  cream: '#F0ECF0',
  ink: '#1E1A24',
  inkSoft: '#4A4350',
  rose: '#7A4040',
  rule: '#CBC3CB',
}
const mono = "'DM Mono', 'Courier New', monospace"

const navLink: React.CSSProperties = {
  fontFamily: mono,
  fontSize: '0.78rem',
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  textDecoration: 'none',
  color: C.inkSoft,
}

export default function PlatformLayout(): React.ReactElement {
  // Own the typography so the frame holds up for any page it wraps. A wrapped page
  // may inject the same stylesheet; duplicate <link>s share a single fetch.
  useEffect(() => {
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = 'https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&display=swap'
    document.head.appendChild(link)
    return () => { document.head.removeChild(link) }
  }, [])

  return (
    <div style={{ background: C.cream, color: C.ink, minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <a
        href="#pf-main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-2 focus:z-50 focus:px-3 focus:py-2"
        style={{ fontFamily: mono, fontSize: '0.8rem', background: C.ink, color: C.cream }}
      >
        Skip to content
      </a>

      <header style={{ borderBottom: `1px solid ${C.rule}` }}>
        <div style={{ maxWidth: '64rem', margin: '0 auto', padding: '1.1rem 1.75rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
          <Link to="/for-libraries" aria-label="L30 home" style={{ fontFamily: mono, fontWeight: 500, fontSize: '1rem', letterSpacing: '0.18em', color: C.ink, textDecoration: 'none' }}>
            L30
          </Link>
          <nav aria-label="Platform" style={{ display: 'flex', gap: '1.6rem', alignItems: 'center' }}>
            <Link to="/" style={navLink}>Tour the demo</Link>
            <a href="mailto:hello@l30.org?subject=L30%20founding%20partner%20pilot" style={navLink}>Talk to us</a>
          </nav>
        </div>
      </header>

      <main id="pf-main" style={{ flex: 1 }}>
        <Outlet />
      </main>

      <footer style={{ borderTop: `1px solid ${C.rule}` }}>
        <div style={{ maxWidth: '64rem', margin: '0 auto', padding: '1.6rem 1.75rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', fontFamily: mono, fontSize: '0.76rem', letterSpacing: '0.04em', color: C.inkSoft }}>
          <span>L30 &middot; an open-source library system (AGPL)</span>
          <Link to="/" style={{ ...navLink, color: C.rose }}>Back to the live library &rarr;</Link>
        </div>
      </footer>
    </div>
  )
}
