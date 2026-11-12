/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'

export interface ReadingGoal {
  id: number
  year: number
  target_books: number
  created_at: string
  updated_at: string
}

export interface ReadingGoalProgress {
  year: number
  target_books: number
  finished_count: number
  percent: number
}

export async function getReadingGoals(token: string): Promise<ReadingGoal[]> {
  return fetchApi<ReadingGoal[]>('/reading-goals', { token })
}

export async function getGoalProgress(
  token: string,
  year: number,
): Promise<ReadingGoalProgress> {
  return fetchApi<ReadingGoalProgress>(`/reading-goals/${year}/progress`, { token })
}

export async function setReadingGoal(
  token: string,
  year: number,
  targetBooks: number,
): Promise<ReadingGoal> {
  return fetchApi<ReadingGoal>(`/reading-goals/${year}`, {
    method: 'PUT',
    token,
    body: { target_books: targetBooks },
  })
}

export async function removeReadingGoal(
  token: string,
  year: number,
): Promise<void> {
  await fetchApi(`/reading-goals/${year}`, { method: 'DELETE', token })
}

export function downloadShelfExport(token: string, format: 'csv' | 'json' = 'json') {
  const baseUrl = import.meta.env.VITE_API_URL || '/api/v1'
  const url = `${baseUrl}/shelf-export?format=${format}`

  // Use a hidden link to trigger browser download with auth header via fetch
  fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  })
    .then((res) => {
      if (!res.ok) throw new Error('Export failed')
      const disposition = res.headers.get('Content-Disposition') || ''
      const match = disposition.match(/filename="(.+)"/)
      const filename = match?.[1] || `reading_shelf.${format}`
      return res.blob().then((blob) => ({ blob, filename }))
    })
    .then(({ blob, filename }) => {
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = filename
      a.click()
      URL.revokeObjectURL(a.href)
    })
}
