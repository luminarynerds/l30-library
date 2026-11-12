/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { usePageMeta } from '@/hooks/usePageMeta'

// Director-facing platform page. Uses L30's own product palette (dusty rose +
// deep plum + goldenrod/sage, Playfair + DM Mono) so the "platform underneath"
// moment is visually continuous with the library a director just toured.
// Styling is self-contained here so it does not touch the product design system.
//
// A11Y-MODE EXEMPTION (maintainer-approved 2026-07-06): because everything below is
// inline `style` from the C palette, the site display modes (high-contrast,
// dark, dyslexia, colorblind) intentionally do not restyle this page. That is
// acceptable for a marketing/sales surface whose default-mode contrast is
// verified below; if this ever becomes patron-critical UI, rewire C to the
// CSS custom properties in index.css instead.
//
// Color roles are contrast-gated (computed against cream #F0ECF0 / plum #1E1A24):
//   roseText #7A4040 -> rose text on cream (6.82:1, AA)
//   roseFill #8B5E5E -> cream text on rose fill (4.65:1, AA); NOT for text on the
//                       card/roseWash bg (4.31:1, sub-AA) -- fill/border use only.
//   roseDark #D49898 -> rose accents on the dark Proof ground (7.12:1, AA)
//   gold     #B8860B -> decoration only on cream (live-dot, fails as text there);
//                       AA on plum (5.25:1). sage #7BA098 -> fill/rule only on cream.

const C = {
  cream: '#F0ECF0',
  creamDeep: '#E6E0E6',
  ink: '#1E1A24',
  inkSoft: '#4A4350',
  roseText: '#7A4040',
  roseFill: '#8B5E5E',
  roseDark: '#D49898',
  roseWash: '#EBDDE0',
  gold: '#B8860B',
  sage: '#7BA098',
  rule: '#CBC3CB',
  card: '#E9E3E9',
}
const display = "'Playfair Display', Georgia, serif"
const mono = "'DM Mono', 'Courier New', monospace"
const body = "Georgia, 'Times New Roman', serif"

// Plum-tinted paper grain: a faint two-tone dot field over the cream ground.
const grain =
  "radial-gradient(rgba(30,26,36,0.022) 1px, transparent 1px)," +
  "radial-gradient(rgba(30,26,36,0.018) 1px, transparent 1px)"

const css = `
@keyframes l30fl-rise {
  from { opacity: 0; transform: translateY(14px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes l30fl-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(184,134,11,0.45); }
  70%      { box-shadow: 0 0 0 7px rgba(184,134,11,0); }
}
.l30fl-rise { opacity: 0; animation: l30fl-rise 0.62s cubic-bezier(0.22,0.61,0.36,1) forwards; }
.l30fl-dot { animation: l30fl-pulse 2.4s ease-out infinite; }
.l30fl-cta { transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease, color 0.18s ease; }
.l30fl-cta:hover { transform: translateY(-2px); box-shadow: 0 8px 22px rgba(30,26,36,0.16); }
.l30fl-cta:focus-visible { outline: 2px solid #7A4040; outline-offset: 3px; }
.l30fl-card { transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease; border: 1px solid transparent; }
.l30fl-card:hover { transform: translateY(-3px); box-shadow: 0 10px 26px rgba(30,26,36,0.1); border-color: #CBC3CB; }
@media (prefers-reduced-motion: reduce) {
  .l30fl-rise { opacity: 1; animation: none; }
  .l30fl-dot { animation: none; }
  .l30fl-cta, .l30fl-card { transition: none; }
  .l30fl-cta:hover, .l30fl-card:hover { transform: none; }
}
.l30fl-own-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; margin-top: 1.5rem; }
@media (max-width: 640px) { .l30fl-own-grid { grid-template-columns: 1fr; } }
.l30fl-h1 { white-space: nowrap; }
@media (max-width: 680px) { .l30fl-h1 { white-space: normal; } }
@media (forced-colors: active) {
  .l30fl-cta { border: 1px solid currentColor; }
  .l30fl-card { border: 1px solid currentColor; }
}
`

function Eyebrow({ children }: { children: React.ReactNode }) {
  return <p style={{ fontFamily: body, fontStyle: 'italic', color: C.roseText, fontSize: '1rem', marginBottom: '0.75rem' }}>{children}</p>
}

export default function ForLibrariesPage(): React.ReactElement {
  usePageMeta({
    title: 'L30 for libraries. Own your library system',
    description: 'L30 is a complete, open-source library system your library owns outright. Live in production today. No licensing fees, no vendor lock-in.',
    canonicalPath: '/for-libraries',
  })
  useEffect(() => {
    const pre1 = document.createElement('link')
    pre1.rel = 'preconnect'; pre1.href = 'https://fonts.googleapis.com'
    const pre2 = document.createElement('link')
    pre2.rel = 'preconnect'; pre2.href = 'https://fonts.gstatic.com'; pre2.crossOrigin = 'anonymous'
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = 'https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,700;1,500&family=DM+Mono:wght@400;500&display=swap'
    document.head.append(pre1, pre2, link)
    return () => { pre1.remove(); pre2.remove(); link.remove() }
  }, [])
  return (
    <div style={{ background: C.cream, color: C.ink, fontFamily: body, fontSize: '1.0625rem', lineHeight: 1.6, backgroundImage: grain, backgroundSize: '22px 22px, 22px 22px', backgroundPosition: '0 0, 11px 11px' }}>
      <style>{css}</style>

      {/* Hero */}
      <header style={{ borderBottom: `1px solid ${C.rule}`, background: `linear-gradient(${C.creamDeep}, ${C.cream})` }}>
        <div style={{ maxWidth: '64rem', margin: '0 auto', padding: '5.5rem 1.75rem 5rem' }}>
          <div className="l30fl-rise" style={{ animationDelay: '0s' }}><Eyebrow>For library directors</Eyebrow></div>
          <h1 className="l30fl-rise l30fl-h1" style={{ animationDelay: '0.08s', fontFamily: display, fontWeight: 700, fontSize: 'clamp(1.9rem, 5vw, 3.2rem)', lineHeight: 1.05, letterSpacing: '-0.01em', marginBottom: '0.6rem', maxWidth: 'none' }}>
            Not a pitch deck. It&rsquo;s <span style={{ fontStyle: 'italic', color: C.roseText }}>running</span>.
          </h1>
          <p className="l30fl-rise" style={{ animationDelay: '0.16s', fontFamily: display, fontStyle: 'italic', fontWeight: 500, fontSize: 'clamp(1.25rem, 2.6vw, 1.6rem)', color: C.inkSoft, marginBottom: '1.5rem' }}>
            A complete library system your library <span style={{ color: C.roseText }}>owns outright</span>.
          </p>
          <p className="l30fl-rise" style={{ animationDelay: '0.24s', maxWidth: '38rem', marginBottom: '1.75rem' }}>
            L30 is a full, open-source library system: catalog, circulation, holds, ebooks, staff tools. The site you&rsquo;re on is a real, working library running on it, in production, today. No licensing fees. No vendor lock-in. Yours to keep.
          </p>
          <p className="l30fl-rise" style={{ animationDelay: '0.32s', fontFamily: mono, fontSize: '0.8rem', letterSpacing: '0.04em', color: C.roseText, display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '1.75rem' }}>
            <span className="l30fl-dot" style={{ width: '9px', height: '9px', borderRadius: '50%', background: C.gold, display: 'inline-block' }} />
            RUNNING LIVE. THE COMPLETE SYSTEM, IN THE OPEN.
          </p>
          <div className="l30fl-rise" style={{ animationDelay: '0.4s', display: 'flex', gap: '0.85rem', flexWrap: 'wrap', marginBottom: '1.75rem' }}>
            <Link to="/catalog" className="l30fl-cta" style={{ fontFamily: mono, fontSize: '0.8rem', letterSpacing: '0.08em', textTransform: 'uppercase', textDecoration: 'none', padding: '0.85rem 1.4rem', background: C.ink, color: C.cream }}>
              Tour the live demo &rarr;
            </Link>
            <a href="#partnership" className="l30fl-cta" style={{ fontFamily: mono, fontSize: '0.8rem', letterSpacing: '0.08em', textTransform: 'uppercase', textDecoration: 'none', padding: '0.85rem 1.4rem', border: `1px solid ${C.ink}`, color: C.ink }}>
              See the partnership &darr;
            </a>
          </div>
          <p className="l30fl-rise" style={{ animationDelay: '0.48s', fontFamily: mono, fontSize: '0.8rem', color: C.inkSoft }}>
            open-source (AGPL) &middot; own your catalog forever &middot; WCAG-native &middot; $0 per-seat
          </p>
        </div>
      </header>

      {/* The math */}
      <section aria-label="Cost comparison" style={{ borderBottom: `1px solid ${C.rule}` }}>
        <div style={{ maxWidth: '64rem', margin: '0 auto', padding: '5rem 1.75rem' }}>
          <Eyebrow>The math your board already knows</Eyebrow>
          <h2 style={{ fontFamily: display, fontWeight: 700, fontSize: 'clamp(1.7rem, 3.6vw, 2.3rem)', lineHeight: 1.15, marginBottom: '2.25rem', maxWidth: '36rem' }}>
            Licensed software rents you access. Owned software is yours.
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1px', background: C.rule, border: `1px solid ${C.ink}`, maxWidth: '46rem' }}>
            <div style={{ background: C.cream, padding: '1.75rem 1.6rem' }}>
              <h3 style={{ fontFamily: mono, fontSize: '0.74rem', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: '1.25rem', color: C.inkSoft }}>A vendor ILS</h3>
              {[
                ['Annual license', 'compounds, forever'],
                ['Your catalog data', 'export = fee, or hostage'],
                ['Source code', 'closed'],
                ['Users', 'priced per seat'],
                ['Leaving', 'migration lock-in'],
              ].map(([k, v]) => (
                <div key={k} style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', fontFamily: mono, fontSize: '0.8rem', padding: '0.55rem 0', borderBottom: `1px dotted ${C.rule}`, color: C.inkSoft }}>
                  <span>{k}</span><span style={{ textAlign: 'right' }}>{v}</span>
                </div>
              ))}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', paddingTop: '1.25rem' }}>
                <span style={{ fontFamily: display, fontStyle: 'italic', color: C.inkSoft }}>You hold</span>
                <span style={{ fontFamily: display, fontWeight: 700, fontSize: '1.4rem', color: C.inkSoft }}>a contract</span>
              </div>
            </div>
            <div style={{ background: C.roseWash, padding: '1.75rem 1.6rem', borderLeft: `4px solid ${C.roseFill}` }}>
              <h3 style={{ fontFamily: mono, fontSize: '0.74rem', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: '1.25rem', color: C.roseText }}>L30</h3>
              {[
                ['License fee', '$0'],
                ['Your catalog data', 'yours, open formats'],
                ['Source code', 'AGPL, fork it'],
                ['Users', 'unlimited'],
                ['Leaving', 'self-host, anytime'],
              ].map(([k, v]) => (
                <div key={k} style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', fontFamily: mono, fontSize: '0.8rem', padding: '0.55rem 0', borderBottom: `1px dotted ${C.rule}`, color: C.ink }}>
                  <span>{k}</span><span style={{ textAlign: 'right', fontWeight: 500 }}><span aria-hidden="true" style={{ color: C.roseText, marginRight: '0.4rem' }}>{'\u2713'}</span>{v}</span>
                </div>
              ))}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', paddingTop: '1.25rem' }}>
                <span style={{ fontFamily: display, fontStyle: 'italic', color: C.inkSoft }}>You hold</span>
                <span style={{ fontFamily: display, fontWeight: 700, fontSize: '1.4rem', color: C.roseText }}>the software</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Proof */}
      <section aria-label="Live production proof" style={{ borderBottom: `1px solid ${C.rule}`, background: C.ink, color: C.cream }}>
        <div style={{ maxWidth: '64rem', margin: '0 auto', padding: '5rem 1.75rem' }}>
          <p style={{ fontFamily: mono, fontSize: '0.76rem', letterSpacing: '0.08em', color: C.roseDark, marginBottom: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span className="l30fl-dot" style={{ width: '8px', height: '8px', borderRadius: '50%', background: C.gold, display: 'inline-block' }} />
            RUNNING LIVE. THE COMPLETE SYSTEM, IN THE OPEN.
          </p>
          <h2 style={{ fontFamily: display, fontWeight: 700, fontSize: 'clamp(1.7rem, 3.6vw, 2.3rem)', color: C.cream, marginBottom: '1rem' }}>
            This site is the proof.
          </h2>
          <p style={{ maxWidth: '40rem', color: '#D6D0D8', marginBottom: '1.5rem' }}>
            l30.org isn&rsquo;t a sandbox with three sample records. It&rsquo;s the entire system (catalog, circulation, holds, ebooks, staff tools), running live, production-grade. We built out a full fictional library so you can stress-test every workflow, as a patron and as staff, right now, without a sales call. What you&rsquo;re touching is exactly what your library would run.
          </p>
          <p style={{ fontFamily: mono, fontSize: '0.78rem', color: C.roseDark, letterSpacing: '0.03em', marginBottom: '1.75rem' }}>
            catalog &middot; circulation &middot; holds &middot; ebooks (MetisLib) &middot; staff tools &middot; all live
          </p>
          <Link to="/" className="l30fl-cta" style={{ fontFamily: mono, fontSize: '0.8rem', letterSpacing: '0.08em', textTransform: 'uppercase', textDecoration: 'none', padding: '0.85rem 1.4rem', border: `1px solid ${C.roseDark}`, color: C.cream }}>
            Tour it as a patron &rarr;
          </Link>
        </div>
      </section>

      {/* What you own */}
      <section aria-label="What you get" style={{ borderBottom: `1px solid ${C.rule}` }}>
        <div style={{ maxWidth: '64rem', margin: '0 auto', padding: '5rem 1.75rem' }}>
          <Eyebrow>What you actually get</Eyebrow>
          <div className="l30fl-own-grid">
            {[
              ['Open source, forever', 'Free and open source under the GNU Affero General Public License (AGPL). Fork it, self-host it, audit it. The software outlives any vendor, us included.'],
              ['Accessibility is the default', 'Built on Atkinson Hyperlegible with a neurodivergent-aware toolkit. WCAG is the floor, not a toggle you pay extra for.'],
              ['Own your ebooks too', 'Through MetisLib: buy a title once for $10, own it for good, $8 of every $10 to the author. Indie and independent-press titles, not a Big Five backlist. Runs alongside your existing ebook vendor. Additive, not a day-one OverDrive replacement.'],
              ['Your data, your formats', 'Open catalog feeds (OPDS), standard MARC records, export anytime. Nothing held hostage.'],
            ].map(([t, d]) => (
              <div key={t} className="l30fl-card" style={{ background: C.card, padding: '1.6rem 1.5rem' }}>
                <h3 style={{ fontFamily: display, fontWeight: 700, fontSize: '1.2rem', marginBottom: '0.5rem' }}>{t}</h3>
                <p style={{ fontSize: '0.95rem', color: C.inkSoft }}>{d}</p>
              </div>
            ))}
          </div>
          <p style={{ fontSize: '0.85rem', color: C.inkSoft, marginTop: '1.75rem', maxWidth: '44rem', fontStyle: 'italic' }}>
            AGPL means self-host, modify, and fork freely. The one obligation: if you offer a modified version as a public network service, you share those changes back. For a library running its own catalog, that&rsquo;s effectively no constraint, your legal team can confirm in five minutes.
          </p>
        </div>
      </section>

      {/* Migration */}
      <section aria-label="Data migration" style={{ borderBottom: `1px solid ${C.rule}` }}>
        <div style={{ maxWidth: '64rem', margin: '0 auto', padding: '5rem 1.75rem' }}>
          <Eyebrow>Getting your data in</Eyebrow>
          <h2 style={{ fontFamily: display, fontWeight: 700, fontSize: 'clamp(1.6rem, 3.4vw, 2.1rem)', lineHeight: 1.15, marginBottom: '1.25rem', maxWidth: '34rem' }}>
            Migration is the part that keeps directors up at night. We don&rsquo;t wave it away.
          </h2>
          <p style={{ maxWidth: '40rem' }}>
            L30 imports standard MARC records (MARC21 and MARCXML) and common export formats, and the 90-day pilot includes hands-on migration help. We map and load your real catalog, and work through your patron and circulation data with you. You pilot on your actual collection, not a toy import.
          </p>
        </div>
      </section>

      {/* Bus factor */}
      <section aria-label="Continuity and support" style={{ borderBottom: `1px solid ${C.rule}` }}>
        <div style={{ maxWidth: '64rem', margin: '0 auto', padding: '5rem 1.75rem' }}>
          <Eyebrow>The question every director asks</Eyebrow>
          <h2 style={{ fontFamily: display, fontWeight: 700, fontSize: 'clamp(1.6rem, 3.4vw, 2.1rem)', lineHeight: 1.15, marginBottom: '1.25rem', maxWidth: '34rem' }}>
            What if you get hit by a bus?
          </h2>
          <p style={{ maxWidth: '40rem' }}>
            Fair question. The answer is the license. L30 is AGPL and self-hostable, so your library is never dependent on us existing. The code is yours to run, audit, and fork. For the founding cohort we provide hands-on setup and direct support, and because it&rsquo;s fully open, any developer or vendor can maintain it after that. You&rsquo;re not trusting a company to stay alive. You&rsquo;re holding software that can&rsquo;t be taken away.
          </p>
        </div>
      </section>

      {/* The ask */}
      <section aria-label="The offer" id="partnership">
        <div style={{ maxWidth: '64rem', margin: '0 auto', padding: '5.5rem 1.75rem' }}>
          <Eyebrow>The offer</Eyebrow>
          <h2 style={{ fontFamily: display, fontWeight: 700, fontSize: 'clamp(1.9rem, 4vw, 2.7rem)', lineHeight: 1.1, marginBottom: '1.25rem', maxWidth: '34rem' }}>
            90-day founding partnership. No cost, no commitment.
          </h2>
          <p style={{ maxWidth: '38rem', marginBottom: '2rem' }}>
            We&rsquo;re recruiting a small cohort of pilot libraries, public libraries who want to own their stack instead of renting it. We help you stand it up, migrate your real data, and you run it for 90 days, then you decide. If it isn&rsquo;t better, you walk, and you keep your data either way.
          </p>
          <a href="mailto:hello@l30.org?subject=L30%20founding%20partner%20pilot" className="l30fl-cta" style={{ fontFamily: mono, fontSize: '0.85rem', letterSpacing: '0.08em', textTransform: 'uppercase', textDecoration: 'none', padding: '1rem 1.75rem', background: C.roseFill, color: C.cream, display: 'inline-block' }}>
            Start the conversation &rarr;
          </a>
        </div>
      </section>
    </div>
  )
}
