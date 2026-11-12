/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useTranslation } from '@/i18n'

export default function PlainLanguageSummary(): React.ReactElement {
  const { t } = useTranslation()
  return (
    <section
      aria-labelledby="ai-plain-summary-heading"
      className="mb-8 p-5 sm:p-6 rounded-xl bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700"
    >
      <h2
        id="ai-plain-summary-heading"
        className="text-base font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2"
      >
        {t('aITools.plainSummaryHeading', 'In plain language')}
      </h2>
      <p className="text-base text-lsc-dark dark:text-lsc-cream leading-relaxed">
        {t(
          'aITools.plainSummaryBody',
          'These are free tools anyone with a library card can use. They help you find books, write a letter, or ask a quick question. They run on a server in our back room. Nothing you type leaves the building. We do not save your questions, and your session is wiped when you close the tab. Prefer to talk to a person? Call us or come in. Staff is always the first choice.',
        )}
      </p>
    </section>
  )
}
