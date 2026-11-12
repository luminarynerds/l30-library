/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export interface RFIDReader {
  id: number
  name: string
  serial_number: string
  location: string | null
  reader_type: string
  status: string
  is_active: boolean
}

export interface RFIDSession {
  id: number
  session_type: string
  reader_id: number
  tags_scanned: number
  is_active: boolean
  started_at: string
  reader_name?: string
}
