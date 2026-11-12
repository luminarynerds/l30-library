/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export { API_BASE } from '@/api/types'
export type { MessageResponse } from '@/api/types'

export type ApiResponse<T> = {
  success: true
  data: T
} | {
  success: false
  error: string
}
