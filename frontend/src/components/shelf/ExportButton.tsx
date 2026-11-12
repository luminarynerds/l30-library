/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Download } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'
import { useUnifiedAccessibility } from '@/features/accessibility/hooks/useUnifiedAccessibility'
import { downloadShelfExport } from '@/api/domains/content/reading-goals-api'
import { clsx } from '@/utils/helpers'
import { t } from '@/i18n'

export default function ExportButton() {
  const { token } = useAuth()
  const { isFeatureEnabled } = useOrganizationFeatures()
  const { announceToScreenReader } = useUnifiedAccessibility()
  const [format, setFormat] = useState<'json' | 'csv'>('csv')

  if (!isFeatureEnabled('shelf_data_export_enabled')) return null

  const handleExport = () => {
    if (!token) return
    downloadShelfExport(token, format)
    announceToScreenReader(`Downloading shelf data as ${format.toUpperCase()}`)
  }

  return (
    <div className="flex items-center gap-3 pt-6 mt-6 border-t border-lsc-border/40 dark:border-earth-700/60">
      <select
        value={format}
        onChange={(e) => setFormat(e.target.value as 'json' | 'csv')}
        aria-label={t('aria.shelf.exportFormat')}
        className="text-sm rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream px-3 py-2 focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
      >
        <option value="csv">CSV</option>
        <option value="json">JSON</option>
      </select>
      <button
        onClick={handleExport}
        className={clsx(
          'inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors',
          'text-lsc-dark/70 dark:text-lsc-cream/60 border border-lsc-border dark:border-earth-600',
          'hover:text-lsc-dark dark:hover:text-lsc-cream hover:bg-earth-50 dark:hover:bg-earth-700',
        )}
      >
        <Download className="w-4 h-4" aria-hidden="true" />
        Export My Data
      </button>
    </div>
  )
}
