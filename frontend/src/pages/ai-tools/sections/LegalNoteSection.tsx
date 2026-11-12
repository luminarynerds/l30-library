/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { Scale } from 'lucide-react'
import { useTranslation } from '@/i18n'

export default function LegalNoteSection(): React.ReactElement {
  const { t } = useTranslation()
  return (
    <div className="bg-lsc-cream dark:bg-lsc-dark/20 border border-lsc-border dark:border-earth-700 rounded-xl p-4 flex items-start gap-3">
      <Scale aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 flex-shrink-0 mt-0.5" />
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        {t(
          'aITools.legalNote',
          'AI tools are statistical models, not experts. Content may not be copyrightable under current US guidance. The patron-facing AI tools on this page run locally on library hardware, so no AI vendor terms apply to them. The staff and admin tools listed in the data-flow matrix above use Anthropic or OpenAI; we follow each vendor\'s Terms of Service and COPPA where it applies.',
        )}{' '}
        <Link
          to="/ai/legal"
          className="text-lsc-rose dark:text-lsc-rose-light hover:underline font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 rounded"
        >
          {t('aITools.legalNoteLink', 'Full legal disclaimers →')}
        </Link>
      </p>
    </div>
  )
}
