/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Languages } from 'lucide-react'
import { useTranslation } from '@/i18n/I18nContext'

// ISO 639-2/B (3-letter) to BCP-47 (2-letter) for Intl.DisplayNames.
// Mirrors the table in CatalogFilterSidebar; kept inline to avoid a cross-file
// dependency churn on a sibling that already works.
const ISO_639_2B_TO_BCP47: Record<string, string> = {
  eng: 'en', spa: 'es', fre: 'fr', ger: 'de', chi: 'zh', ara: 'ar',
  rus: 'ru', jpn: 'ja', kor: 'ko', por: 'pt', ita: 'it', vie: 'vi',
}

interface ZeroResultsLanguageCTAProps {
  languageCode: string
}

export default function ZeroResultsLanguageCTA({ languageCode }: ZeroResultsLanguageCTAProps): React.ReactElement | null {
  const { t, language: uiLanguage } = useTranslation()

  const displayName = useMemo(() => {
    const bcp47 = ISO_639_2B_TO_BCP47[languageCode] ?? languageCode
    try {
      const dn = new Intl.DisplayNames([uiLanguage], { type: 'language' })
      const name = dn.of(bcp47)
      return name && name !== bcp47 ? name : languageCode
    } catch {
      return languageCode
    }
  }, [languageCode, uiLanguage])

  if (!languageCode) return null

  return (
    <div className="mt-2 mb-6 pt-6 border-t border-lsc-border dark:border-earth-700 max-w-md mx-auto">
      <p className="text-sm mb-3 font-medium text-lsc-dark dark:text-lsc-cream">
        {t('catalog.zeroResults.translationCta.heading', { language: displayName })}
      </p>
      <Link
        to="/contact"
        aria-label={t('catalog.zeroResults.translationCta.button', { language: displayName })}
        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-forest-500/40 hover:border-forest-500 hover:bg-forest-500/10 text-lsc-dark dark:text-lsc-cream font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-forest-500 focus:ring-offset-2 dark:focus:ring-offset-lsc-dark"
      >
        <Languages aria-hidden="true" className="w-4 h-4" />
        <span>{t('catalog.zeroResults.translationCta.button', { language: displayName })}</span>
      </Link>
    </div>
  )
}
