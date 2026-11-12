/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * useEpubReader — imperative epub.js bridge for the in-browser reader.
 *
 * Fetches the borrowed EPUB's raw bytes from our own origin (the streaming
 * endpoint, JWT + borrow-scoped), renders them paginated into a container,
 * mirrors the patron's accessibility settings into the rendition, and syncs
 * reading position (CFI + percent) back to the existing reading-progress API.
 *
 * epub.js manipulates an iframe imperatively, so this lives outside React's
 * render cycle behind a ref + effects rather than in a component tree.
 */
import { useCallback, useEffect, useRef, useState, type RefObject } from 'react'
import ePub, { type Book, type Rendition, type Contents } from 'epubjs'

import { API_BASE } from '@/api/types'
import { getAccessToken } from '@/utils/tokenStore'
import { getReadingProgress, updateReadingProgress } from '@/api/indie-engagement-api'

export interface ReaderThemeSettings {
  dyslexiaFont: boolean
  fontSize: 'normal' | 'large' | 'xlarge'
  lineSpacing: 'normal' | 'relaxed' | 'loose'
  letterSpacingBody: 'normal' | 'wide' | 'wider'
  theme: 'light' | 'dark' | 'high-contrast' | 'system'
}

interface UseEpubReaderArgs {
  ebookId: number | null
  settings: ReaderThemeSettings
}

interface UseEpubReaderResult {
  containerRef: RefObject<HTMLDivElement>
  ready: boolean
  error: string | null
  percent: number
  next: () => void
  prev: () => void
}

const FONT_SIZE_PCT: Record<ReaderThemeSettings['fontSize'], string> = {
  normal: '100%',
  large: '125%',
  xlarge: '150%',
}
const LINE_HEIGHT: Record<ReaderThemeSettings['lineSpacing'], string> = {
  normal: '1.5',
  relaxed: '1.8',
  loose: '2.1',
}
const LETTER_SPACING: Record<ReaderThemeSettings['letterSpacingBody'], string> = {
  normal: '0',
  wide: '0.04em',
  wider: '0.08em',
}
const PALETTE: Record<ReaderThemeSettings['theme'], { color: string; background: string }> = {
  light: { color: '#2A2622', background: '#FBF9F6' },
  dark: { color: '#E8E3DC', background: '#1A1714' },
  'high-contrast': { color: '#000000', background: '#FFFFFF' },
  system: { color: '#2A2622', background: '#FBF9F6' },
}

// Atkinson Hyperlegible woff2 → data: URLs, fetched once and shared. Injected
// into each section's iframe document so the dyslexia font resolves inside the
// null-origin blob: document (where a same-origin /fonts URL would not).
let fontFacePromise: Promise<string> | null = null
async function loadDyslexiaFontFace(): Promise<string> {
  if (fontFacePromise) return fontFacePromise
  fontFacePromise = (async () => {
    const weights: Array<[number, string]> = [
      [400, '/fonts/atkinson-hyperlegible/AtkinsonHyperlegible-Regular.woff2'],
      [700, '/fonts/atkinson-hyperlegible/AtkinsonHyperlegible-Bold.woff2'],
    ]
    const faces = await Promise.all(
      weights.map(async ([weight, url]) => {
        try {
          // eslint-disable-next-line no-restricted-syntax -- binary asset fetch (arrayBuffer); fetchApi's JSON contract does not fit
          const res = await fetch(url)
          if (!res.ok) return ''
          const buf = await res.arrayBuffer()
          let binary = ''
          const bytes = new Uint8Array(buf)
          for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i] as number)
          const b64 = btoa(binary)
          return `@font-face{font-family:'Atkinson Hyperlegible';font-style:normal;font-weight:${weight};font-display:swap;src:url(data:font/woff2;base64,${b64}) format('woff2');}`
        } catch {
          return ''
        }
      }),
    )
    return faces.join('')
  })()
  return fontFacePromise
}

export function useEpubReader({ ebookId, settings }: UseEpubReaderArgs): UseEpubReaderResult {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const bookRef = useRef<Book | null>(null)
  const renditionRef = useRef<Rendition | null>(null)
  const locationsReadyRef = useRef(false)
  const themeCounterRef = useRef(0)
  const fontFaceRef = useRef('')
  const currentCfiRef = useRef<string | null>(null)
  const currentPercentRef = useRef(0)
  const writeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [ready, setReady] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [percent, setPercent] = useState(0)

  // Persist position, debounced. epub.js fires `relocated` on every page turn,
  // so a trailing debounce keeps PUT volume sane; flushed on unmount/hide.
  const flushProgress = useCallback(() => {
    if (ebookId == null || !currentCfiRef.current) return
    void updateReadingProgress(ebookId, currentPercentRef.current, currentCfiRef.current).catch(() => {})
  }, [ebookId])

  const scheduleProgressWrite = useCallback(() => {
    if (writeTimerRef.current) clearTimeout(writeTimerRef.current)
    writeTimerRef.current = setTimeout(flushProgress, 1500)
  }, [flushProgress])

  // ---- live re-theme when accessibility settings change ----
  const applyTheme = useCallback(() => {
    const rendition = renditionRef.current
    if (!rendition) return
    const pal = PALETTE[settings.theme] ?? PALETTE.light
    const bodyRules: Record<string, string> = {
      color: `${pal.color} !important`,
      background: `${pal.background} !important`,
      'line-height': `${LINE_HEIGHT[settings.lineSpacing]} !important`,
      'letter-spacing': `${LETTER_SPACING[settings.letterSpacingBody]} !important`,
    }
    if (settings.dyslexiaFont) {
      bodyRules['font-family'] = "'Atkinson Hyperlegible', system-ui, sans-serif !important"
    }
    // Fresh theme name each time so stale overrides (e.g. an old font-family)
    // don't linger when a setting is toggled back off.
    const name = `l30-${themeCounterRef.current++}`
    const childRules = settings.dyslexiaFont
      ? { 'font-family': "'Atkinson Hyperlegible', system-ui, sans-serif !important" }
      : {}
    rendition.themes.register(name, {
      body: bodyRules,
      'p, li, blockquote, div, span, a, h1, h2, h3, h4, h5, h6': childRules,
    })
    rendition.themes.select(name)
    rendition.themes.fontSize(FONT_SIZE_PCT[settings.fontSize])
    if (containerRef.current) containerRef.current.style.background = pal.background
  }, [settings])


  // ---- mount: fetch bytes + render ----
  useEffect(() => {
    let cancelled = false
    const container = containerRef.current
    if (!container || ebookId == null) return

    async function start() {
      try {
        fontFaceRef.current = await loadDyslexiaFontFace()
        if (cancelled) return

        const token = getAccessToken()
        // eslint-disable-next-line no-restricted-syntax -- binary epub content fetch (arrayBuffer); fetchApi's JSON contract does not fit
        const res = await fetch(`${API_BASE}/indie/lending/read/${ebookId}/content`, {
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
          credentials: 'include',
        })
        if (!res.ok) {
          throw new Error(res.status === 403 ? 'This loan has ended.' : 'Could not load this book.')
        }
        const buf = await res.arrayBuffer()
        if (cancelled) return

        const book = ePub(buf)
        bookRef.current = book
        const rendition = book.renderTo(container as HTMLElement, {
          width: '100%',
          height: '100%',
          flow: 'paginated',
          spread: 'auto',
          allowScriptedContent: false,
        })
        renditionRef.current = rendition

        // Make the dyslexia @font-face available inside every section iframe.
        rendition.hooks.content.register((contents: Contents) => {
          const doc = contents.document
          if (fontFaceRef.current && doc.head && !doc.getElementById('l30-fontface')) {
            const style = doc.createElement('style')
            style.id = 'l30-fontface'
            style.textContent = fontFaceRef.current
            doc.head.appendChild(style)
          }
        })

        applyTheme()

        const saved = ebookId != null ? await getReadingProgress(ebookId) : null
        if (cancelled) return
        await rendition.display(saved?.current_position || undefined)

        rendition.on('relocated', (location: { start: { cfi: string } }) => {
          const cfi = location?.start?.cfi
          if (!cfi) return
          currentCfiRef.current = cfi
          if (locationsReadyRef.current) {
            const pct = Math.round((book.locations.percentageFromCfi(cfi) || 0) * 100)
            currentPercentRef.current = pct
            setPercent(pct)
          }
          scheduleProgressWrite()
        })

        if (cancelled) return
        setReady(true)

        // Locations power the percentage readout; generate after first paint so
        // the book opens promptly, then backfill percent for the current spot.
        book.locations
          .generate(1650)
          .then(() => {
            if (cancelled) return
            locationsReadyRef.current = true
            const cfi = currentCfiRef.current
            if (cfi) {
              const pct = Math.round((book.locations.percentageFromCfi(cfi) || 0) * 100)
              currentPercentRef.current = pct
              setPercent(pct)
            }
          })
          .catch(() => {})
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Could not load this book.')
      }
    }

    void start()

    return () => {
      cancelled = true
      if (writeTimerRef.current) clearTimeout(writeTimerRef.current)
      flushProgress()
      try {
        renditionRef.current?.destroy()
        bookRef.current?.destroy()
      } catch {
        /* noop */
      }
      renditionRef.current = null
      bookRef.current = null
      locationsReadyRef.current = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ebookId])

  // Flush position when the tab is hidden or the page unloads.
  useEffect(() => {
    const onHide = () => {
      if (document.visibilityState === 'hidden') flushProgress()
    }
    document.addEventListener('visibilitychange', onHide)
    window.addEventListener('beforeunload', flushProgress)
    return () => {
      document.removeEventListener('visibilitychange', onHide)
      window.removeEventListener('beforeunload', flushProgress)
    }
  }, [flushProgress])

  useEffect(() => {
    if (ready) applyTheme()
  }, [ready, applyTheme])

  const next = useCallback(() => {
    void renditionRef.current?.next()
  }, [])
  const prev = useCallback(() => {
    void renditionRef.current?.prev()
  }, [])

  return { containerRef, ready, error, percent, next, prev }
}
