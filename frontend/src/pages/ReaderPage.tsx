/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * ReaderPage — the in-browser EPUB reader.
 *
 * A full-viewport overlay (it deliberately covers the patron shell so the book
 * owns the screen). Renders a borrowed indie EPUB via epub.js, mirrors the
 * patron's accessibility settings, syncs reading position, and offers calm
 * page navigation (arrow keys, on-screen arrows). No countdowns, no urgency.
 */
import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Loader2 } from 'lucide-react'

import { useAccessibility } from '@/features/accessibility'
import { getActiveBorrows } from '@/api/indie-catalog-api'
import { useEpubReader } from '@/hooks/useEpubReader'
import ReaderToolbar from '@/components/reader/ReaderToolbar'
import ReaderSettingsDrawer from '@/components/reader/ReaderSettingsDrawer'

interface ReaderRouteState {
  title?: string
}

export default function ReaderPage() {
  const { ebookId: ebookIdParam } = useParams<{ ebookId: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const ebookId = ebookIdParam ? Number(ebookIdParam) : null

  const { dyslexiaFont, fontSize, lineSpacing, letterSpacingBody, theme } = useAccessibility()
  const settings = useMemo(
    () => ({ dyslexiaFont, fontSize, lineSpacing, letterSpacingBody, theme }),
    [dyslexiaFont, fontSize, lineSpacing, letterSpacingBody, theme],
  )

  const stateTitle = (location.state as ReaderRouteState | null)?.title
  const [title, setTitle] = useState(stateTitle || 'Reading')
  const [settingsOpen, setSettingsOpen] = useState(false)

  const { containerRef, ready, error, percent, next, prev } = useEpubReader({ ebookId, settings })

  const goBack = () => navigate('/indie/my-borrows')

  // Fill in the title when opened by direct URL (no router state).
  useEffect(() => {
    if (stateTitle || ebookId == null) return
    let cancelled = false
    void getActiveBorrows()
      .then((borrows) => {
        if (cancelled) return
        const match = borrows.find((b) => (b.indie_ebook_id ?? b.ebook_id) === ebookId)
        if (match?.ebook_title) setTitle(match.ebook_title)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [stateTitle, ebookId])

  // Keyboard navigation. Esc exits when no drawer is open.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (settingsOpen) return
      if (e.key === 'ArrowLeft') prev()
      else if (e.key === 'ArrowRight') next()
      else if (e.key === 'Escape') goBack()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settingsOpen, next, prev])

  if (ebookId == null) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-lsc-cream dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream">
        <p>That book could not be found.</p>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-lsc-cream dark:bg-earth-900">
      <ReaderToolbar
        title={title}
        percent={percent}
        showPercent={ready && !error}
        onBack={goBack}
        onOpenSettings={() => setSettingsOpen(true)}
      />

      <div className="relative flex-1 min-h-0">
        {/* epub.js renders into this element */}
        <div ref={containerRef} className="absolute inset-0" />

        {/* Page controls: edge arrows + keyboard. Kept off the text column. */}
        {ready && !error && (
          <>
            <button
              type="button"
              onClick={prev}
              aria-label="Previous page"
              className="absolute left-0 top-0 h-full w-12 sm:w-16 flex items-center justify-center text-lsc-dark/40 dark:text-lsc-cream/40 hover:text-lsc-rose hover:bg-black/5 dark:hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
            >
              <ChevronLeft className="w-6 h-6" aria-hidden="true" />
            </button>
            <button
              type="button"
              onClick={next}
              aria-label="Next page"
              className="absolute right-0 top-0 h-full w-12 sm:w-16 flex items-center justify-center text-lsc-dark/40 dark:text-lsc-cream/40 hover:text-lsc-rose hover:bg-black/5 dark:hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
            >
              <ChevronRight className="w-6 h-6" aria-hidden="true" />
            </button>
          </>
        )}

        {!ready && !error && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-lsc-dark/70 dark:text-lsc-cream/70">
            <Loader2 className="w-7 h-7 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
            <p className="text-sm">Opening your book…</p>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 px-6 text-center text-lsc-dark dark:text-lsc-cream">
            <p className="max-w-sm">{error}</p>
            <button
              type="button"
              onClick={goBack}
              className="min-h-11 px-4 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
            >
              Back to my books
            </button>
          </div>
        )}
      </div>

      <ReaderSettingsDrawer open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  )
}
