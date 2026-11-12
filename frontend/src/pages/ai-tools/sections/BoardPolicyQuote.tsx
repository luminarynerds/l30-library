/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useTranslation } from '@/i18n'

export default function BoardPolicyQuote(): React.ReactElement {
  const { t } = useTranslation()
  return (
    <blockquote className="border-l-4 border-lsc-rose pl-6 py-4">
      <p className="text-lg font-serif italic text-lsc-dark dark:text-lsc-cream">
        {t('aITools.boardPolicyQuote', '"All AI systems deployed by the library shall operate with full transparency. Patrons have the right to understand how automated systems affect their library experience."')}
      </p>
      <footer className="mt-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        {t('aITools.boardPolicyAttribution', '— Board Policy 2026-07.')} {t('aITools.passedUnanimouslyEvenHaroldVoted', 'Passed unanimously. Even Harold voted yes.')}
      </footer>
    </blockquote>
  )
}
