/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { BookMarked, BookOpen, Settings } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useReadingStatus } from '@/hooks/useReadingStatus'
import { usePatronTags } from '@/hooks/usePatronTags'
import { useReadingMilestones } from '@/hooks/useReadingMilestones'
import StatsBar from '@/components/shelf/StatsBar'
import ExportButton from '@/components/shelf/ExportButton'
import CurrentlyReadingHero from '@/components/shelf/CurrentlyReadingHero'
import ActivityFeed from '@/components/shelf/ActivityFeed'
import TagFilterBar from '@/components/shelf/TagFilterBar'
import TagManager from '@/components/shelf/TagManager'
import ShelfTabs from '@/components/shelf/ShelfTabs'
import QuickLogFAB from '@/components/shelf/QuickLogFAB'
import QuickLogSheet from '@/components/shelf/QuickLogSheet'
import ConfettiCelebration from '@/components/shelf/ConfettiCelebration'
import ShelfPreferences from '@/components/shelf/ShelfPreferences'
import { t } from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

export default function ReadingShelfPage() {
  const { user } = useAuth()
  const { allStatuses, stats } = useReadingStatus()
  const { allTags, activeFilters, toggleFilter, clearFilters, handleRename, handleDelete } = usePatronTags()
  const { justEarned } = useReadingMilestones()
  const [quickLogOpen, setQuickLogOpen] = useState(false)
  const [tagManagerOpen, setTagManagerOpen] = useState(false)
  const [prefsOpen, setPrefsOpen] = useState(false)

  // Unauthenticated state
  if (!user) {
    return (
      <PageContainer className="py-12 text-center">
        <BookMarked className="w-12 h-12 mx-auto mb-4 text-lsc-dark/70 dark:text-lsc-cream/60" aria-hidden="true" />
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">My Reading Shelf</h1>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">Sign in to track your reading.</p>
        <Link to="/login" className="text-lsc-rose dark:text-lsc-rose-light font-medium hover:underline">
          Sign in
        </Link>
      </PageContainer>
    )
  }

  // Empty state — new patron with zero shelf entries
  const totalBooks = allStatuses.length
  if (totalBooks === 0) {
    return (
      <PageContainer className="py-8">
        <div className="flex items-center gap-3 mb-6">
          <BookMarked className="w-7 h-7 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">My Reading Shelf</h1>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border/60 dark:border-earth-700/80 p-12 text-center">
          <BookOpen className="w-14 h-14 mx-auto mb-4 text-lsc-rose/40" aria-hidden="true" />
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
            Start your reading journey
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6 max-w-md mx-auto">
            Your personal reading dashboard lives here. Add a book from the catalog to get started — track your progress, earn milestones, and organize with tags.
          </p>
          <Link
            to="/catalog"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-lsc-rose text-white font-medium hover:bg-lsc-rose/90 transition-colors"
          >
            <BookOpen className="w-4 h-4" aria-hidden="true" />
            Browse the Catalog
          </Link>
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer className="py-8">
      {/* Header with title + preferences gear */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <BookMarked className="w-7 h-7 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">My Reading Shelf</h1>
        </div>
        <button
          onClick={() => setPrefsOpen(!prefsOpen)}
          aria-label={t('aria.readingShelf.shelfPreferences')}
          className="w-8 h-8 rounded-full border border-lsc-border dark:border-earth-600 flex items-center justify-center text-lsc-dark/70 dark:text-lsc-cream/50 hover:text-lsc-rose dark:hover:text-lsc-rose-light hover:border-lsc-rose transition-colors"
        >
          <Settings className="w-4 h-4" aria-hidden="true" />
        </button>
      </div>

      {/* Preferences panel (inline toggle) */}
      {prefsOpen && <ShelfPreferences />}

      {/* Stats bar */}
      <StatsBar stats={stats} />

      {/* Zone 1: Currently Reading Hero */}
      <CurrentlyReadingHero activeFilters={activeFilters} allTags={allTags} />

      {/* Zone 2: Activity & Milestones Feed */}
      <ActivityFeed />

      {/* Tag filter bar */}
      <TagFilterBar
        allTags={allTags}
        activeFilters={activeFilters}
        onToggleFilter={toggleFilter}
        onClearFilters={clearFilters}
        onOpenManager={() => setTagManagerOpen(true)}
      />

      {/* Zone 3: Remaining shelf tabs */}
      <ShelfTabs activeFilters={activeFilters} allTags={allTags} />

      {/* Export button */}
      <ExportButton />

      {/* Quick-log FAB */}
      <QuickLogFAB onClick={() => setQuickLogOpen(true)} />

      {/* Quick-log sheet */}
      <QuickLogSheet open={quickLogOpen} onClose={() => setQuickLogOpen(false)} />

      {/* Tag manager modal */}
      <TagManager
        tags={allTags}
        open={tagManagerOpen}
        onClose={() => setTagManagerOpen(false)}
        onRename={handleRename}
        onDelete={handleDelete}
      />

      {/* Confetti overlay */}
      <ConfettiCelebration milestone={justEarned} />
    </PageContainer>
  )
}
