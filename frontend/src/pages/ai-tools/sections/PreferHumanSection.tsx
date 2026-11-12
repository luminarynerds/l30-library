/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { ArrowRight, Users } from 'lucide-react'
import { useTranslation } from '@/i18n'

export default function PreferHumanSection(): React.ReactElement {
  const { t } = useTranslation()
  return (
    <section className="bg-lsc-cream dark:bg-lsc-dark/20 border border-lsc-border dark:border-earth-700 rounded-xl p-6">
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-xl bg-lsc-white dark:bg-earth-800 flex items-center justify-center flex-shrink-0">
          <Users aria-hidden="true" className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
        </div>
        <div>
          <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
            {t('aITools.preferAHuman', 'Prefer a Human?')}
          </h2>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
            {t('aITools.preferAHumanBody', "Have questions about AI tools? Our reference staff can help — reach out and we'll connect you with someone who can walk you through it.")}
          </p>
          <Link
            to="/contact"
            className="inline-flex items-center gap-1 text-sm font-medium text-lsc-rose dark:text-lsc-rose-light hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 rounded"
          >
            {t('aITools.contactUs', 'Contact us')}
            <ArrowRight aria-hidden="true" className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </section>
  )
}
