/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'

export interface ReadingMilestone {
  id: number
  milestone_type: string
  milestone_key: string
  title: string
  description: string | null
  earned_at: string
  dismissed: boolean
}

export async function getMilestones(
  token: string,
  includeDismissed = false,
): Promise<ReadingMilestone[]> {
  return fetchApi<ReadingMilestone[]>('/reading-milestones', {
    token,
    params: { include_dismissed: includeDismissed },
  })
}

export async function dismissMilestone(
  token: string,
  milestoneId: number,
): Promise<void> {
  await fetchApi(`/reading-milestones/${milestoneId}/dismiss`, {
    method: 'POST',
    token,
  })
}
