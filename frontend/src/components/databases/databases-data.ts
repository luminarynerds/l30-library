/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { DatabaseCategory } from '../../api/databases-api'
import type { StatusTone } from '@/components/admin'
import type { SubscriptionStatus } from '../../api/databases-api'

export const subscriptionStatusTone = (status: SubscriptionStatus): StatusTone => {
  switch (status) {
    case 'active':
      return 'success'
    case 'expiring_soon':
    case 'trial':
      return 'warning'
    case 'expired':
      return 'danger'
    default:
      return 'neutral'
  }
}

export const CATEGORY_OPTIONS: { value: DatabaseCategory; label: string }[] = [
  { value: 'general_reference', label: 'General Reference' },
  { value: 'academic', label: 'Academic' },
  { value: 'newspapers', label: 'Newspapers' },
  { value: 'magazines', label: 'Magazines' },
  { value: 'ebooks', label: 'E-Books' },
  { value: 'audiobooks', label: 'Audiobooks' },
  { value: 'genealogy', label: 'Genealogy' },
  { value: 'business', label: 'Business' },
  { value: 'legal', label: 'Legal' },
  { value: 'health', label: 'Health & Wellness' },
  { value: 'children', label: 'Children' },
  { value: 'teen', label: 'Teen' },
  { value: 'language_learning', label: 'Language Learning' },
  { value: 'test_prep', label: 'Test Preparation' },
  { value: 'streaming_video', label: 'Streaming Video' },
  { value: 'streaming_music', label: 'Streaming Music' },
  { value: 'diy_crafts', label: 'DIY & Crafts' },
  { value: 'automotive', label: 'Automotive' },
  { value: 'other', label: 'Other' },
]

export const inputClasses =
  'w-full px-3 py-2 border border-earth-300 dark:border-earth-500 rounded-lg bg-lsc-white dark:bg-earth-700 text-earth-900 dark:text-lsc-cream'

export const labelClasses = 'block text-sm font-medium text-earth-700 dark:text-earth-300 mb-1'
