/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'

export interface AttentionItem {
  id: string
  urgency: 'overdue' | 'upcoming' | 'routine'
  title: string
  description: string
  deadline: string | null
  action_label: string
  action_url: string
}

export interface StatusEntry { label: string; value: string; warning: boolean }
export interface StatusArea { title: string; icon: string; entries: StatusEntry[] }
export interface BoardActivityItem { id: number; icon: string; description: string; timestamp: string }
export interface SignOffItem { id: string; title: string; description: string; action_label: string; action_url: string }
export interface ChecklistItem { label: string; done: boolean }
export interface NextMeeting { date: string; time: string; location: string; is_chairing: boolean; relative_time: string | null; checklist: ChecklistItem[] }
export interface UpcomingItem { date: string; title: string; note: string }

export async function getBoardAttention(token: string): Promise<{ items: AttentionItem[] }> {
  return fetchApi('/board/dashboard/attention', { token })
}

export async function getBoardStatus(token: string): Promise<{ areas: StatusArea[] }> {
  return fetchApi('/board/dashboard/status', { token })
}

export async function getBoardActivity(token: string): Promise<{ items: BoardActivityItem[] }> {
  return fetchApi('/board/dashboard/activity', { token })
}

export async function getPresidentSignoffs(token: string): Promise<{ items: SignOffItem[] }> {
  return fetchApi('/board/dashboard/president/signoffs', { token })
}

export async function getPresidentNextMeeting(token: string): Promise<NextMeeting> {
  return fetchApi('/board/dashboard/president/next-meeting', { token })
}

export async function getPresidentUpcoming(token: string): Promise<{ items: UpcomingItem[] }> {
  return fetchApi('/board/dashboard/president/upcoming', { token })
}
