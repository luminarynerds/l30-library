/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export interface CascadeData {
  id: number
  cascade_name: string
  cascade_description?: string | null
  is_active: boolean
  auto_trigger_events?: string[] | null
  manual_approval_required: boolean
  max_contact_levels: number
  created_at: string
}

export interface CascadeContact {
  id: number
  level: number
  contact_role: string
  contact_name: string
  contact_email?: string | null
  contact_phone?: string | null
  contact_method: string
  is_active: boolean
}

export interface CascadeFormState {
  cascade_name: string
  cascade_description: string
  auto_trigger_events: string[]
  manual_approval_required: boolean
  max_contact_levels: number
}

export interface ContactFormState {
  level: number
  contact_role: string
  contact_name: string
  contact_email: string
  contact_phone: string
  contact_method: string
  wait_time_seconds: number
  retry_attempts: number
}

export const INITIAL_CASCADE_FORM: CascadeFormState = {
  cascade_name: "",
  cascade_description: "",
  auto_trigger_events: [],
  manual_approval_required: true,
  max_contact_levels: 5,
}

export const INITIAL_CONTACT_FORM: ContactFormState = {
  level: 1,
  contact_role: "",
  contact_name: "",
  contact_email: "",
  contact_phone: "",
  contact_method: "email",
  wait_time_seconds: 0,
  retry_attempts: 2,
}

export const TRIGGER_EVENTS = [
  { id: "building_closure", label: "Building Closure" },
  { id: "power_outage", label: "Power Outage" },
  { id: "data_loss", label: "Data Loss" },
  { id: "security_incident", label: "Security Incident" },
  { id: "natural_disaster", label: "Natural Disaster" },
  { id: "system_failure", label: "System Failure" },
  { id: "manual_trigger", label: "Manual Trigger" },
]

export const CONTACT_METHODS = [
  { id: "email", label: "Email" },
  { id: "sms", label: "SMS" },
  { id: "phone_call", label: "Phone Call" },
  { id: "all", label: "All Methods" },
]
