/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { Leaf } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useTranslation } from '../i18n/I18nContext'

const CO2_GRAMS_PER_BYTE = 0.00000040014

export function FooterCarbonBadge() {
  const { t } = useTranslation()
  const [co2Grams, setCo2Grams] = useState<number | null>(null)

  useEffect(() => {
    const calculate = () => {
      try {
        const entries = performance.getEntriesByType('resource') as PerformanceResourceTiming[]
        const navEntry = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined

        let totalBytes = 0
        for (const entry of entries) {
          if (entry.transferSize > 0) {
            totalBytes += entry.transferSize
          }
        }
        if (navEntry?.transferSize) {
          totalBytes += navEntry.transferSize
        }
        if (totalBytes > 0) {
          setCo2Grams(totalBytes * CO2_GRAMS_PER_BYTE)
        }
      } catch {
        // Performance API not available
      }
    }

    const timer = setTimeout(calculate, 2000)
    return () => clearTimeout(timer)
  }, [])

  if (co2Grams === null) return null

  const display = co2Grams < 0.1
    ? `~${(co2Grams * 1000).toFixed(0)}mg`
    : `~${co2Grams.toFixed(2)}g`

  return (
    <Link
      to="/sustainability"
      className="inline-flex items-center gap-1.5 text-xs text-earth-300 hover:text-status-success-400 transition-colors"
      title={t('footer.carbonBadgeTitle', "This page's estimated carbon footprint. Click to learn more.")}
    >
      <Leaf className="w-3 h-3" aria-hidden="true" />
      <span>{display} CO<sub>2</sub></span>
    </Link>
  )
}
