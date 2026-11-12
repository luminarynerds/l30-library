/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export type GuideCategoryId = 'account' | 'printing' | 'email' | 'connectivity' | 'safety'

export interface GuideCategoryMeta {
  id: GuideCategoryId
  /** i18n key under `guidesIndex.categories` */
  labelKey: string
  /** Lucide icon name to render in the category chip */
  iconName: 'CreditCard' | 'Printer' | 'Mail' | 'Wifi' | 'ShieldAlert'
}

export const GUIDE_CATEGORIES: GuideCategoryMeta[] = [
  { id: 'account', labelKey: 'guidesIndex.categories.account', iconName: 'CreditCard' },
  { id: 'printing', labelKey: 'guidesIndex.categories.printing', iconName: 'Printer' },
  { id: 'email', labelKey: 'guidesIndex.categories.email', iconName: 'Mail' },
  { id: 'connectivity', labelKey: 'guidesIndex.categories.connectivity', iconName: 'Wifi' },
  { id: 'safety', labelKey: 'guidesIndex.categories.safety', iconName: 'ShieldAlert' },
]

export type GuideIconName =
  | 'CreditCard'
  | 'BookMarked'
  | 'Printer'
  | 'FileCheck'
  | 'Mail'
  | 'Smartphone'
  | 'Wifi'
  | 'KeyRound'
  | 'ShieldAlert'

export interface GuideMeta {
  /** Stable id used in routes, JSON-LD @id, and analytics */
  id: string
  /** Path under /guides/ (kept in sync with public.tsx routes) */
  href: string
  /** i18n key under `guidesIndex.cards.<id>.title` */
  titleKey: string
  /** i18n key under `guidesIndex.cards.<id>.description` */
  descriptionKey: string
  iconName: GuideIconName
  category: GuideCategoryId
  /** Approximate read/walkthrough time in minutes — surfaced in card + HowTo schema */
  estimatedMinutes: number
}

export const GUIDES: GuideMeta[] = [
  {
    id: 'library-card',
    href: '/guides/library-card',
    titleKey: 'guidesIndex.cards.libraryCard.title',
    descriptionKey: 'guidesIndex.cards.libraryCard.description',
    iconName: 'CreditCard',
    category: 'account',
    estimatedMinutes: 8,
  },
  {
    id: 'placing-holds',
    href: '/guides/placing-holds',
    titleKey: 'guidesIndex.cards.placingHolds.title',
    descriptionKey: 'guidesIndex.cards.placingHolds.description',
    iconName: 'BookMarked',
    category: 'account',
    estimatedMinutes: 4,
  },
  {
    id: 'wireless-printing',
    href: '/guides/wireless-printing',
    titleKey: 'guidesIndex.cards.wirelessPrinting.title',
    descriptionKey: 'guidesIndex.cards.wirelessPrinting.description',
    iconName: 'Printer',
    category: 'printing',
    estimatedMinutes: 6,
  },
  {
    id: 'check-print-jobs',
    href: '/guides/check-print-jobs',
    titleKey: 'guidesIndex.cards.checkPrintJobs.title',
    descriptionKey: 'guidesIndex.cards.checkPrintJobs.description',
    iconName: 'FileCheck',
    category: 'printing',
    estimatedMinutes: 3,
  },
  {
    id: 'email-account',
    href: '/guides/email-account',
    titleKey: 'guidesIndex.cards.emailAccount.title',
    descriptionKey: 'guidesIndex.cards.emailAccount.description',
    iconName: 'Mail',
    category: 'email',
    estimatedMinutes: 10,
  },
  {
    id: 'email-on-phone',
    href: '/guides/email-on-phone',
    titleKey: 'guidesIndex.cards.emailOnPhone.title',
    descriptionKey: 'guidesIndex.cards.emailOnPhone.description',
    iconName: 'Smartphone',
    category: 'email',
    estimatedMinutes: 8,
  },
  {
    id: 'wifi-troubleshooting',
    href: '/guides/wifi-troubleshooting',
    titleKey: 'guidesIndex.cards.wifiTroubleshooting.title',
    descriptionKey: 'guidesIndex.cards.wifiTroubleshooting.description',
    iconName: 'Wifi',
    category: 'connectivity',
    estimatedMinutes: 7,
  },
  {
    id: 'password-reset',
    href: '/guides/password-reset',
    titleKey: 'guidesIndex.cards.passwordReset.title',
    descriptionKey: 'guidesIndex.cards.passwordReset.description',
    iconName: 'KeyRound',
    category: 'account',
    estimatedMinutes: 5,
  },
  {
    id: 'scam-recognition',
    href: '/guides/scam-recognition',
    titleKey: 'guidesIndex.cards.scamRecognition.title',
    descriptionKey: 'guidesIndex.cards.scamRecognition.description',
    iconName: 'ShieldAlert',
    category: 'safety',
    estimatedMinutes: 9,
  },
]

/**
 * Earth/Sage palette tokens per category (CLAUDE.md design mandate).
 * These are full Tailwind class strings so they are picked up by the JIT scanner.
 */
export const CATEGORY_TILE_CLASSES: Record<GuideCategoryId, string> = {
  account: 'bg-sage-100 dark:bg-sage-900/30 text-sage-700 dark:text-sage-300',
  printing: 'bg-earth-100 dark:bg-earth-700/40 text-earth-700 dark:text-earth-200',
  email: 'bg-cream-100 dark:bg-cream-800/40 text-earth-700 dark:text-cream-200',
  connectivity: 'bg-sage-50 dark:bg-sage-900/20 text-sage-700 dark:text-sage-300',
  safety: 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300',
}

export function findGuide(id: string): GuideMeta | undefined {
  return GUIDES.find((g) => g.id === id)
}
