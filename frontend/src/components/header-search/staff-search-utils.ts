/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export type StaffSearchEntityType = 'patron' | 'item' | 'order' | 'event' | 'staff'

export interface StaffSearchResult {
  id: string
  type: StaffSearchEntityType
  title: string
  subtitle: string
  route: string
  searchableText: string
  score?: number
}

export function normalizeText(value: string): string {
  return value.toLowerCase().trim()
}

function levenshteinDistance(a: string, b: string): number {
  if (a.length === 0) return b.length
  if (b.length === 0) return a.length

  const matrix = Array.from({ length: b.length + 1 }, () => Array(a.length + 1).fill(0))

  for (let i = 0; i <= b.length; i += 1) matrix[i]![0] = i
  for (let j = 0; j <= a.length; j += 1) matrix[0]![j] = j

  for (let i = 1; i <= b.length; i += 1) {
    for (let j = 1; j <= a.length; j += 1) {
      const cost = b[i - 1] === a[j - 1] ? 0 : 1
      matrix[i]![j] = Math.min(
        matrix[i - 1]![j]! + 1,
        matrix[i]![j - 1]! + 1,
        matrix[i - 1]![j - 1]! + cost
      )
    }
  }

  return matrix[b.length]![a.length]!
}

export function fuzzyScore(query: string, candidate: string): number {
  const normalizedQuery = normalizeText(query)
  const normalizedCandidate = normalizeText(candidate)

  if (!normalizedQuery || !normalizedCandidate) return 0
  if (normalizedCandidate.includes(normalizedQuery)) return 1

  const queryTokens = normalizedQuery.split(/\s+/).filter(Boolean)
  const candidateTokens = normalizedCandidate.split(/\s+/).filter(Boolean)

  const tokenScore = queryTokens.reduce((acc, queryToken) => {
    const bestToken = candidateTokens.reduce((best, candidateToken) => {
      if (candidateToken.includes(queryToken)) {
        return Math.max(best, 0.95)
      }
      const distance = levenshteinDistance(queryToken, candidateToken)
      const maxLen = Math.max(queryToken.length, candidateToken.length)
      const similarity = maxLen ? 1 - distance / maxLen : 0
      return Math.max(best, similarity)
    }, 0)

    return acc + bestToken
  }, 0)

  return tokenScore / queryTokens.length
}

export function rankStaffSearchResults(query: string, results: StaffSearchResult[]): StaffSearchResult[] {
  return results
    .map((result) => ({
      ...result,
      score: fuzzyScore(query, `${result.title} ${result.subtitle} ${result.searchableText}`),
    }))
    .filter((result) => (result.score ?? 0) >= 0.45)
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
}

export function buildDidYouMean(query: string, results: StaffSearchResult[]): string | null {
  if (!query || results.length === 0) return null
  const best = results[0]!
  if (!best.score || best.score >= 0.9) return null
  return best.title
}

export const STAFF_TYPE_FILTERS: Array<{ value: 'all' | StaffSearchEntityType; label: string }> = [
  { value: 'all', label: 'All' },
  { value: 'page' as StaffSearchEntityType, label: 'Pages & Tools' },
  { value: 'patron', label: 'Patrons' },
  { value: 'staff', label: 'Staff' },
  { value: 'item', label: 'Items' },
  { value: 'order', label: 'Orders' },
  { value: 'event', label: 'Events' },
]
