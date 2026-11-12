/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { parseSubjectsField } from './parseSubjectsField'

/** Hardcoded format facets matching actual catalog data (33 items). */
export const FORMAT_FACETS = [
  { value: 'book', count: 20 },
  { value: 'ebook', count: 8 },
  { value: 'audiobook', count: 2 },
  { value: 'dvd', count: 2 },
  { value: 'cd', count: 0 },
  { value: 'magazine', count: 0 },
  { value: 'game', count: 1 },
  { value: 'kit', count: 4 },
  { value: 'equipment', count: 4 },
]

export const READING_TIME_BRACKETS = [
  { value: 'under_2h', label: 'Under 2 hours', maxPages: 150 },
  { value: '2_to_4h', label: '2\u20134 hours', minPages: 150, maxPages: 300 },
  { value: 'over_4h', label: '4+ hours', minPages: 300 },
] as const

export const ACCESS_FILTERS = [
  { value: 'visual_graphic', label: 'Visual / graphic' },
  { value: 'short_gentle', label: 'Short & gentle (under 200 pages)' },
] as const

export const TOPIC_FILTERS = [
  { value: 'fiction', label: 'Fiction', match: ['Fiction', 'Historical Fiction', 'Science Fiction', 'Canadian Fiction'] },
  { value: 'nonfiction', label: 'Nonfiction', match: ['Self-Help', 'Psychology', 'Technology', 'History', 'Cooking', 'Nature', 'Philosophy'] },
  { value: 'scifi', label: 'Sci-Fi', match: ['Science Fiction'] },
  { value: 'memoir', label: 'Memoir', match: ['Memoir'] },
  { value: 'poetry', label: 'Poetry', match: ['Poetry'] },
  { value: 'lgbtq', label: 'LGBTQ+', match: ['LGBTQ+'] },
  { value: 'neurodiversity', label: 'Neurodiversity', match: ['Neurodiversity', 'Autism', 'ADHD'] },
  { value: 'middle_grade', label: 'Middle Grade', match: ['Middle Grade', 'Juvenile Fiction', "Children's Fiction"] },
  { value: 'young_adult', label: 'Young Adult', match: ['Young Adult', 'Teen Fiction', 'YA Fiction'] },
  { value: 'stem', label: 'STEM & Science', match: ['STEM', 'Astronomy', 'Science', 'Energy'] },
  { value: 'health', label: 'Health & Wellness', match: ['Health', 'Wellness', 'Medical'] },
  { value: 'home', label: 'Home & Garden', match: ['Home', 'Gardening', 'Baking', 'Cooking', 'Kitchen', 'Sustainability'] },
] as const

export function itemMatchesTopic(subjects: string | null, topicValue: string): boolean {
  if (!subjects) return false
  const topic = TOPIC_FILTERS.find(t => t.value === topicValue)
  if (!topic) return false
  // ``parseSubjectsField`` handles comma, semicolon, and legacy array-literal
  // shapes -- the previous comma-only split silently missed semicolon-
  // delimited rows in production data.
  const subjectList = parseSubjectsField(subjects)
  return topic.match.some(m => subjectList.some(s => s.toLowerCase().includes(m.toLowerCase())))
}

export function itemMatchesReadingTime(pageCount: number | null, bracket: string): boolean {
  if (pageCount === null || pageCount === undefined) return false
  const b = READING_TIME_BRACKETS.find(r => r.value === bracket)
  if (!b) return false
  if ('minPages' in b && 'maxPages' in b) return pageCount >= b.minPages && pageCount < b.maxPages
  if ('maxPages' in b) return pageCount < b.maxPages
  if ('minPages' in b) return pageCount >= b.minPages
  return false
}

export function itemMatchesAccess(
  item: { title: string; item_type: string; subjects: string | null; page_count: number | null },
  accessValue: string,
  allItems: Array<{ title: string; item_type: string }>
): boolean {
  switch (accessValue) {
    case 'has_audio':
      return allItems.some(
        other => other.item_type === 'audiobook' &&
        other.title.toLowerCase() === item.title.toLowerCase()
      )
    case 'visual_graphic':
      return (item.subjects || '').toLowerCase().includes('graphic novel')
    case 'short_gentle':
      return (item.page_count ?? 999) <= 200
    default:
      return false
  }
}
