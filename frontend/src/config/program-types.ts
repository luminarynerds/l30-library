/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { BookOpen, Sun, Snowflake, PartyPopper, type LucideIcon } from 'lucide-react'

export interface ProgramTypeConfig {
  value: string
  label: string
  icon: LucideIcon
  bgColor: string
  textColor: string
}

export const PROGRAM_TYPES: ProgramTypeConfig[] = [
  { value: 'summer', label: 'Summer Reading', icon: Sun, bgColor: 'bg-status-warning-100 dark:bg-status-warning-900/30', textColor: 'text-status-warning-600 dark:text-status-warning-400' },
  { value: 'winter', label: 'Winter Reading', icon: Snowflake, bgColor: 'bg-earth-100 dark:bg-earth-800/30', textColor: 'text-lsc-rose dark:text-lsc-rose-light' },
  { value: 'year_round', label: 'Year-Round', icon: BookOpen, bgColor: 'bg-status-success-100 dark:bg-status-success-900/30', textColor: 'text-status-success-800 dark:text-status-success-400' },
  { value: 'special', label: 'Special Challenge', icon: PartyPopper, bgColor: 'bg-category-100 dark:bg-category-900/30', textColor: 'text-category-600 dark:text-category-400' },
]

const FALLBACK: ProgramTypeConfig = { value: '', label: '', icon: BookOpen, bgColor: 'bg-lsc-cream dark:bg-lsc-brown/30', textColor: 'text-lsc-rose dark:text-lsc-rose-light' }

export function getProgramTypeConfig(type: string): ProgramTypeConfig {
  return PROGRAM_TYPES.find((t) => t.value === type) || { ...FALLBACK, value: type, label: type }
}
