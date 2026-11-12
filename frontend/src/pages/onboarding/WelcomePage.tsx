/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useNavigate } from 'react-router-dom'
import { BookOpen, Search, Bookmark, Calendar, ArrowRight } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useOnboarding } from '@/contexts/OnboardingContext'
import { patronOnboardingApi } from '@/api/domains/patron/patron-onboarding-api'
import { useBranding } from '@/contexts/BrandingContext'
import { t } from '@/i18n'

const VALUE_PROPS = [
  { icon: Search, label: 'Search our entire catalog' },
  { icon: Bookmark, label: 'Hold & borrow with ease' },
  { icon: BookOpen, label: 'Track your reading journey' },
  { icon: Calendar, label: 'Discover events & programs' },
]

export default function WelcomePage(): React.ReactElement {
  const navigate = useNavigate()
  const { user } = useAuth()
  const branding = useBranding()
  const { skipWelcomeWizard } = useOnboarding()

  const handleContinue = async () => {
    try {
      await patronOnboardingApi.completeStep(1)
    } catch {
      // Continue even if tracking fails
    }
    navigate('/onboarding/preferences')
  }

  const handleSkip = async () => {
    try {
      await patronOnboardingApi.skip(1)
    } catch {
      // Continue even if tracking fails
    }
    skipWelcomeWizard()
    navigate('/catalog')
  }

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark flex flex-col">
      {/* Hero area */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-12">
        <div className="max-w-lg w-full text-center space-y-8">
          {/* Library icon */}
          <div className="mx-auto w-20 h-20 rounded-xl bg-lsc-rose/10 dark:bg-lsc-rose/20 flex items-center justify-center">
            <BookOpen className="w-10 h-10 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
          </div>

          {/* Welcome heading */}
          <div className="space-y-3">
            <h1 className="font-serif text-3xl md:text-4xl font-bold text-lsc-dark dark:text-lsc-cream">
              Welcome{user?.first_name ? `, ${user.first_name}` : ''}!
            </h1>
            <p className="text-lg text-lsc-dark/70 dark:text-lsc-cream/70">
              Welcome to {branding.library_name}
            </p>
          </div>

          {/* Value propositions */}
          <div className="grid grid-cols-2 gap-3">
            {VALUE_PROPS.map((prop) => (
              <div
                key={prop.label}
                className="flex items-center gap-3 bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700 text-left"
              >
                <div className="w-9 h-9 rounded-lg bg-lsc-cream dark:bg-lsc-brown flex items-center justify-center flex-shrink-0">
                  <prop.icon className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
                </div>
                <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{prop.label}</span>
              </div>
            ))}
          </div>

          {/* CTA */}
          <div className="space-y-3 pt-4">
            <button
              onClick={handleContinue}
              className="w-full flex items-center justify-center gap-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-semibold py-3 px-6 rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-lsc-dark"
            >
              Let&apos;s set up your experience
              <ArrowRight className="w-5 h-5" aria-hidden="true" />
            </button>
            <button
              onClick={handleSkip}
              className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light transition-colors underline decoration-lsc-dark/20 dark:decoration-lsc-cream/20 hover:decoration-lsc-rose"
            >
              Skip to homepage
            </button>
          </div>

          {/* Progress dots */}
          <div className="flex items-center justify-center gap-2 pt-2" aria-label={t('aria.welcome.step1Of5')}>
            <div className="w-2.5 h-2.5 rounded-full bg-lsc-rose" />
            <div className="w-2 h-2 rounded-full bg-lsc-dark/20 dark:bg-lsc-cream/20" />
            <div className="w-2 h-2 rounded-full bg-lsc-dark/20 dark:bg-lsc-cream/20" />
            <div className="w-2 h-2 rounded-full bg-lsc-dark/20 dark:bg-lsc-cream/20" />
            <div className="w-2 h-2 rounded-full bg-lsc-dark/20 dark:bg-lsc-cream/20" />
          </div>
        </div>
      </div>
    </div>
  )
}