/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { MoodIcon } from '@/pages/catalog/utils/catalogLandingConfig'
import { useMoodCategories } from '@/hooks/useMoodCategories'
import type { MoodCategory } from '@/api/domains/catalog/mood-categories-api'

interface MoodBrowseRowProps {
  quietMode?: boolean
}

// Soft pastel palette — six cycling tones so the row reads as a coherent set.
// Light-mode tints are the named `mood-*` tokens (tailwind.config.js).
// Backgrounds chosen for WCAG AA contrast with text-lsc-dark in light mode
// and lsc-cream in dark mode (verified at ~7:1 / ~8:1).
const PALETTE = [
  {
    bg: 'bg-mood-rose dark:bg-rose-900/30',
    hoverBg: 'group-hover:bg-mood-rose-hover dark:group-hover:bg-rose-900/50',
    icon: 'text-rose-700 dark:text-rose-200',
    chip: 'bg-white/70 text-rose-800 dark:bg-rose-950/60 dark:text-rose-100',
  },
  {
    bg: 'bg-mood-lime dark:bg-yellow-900/25',
    hoverBg: 'group-hover:bg-mood-lime-hover dark:group-hover:bg-yellow-900/45',
    icon: 'text-yellow-800 dark:text-yellow-100',
    chip: 'bg-white/70 text-yellow-900 dark:bg-yellow-950/60 dark:text-yellow-100',
  },
  {
    bg: 'bg-mood-lilac dark:bg-purple-900/30',
    hoverBg: 'group-hover:bg-mood-lilac-hover dark:group-hover:bg-purple-900/50',
    icon: 'text-purple-800 dark:text-purple-100',
    chip: 'bg-white/70 text-purple-900 dark:bg-purple-950/60 dark:text-purple-100',
  },
  {
    bg: 'bg-mood-gold dark:bg-amber-900/25',
    hoverBg: 'group-hover:bg-mood-gold-hover dark:group-hover:bg-amber-900/45',
    icon: 'text-amber-800 dark:text-amber-100',
    chip: 'bg-white/70 text-amber-900 dark:bg-amber-950/60 dark:text-amber-100',
  },
  {
    bg: 'bg-mood-mint dark:bg-emerald-900/25',
    hoverBg: 'group-hover:bg-mood-mint-hover dark:group-hover:bg-emerald-900/45',
    icon: 'text-emerald-800 dark:text-emerald-100',
    chip: 'bg-white/70 text-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-100',
  },
  {
    bg: 'bg-mood-sky dark:bg-sky-900/25',
    hoverBg: 'group-hover:bg-mood-sky-hover dark:group-hover:bg-sky-900/45',
    icon: 'text-sky-800 dark:text-sky-100',
    chip: 'bg-white/70 text-sky-900 dark:bg-sky-950/60 dark:text-sky-100',
  },
] as const

function MoodCard({ mood, index }: { mood: MoodCategory; index: number }) {
  const tone = PALETTE[index % PALETTE.length]!
  return (
    <Link
      to={`/catalog/mood/${mood.slug}`}
      className="group block h-full rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 dark:focus-visible:ring-offset-lsc-dark"
    >
      <div
        className={`relative overflow-hidden rounded-xl ${tone.bg} ${tone.hoverBg} h-full px-4 pt-8 pb-5 min-h-[150px] flex flex-col items-center text-center transition-[background-color,transform,box-shadow] duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] motion-safe:[@media(hover:hover)_and_(pointer:fine)]:group-hover:-translate-y-0.5 motion-safe:group-focus-visible:-translate-y-0.5 motion-safe:group-hover:shadow-md motion-safe:group-focus-visible:shadow-md`}
      >
        <span
          className={`inline-flex items-center px-2.5 py-0.5 mb-3 rounded-full text-[10px] uppercase tracking-wide font-semibold ${tone.chip}`}
        >
          Mood
        </span>
        <span
          className={`motion-safe:transform motion-safe:translate-y-2 motion-safe:[@media(hover:hover)_and_(pointer:fine)]:group-hover:translate-y-0 motion-safe:group-focus-visible:translate-y-0 motion-safe:transition-transform motion-safe:duration-150 motion-safe:ease-[cubic-bezier(0.23,1,0.32,1)]`}
        >
          <MoodIcon name={mood.icon} className={`w-9 h-9 ${tone.icon}`} />
        </span>
        <span className="mt-3 text-sm font-medium text-lsc-dark dark:text-lsc-cream leading-snug">
          {mood.label}
        </span>
      </div>
    </Link>
  )
}

export default function MoodBrowseRow({ quietMode }: MoodBrowseRowProps) {
  const { data: moods } = useMoodCategories()

  if (quietMode) return null
  if (!moods || moods.length === 0) return null

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          How are you feeling?
        </h2>
      </div>
      <div
        role="list"
        aria-label="Browse by mood"
        className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3"
      >
        {moods.map((mood, idx) => (
          <div key={mood.slug} role="listitem" className="h-full">
            <MoodCard mood={mood} index={idx} />
          </div>
        ))}
      </div>
    </div>
  )
}
