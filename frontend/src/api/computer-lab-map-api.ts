/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { api } from '@/lib/api-client'

export interface LabMapStation {
  id: number
  name: string
  computer_number: string
  location: string | null
  computer_type: string
  status: 'available' | 'in_use' | 'maintenance' | 'offline' | 'reserved'
  map_x: number | null
  map_y: number | null
  map_floor: string | null
  available_at: string | null
}

export interface LabMapResponse {
  stations: LabMapStation[]
  generated_at: string
}

export async function getLabMap(): Promise<LabMapResponse> {
  return api.get('/computers/lab-map')
}
