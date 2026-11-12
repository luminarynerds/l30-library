/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { useTranslation } from '@/i18n'
import { MAGNETIC_HOVER } from '../motion'

export default function ReadyToTrySection(): React.ReactElement {
  const { t } = useTranslation()
  return (
    <section className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-6 text-center">
      <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
        {t('aITools.readyHeading', 'Ready to Try It?')}
      </h2>
      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
        {t(
          'aITools.readyBody',
          "Come to the library and ask any staff member. We'll show you around.",
        )}
      </p>
      <div className="flex flex-col items-center gap-3">
        <Link
          to="/branches"
          className={clsx(
            'inline-flex items-center justify-center px-6 py-3 bg-lsc-rose text-white rounded-xl font-semibold hover:bg-lsc-rose/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2',
            MAGNETIC_HOVER,
          )}
        >
          {t('aITools.comeInAndTry', 'Come in and try it')}
          <ArrowRight aria-hidden="true" className="w-5 h-5 ml-2" />
        </Link>
        <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60">
          {t('aITools.orExploreDigital', 'Or explore our')}{' '}
          <Link
            to="/digital"
            className="font-medium text-lsc-rose dark:text-lsc-rose-light hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 rounded"
          >
            {t('aITools.allDigitalResources', 'all digital resources')}
          </Link>
        </p>
      </div>
    </section>
  )
}
