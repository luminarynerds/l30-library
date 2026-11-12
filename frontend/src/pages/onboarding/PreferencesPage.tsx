/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BookOpen, Wand2, Rocket, Heart, User, History,
  Baby, Palette, Globe, FlaskConical, Swords, Music,
  Book, Headphones, Tablet, Newspaper,
  ArrowRight, ArrowLeft, Check,
} from 'lucide-react'
import { patronOnboardingApi } from '@/api/domains/patron/patron-onboarding-api'
import { useOnboarding } from '@/contexts/OnboardingContext'
import { t } from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

const GENRES = [
  { id: 'fiction', label: 'Fiction', icon: BookOpen },
  { id: 'mystery', label: 'Mystery & Thriller', icon: Wand2 },
  { id: 'sci-fi', label: 'Sci-Fi & Fantasy', icon: Rocket },
  { id: 'romance', label: 'Romance', icon: Heart },
  { id: 'biography', label: 'Biography & Memoir', icon: User },
  { id: 'history', label: 'History', icon: History },
  { id: 'children', label: "Children's", icon: Baby },
  { id: 'art', label: 'Art & Design', icon: Palette },
  { id: 'travel', label: 'Travel & Culture', icon: Globe },
  { id: 'science', label: 'Science & Nature', icon: FlaskConical },
  { id: 'adventure', label: 'Action & Adventure', icon: Swords },
  { id: 'music', label: 'Music & Film', icon: Music },
]

const FORMATS = [
  { id: 'book', label: 'Book', icon: Book },
  { id: 'ebook', label: 'eBook', icon: Tablet },
  { id: 'audiobook', label: 'Audiobook', icon: Headphones },
  { id: 'magazine', label: 'Magazine', icon: Newspaper },
]

const GOALS = [
  { id: 'casual', label: 'Casual', desc: '1-2 per month' },
  { id: 'regular', label: 'Regular', desc: '3-4 per month' },
  { id: 'avid', label: 'Avid', desc: '5+ per month' },
]

export default function PreferencesPage(): React.ReactElement {
  const navigate = useNavigate()
  const { skipWelcomeWizard } = useOnboarding()
  const [selectedGenres, setSelectedGenres] = useState<string[]>([])
  const [selectedFormats, setSelectedFormats] = useState<string[]>([])
  const [readingGoal, setReadingGoal] = useState<string>('')
  const [saving, setSaving] = useState(false)

  const toggleGenre = (id: string) => {
    setSelectedGenres((prev) =>
      prev.includes(id) ? prev.filter((g) => g !== id) : [...prev, id]
    )
  }

  const toggleFormat = (id: string) => {
    setSelectedFormats((prev) =>
      prev.includes(id) ? prev.filter((f) => f !== id) : [...prev, id]
    )
  }

  const canContinue = selectedGenres.length >= 3 && selectedFormats.length >= 1 && readingGoal

  const handleContinue = async () => {
    if (!canContinue) return
    setSaving(true)
    try {
      await patronOnboardingApi.savePreferences({
        preferred_genres: selectedGenres,
        preferred_formats: selectedFormats,
        reading_goal: readingGoal as 'casual' | 'regular' | 'avid',
      })
    } catch {
      // Continue even if save fails
    }
    setSaving(false)
    navigate('/onboarding/branch')
  }

  const handleSkip = async () => {
    try {
      await patronOnboardingApi.skip(2)
    } catch {
      // ignore
    }
    skipWelcomeWizard()
    navigate('/catalog')
  }

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark">
      <PageContainer width="form" className="py-8 space-y-8">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="font-serif text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
            What do you enjoy reading?
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Pick at least 3 genres so we can personalize your recommendations.
          </p>
        </div>

        {/* Genre selection */}
        <section>
          <h2 className="font-serif font-semibold text-lg text-lsc-dark dark:text-lsc-cream mb-3">
            Genres <span className="text-sm font-normal text-lsc-dark/70 dark:text-lsc-cream/70">({selectedGenres.length} selected, 3 min)</span>
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {GENRES.map((genre) => {
              const selected = selectedGenres.includes(genre.id)
              return (
                <button
                  key={genre.id}
                  onClick={() => toggleGenre(genre.id)}
                  className={`relative flex items-center gap-3 p-3 rounded-xl border-2 transition-all text-left ${
                    selected
                      ? 'border-lsc-rose bg-lsc-rose/5 dark:bg-lsc-rose/10'
                      : 'border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 hover:border-lsc-rose/50'
                  }`}
                  aria-pressed={selected}
                >
                  {selected && (
                    <div className="absolute top-1.5 right-1.5 w-5 h-5 rounded-full bg-lsc-rose flex items-center justify-center">
                      <Check className="w-3 h-3 text-white" aria-hidden="true" />
                    </div>
                  )}
                  <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${
                    selected ? 'bg-lsc-rose/10 dark:bg-lsc-rose/20' : 'bg-lsc-cream dark:bg-lsc-brown'
                  }`}>
                    <genre.icon className={`w-4 h-4 ${selected ? 'text-lsc-rose' : 'text-lsc-dark/70 dark:text-lsc-cream/70'}`} aria-hidden="true" />
                  </div>
                  <span className={`text-sm font-medium ${selected ? 'text-lsc-rose' : 'text-lsc-dark dark:text-lsc-cream'}`}>
                    {genre.label}
                  </span>
                </button>
              )
            })}
          </div>
        </section>

        {/* Format selection */}
        <section>
          <h2 className="font-serif font-semibold text-lg text-lsc-dark dark:text-lsc-cream mb-3">
            How do you prefer to read?
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {FORMATS.map((fmt) => {
              const selected = selectedFormats.includes(fmt.id)
              return (
                <button
                  key={fmt.id}
                  onClick={() => toggleFormat(fmt.id)}
                  className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${
                    selected
                      ? 'border-lsc-rose bg-lsc-rose/5 dark:bg-lsc-rose/10'
                      : 'border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 hover:border-lsc-rose/50'
                  }`}
                  aria-pressed={selected}
                >
                  <fmt.icon className={`w-6 h-6 ${selected ? 'text-lsc-rose' : 'text-lsc-dark/70 dark:text-lsc-cream/70'}`} aria-hidden="true" />
                  <span className={`text-sm font-medium ${selected ? 'text-lsc-rose' : 'text-lsc-dark dark:text-lsc-cream'}`}>
                    {fmt.label}
                  </span>
                </button>
              )
            })}
          </div>
        </section>

        {/* Reading goal */}
        <section>
          <h2 className="font-serif font-semibold text-lg text-lsc-dark dark:text-lsc-cream mb-3">
            What&apos;s your reading goal?
          </h2>
          <div className="grid grid-cols-3 gap-3">
            {GOALS.map((goal) => {
              const selected = readingGoal === goal.id
              return (
                <button
                  key={goal.id}
                  onClick={() => setReadingGoal(goal.id)}
                  className={`flex flex-col items-center gap-1 p-4 rounded-xl border-2 transition-all ${
                    selected
                      ? 'border-lsc-rose bg-lsc-rose/5 dark:bg-lsc-rose/10'
                      : 'border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 hover:border-lsc-rose/50'
                  }`}
                  aria-pressed={selected}
                >
                  <span className={`text-base font-semibold ${selected ? 'text-lsc-rose' : 'text-lsc-dark dark:text-lsc-cream'}`}>
                    {goal.label}
                  </span>
                  <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{goal.desc}</span>
                </button>
              )
            })}
          </div>
        </section>

        {/* Navigation */}
        <div className="flex items-center justify-between pt-4">
          <button
            onClick={() => navigate('/onboarding/welcome')}
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
              disabled={!canContinue || saving}
              className="flex items-center gap-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-2.5 px-5 rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-lsc-dark"
            >
              {saving ? 'Saving...' : 'Continue'}
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Progress dots */}
        <div className="flex items-center justify-center gap-2" aria-label={t('aria.preferences.step2Of5')}>
          <div className="w-2 h-2 rounded-full bg-lsc-rose/40" />
          <div className="w-2.5 h-2.5 rounded-full bg-lsc-rose" />
          <div className="w-2 h-2 rounded-full bg-lsc-dark/20 dark:bg-lsc-cream/20" />
          <div className="w-2 h-2 rounded-full bg-lsc-dark/20 dark:bg-lsc-cream/20" />
          <div className="w-2 h-2 rounded-full bg-lsc-dark/20 dark:bg-lsc-cream/20" />
        </div>
      </PageContainer>
    </div>
  )
}