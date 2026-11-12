/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Community Types ====================

export interface StaffBio {
  id: number
  staff_name: string
  role: string
  bio: string
  photo_url: string | null
  fun_fact: string | null
  favorite_book: string | null
  years_of_service: number | null
  sort_order: number
}

export interface StaffBioCreate {
  staff_name: string
  role: string
  bio: string
  photo_url?: string | null
  fun_fact?: string | null
  favorite_book?: string | null
  years_of_service?: number | null
  is_visible?: boolean
  sort_order?: number
}

export interface StaffBioUpdate {
  staff_name?: string
  role?: string
  bio?: string
  photo_url?: string | null
  fun_fact?: string | null
  favorite_book?: string | null
  years_of_service?: number | null
  is_visible?: boolean
  sort_order?: number
}

export interface CommunityResource {
  id: number
  title: string
  description: string | null
  resource_type: string
  url: string | null
  file_path: string | null
  category: string
  is_featured: boolean
  is_public: boolean
  view_count: number
  created_by: string
  created_at: string
  updated_at: string
}

export interface CommunityResourceCreate {
  title: string
  description?: string | null
  resource_type: string
  url?: string | null
  file_path?: string | null
  category: string
  is_featured?: boolean
  is_public?: boolean
}

export interface CommunityPartner {
  id: number
  name: string
  description: string | null
  partner_type: string
  contact_name: string | null
  contact_email: string | null
  contact_phone: string | null
  website: string | null
  address: string | null
  city: string | null
  state: string | null
  zip_code: string | null
  logo_url: string | null
  is_active: boolean
  partnership_start_date: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface CommunityPartnerCreate {
  name: string
  description?: string | null
  partner_type: string
  contact_name?: string | null
  contact_email?: string | null
  contact_phone?: string | null
  website?: string | null
  address?: string | null
  city?: string | null
  state?: string | null
  zip_code?: string | null
  logo_url?: string | null
  is_active?: boolean
  partnership_start_date?: string | null
  notes?: string | null
}

export interface CommunityEvent {
  id: number
  title: string
  description: string | null
  event_type: string
  start_date: string
  end_date: string | null
  start_time: string | null
  end_time: string | null
  location: string | null
  address: string | null
  is_virtual: boolean
  virtual_link: string | null
  max_attendees: number | null
  registration_required: boolean
  registration_deadline: string | null
  is_public: boolean
  is_featured: boolean
  image_url: string | null
  organizer: string
  contact_email: string | null
  contact_phone: string | null
  created_at: string
  updated_at: string
}

export interface CommunityEventCreate {
  title: string
  description?: string | null
  event_type: string
  start_date: string
  end_date?: string | null
  start_time?: string | null
  end_time?: string | null
  location?: string | null
  address?: string | null
  is_virtual?: boolean
  virtual_link?: string | null
  max_attendees?: number | null
  registration_required?: boolean
  registration_deadline?: string | null
  is_public?: boolean
  is_featured?: boolean
  image_url?: string | null
  contact_email?: string | null
  contact_phone?: string | null
}

// ==================== Community Functions ====================

// Staff Bios
export async function getStaffBios(): Promise<StaffBio[]> {
  try {
    return await fetchApi<StaffBio[]>('/community/staff')
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch staff bios')
    }
    throw error
  }
}

export async function getStaffBio(staffId: number): Promise<StaffBio> {
  try {
    return await fetchApi<StaffBio>(`/community/staff/${staffId}`)
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch staff bio')
    }
    throw error
  }
}

export async function createStaffBio(token: string, data: StaffBioCreate): Promise<StaffBio> {
  try {
    return await fetchApi<StaffBio>('/community/admin/staff', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create staff bio')
    }
    throw error
  }
}

export async function updateStaffBio(token: string, staffId: number, data: StaffBioUpdate): Promise<StaffBio> {
  try {
    return await fetchApi<StaffBio>(`/community/admin/staff/${staffId}`, {
      method: 'PUT',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update staff bio')
    }
    throw error
  }
}

export async function deleteStaffBio(token: string, staffId: number): Promise<void> {
  try {
    await fetchApi<void>(`/community/admin/staff/${staffId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete staff bio')
    }
    throw error
  }
}

// Community Resources
export async function createResource(token: string, data: CommunityResourceCreate): Promise<CommunityResource> {
  try {
    return await fetchApi<CommunityResource>('/community/resources', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create resource')
    }
    throw error
  }
}

// Community Partners
export async function createPartner(token: string, data: CommunityPartnerCreate): Promise<CommunityPartner> {
  try {
    return await fetchApi<CommunityPartner>('/community/partners', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create partner')
    }
    throw error
  }
}

// Community Events
export async function createCommunityEvent(token: string, data: CommunityEventCreate): Promise<CommunityEvent> {
  try {
    return await fetchApi<CommunityEvent>('/community/events', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create community event')
    }
    throw error
  }
}
