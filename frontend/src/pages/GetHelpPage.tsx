/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from "react-router-dom"
import { useOrganizationFeatures } from "@/contexts/OrganizationFeaturesContext"
import {
  BookOpen,
  Bot,
  MessageCircle,
  Monitor,
  Scale,
  Phone,
  Users,
  HelpCircle,
  LifeBuoy,
} from "lucide-react"
import StandardPageLayout from "@/components/StandardPageLayout"
import { useTranslation } from "@/i18n/I18nContext"
import { usePageTitle } from "@/hooks/usePageTitle"
import SeasonalFAQBanner from "@/components/SeasonalFAQBanner"
import EscalationModal from "@/components/EscalationModal"

interface HelpCard {
  title: string
  description: string
  to: string
  icon: React.ElementType
  featureFlag?: string
}

export default function GetHelpPage(): React.ReactElement {
  const { isFeatureEnabled } = useOrganizationFeatures()
  const { t } = useTranslation()
  usePageTitle(t('getHelp.pageTitle'))

  const helpCards: HelpCard[] = [
    {
      title: 'How-to Guides',
      description: 'Step-by-step visual guides for printing, WiFi, library cards, password reset, and more.',
      to: '/guides',
      icon: BookOpen,
    },
    {
      title: 'Knowledge Base',
      description: 'Searchable answers to common questions about the library, accounts, and services.',
      to: '/help',
      icon: HelpCircle,
    },
    {
      title: t('getHelp.askLibrarian.title'),
      description: t('getHelp.askLibrarian.description'),
      to: "/ask-librarian",
      icon: MessageCircle,
    },
    {
      title: t('getHelp.faqChat.title'),
      description: t('getHelp.faqChat.description'),
      to: "/help/chat",
      icon: Bot,
      featureFlag: "faq_chatbot_enabled",
    },
    {
      title: t('getHelp.techSupport.title'),
      description: t('getHelp.techSupport.description'),
      to: "/tech",
      icon: Monitor,
    },
    {
      title: t('getHelp.legalHelp.title'),
      description: t('getHelp.legalHelp.description'),
      to: "/legal",
      icon: Scale,
    },
    {
      title: t('getHelp.contactUs.title'),
      description: t('getHelp.contactUs.description'),
      to: "/contact",
      icon: Phone,
    },
    {
      title: t('getHelp.communityResources.title'),
      description: t('getHelp.communityResources.description'),
      to: "/help-guide",
      icon: Users,
    },
  ]
  const visibleCards = helpCards.filter(c => !c.featureFlag || isFeatureEnabled(c.featureFlag as any))

  return (
    <StandardPageLayout
      title={t('getHelp.pageTitle')}
      subtitle={t('getHelp.pageSubtitle')}
      icon={HelpCircle}
    >
      <SeasonalFAQBanner />
      <section aria-labelledby="help-cards-heading">
        <h2 id="help-cards-heading" className="sr-only">
          Support options
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {visibleCards.map(({ title, description, to, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className="group flex flex-col gap-4 p-6 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 hover:border-lsc-rose/40 dark:hover:border-lsc-rose/40 hover:shadow-md transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
            >
              <div className="w-12 h-12 rounded-xl bg-lsc-rose/10 dark:bg-lsc-rose/20 flex items-center justify-center flex-shrink-0">
                <Icon
                  className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light"
                  aria-hidden="true"
                />
              </div>
              <div>
                <h3 className="font-serif text-lg font-semibold text-earth-700 dark:text-lsc-cream group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light transition-colors">
                  {title}
                </h3>
                <p className="mt-1 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm leading-relaxed">
                  {description}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </section>

      <section
        aria-labelledby="submit-ticket-heading"
        className="mt-10 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-cream dark:bg-earth-800 p-6"
      >
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-lsc-rose/10 dark:bg-lsc-rose/20 flex items-center justify-center flex-shrink-0">
            <LifeBuoy
              className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light"
              aria-hidden="true"
            />
          </div>
          <div className="flex-1">
            <h2
              id="submit-ticket-heading"
              className="font-serif text-lg font-semibold text-earth-700 dark:text-lsc-cream"
            >
              {t('getHelp.supportTicket.heading')}
            </h2>
            <p className="mt-1 mb-4 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm leading-relaxed">
              {t('getHelp.supportTicket.description')}
            </p>
            <EscalationModal
              guideTitle={t('getHelp.supportTicket.requestTitle')}
              stepNumber={1}
              totalSteps={1}
            />
          </div>
        </div>
      </section>
    </StandardPageLayout>
  )
}
