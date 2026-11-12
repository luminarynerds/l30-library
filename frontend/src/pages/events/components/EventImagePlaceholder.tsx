/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { BookOpen, Wrench, Users, Baby, Monitor, Briefcase, Music, Palette, Coffee, MessageCircle } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

interface CategoryTheme {
  icon: LucideIcon
  from: string
  to: string
}

const CATEGORY_THEMES: Record<string, CategoryTheme> = {
  'Business': { icon: Briefcase, from: 'from-blue-400', to: 'to-blue-600' },
  'Makerspace': { icon: Wrench, from: 'from-category-400', to: 'to-category-600' },
  'Workshop': { icon: Monitor, from: 'from-green-400', to: 'to-emerald-600' },
  'Storytime': { icon: Baby, from: 'from-pink-400', to: 'to-rose-500' },
  'Story Time': { icon: Baby, from: 'from-pink-400', to: 'to-rose-500' },
  'Book Club': { icon: Coffee, from: 'from-status-warning-400', to: 'to-orange-500' },
  'Tech Class': { icon: Monitor, from: 'from-cyan-400', to: 'to-blue-600' },
  'Community': { icon: Users, from: 'from-teal-400', to: 'to-cyan-600' },
  'Reading': { icon: BookOpen, from: 'from-lsc-rose', to: 'to-violet-600' },
  'Music': { icon: Music, from: 'from-fuchsia-400', to: 'to-pink-600' },
  'Art': { icon: Palette, from: 'from-rose-400', to: 'to-red-500' },
  'Discussion': { icon: MessageCircle, from: 'from-slate-400', to: 'to-slate-600' },
}

const DEFAULT_THEME: CategoryTheme = { icon: BookOpen, from: 'from-lsc-rose', to: 'to-status-warning-600' }

export default function EventImagePlaceholder({ category }: { category: string | null }): React.ReactElement {
  const theme = (category && CATEGORY_THEMES[category]) || DEFAULT_THEME
  const Icon = theme.icon

  return (
    <div className={`w-full h-full bg-gradient-to-br ${theme.from} ${theme.to} flex items-center justify-center relative overflow-hidden`}>
      <div className="absolute inset-0 opacity-10" style={{
        backgroundImage: 'radial-gradient(circle at 25% 75%, white 1px, transparent 1px), radial-gradient(circle at 75% 25%, white 1px, transparent 1px)',
        backgroundSize: '24px 24px',
      }} />
      <Icon className="w-10 h-10 text-white/80 relative z-10 drop-shadow-sm" aria-hidden="true" />
    </div>
  )
}
