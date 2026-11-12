/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { apiClient } from '@/lib/api-client'

export interface ActiveReadingProgram {
  id: number
  name: string
  description: string | null
  program_type: string
  age_group: string | null
  start_date: string
  end_date: string
  enrollment_count: number
  reading_goal_type: string | null
  reading_goal_value: number | null
}

export function getActiveReadingPrograms(): Promise<ActiveReadingProgram[]> {
  return apiClient<ActiveReadingProgram[]>('/youth/active-reading-programs')
}

export interface UpcomingYouthEvent {
  id: number
  title: string
  program_date: string
  start_time: string
  end_time: string | null
  location_name: string | null
  audience: string
  registration_count: number
  capacity: number | null
}

export function getUpcomingYouthEvents(limit = 4): Promise<UpcomingYouthEvent[]> {
  return apiClient<UpcomingYouthEvent[]>('/youth/upcoming-events', {
    params: { limit },
  })
}


export interface MyReadingProgressData {
  enrolled_programs: {
    program_name: string
    goal_type: string | null
    goal_target: number | null
    start_date: string
    end_date: string
    progress_minutes: number
    log_count: number
  }[]
  books_read_count: number
  total_reading_minutes: number
}

export function getMyReadingProgress(): Promise<MyReadingProgressData> {
  return apiClient<MyReadingProgressData>('/youth/my-reading-progress')
}
