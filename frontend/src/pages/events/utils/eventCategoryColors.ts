/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  Baby, BookOpen, Briefcase, Clapperboard, Coffee, HandHeart, Heart,
  MessageCircle, Microscope, Monitor, Music, Palette, PartyPopper,
  Pencil, Trophy, Users, Wrench,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

type CategoryColorConfig = {
  display: string
  icon: LucideIcon
  bg: string
  text: string
  border: string
  /** Solid accent for the date-plate rule/edge. */
  accent: string
  headerBg: string
  headerBgDark: string
}

/**
 * Normalize a raw DB category to a lookup key: lowercase, strip spaces,
 * underscores, hyphens, and punctuation. "Book Club", "book_club", and
 * "Book clubs" all become comparable keys.
 */
export function normalizeCategoryKey(category: string): string {
  return category.toLowerCase().replace(/[^a-z0-9]/g, '')
}

// Canonical entries, keyed by normalized key. One hue + one icon per category,
// shared by the date plate, the category pill, and filter chips.
const categoryConfigs: Record<string, CategoryColorConfig> = {
  storytime: {
    display: 'Storytime', icon: Baby,
    bg: 'bg-pink-100 dark:bg-pink-900/30', text: 'text-pink-700 dark:text-pink-300',
    border: 'border-pink-300 dark:border-pink-700', accent: 'bg-pink-500 dark:bg-pink-400',
    headerBg: 'from-pink-500 to-pink-600', headerBgDark: 'dark:from-pink-700 dark:to-pink-800',
  },
  bookclub: {
    display: 'Book Club', icon: Coffee,
    bg: 'bg-status-warning-100 dark:bg-status-warning-900/30', text: 'text-status-warning-700 dark:text-status-warning-300',
    border: 'border-status-warning-300 dark:border-status-warning-700', accent: 'bg-status-warning-600 dark:bg-status-warning-400',
    headerBg: 'from-status-warning-500 to-status-warning-600', headerBgDark: 'dark:from-status-warning-700 dark:to-status-warning-800',
  },
  community: {
    display: 'Community', icon: Users,
    bg: 'bg-teal-100 dark:bg-teal-900/30', text: 'text-teal-700 dark:text-teal-300',
    border: 'border-teal-300 dark:border-teal-700', accent: 'bg-teal-600 dark:bg-teal-400',
    headerBg: 'from-teal-600 to-teal-700', headerBgDark: 'dark:from-teal-800 dark:to-teal-900',
  },
  technology: {
    display: 'Technology', icon: Monitor,
    bg: 'bg-cyan-100 dark:bg-cyan-900/30', text: 'text-cyan-700 dark:text-cyan-300',
    border: 'border-cyan-300 dark:border-cyan-700', accent: 'bg-cyan-600 dark:bg-cyan-400',
    headerBg: 'from-cyan-600 to-cyan-700', headerBgDark: 'dark:from-cyan-800 dark:to-cyan-900',
  },
  wellness: {
    display: 'Wellness', icon: Heart,
    bg: 'bg-emerald-100 dark:bg-emerald-900/30', text: 'text-emerald-700 dark:text-emerald-300',
    border: 'border-emerald-300 dark:border-emerald-700', accent: 'bg-emerald-600 dark:bg-emerald-400',
    headerBg: 'from-emerald-600 to-emerald-700', headerBgDark: 'dark:from-emerald-800 dark:to-emerald-900',
  },
  entertainment: {
    display: 'Entertainment', icon: PartyPopper,
    bg: 'bg-fuchsia-100 dark:bg-fuchsia-900/30', text: 'text-fuchsia-700 dark:text-fuchsia-300',
    border: 'border-fuchsia-300 dark:border-fuchsia-700', accent: 'bg-fuchsia-600 dark:bg-fuchsia-400',
    headerBg: 'from-fuchsia-500 to-fuchsia-600', headerBgDark: 'dark:from-fuchsia-700 dark:to-fuchsia-800',
  },
  stem: {
    display: 'STEM', icon: Microscope,
    bg: 'bg-sky-100 dark:bg-sky-900/30', text: 'text-sky-700 dark:text-sky-300',
    border: 'border-sky-300 dark:border-sky-700', accent: 'bg-sky-600 dark:bg-sky-400',
    headerBg: 'from-sky-600 to-sky-700', headerBgDark: 'dark:from-sky-800 dark:to-sky-900',
  },
  fundraiser: {
    display: 'Fundraiser', icon: HandHeart,
    bg: 'bg-rose-100 dark:bg-rose-900/30', text: 'text-rose-700 dark:text-rose-300',
    border: 'border-rose-300 dark:border-rose-700', accent: 'bg-rose-600 dark:bg-rose-400',
    headerBg: 'from-rose-500 to-rose-600', headerBgDark: 'dark:from-rose-700 dark:to-rose-800',
  },
  social: {
    display: 'Social', icon: MessageCircle,
    bg: 'bg-indigo-100 dark:bg-indigo-900/30', text: 'text-indigo-700 dark:text-indigo-300',
    border: 'border-indigo-300 dark:border-indigo-700', accent: 'bg-indigo-600 dark:bg-indigo-400',
    headerBg: 'from-indigo-600 to-indigo-700', headerBgDark: 'dark:from-indigo-800 dark:to-indigo-900',
  },
  business: {
    display: 'Business', icon: Briefcase,
    bg: 'bg-earth-100 dark:bg-earth-800/30', text: 'text-earth-700 dark:text-earth-300',
    border: 'border-earth-300 dark:border-earth-600', accent: 'bg-earth-500 dark:bg-earth-400',
    headerBg: 'from-blue-600 to-blue-700', headerBgDark: 'dark:from-blue-800 dark:to-blue-900',
  },
  makerspace: {
    display: 'Makerspace', icon: Wrench,
    bg: 'bg-category-100 dark:bg-category-900/30', text: 'text-category-700 dark:text-category-300',
    border: 'border-category-300 dark:border-category-700', accent: 'bg-category-600 dark:bg-category-400',
    headerBg: 'from-category-600 to-category-700', headerBgDark: 'dark:from-category-800 dark:to-category-900',
  },
  workshop: {
    display: 'Workshop', icon: Pencil,
    bg: 'bg-status-success-100 dark:bg-status-success-900/30', text: 'text-status-success-700 dark:text-status-success-300',
    border: 'border-status-success-300 dark:border-status-success-700', accent: 'bg-status-success-600 dark:bg-status-success-400',
    headerBg: 'from-green-600 to-green-700', headerBgDark: 'dark:from-green-800 dark:to-green-900',
  },
  reading: {
    display: 'Reading', icon: BookOpen,
    bg: 'bg-violet-100 dark:bg-violet-900/30', text: 'text-violet-700 dark:text-violet-300',
    border: 'border-violet-300 dark:border-violet-700', accent: 'bg-violet-600 dark:bg-violet-400',
    headerBg: 'from-violet-600 to-violet-700', headerBgDark: 'dark:from-violet-800 dark:to-violet-900',
  },
  authorvisits: {
    display: 'Author visits', icon: Pencil,
    bg: 'bg-fuchsia-100 dark:bg-fuchsia-900/30', text: 'text-fuchsia-700 dark:text-fuchsia-300',
    border: 'border-fuchsia-300 dark:border-fuchsia-700', accent: 'bg-fuchsia-600 dark:bg-fuchsia-400',
    headerBg: 'from-fuchsia-500 to-fuchsia-600', headerBgDark: 'dark:from-fuchsia-700 dark:to-fuchsia-800',
  },
  moviescreenings: {
    display: 'Movie screenings', icon: Clapperboard,
    bg: 'bg-violet-100 dark:bg-violet-900/30', text: 'text-violet-700 dark:text-violet-300',
    border: 'border-violet-300 dark:border-violet-700', accent: 'bg-violet-600 dark:bg-violet-400',
    headerBg: 'from-violet-600 to-violet-700', headerBgDark: 'dark:from-violet-800 dark:to-violet-900',
  },
  childrensprograms: {
    display: "Children's programs", icon: Baby,
    bg: 'bg-pink-100 dark:bg-pink-900/30', text: 'text-pink-700 dark:text-pink-300',
    border: 'border-pink-300 dark:border-pink-700', accent: 'bg-pink-500 dark:bg-pink-400',
    headerBg: 'from-pink-500 to-rose-600', headerBgDark: 'dark:from-pink-700 dark:to-rose-800',
  },
  craftsandmakerevents: {
    display: 'Crafts and maker events', icon: Palette,
    bg: 'bg-status-warning-100 dark:bg-status-warning-900/30', text: 'text-status-warning-700 dark:text-status-warning-300',
    border: 'border-status-warning-300 dark:border-status-warning-700', accent: 'bg-status-warning-600 dark:bg-status-warning-400',
    headerBg: 'from-status-warning-500 to-orange-600', headerBgDark: 'dark:from-status-warning-700 dark:to-orange-800',
  },
  allagesevents: {
    display: 'All-ages events', icon: Users,
    bg: 'bg-emerald-100 dark:bg-emerald-900/30', text: 'text-emerald-700 dark:text-emerald-300',
    border: 'border-emerald-300 dark:border-emerald-700', accent: 'bg-emerald-600 dark:bg-emerald-400',
    headerBg: 'from-emerald-600 to-green-700', headerBgDark: 'dark:from-emerald-800 dark:to-green-900',
  },
  teenprograms: {
    display: 'Teen programs', icon: Users,
    bg: 'bg-violet-100 dark:bg-violet-900/30', text: 'text-violet-700 dark:text-violet-300',
    border: 'border-violet-300 dark:border-violet-700', accent: 'bg-violet-600 dark:bg-violet-400',
    headerBg: 'from-violet-600 to-violet-700', headerBgDark: 'dark:from-violet-800 dark:to-violet-900',
  },
  sports: {
    display: 'Sports', icon: Trophy,
    bg: 'bg-lime-100 dark:bg-lime-900/30', text: 'text-lime-700 dark:text-lime-300',
    border: 'border-lime-300 dark:border-lime-700', accent: 'bg-lime-600 dark:bg-lime-400',
    headerBg: 'from-lime-600 to-lime-700', headerBgDark: 'dark:from-lime-800 dark:to-lime-900',
  },
  music: {
    display: 'Music', icon: Music,
    bg: 'bg-fuchsia-100 dark:bg-fuchsia-900/30', text: 'text-fuchsia-700 dark:text-fuchsia-300',
    border: 'border-fuchsia-300 dark:border-fuchsia-700', accent: 'bg-fuchsia-600 dark:bg-fuchsia-400',
    headerBg: 'from-fuchsia-500 to-pink-600', headerBgDark: 'dark:from-fuchsia-700 dark:to-pink-800',
  },
  art: {
    display: 'Art', icon: Palette,
    bg: 'bg-rose-100 dark:bg-rose-900/30', text: 'text-rose-700 dark:text-rose-300',
    border: 'border-rose-300 dark:border-rose-700', accent: 'bg-rose-500 dark:bg-rose-400',
    headerBg: 'from-rose-400 to-red-500', headerBgDark: 'dark:from-rose-700 dark:to-red-800',
  },
  discussion: {
    display: 'Discussion', icon: MessageCircle,
    bg: 'bg-slate-100 dark:bg-slate-800/40', text: 'text-slate-700 dark:text-slate-300',
    border: 'border-slate-300 dark:border-slate-600', accent: 'bg-slate-500 dark:bg-slate-400',
    headerBg: 'from-slate-500 to-slate-600', headerBgDark: 'dark:from-slate-700 dark:to-slate-800',
  },
}

// Normalized variant -> canonical key. Only needed where normalization alone
// does not collapse the variant ("Story Time" -> "storytime" needs no alias;
// "tech_class" -> "technology" does).
const categoryAliases: Record<string, string> = {
  bookclubs: 'bookclub',
  techclass: 'technology',
  stemprograms: 'stem',
  communitymeetings: 'community',
  children: 'childrensprograms',
  sportscards: 'sports',
  wnba: 'sports',
}

// Neutral (deliberately not rose/brand) fallback for unknown categories.
const defaultCategoryColor: CategoryColorConfig = {
  display: '',
  icon: BookOpen,
  bg: 'bg-earth-100 dark:bg-earth-700/50',
  text: 'text-earth-700 dark:text-lsc-cream/80',
  border: 'border-earth-300 dark:border-earth-600',
  accent: 'bg-earth-400 dark:bg-earth-500',
  headerBg: 'from-earth-500 to-earth-600',
  headerBgDark: 'dark:from-earth-700 dark:to-earth-800',
}

function resolveCategory(category: string): CategoryColorConfig {
  const key = normalizeCategoryKey(category)
  const canonical = categoryAliases[key] ?? key
  return categoryConfigs[canonical] ?? defaultCategoryColor
}

export function getCategoryColorClasses(category: string | null): string {
  if (!category) return `${defaultCategoryColor.bg} ${defaultCategoryColor.text}`
  const colors = resolveCategory(category)
  return `${colors.bg} ${colors.text}`
}

export function getCategoryDisplayName(category: string | null): string {
  if (!category) return ''
  const config = resolveCategory(category)
  if (config.display) return config.display
  // Unknown category: format the raw value nicely.
  return category.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

export function getCategoryBorderClasses(category: string | null): string {
  if (!category) return defaultCategoryColor.border
  return resolveCategory(category).border
}

export function getCategoryAccentClasses(category: string | null): string {
  if (!category) return defaultCategoryColor.accent
  return resolveCategory(category).accent
}

export function getCategoryIcon(category: string | null): LucideIcon {
  if (!category) return defaultCategoryColor.icon
  return resolveCategory(category).icon
}

export function getCategoryHeaderGradient(category: string | null): string {
  if (!category) return `${defaultCategoryColor.headerBg} ${defaultCategoryColor.headerBgDark}`
  const colors = resolveCategory(category)
  return `${colors.headerBg} ${colors.headerBgDark}`
}
