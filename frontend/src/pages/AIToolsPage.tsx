/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { ArrowRight, Cpu } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import StandardPageLayout from '@/components/StandardPageLayout'
import { useTranslation } from '@/i18n'
import { aiTools } from './ai-tools/data/ai-tools-data'
import { useExpandedSet } from './ai-tools/useExpandedSet'
import { MAGNETIC_HOVER } from './ai-tools/motion'
import TableOfContents, { type TocEntry } from './ai-tools/components/TableOfContents'
import PlainLanguageSummary from './ai-tools/sections/PlainLanguageSummary'
import TryOneNowStrip from './ai-tools/sections/TryOneNowStrip'
import AIPromiseSection from './ai-tools/sections/AIPromiseSection'
import AllToolsSection from './ai-tools/sections/AllToolsSection'
import PreferHumanSection from './ai-tools/sections/PreferHumanSection'
import FAQSection from './ai-tools/sections/FAQSection'
import CrossLinks from './ai-tools/sections/CrossLinks'
import ReadyToTrySection from './ai-tools/sections/ReadyToTrySection'

export default function AIToolsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { expanded, toggle } = useExpandedSet('ai-tools:expanded')

  // Patron-first TOC. The long-form philosophy/receipts list lives at /ai/how-it-works.
  const tocEntries: TocEntry[] = [
    { id: 'promise', label: t('aITools.tocPromise', 'Our promise') },
    { id: 'tools', label: t('aITools.tocTools', 'All tools') },
    { id: 'faq', label: t('aITools.tocFaq', 'FAQ') },
  ]

  return (
    <StandardPageLayout
      title={t('aITools.aiAtTheLibrary', 'AI at the Library')}
      subtitle={t(
        'aITools.heroSubtitle',
        'Runs on a server in our back room. Nothing leaves the building. Built by Stevie, our systems librarian, so Marlene can spend her thirty years of reader\'s advisory on the patrons who need it.',
      )}
      icon={Cpu}
    >
      {/* Plain-language orientation block. */}
      <PlainLanguageSummary />

      {/* Two patron-ready, from-home tools, given prominent launch cards. */}
      <TryOneNowStrip />

      <div className="lg:grid lg:grid-cols-[1fr_14rem] lg:gap-10">
        <div className="space-y-8 lg:order-1 min-w-0">
          {/* Patron flow: what's available, how to try it, who to ask. */}
          <AIPromiseSection />
          <AllToolsSection tools={aiTools} expanded={expanded} onToggle={toggle} />
          <PreferHumanSection />
          <FAQSection />
          <CrossLinks />

          {/* Link card replacing the old in-page "Want to know how it works?" divider.
              Routes curious readers to the long-form philosophy + receipts page. */}
          <Link
            to="/ai/how-it-works"
            className={clsx(
              'group flex items-center gap-4 p-5 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2',
              MAGNETIC_HOVER,
            )}
          >
            <div className="flex-1">
              <p className="text-base font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                {t('aITools.deepDiveDivider', 'Want to know how it works?')}
              </p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                {t(
                  'aITools.howItWorksCtaSubtitle',
                  'The long version: policy, the eight questions we ask, the hardware, and what we got wrong.',
                )}
              </p>
            </div>
            <ArrowRight
              aria-hidden="true"
              className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light flex-shrink-0"
            />
          </Link>

          <ReadyToTrySection />
        </div>

        <aside className="lg:order-2">
          <TableOfContents entries={tocEntries} />
        </aside>
      </div>
    </StandardPageLayout>
  )
}
