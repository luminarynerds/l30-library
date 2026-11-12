/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  BookOpen,
  Disc,
  Headphones,
  Film,
  Gamepad2,
  Newspaper,
  Package,
  Smartphone,
} from 'lucide-react'
import { createElement } from 'react'

// Format icons mapping
export const FORMAT_ICONS: Record<string, { icon: React.ReactNode; label: string }> = {
  book: { icon: createElement(BookOpen, { className: 'w-16 h-16', 'aria-hidden': true }), label: 'Book' },
  ebook: { icon: createElement(Smartphone, { className: 'w-16 h-16', 'aria-hidden': true }), label: 'E-Book' },
  audiobook: { icon: createElement(Headphones, { className: 'w-16 h-16', 'aria-hidden': true }), label: 'Audiobook' },
  dvd: { icon: createElement(Film, { className: 'w-16 h-16', 'aria-hidden': true }), label: 'DVD' },
  bluray: { icon: createElement(Film, { className: 'w-16 h-16', 'aria-hidden': true }), label: 'Blu-ray' },
  cd: { icon: createElement(Disc, { className: 'w-16 h-16', 'aria-hidden': true }), label: 'CD' },
  vinyl: { icon: createElement(Disc, { className: 'w-16 h-16', 'aria-hidden': true }), label: 'Vinyl' },
  magazine: { icon: createElement(Newspaper, { className: 'w-16 h-16', 'aria-hidden': true }), label: 'Magazine' },
  game: { icon: createElement(Gamepad2, { className: 'w-16 h-16', 'aria-hidden': true }), label: 'Video Game' },
  equipment: { icon: createElement(Package, { className: 'w-16 h-16', 'aria-hidden': true }), label: 'Equipment' },
  kit: { icon: createElement(Package, { className: 'w-16 h-16', 'aria-hidden': true }), label: 'Kit' },
  other: { icon: createElement(Package, { className: 'w-16 h-16', 'aria-hidden': true }), label: 'Other' },
}

// Sensory warnings for different media types
export const SENSORY_WARNINGS: Record<string, string[]> = {
  dvd: ['Visual warning: May contain flashing lights or rapid scene changes that could affect photosensitive viewers', 'Audio warning: May contain loud or sudden sounds - consider adjusting volume before starting'],
  bluray: ['Visual warning: May contain flashing lights or rapid scene changes that could affect photosensitive viewers', 'Audio warning: May contain loud or sudden sounds - consider adjusting volume before starting'],
  game: ['Visual warning: May contain flashing lights or rapid visual changes', 'Pacing warning: May require quick reactions or include timed challenges'],
  cd: ['Audio content: Headphones recommended for best listening experience'],
  vinyl: ['Audio content: Requires a record player to enjoy', 'Handling note: Handle records by edges only to preserve audio quality'],
  audiobook: ['Audio content: Listening time varies by title - check the runtime in details below'],
}

export function getItemIcon(itemType: string): React.ReactNode {
  const format = FORMAT_ICONS[itemType] ?? FORMAT_ICONS.other
  return createElement('span', { className: 'text-lsc-rose' }, format?.icon)
}

export function formatItemType(itemType: string): string {
  return FORMAT_ICONS[itemType]?.label || itemType
}

export function getStatusConfig(status: string): { label: string; className: string; description: string; icon: string } {
  switch (status) {
    case 'available':
      return {
        label: 'Available',
        icon: 'CircleCheck',
        className: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200',
        description: 'This item is available for checkout right now. You can borrow it today.',
      }
    case 'checked_out':
      return {
        label: 'Checked Out',
        icon: 'Clock',
        className: 'bg-lsc-cream text-lsc-rose dark:bg-lsc-dark dark:text-lsc-rose-light',
        description: 'Another patron is currently borrowing this item. You can place a hold, and we will email you when it is returned (usually within 3 weeks).',
      }
    case 'on_hold':
      return {
        label: 'Reserved',
        icon: 'Users',
        className: 'bg-earth-100 text-lsc-rose dark:bg-earth-800 dark:text-lsc-rose-light/80',
        description: 'This item is reserved for another patron who is waiting to pick it up. You can still place a hold to be next in line.',
      }
    case 'in_transit':
      return {
        label: 'In Transit',
        icon: 'Truck',
        className: 'bg-category-100 text-category-700 dark:bg-category-900 dark:text-category-200',
        description: 'This item is traveling between library locations. It should arrive within 3-5 business days. You can place a hold to reserve it.',
      }
    case 'lost':
      return {
        label: 'Lost',
        icon: 'Clock',
        className: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200',
        description: 'This copy was not returned and is marked as lost. We may order a replacement. Ask staff if you need this title, and they can help find alternatives.',
      }
    case 'damaged':
      return {
        label: 'Damaged',
        icon: 'Clock',
        className: 'bg-earth-100 text-earth-700 dark:bg-earth-800 dark:text-earth-200',
        description: 'This copy is damaged and being evaluated for repair. Ask a staff member if we have another copy available.',
      }
    case 'on_order':
      return {
        label: 'On Order',
        icon: 'PackageSearch',
        className: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200',
        description: 'This item has been ordered but not yet received. Check back soon or place a hold to be notified when it arrives.',
      }
    case 'in_processing':
      return {
        label: 'In Processing',
        icon: 'PackageSearch',
        className: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200',
        description: 'This item is being cataloged and prepared for the shelf. It will be available soon. You can place a hold to reserve it.',
      }
    case 'missing':
      return {
        label: 'Missing',
        icon: 'Clock',
        className: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200',
        description: 'This item cannot be located on the shelf. Staff are searching for it. Ask at the desk for help finding alternatives.',
      }
    case 'withdrawn':
      return {
        label: 'Withdrawn',
        icon: 'Clock',
        className: 'bg-earth-100 text-earth-700 dark:bg-earth-800 dark:text-earth-200',
        description: 'This item has been removed from the collection and is no longer available. Ask staff to suggest similar titles.',
      }
    case 'reference':
      return {
        label: 'Reference',
        icon: 'Clock',
        className: 'bg-category-100 text-category-700 dark:bg-category-900 dark:text-category-200',
        description: 'This is a reference item and cannot be checked out. It is available for in-library use only. Ask staff for assistance.',
      }
    case 'restricted':
      return {
        label: 'Restricted',
        icon: 'Clock',
        className: 'bg-category-100 text-category-700 dark:bg-category-900 dark:text-category-200',
        description: 'This item requires special access. Please ask staff at the reference desk for assistance.',
      }
    default:
      return {
        label: status,
        icon: 'Clock',
        className: 'bg-lsc-cream text-lsc-dark dark:bg-lsc-brown dark:text-earth-300',
        description: 'Status information is being updated. Please ask staff for current availability.',
      }
  }
}

export function getReadingTimeEstimate(pageCount: number | null, itemType: string): string | null {
  if (!pageCount) return null

  const wordsPerPage = 250
  const wordsPerMinute = itemType === 'magazine' ? 250 : 200
  const totalMinutes = Math.ceil((pageCount * wordsPerPage) / wordsPerMinute)

  if (totalMinutes < 60) {
    return `About ${totalMinutes} minutes to read`
  } else {
    const hours = Math.floor(totalMinutes / 60)
    const mins = totalMinutes % 60
    return mins > 0 ? `About ${hours} hours ${mins} minutes to read` : `About ${hours} hours to read`
  }
}

export function getComplexityRating(pageCount: number | null, itemType: string): { label: string; level: 'easy' | 'medium' | 'complex'; description: string } | null {
  if (!pageCount) return null

  if (itemType === 'magazine') {
    return { label: 'Quick Read', level: 'easy', description: 'Can be read in one sitting (30-60 minutes)' }
  }

  if (pageCount < 150) {
    return { label: `Short (${pageCount} pages)`, level: 'easy', description: `Under 150 pages. Most readers finish in 4-6 hours total.` }
  } else if (pageCount < 400) {
    return { label: `Medium (${pageCount} pages)`, level: 'medium', description: `150-400 pages. Typically takes 1-2 weeks of regular reading.` }
  } else {
    return { label: `Long (${pageCount} pages)`, level: 'complex', description: `Over 400 pages. Plan for 2-4 weeks of reading time.` }
  }
}

/** Mood/experience tags for catalog items (by ID for the 25 known items). */
export const MOOD_TAGS: Record<number, string[]> = {
  1: ['Mind-bending', 'Hopeful'],
  2: ['Intense', 'Personal'],
  3: ['Calm', 'Gentle'],
  4: ['Personal', 'Hopeful'],
  5: ['Personal', 'Hopeful'],
  6: ['Intense', 'Fast-paced'],
  7: ['Intense', 'Dark'],
  8: ['Hopeful', 'Mind-bending'],
  9: ['Intense', 'Personal'],
  10: ['Personal', 'Intense'],
  11: ['Fast-paced', 'Intense'],
  12: ['Personal', 'Hopeful'],
  13: ['Gentle', 'Hopeful'],
  14: ['Mind-bending', 'Funny'],
  15: ['Calm', 'Personal'],
  16: ['Mind-bending'],
  17: ['Gentle', 'Hopeful'],
  18: ['Intense', 'Hopeful'],
  19: ['Intense', 'Dark'],
  20: ['Dark', 'Hopeful'],
  21: ['Gentle', 'Calm'],
  22: ['Calm', 'Personal'],
  23: ['Mind-bending'],
  24: ['Gentle', 'Funny'],
  25: ['Calm', 'Gentle'],
}

export function getMoodTags(itemId: number, subjects: string | null): string[] {
  const hardcoded = MOOD_TAGS[itemId]
  if (hardcoded) return hardcoded

  if (!subjects) return []
  const s = subjects.toLowerCase()
  const moods: string[] = []

  if (s.includes('thriller') || s.includes('suspense') || s.includes('mystery') || s.includes('noir') || s.includes('psychological') || s.includes('crime') || s.includes('police') || s.includes('courtroom') || s.includes('cyberattack') || s.includes('domestic suspense')) moods.push('Intense')
  if (s.includes('poetry') || s.includes('nature') || s.includes('gardening') || s.includes('watercolor') || s.includes('birds') || s.includes('relaxation') || s.includes('literary fiction') || s.includes('art')) moods.push('Calm')
  if ((s.includes('humor') && !s.includes('dark')) || (s.includes('comedy') && !s.includes('dark')) || s.includes('funny') || s.includes('cozy mystery')) moods.push('Funny')
  if (s.includes('coming-of-age') || s.includes('romance') || s.includes('community') || s.includes('friendship') || s.includes('family') || s.includes('recovery') || s.includes('hopeful')) moods.push('Hopeful')
  if (s.includes('dystopian') || s.includes('horror') || s.includes('post-apocalyptic') || s.includes('dark')) moods.push('Dark')
  if (s.includes('science fiction') || s.includes('time travel') || s.includes('cyberpunk') || s.includes('solarpunk') || s.includes('space') || s.includes('genetics') || s.includes('climate fiction') || s.includes('fantasy')) moods.push('Mind-bending')
  if (s.includes('cooking') || s.includes('self-help') || s.includes('crafts') || s.includes('sewing') || s.includes('herbs') || s.includes('wellness') || s.includes('mindfulness') || s.includes('baking')) moods.push('Gentle')
  if (s.includes('memoir') || s.includes('identity') || s.includes('immigration') || s.includes('mental health') || s.includes('neurodivergence') || s.includes('autism') || s.includes('adhd') || s.includes('disability') || s.includes('introversion')) moods.push('Personal')
  if (s.includes('history') || s.includes('maritime')) moods.push('Fast-paced')

  return moods
}

export function getContentTones(subjects: string | null): { label: string; emoji: string }[] {
  if (!subjects) return []
  const s = subjects.toLowerCase()
  const tones: { label: string; emoji: string }[] = []

  if (s.includes('thriller') || s.includes('suspense')) tones.push({ label: 'Intense / suspenseful', emoji: '\u26A1' })
  if (s.includes('poetry') || s.includes('nature')) tones.push({ label: 'Calm & reflective', emoji: '\uD83C\uDF3F' })
  if (s.includes('coming-of-age') || s.includes('memoir')) tones.push({ label: 'Personal stories', emoji: '\uD83D\uDCAC' })
  if ((s.includes('humor') && !s.includes('dark')) || s.includes('funny') || (s.includes('comedy') && !s.includes('dark'))) tones.push({ label: 'Funny & light', emoji: '\uD83D\uDE04' })
  if (s.includes('dystopian') || s.includes('science fiction')) tones.push({ label: 'Speculative / imaginative', emoji: '\uD83C\uDF00' })
  if (s.includes('history') || s.includes('historical')) tones.push({ label: 'Historical', emoji: '\uD83D\uDCDC' })
  if (s.includes('self-help') || s.includes('mental health')) tones.push({ label: 'Supportive & practical', emoji: '\uD83E\uDD1D' })

  return tones
}


// ---------------------------------------------------------------------------
// Patron-facing mood labels (maps internal tags to first-person prompts)
// ---------------------------------------------------------------------------

export const MOOD_TO_PATRON_LABEL: Record<string, { label: string; slug: string }> = {
  Calm: { label: 'I want something quiet', slug: 'quiet' },
  Gentle: { label: 'I want something quiet', slug: 'quiet' },
  Funny: { label: 'I want to laugh', slug: 'funny' },
  Hopeful: { label: 'I want to feel good', slug: 'hopeful' },
  Intense: { label: 'I want something gripping', slug: 'gripping' },
  Dark: { label: 'I want something gripping', slug: 'gripping' },
  'Mind-bending': { label: 'I want to be surprised', slug: 'surprising' },
  Personal: { label: 'I want to feel understood', slug: 'understood' },
}

export function getPatronMoodLabels(
  itemId: number,
  subjects: string | null
): Array<{ label: string; slug: string }> {
  const tags = getMoodTags(itemId, subjects)
  const seen = new Set<string>()
  const labels: Array<{ label: string; slug: string }> = []

  for (const tag of tags) {
    if (tag === 'Fast-paced') continue // reclassified as filter, not mood
    const mapped = MOOD_TO_PATRON_LABEL[tag]
    if (mapped && !seen.has(mapped.slug)) {
      seen.add(mapped.slug)
      labels.push(mapped)
    }
  }

  return labels
}
