/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { useTranslation } from '@/i18n/I18nContext'
import { MOOD_TO_PATRON_LABEL } from '@/pages/catalog/utils/catalogItemUtils'

// ---------------------------------------------------------------------------
// MoodTag
//
// A single mood pill. When the internal tag maps to a patron mood category it
// renders as a Link that browses that mood (/catalog/mood/{slug}, the same
// surface the landing-page mood row uses). Tags with no mapping (e.g.
// "Fast-paced", which is a filter not a mood) render as a plain, non-clickable
// pill so we never produce a dead link.
// ---------------------------------------------------------------------------

interface MoodTagProps {
  mood: string
  /** 'sm' for the dense grid meta line, 'md' for the list card pill row. */
  size?: 'sm' | 'md'
}

export default function MoodTag({ mood, size = 'md' }: MoodTagProps) {
  const { t } = useTranslation()
  const mapped = MOOD_TO_PATRON_LABEL[mood]

  const pill = size === 'sm' ? 'text-[11px] px-1.5 py-0.5' : 'text-xs px-2 py-0.5'
  const base = `inline-flex items-center rounded-full font-medium border transition-colors ${pill}`

  if (!mapped) {
    return (
      <span className={`${base} bg-category-50 dark:bg-category-900/20 text-category-600 dark:text-category-400 border-category-200 dark:border-category-800/30`}>
        {mood}
      </span>
    )
  }

  return (
    <Link
      to={`/catalog/mood/${mapped.slug}`}
      // Sits above the card's overlay link so the mood filter wins the click.
      className={`relative z-[1] ${base} bg-category-50 dark:bg-category-900/20 text-category-700 dark:text-category-300 border-category-200 dark:border-category-800/40 hover:bg-category-100 hover:border-lsc-rose/50 focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose`}
      aria-label={t('catalog.mood.browseTagAria', 'Browse {mood} titles').replace('{mood}', mood)}
      title={t('catalog.mood.browseTagTitle', 'Browse more like this')}
    >
      {mood}
    </Link>
  )
}
