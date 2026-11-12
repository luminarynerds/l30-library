/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'

export async function getPatronTags(token: string): Promise<string[]> {
  return fetchApi<string[]>('/patron-tags', { token })
}

export async function renamePatronTag(
  token: string,
  oldName: string,
  newName: string,
): Promise<{ updated: number }> {
  return fetchApi<{ updated: number }>('/patron-tags/rename', {
    method: 'PUT',
    token,
    body: { old_name: oldName, new_name: newName },
  })
}

export async function deletePatronTag(
  token: string,
  tagName: string,
): Promise<{ updated: number }> {
  return fetchApi<{ updated: number }>(`/patron-tags/${encodeURIComponent(tagName)}`, {
    method: 'DELETE',
    token,
  })
}
