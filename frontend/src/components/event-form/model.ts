/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable complexity */

export interface Presenter {
  name: string
  bio: string
  program_partner_id: number | null
}

export interface ProgramPartnerOption {
  id: number
  name: string
}

export interface EventFormData {
  title: string
  description: string
  category: string
  audience: string
  event_language: string
  location: string
  start_time: string
  end_time: string
  registration_required: boolean
  max_attendees: string
  tags: string[]
  image_url: string
  is_featured: boolean
  is_virtual: boolean
  virtual_link: string
  series_id: string
  series_name: string
  branch_id: string
  accessibility_notes: string
  wheelchair_accessible: boolean
  asl_provided: boolean
  captioning_provided: boolean
  assistive_listening: boolean
  sensory_friendly: boolean
  large_print_available: boolean
  lighting: string
  noise_level: string
  crowd_size: string
  quiet_space_available: boolean
  recurrence_rule: string
  presenters: Presenter[]
  min_age: string
  max_age: string
  caregiver_required: boolean
  photos_will_be_taken: boolean
}

export interface EventFormProps {
  onSubmit: (data: EventFormData) => Promise<void>
  onCancel: () => void
  initialData?: Partial<EventFormData> | undefined
  isSubmitting?: boolean
  availableCategories?: string[]
  availableAudiences?: string[]
  availableProgramPartners?: ProgramPartnerOption[]
}

export interface FormErrors {
  title?: string
  start_time?: string
  end_time?: string
  max_attendees?: string
  series?: string
  virtual?: string
  image_url?: string
}

export const ACCESSIBILITY_FLAG_KEYS = [
  'wheelchair_accessible',
  'asl_provided',
  'captioning_provided',
  'assistive_listening',
  'sensory_friendly',
  'large_print_available',
] as const

export function makeDefaultFormData(initial?: Partial<EventFormData>): EventFormData {
  return {
    title: initial?.title || '',
    description: initial?.description || '',
    category: initial?.category || '',
    audience: initial?.audience || '',
    event_language: initial?.event_language || '',
    location: initial?.location || '',
    start_time: initial?.start_time || '',
    end_time: initial?.end_time || '',
    registration_required: initial?.registration_required || false,
    max_attendees: initial?.max_attendees || '',
    tags: initial?.tags || [],
    image_url: initial?.image_url || '',
    is_featured: initial?.is_featured || false,
    is_virtual: initial?.is_virtual || false,
    virtual_link: initial?.virtual_link || '',
    series_id: initial?.series_id || '',
    series_name: initial?.series_name || '',
    branch_id: initial?.branch_id || '',
    accessibility_notes: initial?.accessibility_notes || '',
    wheelchair_accessible: initial?.wheelchair_accessible || false,
    asl_provided: initial?.asl_provided || false,
    captioning_provided: initial?.captioning_provided || false,
    assistive_listening: initial?.assistive_listening || false,
    sensory_friendly: initial?.sensory_friendly || false,
    large_print_available: initial?.large_print_available || false,
    lighting: initial?.lighting || '',
    noise_level: initial?.noise_level || '',
    crowd_size: initial?.crowd_size || '',
    quiet_space_available: initial?.quiet_space_available || false,
    recurrence_rule: initial?.recurrence_rule || '',
    presenters: initial?.presenters || [],
    min_age: initial?.min_age || '',
    max_age: initial?.max_age || '',
    caregiver_required: initial?.caregiver_required || false,
    photos_will_be_taken: initial?.photos_will_be_taken || false,
  }
}
