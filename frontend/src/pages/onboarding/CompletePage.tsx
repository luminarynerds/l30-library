/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  PartyPopper, Search, Bookmark, Calendar, CreditCard,
  CheckCircle2, ArrowRight, BookOpen,
} from 'lucide-react'
import { patronOnboardingApi } from '@/api/domains/patron/patron-onboarding-api'
import { useAuth } from '@/contexts/AuthContext'
import { useOnboarding } from '@/contexts/OnboardingContext'
import { useBranding } from '@/contexts/BrandingContext'
import { t } from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

const GENRE_LABELS: Record<string, string> = {
  fiction: 'Fiction',
  mystery: 'Mystery & Thriller',
  'sci-fi': 'Sci-Fi & Fantasy',
  romance: 'Romance',
  biography: 'Biography & Memoir',
  history: 'History',
  children: "Children's",
  art: 'Art & Design',
  travel: 'Travel & Culture',
  science: 'Science & Nature',
  adventure: 'Action & Adventure',
  music: 'Music & Film',
}

const CHECKLIST_ITEMS = [
  { id: 'search', icon: Search, label: 'Search the catalog', route: '/catalog' },
  { id: 'hold', icon: Bookmark, label: 'Place your first hold', route: '/catalog' },
  { id: 'event', icon: Calendar, label: 'Join a program or event', route: '/events' },
]

export default function CompletePage(): React.ReactElement {
  const navigate = useNavigate()
  const branding = useBranding()
  const { user } = useAuth()
  const { completeWelcomeWizard } = useOnboarding()
  const [completed, setCompleted] = useState(false)

  const { data: status } = useQuery({
    queryKey: ['onboarding-status'],
    queryFn: () => patronOnboardingApi.getStatus(),
  })

  useEffect(() => {
    if (completed) return
    // eslint-disable-next-line react-hooks/set-state-in-effect -- run-once guard for one-shot completion side-effect
    setCompleted(true)
    const markDone = async () => {
      try {
        await patronOnboardingApi.completeStep(5)
        completeWelcomeWizard()
      } catch {
        // Non-blocking
      }
    }
    markDone()
  }, [completed, completeWelcomeWizard])

  const genres = status?.preferred_genres ?? []
  const displayGenres = genres.slice(0, 4).map((g) => GENRE_LABELS[g] || g)

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark">
      <PageContainer width="form" className="py-8 space-y-8">
        {/* Success header */}
        <div className="text-center space-y-4">
          <div className="mx-auto w-16 h-16 rounded-full bg-sage-100 dark:bg-sage-900 flex items-center justify-center">
            <PartyPopper className="w-8 h-8 text-sage-600 dark:text-sage-400" aria-hidden="true" />
          </div>
          <h1 className="font-serif text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
            You&apos;re all set{user?.first_name ? `, ${user.first_name}` : ''}!
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Your library experience is personalized and ready to go.
          </p>
        </div>

        {/* Digital library card preview */}
        <div className="bg-gradient-to-br from-lsc-brown to-lsc-dark rounded-xl p-6 text-white shadow-lg">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs text-white/60 uppercase tracking-wider">{branding.library_name}</p>
              <p className="text-xl font-serif font-bold mt-1">
                {user?.first_name} {user?.last_name}
              </p>
            </div>
            <CreditCard className="w-8 h-8 text-white/40" aria-hidden="true" />
          </div>
          <div className="mt-4 flex items-end justify-between">
            <div>
              <p className="text-xs text-white/60">Card Number</p>
              <p className="font-mono text-sm">{user?.library_card || 'Pending'}</p>
            </div>
            {status?.home_branch_name && (
              <div className="text-right">
                <p className="text-xs text-white/60">Home Branch</p>
                <p className="text-sm">{status.home_branch_name}</p>
              </div>
            )}
          </div>
        </div>

        {/* Personalized recommendations based on genres */}
        {displayGenres.length > 0 && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
            <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
              Recommended for you
            </h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
              Based on your interest in {displayGenres.join(', ')}:
            </p>
            <div className="grid grid-cols-2 gap-2">
              {displayGenres.map((genre) => (
                <Link
                  key={genre}
                  to={`/catalog?genre=${encodeURIComponent(genre)}`}
                  className="flex items-center gap-2 p-2.5 rounded-lg bg-lsc-cream dark:bg-lsc-brown hover:bg-lsc-rose/10 dark:hover:bg-lsc-rose/10 transition-colors"
                >
                  <BookOpen className="w-4 h-4 text-lsc-rose" aria-hidden="true" />
                  <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                    Browse {genre}
                  </span>
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Things to try checklist */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
          <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
            Things to try
          </h2>
          <div className="space-y-2">
            {CHECKLIST_ITEMS.map((item) => (
              <Link
                key={item.id}
                to={item.route}
                className="flex items-center gap-3 p-3 rounded-lg hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors group"
              >
                <div className="w-8 h-8 rounded-full bg-lsc-cream dark:bg-lsc-brown flex items-center justify-center group-hover:bg-lsc-rose/10">
                  <item.icon className="w-4 h-4 text-lsc-rose" aria-hidden="true" />
                </div>
                <span className="flex-1 text-sm font-medium text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose transition-colors">
                  {item.label}
                </span>
                <ArrowRight className="w-4 h-4 text-lsc-dark/30 dark:text-lsc-cream/60 group-hover:text-lsc-rose transition-colors" aria-hidden="true" />
              </Link>
            ))}
          </div>
        </div>

        {/* Reading goal */}
        {status?.reading_goal && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
            <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2 flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-sage-600" aria-hidden="true" />
              Reading Goal
            </h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {status.reading_goal === 'casual' && 'Casual reader - 1-2 books per month'}
              {status.reading_goal === 'regular' && 'Regular reader - 3-4 books per month'}
              {status.reading_goal === 'avid' && 'Avid reader - 5+ books per month'}
            </p>
            <div className="mt-3 w-full h-2 bg-lsc-cream dark:bg-lsc-brown rounded-full">
              <div className="h-2 bg-lsc-rose rounded-full w-0" />
            </div>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              0 of {status.reading_goal === 'casual' ? '2' : status.reading_goal === 'regular' ? '4' : '5'} this month
            </p>
          </div>
        )}

        {/* Go to homepage */}
        <div className="text-center pt-4">
          <button
            onClick={() => navigate('/')}
            className="inline-flex items-center gap-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-semibold py-3 px-8 rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-lsc-dark"
          >
            Go to homepage
            <ArrowRight className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        {/* Progress dots */}
        <div className="flex items-center justify-center gap-2" aria-label={t('aria.complete.step5Of5Complete')}>
          <div className="w-2 h-2 rounded-full bg-lsc-rose/40" />
          <div className="w-2 h-2 rounded-full bg-lsc-rose/40" />
          <div className="w-2 h-2 rounded-full bg-lsc-rose/40" />
          <div className="w-2 h-2 rounded-full bg-lsc-rose/40" />
          <div className="w-2.5 h-2.5 rounded-full bg-lsc-rose" />
        </div>
      </PageContainer>
    </div>
  )
}