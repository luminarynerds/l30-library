/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { BookOpen, FileText, Bell, BarChart3 } from 'lucide-react'

export const TEMPLATE_CATEGORIES = [
  { value: '', label: 'All Categories' },
  { value: 'summer_reading', label: 'Summer Reading' },
  { value: 'storytime', label: 'Storytime' },
  { value: 'workshop', label: 'Workshop' },
  { value: 'book_club', label: 'Book Club' },
  { value: 'stem', label: 'STEM' },
  { value: 'arts_crafts', label: 'Arts & Crafts' },
  { value: 'technology', label: 'Technology' },
  { value: 'outreach', label: 'Outreach' },
  { value: 'lecture', label: 'Lecture' },
  { value: 'performance', label: 'Performance' },
  { value: 'holiday', label: 'Holiday' },
  { value: 'community', label: 'Community' },
  { value: 'other', label: 'Other' },
]

export const AUDIENCES = [
  'children', 'teen', 'adult', 'senior', 'family', 'all_ages',
]

export const PROGRAM_TYPES = [
  'storytime', 'workshop', 'book_club', 'lecture', 'performance',
  'educational', 'recreational', 'outreach', 'technology', 'arts_crafts',
  'stem', 'music', 'other',
]

export type ActiveTab = 'templates' | 'plans' | 'reminders' | 'metrics'

export const TAB_DEFINITIONS = [
  { key: 'templates' as const, label: 'Template Library', icon: BookOpen },
  { key: 'plans' as const, label: 'Program Plans', icon: FileText },
  { key: 'reminders' as const, label: 'Marketing Reminders', icon: Bell },
  { key: 'metrics' as const, label: 'Success Metrics', icon: BarChart3 },
] as const

export const TAB_KEYS: ActiveTab[] = TAB_DEFINITIONS.map(t => t.key)
