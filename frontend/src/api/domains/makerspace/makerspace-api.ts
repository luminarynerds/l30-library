/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable max-lines */
import { fetchApi, isApiError } from '@/lib/api-client'
import type { components } from '@/api/generated/schema';

// ==================== Types ====================

export type ResourceType =
  | '3d_printer'
  | 'laser_cutter'
  | 'cnc_router'
  | 'vinyl_cutter'
  | 'embroidery_machine'
  | 'sewing_machine'
  | 'soldering_station'
  | 'electronics_workbench'
  | 'woodworking_station'
  | 'recording_studio'
  | 'video_editing_station'
  | 'vr_station'
  | 'other'

export type ResourceStatus = components['schemas']['ResourceStatus'];
export type ReservationStatus = 'pending' | 'confirmed' | 'checked_in' | 'completed' | 'cancelled' | 'no_show' | 'expired'

export type JobStatus =
  | 'submitted'
  | 'pending_review'
  | 'rejected'
  | 'approved'
  | 'queued'
  | 'in_progress'
  | 'paused'
  | 'failed'
  | 'completed'
  | 'ready_pickup'
  | 'picked_up'
  | 'cancelled'

export type CertificationStatus = components['schemas']['CertificationStatus'];
export type PaymentStatus = components['schemas']['PaymentStatus'];
export type WaitlistStatus = 'waiting' | 'notified' | 'expired' | 'cancelled' | 'fulfilled'

export type WorkshopStatus = components['schemas']['WorkshopStatus'];
export type WorkshopLevel = components['schemas']['WorkshopLevel'];
export type RegistrationStatus = 'registered' | 'waitlisted' | 'confirmed' | 'attended' | 'no_show' | 'cancelled'

export interface MakerspaceResource {
  id: number
  name: string
  description: string | null
  resource_type: ResourceType
  location: string | null
  asset_tag: string | null
  status: ResourceStatus
  requires_certification: boolean
  certification_type_id: number | null
  minimum_age: number
  hourly_cost: string
  setup_fee: string
  max_reservation_hours: number
  min_reservation_hours: number
  available_from: string
  available_until: string
  available_days: number[]
  build_volume_x: number | null
  build_volume_y: number | null
  build_volume_z: number | null
  supported_materials: string | null
  supported_file_formats: string | null
  image_url: string | null
  total_reservations: number
  total_hours_used: string
  total_revenue: string
  last_maintenance_date: string | null
  next_maintenance_date: string | null
  is_active: boolean
  created_at: string
}

export interface ResourceSummary {
  id: number
  name: string
  resource_type: ResourceType
  status: ResourceStatus
  location: string | null
  hourly_cost: string
  requires_certification: boolean
  certification_type_id: number | null
}

export interface TimeSlot {
  start_time: string
  end_time: string
  is_available: boolean
  reservation_id: number | null
}

export interface AvailabilityResponse {
  resource_id: number
  date: string
  slots: TimeSlot[]
}

export interface CertificationType {
  id: number
  name: string
  description: string | null
  training_duration_hours: string
  requires_safety_quiz: boolean
  passing_score: number
  validity_months: number
  certification_fee: string
  renewal_fee: string
  training_materials_url: string | null
  safety_video_url: string | null
  is_active: boolean
  created_at: string
}

export interface Certification {
  id: number
  user_id: number
  certification_type_id: number
  status: CertificationStatus
  training_completed_at: string | null
  quiz_score: number | null
  quiz_attempts: number
  certified_at: string | null
  expires_at: string | null
  certified_by_id: number | null
  suspended_at: string | null
  suspended_reason: string | null
  renewal_count: number
  notes: string | null
  created_at: string
  certification_type_name?: string
  user_name?: string
}

export interface Reservation {
  id: number
  user_id: number | null
  resource_id: number
  status: ReservationStatus
  start_time: string
  end_time: string
  checked_in_at: string | null
  checked_out_at: string | null
  project_name: string | null
  project_description: string | null
  estimated_cost: string
  actual_cost: string | null
  consumables_cost: string
  payment_status: PaymentStatus
  notes: string | null
  created_at: string
  user_name?: string
  user_email?: string
  resource_name?: string
  resource_type?: ResourceType
}

export interface ReservationCreate {
  resource_id: number
  start_time: string
  end_time: string
  project_name?: string
  project_description?: string
  notes?: string
}

export interface Job {
  id: number
  job_number: string
  user_id: number | null
  resource_id: number | null
  status: JobStatus
  priority: 'low' | 'normal' | 'high' | 'urgent'
  queue_position: number | null
  project_name: string
  project_description: string | null
  file_name: string | null
  file_size_bytes: number | null
  file_format: string | null
  material_type: string | null
  material_color: string | null
  infill_percentage: number | null
  layer_height: string | null
  supports_needed: boolean
  estimated_print_time_minutes: number | null
  estimated_material_grams: string | null
  actual_print_time_minutes: number | null
  actual_material_grams: string | null
  estimated_cost: string
  actual_cost: string | null
  material_cost: string
  machine_time_cost: string
  payment_status: PaymentStatus
  rejection_reason: string | null
  contact_email: string | null
  contact_phone: string | null
  notes: string | null
  created_at: string
  user_name?: string
  user_email?: string
  resource_name?: string
}

export interface JobCreate {
  resource_id?: number
  project_name: string
  project_description?: string
  material_type?: string
  material_color?: string
  infill_percentage?: number
  layer_height?: string
  supports_needed?: boolean
  contact_email?: string
  contact_phone?: string
  notes?: string
}

export interface CostEstimate {
  machine_time_hours: string
  machine_time_cost: string
  consumables_cost: string
  setup_fee: string
  total_cost: string
  breakdown: Array<{ item: string; cost: string }>
}

export interface QueueItem {
  position: number
  job_number: string
  status: string
  estimated_time_minutes: number | null
  resource_name: string | null
  submitted_at: string | null
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
}

// ==================== Operating Hours & Dynamic Availability ====================

export interface ResourceOperatingHours {
  resource_id: number
  resource_name: string
  available_from: string
  available_until: string
  available_days: number[]
  buffer_minutes: number
  min_reservation_hours: number
  max_reservation_hours: number
}

export interface DynamicTimeSlot {
  start_time: string
  end_time: string
  is_available: boolean
  is_past: boolean
  reservation_id: number | null
}

export interface DynamicAvailabilityResponse {
  resource_id: number
  resource_name: string
  date: string
  operating_hours: ResourceOperatingHours
  slots: DynamicTimeSlot[]
  waitlist_count: number
}

// ==================== Waitlist Types ====================

export interface WaitlistEntry {
  id: number
  user_id: number
  resource_id: number
  preferred_date: string
  preferred_start_time: string | null
  preferred_end_time: string | null
  flexible_dates: boolean
  status: WaitlistStatus
  position: number | null
  notified_at: string | null
  notification_expires_at: string | null
  notify_email: boolean
  notify_sms: boolean
  contact_phone: string | null
  notes: string | null
  created_at: string
  updated_at: string | null
  user_name?: string
  user_email?: string
  resource_name?: string
  resource_type?: string
}

export interface WaitlistCreate {
  resource_id: number
  preferred_date: string
  preferred_start_time?: string
  preferred_end_time?: string
  flexible_dates?: boolean
  notify_email?: boolean
  notify_sms?: boolean
  contact_phone?: string
  notes?: string
}

export interface WaitlistPosition {
  waitlist_id: number
  position: number
  total_waiting: number
  estimated_wait: string | null
}

// ==================== Workshop Types ====================

export interface Workshop {
  id: number
  title: string
  description: string | null
  short_description: string | null
  is_certification_training: boolean
  certification_type_id: number | null
  start_time: string
  end_time: string
  duration_minutes: number
  location: string | null
  room_id: number | null
  is_virtual: boolean
  virtual_meeting_url: string | null
  max_participants: number
  min_participants: number
  current_participants: number
  allow_waitlist: boolean
  waitlist_count: number
  instructor_id: number | null
  instructor_name: string | null
  instructor_bio: string | null
  skill_level: WorkshopLevel
  prerequisites: string | null
  age_requirement: number
  required_materials: string | null
  fee: string
  materials_fee: string
  materials_included: boolean
  registration_opens_at: string | null
  registration_closes_at: string | null
  registration_required: boolean
  cancellation_deadline_hours: number
  status: WorkshopStatus
  resources_used: string | null
  image_url: string | null
  syllabus_url: string | null
  materials_list_url: string | null
  tags: string[] | null
  created_by_id: number | null
  created_at: string
  updated_at: string | null
  certification_type_name?: string
  instructor_user_name?: string
  room_name?: string
  spots_remaining?: number
  is_full?: boolean
  is_registration_open?: boolean
}

export interface WorkshopSummary {
  id: number
  title: string
  short_description: string | null
  start_time: string
  end_time: string
  location: string | null
  is_virtual: boolean
  skill_level: WorkshopLevel
  fee: string
  max_participants: number
  current_participants: number
  spots_remaining: number
  is_full: boolean
  has_waitlist: boolean
  waitlist_count: number
  is_certification_training: boolean
  certification_type_id: number | null
  instructor_name: string | null
  image_url: string | null
  tags: string[] | null
  status: WorkshopStatus
}

export interface WorkshopRegistration {
  id: number
  workshop_id: number
  user_id: number
  status: RegistrationStatus
  waitlist_position: number | null
  contact_email: string | null
  contact_phone: string | null
  payment_status: PaymentStatus
  amount_paid: string
  checked_in_at: string | null
  certification_awarded_id: number | null
  cancelled_at: string | null
  cancellation_reason: string | null
  refund_issued: boolean
  confirmation_sent_at: string | null
  reminder_sent_at: string | null
  notes: string | null
  created_at: string
  updated_at: string | null
}

export interface WorkshopRegistrationCreate {
  workshop_id: number
  contact_email?: string
  contact_phone?: string
  notes?: string
}

export interface MyWorkshopRegistration {
  registration_id: number
  workshop_id: number
  workshop_title: string
  workshop_start_time: string
  workshop_end_time: string
  workshop_location: string | null
  is_virtual: boolean
  virtual_meeting_url: string | null
  status: RegistrationStatus
  waitlist_position: number | null
  is_waitlisted: boolean
  confirmation_sent: boolean
  reminder_sent: boolean
}

// ==================== Resource Functions ====================

export async function getResources(params?: {
  resource_type?: ResourceType
  status?: ResourceStatus
  page?: number
  per_page?: number
}): Promise<PaginatedResponse<ResourceSummary>> {
  const searchParams = new URLSearchParams()
  if (params?.resource_type) searchParams.set('resource_type', params.resource_type)
  if (params?.status) searchParams.set('status', params.status)
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.per_page) searchParams.set('per_page', String(params.per_page))

  const query = searchParams.toString()
  const raw = await fetchApi<{ data: ResourceSummary[]; pagination: { page: number; per_page: number; total: number } }>(
    `/makerspace/resources${query ? `?${query}` : ''}`
  )
  return {
    items: raw.data,
    total: raw.pagination.total,
    page: raw.pagination.page,
    per_page: raw.pagination.per_page,
  }
}

export async function getResource(resourceId: number): Promise<MakerspaceResource> {
  return await fetchApi<MakerspaceResource>(`/makerspace/resources/${resourceId}`)
}

export async function getResourceAvailability(
  resourceId: number,
  date: string,
  slotDurationMinutes = 60
): Promise<AvailabilityResponse> {
  return await fetchApi<AvailabilityResponse>(
    `/makerspace/resources/${resourceId}/availability?target_date=${date}&slot_duration_minutes=${slotDurationMinutes}`
  )
}

export async function getResourceTypes(): Promise<Array<{ value: string; label: string }>> {
  return await fetchApi<Array<{ value: string; label: string }>>('/makerspace/resource-types')
}

// ==================== Certification Functions ====================

export async function getCertificationTypes(): Promise<CertificationType[]> {
  return await fetchApi<CertificationType[]>('/makerspace/certifications/types')
}

export async function getCertificationType(typeId: number): Promise<CertificationType> {
  return await fetchApi<CertificationType>(`/makerspace/certifications/types/${typeId}`)
}

export async function getMyCertifications(
  token: string,
  status?: CertificationStatus
): Promise<Certification[]> {
  const params = status ? `?status=${status}` : ''
  return await fetchApi<Certification[]>(`/makerspace/my/certifications${params}`, { token })
}

export async function enrollInCertification(
  token: string,
  certificationTypeId: number
): Promise<Certification> {
  return await fetchApi<Certification>(`/makerspace/certifications/enroll/${certificationTypeId}`, {
    method: 'POST',
    token,
  })
}

export async function completeTraining(
  token: string,
  certificationId: number
): Promise<Certification> {
  return await fetchApi<Certification>(
    `/makerspace/certifications/${certificationId}/complete-training`,
    {
      method: 'POST',
      token,
    }
  )
}

export async function submitQuiz(
  token: string,
  certificationId: number,
  answers: Record<string, string | number>
): Promise<{ score: number; passed: boolean; passing_score: number; feedback?: Record<string, string> }> {
  return await fetchApi(`/makerspace/certifications/${certificationId}/submit-quiz`, {
    method: 'POST',
    token,
    body: { answers },
  })
}

// ==================== Reservation Functions ====================

export async function getMyReservations(
  token: string,
  params?: {
    status?: ReservationStatus
    start_date?: string
    end_date?: string
    page?: number
    per_page?: number
  }
): Promise<PaginatedResponse<Reservation>> {
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set('status', params.status)
  if (params?.start_date) searchParams.set('start_date', params.start_date)
  if (params?.end_date) searchParams.set('end_date', params.end_date)
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.per_page) searchParams.set('per_page', String(params.per_page))

  const query = searchParams.toString()
  return await fetchApi<PaginatedResponse<Reservation>>(
    `/makerspace/my/reservations${query ? `?${query}` : ''}`,
    { token }
  )
}

export async function createReservation(
  token: string,
  data: ReservationCreate
): Promise<Reservation> {
  try {
    return await fetchApi<Reservation>('/makerspace/reservations', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create reservation')
    }
    throw error
  }
}

export async function getReservation(token: string, reservationId: number): Promise<Reservation> {
  return await fetchApi<Reservation>(`/makerspace/reservations/${reservationId}`, { token })
}

export async function cancelReservation(
  token: string,
  reservationId: number,
  reason?: string
): Promise<void> {
  const params = reason ? `?reason=${encodeURIComponent(reason)}` : ''
  await fetchApi(`/makerspace/reservations/${reservationId}${params}`, {
    method: 'DELETE',
    token,
    skipJsonParse: true,
  })
}

// ==================== Job Queue Functions ====================

export async function getMyJobs(
  token: string,
  params?: {
    status?: JobStatus
    page?: number
    per_page?: number
  }
): Promise<PaginatedResponse<Job>> {
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set('status', params.status)
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.per_page) searchParams.set('per_page', String(params.per_page))

  const query = searchParams.toString()
  return await fetchApi<PaginatedResponse<Job>>(
    `/makerspace/my/jobs${query ? `?${query}` : ''}`,
    { token }
  )
}

export async function submitJob(token: string, data: JobCreate): Promise<Job> {
  try {
    return await fetchApi<Job>('/makerspace/jobs', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to submit job')
    }
    throw error
  }
}

export async function uploadJobFile(
  token: string,
  jobId: number,
  file: File
): Promise<{ message: string; file_name: string; file_size: number }> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(
    `${import.meta.env.VITE_API_URL || '/api/v1'}/makerspace/jobs/upload?job_id=${jobId}`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    }
  )

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to upload file')
  }

  return response.json()
}

export async function getJob(token: string, jobId: number): Promise<Job> {
  return await fetchApi<Job>(`/makerspace/jobs/${jobId}`, { token })
}

export async function getJobByNumber(token: string, jobNumber: string): Promise<Job> {
  return await fetchApi<Job>(`/makerspace/jobs/number/${jobNumber}`, { token })
}

export async function cancelJob(token: string, jobId: number, reason?: string): Promise<void> {
  const params = reason ? `?reason=${encodeURIComponent(reason)}` : ''
  await fetchApi(`/makerspace/jobs/${jobId}${params}`, {
    method: 'DELETE',
    token,
    skipJsonParse: true,
  })
}

export async function getQueueStatus(resourceId?: number): Promise<{ queue: QueueItem[]; total_jobs: number }> {
  const params = resourceId ? `?resource_id=${resourceId}` : ''
  return await fetchApi(`/makerspace/queue${params}`)
}

// ==================== Cost Calculation ====================

export async function calculateCost(
  resourceId: number,
  durationHours: number,
  consumables?: Array<{ consumable_id: number; quantity_used: number }>
): Promise<CostEstimate> {
  return await fetchApi<CostEstimate>('/makerspace/calculate-cost', {
    method: 'POST',
    body: {
      resource_id: resourceId,
      duration_hours: durationHours,
      consumables,
    },
  })
}

// ==================== Operating Hours & Dynamic Availability Functions ====================

export async function getResourceOperatingHours(resourceId: number): Promise<ResourceOperatingHours> {
  return await fetchApi<ResourceOperatingHours>(`/makerspace/resources/${resourceId}/operating-hours`)
}

export async function getDynamicAvailability(
  resourceId: number,
  date: string,
  slotDurationMinutes = 60
): Promise<DynamicAvailabilityResponse> {
  return await fetchApi<DynamicAvailabilityResponse>(
    `/makerspace/resources/${resourceId}/dynamic-availability?target_date=${date}&slot_duration_minutes=${slotDurationMinutes}`
  )
}

// ==================== Waitlist Functions ====================

export async function getMyWaitlistEntries(
  token: string,
  status?: WaitlistStatus
): Promise<WaitlistEntry[]> {
  const params = status ? `?status=${status}` : ''
  return await fetchApi<WaitlistEntry[]>(`/makerspace/my/waitlist${params}`, { token })
}

export async function joinWaitlist(
  token: string,
  data: WaitlistCreate
): Promise<WaitlistEntry> {
  try {
    return await fetchApi<WaitlistEntry>('/makerspace/waitlist', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to join waitlist')
    }
    throw error
  }
}

export async function getMakerspaceWaitlistPosition(
  token: string,
  waitlistId: number
): Promise<WaitlistPosition> {
  return await fetchApi<WaitlistPosition>(`/makerspace/waitlist/${waitlistId}/position`, { token })
}

export async function leaveWaitlist(token: string, waitlistId: number): Promise<void> {
  await fetchApi(`/makerspace/waitlist/${waitlistId}`, {
    method: 'DELETE',
    token,
    skipJsonParse: true,
  })
}

// ==================== Workshop Functions ====================

export async function getWorkshops(params?: {
  skill_level?: WorkshopLevel
  is_certification_training?: boolean
  start_date?: string
  end_date?: string
  page?: number
  per_page?: number
}): Promise<PaginatedResponse<WorkshopSummary>> {
  const searchParams = new URLSearchParams()
  if (params?.skill_level) searchParams.set('skill_level', params.skill_level)
  if (params?.is_certification_training !== undefined) {
    searchParams.set('is_certification_training', String(params.is_certification_training))
  }
  if (params?.start_date) searchParams.set('start_date', params.start_date)
  if (params?.end_date) searchParams.set('end_date', params.end_date)
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.per_page) searchParams.set('per_page', String(params.per_page))

  const query = searchParams.toString()
  return await fetchApi<PaginatedResponse<WorkshopSummary>>(
    `/makerspace/workshops${query ? `?${query}` : ''}`
  )
}

export async function getWorkshop(workshopId: number): Promise<Workshop> {
  return await fetchApi<Workshop>(`/makerspace/workshops/${workshopId}`)
}

export async function registerForWorkshop(
  token: string,
  workshopId: number,
  data?: WorkshopRegistrationCreate
): Promise<WorkshopRegistration> {
  try {
    return await fetchApi<WorkshopRegistration>(`/makerspace/workshops/${workshopId}/register`, {
      method: 'POST',
      token,
      body: data || { workshop_id: workshopId },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to register for workshop')
    }
    throw error
  }
}

export async function getMyWorkshopRegistrations(
  token: string,
  includePast = false
): Promise<MyWorkshopRegistration[]> {
  const params = includePast ? '?include_past=true' : ''
  return await fetchApi<MyWorkshopRegistration[]>(`/makerspace/my/workshops${params}`, { token })
}

export async function cancelWorkshopRegistration(
  token: string,
  workshopId: number,
  reason?: string
): Promise<void> {
  const params = reason ? `?reason=${encodeURIComponent(reason)}` : ''
  await fetchApi(`/makerspace/workshops/${workshopId}/registration${params}`, {
    method: 'DELETE',
    token,
    skipJsonParse: true,
  })
}

// ==================== Staff Certification Functions ====================

export interface StaffCertificationListItem extends Certification {
  certification_type_name?: string
  user_name?: string
}

export interface StaffCertificationListResponse {
  items: StaffCertificationListItem[]
  total: number
  page: number
  per_page: number
}

export async function getStaffCertifications(
  token: string,
  params?: {
    user_id?: number
    certification_type_id?: number
    status?: CertificationStatus
    page?: number
    per_page?: number
  }
): Promise<StaffCertificationListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.user_id) searchParams.set('user_id', String(params.user_id))
  if (params?.certification_type_id) searchParams.set('certification_type_id', String(params.certification_type_id))
  if (params?.status) searchParams.set('status', params.status)
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.per_page) searchParams.set('per_page', String(params.per_page))

  const query = searchParams.toString()
  return await fetchApi<StaffCertificationListResponse>(
    `/staff/makerspace/certifications${query ? `?${query}` : ''}`,
    { token }
  )
}

export async function getExpiringCertifications(
  token: string,
  days = 30
): Promise<StaffCertificationListItem[]> {
  return await fetchApi<StaffCertificationListItem[]>(
    `/staff/makerspace/certifications/expiring?days=${days}`,
    { token }
  )
}

export async function certifyUser(
  token: string,
  userId: number,
  certificationTypeId: number,
  notes?: string
): Promise<Certification> {
  const params = new URLSearchParams()
  params.set('certification_type_id', String(certificationTypeId))
  if (notes) params.set('notes', notes)

  return await fetchApi<Certification>(
    `/staff/makerspace/certifications/${userId}/certify?${params.toString()}`,
    { method: 'POST', token }
  )
}

export async function suspendCertification(
  token: string,
  certificationId: number,
  reason: string
): Promise<{ message: string }> {
  return await fetchApi<{ message: string }>(
    `/staff/makerspace/certifications/${certificationId}/suspend?reason=${encodeURIComponent(reason)}`,
    { method: 'POST', token }
  )
}

export async function reinstateCertification(
  token: string,
  certificationId: number,
  notes?: string
): Promise<{ message: string }> {
  const params = notes ? `?notes=${encodeURIComponent(notes)}` : ''
  return await fetchApi<{ message: string }>(
    `/staff/makerspace/certifications/${certificationId}/reinstate${params}`,
    { method: 'POST', token }
  )
}

// ==================== Staff Resource Types ====================

export interface MakerspaceResourceCreate {
  name: string
  description?: string
  resource_type: ResourceType
  location?: string
  asset_tag?: string
  status?: ResourceStatus
  requires_certification?: boolean
  certification_type_id?: number
  minimum_age?: number
  hourly_cost?: string
  setup_fee?: string
  max_reservation_hours?: number
  min_reservation_hours?: number
  available_from?: string
  available_until?: string
  available_days?: number[]
  build_volume_x?: number
  build_volume_y?: number
  build_volume_z?: number
  supported_materials?: string
  supported_file_formats?: string
  image_url?: string
}

export interface CertificationTypeCreate {
  name: string
  description?: string
  training_duration_hours?: string
  requires_safety_quiz?: boolean
  passing_score?: number
  validity_months?: number
  certification_fee?: string
  renewal_fee?: string
  training_materials_url?: string
  safety_video_url?: string
}

// ==================== Staff Reservation Types ====================

export interface ReservationCheckIn {
  notes?: string
}

export interface ReservationCheckOut {
  notes?: string
  consumable_usage?: ConsumableUsageCreate[]
}

export interface ConsumableUsageCreate {
  consumable_id: number
  quantity_used: number
}

// ==================== Staff Job Types ====================

export type JobPriority = components['schemas']['JobPriority'];
export interface JobReview {
  approved: boolean
  notes?: string
  rejection_reason?: string
  estimated_print_time_minutes?: number
  estimated_material_grams?: string
  estimated_cost?: string
  priority?: JobPriority
}

export interface JobComplete {
  actual_print_time_minutes: number
  actual_material_grams: string
  notes?: string
  consumable_usage?: ConsumableUsageCreate[]
}

export interface JobPickup {
  notes?: string
}

// ==================== Staff Consumable Types ====================

export type ConsumableUnit = components['schemas']['ConsumableUnit'];
export interface Consumable {
  id: number
  name: string
  description: string | null
  sku: string | null
  category: string | null
  material_type: string | null
  color: string | null
  diameter_mm: string | null
  unit: ConsumableUnit
  quantity_in_stock: string
  reorder_threshold: string
  reorder_quantity: string
  cost_per_unit: string
  price_per_unit: string
  supplier_name: string | null
  supplier_sku: string | null
  compatible_resources: string | null
  is_active: boolean
  last_order_date: string | null
  created_at: string
  updated_at: string | null
}

export interface ConsumableCreate {
  name: string
  description?: string
  sku?: string
  category?: string
  material_type?: string
  color?: string
  diameter_mm?: string
  unit?: ConsumableUnit
  quantity_in_stock?: string
  reorder_threshold?: string
  reorder_quantity?: string
  cost_per_unit?: string
  price_per_unit?: string
  supplier_name?: string
  supplier_sku?: string
  compatible_resources?: string
}

export interface ConsumableStockAdjustment {
  quantity: string
  reason: string
}

// ==================== Staff Incident Types ====================

export type IncidentSeverity = 'minor' | 'moderate' | 'serious' | 'critical';
export interface SafetyIncident {
  id: number
  incident_number: string
  resource_id: number | null
  reported_by_id: number | null
  involved_user_id: number | null
  incident_date: string
  severity: IncidentSeverity
  title: string
  description: string
  location: string | null
  injuries_reported: boolean
  injury_description: string | null
  equipment_damage: boolean
  damage_description: string | null
  immediate_action_taken: string | null
  first_aid_administered: boolean
  emergency_services_called: boolean
  investigated_by_id: number | null
  investigation_notes: string | null
  root_cause: string | null
  corrective_actions: string | null
  corrective_action_deadline: string | null
  corrective_action_completed_at: string | null
  follow_up_required: boolean
  follow_up_notes: string | null
  is_resolved: boolean
  resolved_at: string | null
  resolved_by_id: number | null
  created_at: string
  updated_at: string | null
  resource_name?: string
}

export interface SafetyIncidentCreate {
  resource_id?: number
  incident_date: string
  severity?: IncidentSeverity
  title: string
  description: string
  location?: string
  injuries_reported?: boolean
  injury_description?: string
  equipment_damage?: boolean
  damage_description?: string
  immediate_action_taken?: string
  first_aid_administered?: boolean
  emergency_services_called?: boolean
  involved_user_id?: number
}

export interface SafetyIncidentResolve {
  resolution_notes?: string
}

// ==================== Staff Maintenance Types ====================

export type MaintenanceType = 'preventive' | 'corrective' | 'emergency' | 'calibration' | 'cleaning'

export type MaintenanceStatus = 'scheduled' | 'in_progress' | 'completed' | 'cancelled' | 'overdue'

export interface Maintenance {
  id: number
  resource_id: number
  maintenance_type: MaintenanceType
  status: MaintenanceStatus
  scheduled_date: string
  scheduled_by_id: number | null
  title: string
  description: string | null
  checklist: string | null
  started_at: string | null
  completed_at: string | null
  performed_by_id: number | null
  findings: string | null
  parts_replaced: string | null
  parts_cost: string
  labor_hours: string
  next_maintenance_date: string | null
  notes: string | null
  created_at: string
  updated_at: string | null
  resource_name?: string
}

export interface MaintenanceCreate {
  resource_id: number
  maintenance_type?: MaintenanceType
  scheduled_date: string
  title: string
  description?: string
  checklist?: string
}

export interface MaintenanceComplete {
  findings?: string
  parts_replaced?: string
  parts_cost?: string
  labor_hours?: string
  notes?: string
  next_maintenance_date?: string
}

// ==================== Staff Payment Types ====================

export interface Payment {
  id: number
  user_id: number | null
  amount: string
  payment_method: string
  status: PaymentStatus
  payment_reference: string | null
  receipt_number: string | null
  machine_time_fee: string
  consumables_fee: string
  setup_fee: string
  refund_amount: string
  refunded_at: string | null
  refund_reason: string | null
  processed_by_id: number | null
  notes: string | null
  created_at: string
  updated_at: string | null
}

export interface PaymentCreate {
  user_id: number
  amount: string
  payment_method: string
  reservation_id?: number
  job_id?: number
  notes?: string
}

export interface PaymentRefund {
  amount: string
  reason: string
}

// ==================== Staff Resource Functions ====================

export async function createResource(
  token: string,
  data: MakerspaceResourceCreate
): Promise<MakerspaceResource> {
  return await fetchApi<MakerspaceResource>('/staff/makerspace/resources', {
    method: 'POST',
    token,
    body: data,
  })
}

// ==================== Staff Certification Type Functions ====================

export async function createCertificationType(
  token: string,
  data: CertificationTypeCreate
): Promise<CertificationType> {
  return await fetchApi<CertificationType>('/staff/makerspace/certification-types', {
    method: 'POST',
    token,
    body: data,
  })
}

// ==================== Staff Reservation Functions ====================

export async function approveReservation(
  token: string,
  reservationId: number,
  notes?: string
): Promise<Reservation> {
  const params = notes ? `?notes=${encodeURIComponent(notes)}` : ''
  return await fetchApi<Reservation>(
    `/staff/makerspace/reservations/${reservationId}/approve${params}`,
    { method: 'POST', token }
  )
}

export async function checkInReservation(
  token: string,
  reservationId: number,
  data?: ReservationCheckIn
): Promise<Reservation> {
  return await fetchApi<Reservation>(
    `/staff/makerspace/reservations/${reservationId}/check-in`,
    {
      method: 'POST',
      token,
      body: data || {},
    }
  )
}

export async function checkOutReservation(
  token: string,
  reservationId: number,
  data?: ReservationCheckOut
): Promise<Reservation> {
  return await fetchApi<Reservation>(
    `/staff/makerspace/reservations/${reservationId}/check-out`,
    {
      method: 'POST',
      token,
      body: data || {},
    }
  )
}

export async function markReservationNoShow(
  token: string,
  reservationId: number
): Promise<{ message: string }> {
  return await fetchApi<{ message: string }>(
    `/staff/makerspace/reservations/${reservationId}/no-show`,
    { method: 'POST', token }
  )
}

// ==================== Staff Job Functions ====================

export async function reviewJob(
  token: string,
  jobId: number,
  review: JobReview
): Promise<Job> {
  return await fetchApi<Job>(`/staff/makerspace/jobs/${jobId}/review`, {
    method: 'POST',
    token,
    body: review,
  })
}

export async function startJob(token: string, jobId: number): Promise<Job> {
  return await fetchApi<Job>(`/staff/makerspace/jobs/${jobId}/start`, {
    method: 'POST',
    token,
  })
}

export async function completeJob(
  token: string,
  jobId: number,
  completion: JobComplete
): Promise<Job> {
  return await fetchApi<Job>(`/staff/makerspace/jobs/${jobId}/complete`, {
    method: 'POST',
    token,
    body: completion,
  })
}

export async function markJobReadyForPickup(
  token: string,
  jobId: number
): Promise<Job> {
  return await fetchApi<Job>(`/staff/makerspace/jobs/${jobId}/ready-pickup`, {
    method: 'POST',
    token,
  })
}

export async function markJobPickedUp(
  token: string,
  jobId: number,
  data?: JobPickup
): Promise<Job> {
  return await fetchApi<Job>(`/staff/makerspace/jobs/${jobId}/pickup`, {
    method: 'POST',
    token,
    body: data || {},
  })
}

export async function failJob(
  token: string,
  jobId: number,
  reason: string
): Promise<{ message: string }> {
  return await fetchApi<{ message: string }>(
    `/staff/makerspace/jobs/${jobId}/fail?reason=${encodeURIComponent(reason)}`,
    { method: 'POST', token }
  )
}

export async function reorderJobQueue(
  token: string,
  jobIds: number[]
): Promise<Job[]> {
  return await fetchApi<Job[]>('/staff/makerspace/jobs/reorder', {
    method: 'POST',
    token,
    body: jobIds,
  })
}

// ==================== Staff Consumable Functions ====================

export async function createConsumable(
  token: string,
  data: ConsumableCreate
): Promise<Consumable> {
  return await fetchApi<Consumable>('/staff/makerspace/consumables', {
    method: 'POST',
    token,
    body: data,
  })
}

export async function adjustConsumableStock(
  token: string,
  consumableId: number,
  adjustment: ConsumableStockAdjustment
): Promise<Consumable> {
  return await fetchApi<Consumable>(
    `/staff/makerspace/consumables/${consumableId}/adjust-stock`,
    {
      method: 'POST',
      token,
      body: adjustment,
    }
  )
}

// ==================== Staff Incident Functions ====================

export async function createIncident(
  token: string,
  data: SafetyIncidentCreate
): Promise<SafetyIncident> {
  return await fetchApi<SafetyIncident>('/staff/makerspace/incidents', {
    method: 'POST',
    token,
    body: data,
  })
}

export async function resolveIncident(
  token: string,
  incidentId: number,
  data?: SafetyIncidentResolve
): Promise<{ message: string }> {
  return await fetchApi<{ message: string }>(
    `/staff/makerspace/incidents/${incidentId}/resolve`,
    {
      method: 'POST',
      token,
      body: data || {},
    }
  )
}

// ==================== Staff Maintenance Functions ====================

export async function scheduleMaintenance(
  token: string,
  data: MaintenanceCreate
): Promise<Maintenance> {
  return await fetchApi<Maintenance>('/staff/makerspace/maintenance', {
    method: 'POST',
    token,
    body: data,
  })
}

export async function startMaintenance(
  token: string,
  maintenanceId: number
): Promise<Maintenance> {
  return await fetchApi<Maintenance>(
    `/staff/makerspace/maintenance/${maintenanceId}/start`,
    { method: 'POST', token }
  )
}

export async function completeMaintenance(
  token: string,
  maintenanceId: number,
  completion: MaintenanceComplete
): Promise<Maintenance> {
  return await fetchApi<Maintenance>(
    `/staff/makerspace/maintenance/${maintenanceId}/complete`,
    {
      method: 'POST',
      token,
      body: completion,
    }
  )
}

// ==================== Staff Payment Functions ====================

export async function createPayment(
  token: string,
  data: PaymentCreate
): Promise<Payment> {
  return await fetchApi<Payment>('/staff/makerspace/payments', {
    method: 'POST',
    token,
    body: data,
  })
}

export async function refundPayment(
  token: string,
  paymentId: number,
  refundData: PaymentRefund
): Promise<Payment> {
  return await fetchApi<Payment>(
    `/staff/makerspace/payments/${paymentId}/refund`,
    {
      method: 'POST',
      token,
      body: refundData,
    }
  )
}