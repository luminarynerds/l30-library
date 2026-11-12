/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Search, Bookmark, User, Calendar,
  ArrowRight, ArrowLeft, ExternalLink,
} from 'lucide-react'
import { patronOnboardingApi } from '@/api/domains/patron/patron-onboarding-api'
import { useOnboarding } from '@/contexts/OnboardingContext'
import { t } from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

const TOUR_PANELS = [
  {
    id: 'search',
    icon: Search,
    title: 'Search',
    headline: 'Find anything in our catalog',
    description:
      'Search for books, eBooks, audiobooks, movies, and more. Use filters to narrow down results by format, availability, and genre.',
    tryItLabel: 'Try searching',
    tryItRoute: '/catalog',
  },
  {
    id: 'holds',
    icon: Bookmark,
    title: 'Holds',
    headline: 'Reserve items and pick up at your branch',
    description:
      "Place a hold on any item and we'll notify you when it's ready for pickup at your chosen branch. You can manage all your holds from your account.",
    tryItLabel: 'Browse to hold',
    tryItRoute: '/catalog',
  },
  {
    id: 'account',
    icon: User,
    title: 'Account',
    headline: 'Track your checkouts and reading history',
    description:
      'View your current checkouts, due dates, fines, and reading history all in one place. Set up notifications so you never miss a due date.',
    tryItLabel: 'View account',
    tryItRoute: '/account',
  },
  {
    id: 'events',
    icon: Calendar,
    title: 'Events',
    headline: 'Discover programs and events',
    description:
      'From book clubs to maker workshops, storytimes to tech classes - find programs for all ages at your local branch.',
    tryItLabel: 'See events',
    tryItRoute: '/events',
  },
]

export default function TourPage(): React.ReactElement {
  const navigate = useNavigate()
  const { skipWelcomeWizard } = useOnboarding()
  const [activePanel, setActivePanel] = useState(0)

  const handleContinue = async () => {
    try {
      await patronOnboardingApi.completeStep(4)
    } catch {
      // Continue even if tracking fails
    }
    navigate('/onboarding/complete')
  }

  const handleSkip = async () => {
    try {
      await patronOnboardingApi.skip(4)
    } catch {
      // ignore
    }
    skipWelcomeWizard()
    navigate('/catalog')
  }

  const panel = TOUR_PANELS[activePanel]!

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark">
      <PageContainer width="form" className="py-8 space-y-8">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="font-serif text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
            Quick Tour
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Here&apos;s what you can do with your library account.
          </p>
        </div>

        {/* Panel tabs */}
        <div className="flex gap-2">
          {TOUR_PANELS.map((p, i) => (
            <button
              key={p.id}
              onClick={() => setActivePanel(i)}
              className={`flex-1 flex flex-col items-center gap-1 py-3 px-2 rounded-xl border-2 transition-all ${
                i === activePanel
                  ? 'border-lsc-rose bg-lsc-rose/5 dark:bg-lsc-rose/10'
                  : 'border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 hover:border-lsc-rose/50'
              }`}
              aria-pressed={i === activePanel}
            >
              <p.icon className={`w-5 h-5 ${i === activePanel ? 'text-lsc-rose' : 'text-lsc-dark/70 dark:text-lsc-cream/70'}`} aria-hidden="true" />
              <span className={`text-xs font-medium ${i === activePanel ? 'text-lsc-rose' : 'text-lsc-dark/70 dark:text-lsc-cream/70'}`}>
                {p.title}
              </span>
            </button>
          ))}
        </div>

        {/* Active panel content */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6 space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-lsc-rose/10 dark:bg-lsc-rose/20 flex items-center justify-center">
              <panel.icon className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
            </div>
            <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">
              {panel.headline}
            </h2>
          </div>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed">
            {panel.description}
          </p>
          <button
            onClick={() => navigate(panel.tryItRoute)}
            className="inline-flex items-center gap-2 text-sm font-semibold text-lsc-rose hover:text-lsc-rose/80 dark:text-lsc-rose-light transition-colors"
          >
            <ExternalLink className="w-4 h-4" aria-hidden="true" />
            {panel.tryItLabel}
          </button>
        </div>

        {/* Panel navigation dots */}
        <div className="flex items-center justify-center gap-2">
          {TOUR_PANELS.map((_, i) => (
            <button
              key={i}
              onClick={() => setActivePanel(i)}
              className={`rounded-full transition-all ${
                i === activePanel ? 'w-6 h-2 bg-lsc-rose' : 'w-2 h-2 bg-lsc-dark/20 dark:bg-lsc-cream/20 hover:bg-lsc-rose/50'
              }`}
              aria-label={`Go to panel ${i + 1}`}
            />
          ))}
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between pt-4">
          <button
            onClick={() => navigate('/onboarding/branch')}
            className="flex items-center gap-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose transition-colors"
          >
            <ArrowLeft className="w-4 h-4" aria-hidden="true" />
            Back
          </button>
          <div className="flex items-center gap-3">
            <button
              onClick={handleSkip}
              className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose transition-colors underline"
            >
              Skip to homepage
            </button>
            <button
              onClick={handleContinue}
              className="flex items-center gap-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-semibold py-2.5 px-5 rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-lsc-dark"
            >
              Continue
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Progress dots */}
        <div className="flex items-center justify-center gap-2" aria-label={t('aria.tour.step4Of5')}>
          <div className="w-2 h-2 rounded-full bg-lsc-rose/40" />
          <div className="w-2 h-2 rounded-full bg-lsc-rose/40" />
          <div className="w-2 h-2 rounded-full bg-lsc-rose/40" />
          <div className="w-2.5 h-2.5 rounded-full bg-lsc-rose" />
          <div className="w-2 h-2 rounded-full bg-lsc-dark/20 dark:bg-lsc-cream/20" />
        </div>
      </PageContainer>
    </div>
  )
}