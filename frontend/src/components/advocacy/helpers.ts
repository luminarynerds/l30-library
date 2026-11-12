/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { ResourceItem } from './types'

export function getPartyColor(party: string): string {
  const p = party?.toLowerCase() ?? ''
  if (p.startsWith('d') || p.includes('democrat')) return 'bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light'
  if (p.startsWith('r') || p.includes('republican')) return 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300'
  return 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'
}

export function getPartyAbbrev(party: string): string {
  const p = party?.toLowerCase() ?? ''
  if (p.startsWith('d') || p.includes('democrat')) return 'D'
  if (p.startsWith('r') || p.includes('republican')) return 'R'
  if (p.includes('independent')) return 'I'
  return party?.charAt(0)?.toUpperCase() ?? '?'
}

export function getLevelLabel(level: string): string {
  if (level === 'federal') return 'Federal Representatives'
  if (level === 'state') return 'State Representatives'
  return 'Local Officials'
}

export function getTargetLevelBadge(level: string): string {
  if (level === 'federal') return 'bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light'
  if (level === 'state') return 'bg-category-100 dark:bg-category-900/30 text-category-700 dark:text-category-300'
  if (level === 'local') return 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300'
  return 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'
}

export function getInitials(name: string): string {
  return name
    .split(' ')
    .filter(Boolean)
    .map((n) => n[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

export function getResources(t: (key: string) => string): ResourceItem[] {
  return [
    {
      name: 'American Library Association (ALA)',
      description: t('advocacy.officeForIntellectualFreedom'),
      url: 'https://www.ala.org/advocacy/intfreedom',
    },
    {
      name: 'PEN America',
      description: t('advocacy.trackingBookBansAcrossThe'),
      url: 'https://pen.org/issue/book-bans/',
    },
    {
      name: 'EveryLibrary',
      description: t('advocacy.politicalActionCommitteeForLibraries'),
      url: 'https://www.everylibrary.org/',
    },
    {
      name: 'ACLU',
      description: t('advocacy.freeSpeechAndCensorshipResources'),
      url: 'https://www.aclu.org/issues/free-speech',
    },
    {
      name: 'Freedom to Read Foundation',
      description: t('advocacy.defendingTheFirstAmendmentIn'),
      url: 'https://www.ftrf.org/',
    },
    {
      name: 'National Coalition Against Censorship',
      description: t('advocacy.promotingFreedomOfThought'),
      url: 'https://ncac.org/',
    },
  ]
}
