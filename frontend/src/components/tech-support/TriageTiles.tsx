/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { KeyRound, CreditCard, Printer, Wifi } from 'lucide-react'
import { findGuide } from '@/pages/guides/_data'
import { useTranslation } from '@/i18n'

interface TriageTileMeta {
  guideId: string
  labelKey: string
  label: string
  icon: React.ReactNode
}

interface TriageTilesProps {
  /** Stable guide id whose tile should receive focus + scroll on mount. */
  highlightGuideId?: string | null
}

const TILES: TriageTileMeta[] = [
  {
    guideId: 'password-reset',
    labelKey: 'techSupport.triage.resetPassword',
    label: 'Reset my password',
    icon: <KeyRound aria-hidden="true" className="w-8 h-8" />,
  },
  {
    guideId: 'library-card',
    labelKey: 'techSupport.triage.cantLogIn',
    label: "Can't log in / library card",
    icon: <CreditCard aria-hidden="true" className="w-8 h-8" />,
  },
  {
    guideId: 'check-print-jobs',
    labelKey: 'techSupport.triage.printingNotWorking',
    label: "Printing isn't working",
    icon: <Printer aria-hidden="true" className="w-8 h-8" />,
  },
  {
    guideId: 'wifi-troubleshooting',
    labelKey: 'techSupport.triage.wifiWontConnect',
    label: "WiFi won't connect",
    icon: <Wifi aria-hidden="true" className="w-8 h-8" />,
  },
]

export default function TriageTiles({
  highlightGuideId,
}: TriageTilesProps = {}): React.ReactElement {
  const { t } = useTranslation()
  // Resolve hrefs at render time so a stale tile id surfaces loudly
  // (filtered out) rather than producing a broken link.
  const resolved = TILES.map((tile) => {
    const guide = findGuide(tile.guideId)
    return guide ? { ...tile, href: guide.href } : null
  }).filter((tile): tile is TriageTileMeta & { href: string } => tile !== null)

  const tileRefs = useRef<Record<string, HTMLAnchorElement | null>>({})

  useEffect(() => {
    if (!highlightGuideId) return
    const target = tileRefs.current[highlightGuideId]
    if (!target) return
    // jsdom doesn't implement scrollIntoView — feature-check so the
    // focus path still works under tests.
    if (typeof target.scrollIntoView === 'function') {
      target.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
    target.focus()
  }, [highlightGuideId])

  return (
    <section
      aria-labelledby="tech-triage-heading"
      className="mb-8"
      data-testid="tech-triage-tiles"
    >
      <h2 id="tech-triage-heading" className="sr-only">
        {t('techSupport.quickFixesHeading', 'Quick fixes for common problems')}
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {resolved.map((tile) => (
          <Link
            key={tile.guideId}
            to={tile.href}
            data-guide-id={tile.guideId}
            ref={(el) => {
              tileRefs.current[tile.guideId] = el
            }}
            className="group flex items-center gap-4 min-h-[88px] p-4 bg-lsc-white dark:bg-earth-800 border-2 border-lsc-rose/30 dark:border-lsc-rose/40 rounded-xl hover:border-lsc-rose hover:bg-lsc-rose/5 dark:hover:bg-lsc-rose/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 transition-colors"
          >
            <span className="flex-shrink-0 inline-flex items-center justify-center w-12 h-12 rounded-xl bg-lsc-rose/10 dark:bg-lsc-rose/20 text-lsc-rose dark:text-lsc-rose-light group-hover:bg-lsc-rose/20 dark:group-hover:bg-lsc-rose/30">
              {tile.icon}
            </span>
            <span className="font-serif font-semibold text-base sm:text-lg text-lsc-dark dark:text-earth-50">
              {t(tile.labelKey, tile.label)}
            </span>
          </Link>
        ))}
      </div>
    </section>
  )
}
