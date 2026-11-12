/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { api } from '@/lib/api-client'

export interface AdminComputer {
  id: number
  name: string
  computer_number: string
  description: string | null
  branch_id: number | null
  branch_name: string | null
  location: string | null
  computer_type: string
  os_type: string | null
  has_internet: boolean
  has_print_release: boolean
  max_session_minutes: number
  installed_software: string[]
  status: string
  is_active: boolean
  created_at: string | null
  updated_at: string | null
  map_x: number | null
  map_y: number | null
  map_floor: string | null
}

export interface AdminComputerListResponse {
  total: number
  skip: number
  limit: number
  items: AdminComputer[]
}

export interface AdminComputerCreate {
  name: string
  computer_number: string
  computer_type: string
  location: string
  description?: string | null
  branch_id?: number | null
  branch_name?: string | null
  os_type?: string | null
  has_internet: boolean
  has_print_release: boolean
  max_session_minutes: number
  installed_software?: string[]
  is_active?: boolean
}

export interface AdminComputerUpdate {
  name?: string
  computer_number?: string
  computer_type?: string
  location?: string
  description?: string | null
  branch_id?: number | null
  branch_name?: string | null
  os_type?: string | null
  has_internet?: boolean
  has_print_release?: boolean
  max_session_minutes?: number
  installed_software?: string[]
  status?: string
  is_active?: boolean
  map_x?: number | null
  map_y?: number | null
  map_floor?: string | null
}

export async function getAdminComputers(): Promise<AdminComputerListResponse> {
  return api.get('/admin/computers')
}

export async function createAdminComputer(data: AdminComputerCreate): Promise<AdminComputer> {
  return api.post('/admin/computers', data)
}

export async function updateAdminComputer(id: number, data: AdminComputerUpdate): Promise<AdminComputer> {
  return api.patch(`/admin/computers/${id}`, data)
}

export async function updateComputerStatus(id: number, status: string): Promise<AdminComputer> {
  return api.patch(`/admin/computers/${id}/status`, { status })
}

export async function deleteAdminComputer(id: number): Promise<void> {
  await api.delete(`/admin/computers/${id}`)
}
