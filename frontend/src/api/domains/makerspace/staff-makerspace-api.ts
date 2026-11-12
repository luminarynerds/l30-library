/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'
import type {
  ResourceType,
  ResourceStatus,
  PaymentStatus,
  MakerspaceResource,
  CertificationType,
  Certification,
  Reservation,
  Job,
} from './makerspace-api'

// ==================== Enums ====================

export type IncidentSeverity = 'minor' | 'moderate' | 'serious' | 'critical';
export type MaintenanceType = 'preventive' | 'corrective' | 'emergency' | 'calibration' | 'inspection'

export type MaintenanceStatus = 'scheduled' | 'in_progress' | 'completed' | 'cancelled' | 'overdue'

export type ConsumableUnit = 'grams' | 'kilograms' | 'meters' | 'feet' | 'sheets' | 'pieces' | 'liters' | 'milliliters';
export type JobPriority = 'low' | 'normal' | 'high' | 'urgent';
// ==================== Resource Types ====================

export interface ResourceCreate {
  name: string
  description?: string | null
  resource_type: ResourceType
  location?: string | null
  asset_tag?: string | null
  serial_number?: string | null
  manufacturer?: string | null
  model?: string | null
  status?: ResourceStatus
  status_notes?: string | null
  requires_certification?: boolean
  certification_type_id?: number | null
  minimum_age?: number
  hourly_cost?: string
  setup_fee?: string
  max_reservation_hours?: number
  min_reservation_hours?: number
  advance_booking_days?: number
  buffer_minutes?: number
  available_from?: string
  available_until?: string
  available_days?: number[]
  specifications?: string | null
  build_volume_x?: number | null
  build_volume_y?: number | null
  build_volume_z?: number | null
  supported_materials?: string | null
  supported_file_formats?: string | null
  image_url?: string | null
  manual_url?: string | null
  safety_guidelines_url?: string | null
  maintenance_interval_days?: number
}

export interface ResourceUpdate {
  name?: string | null
  description?: string | null
  resource_type?: ResourceType | null
  location?: string | null
  status?: ResourceStatus | null
  status_notes?: string | null
  requires_certification?: boolean | null
  certification_type_id?: number | null
  minimum_age?: number | null
  hourly_cost?: string | null
  setup_fee?: string | null
  max_reservation_hours?: number | null
  min_reservation_hours?: number | null
  advance_booking_days?: number | null
  buffer_minutes?: number | null
  available_from?: string | null
  available_until?: string | null
  available_days?: number[] | null
  specifications?: string | null
  build_volume_x?: number | null
  build_volume_y?: number | null
  build_volume_z?: number | null
  supported_materials?: string | null
  supported_file_formats?: string | null
  image_url?: string | null
  manual_url?: string | null
  safety_guidelines_url?: string | null
  maintenance_interval_days?: number | null
  is_active?: boolean | null
}

// ==================== Certification Type Types ====================

export interface CertificationTypeCreate {
  name: string
  description?: string | null
  training_duration_hours?: string
  requires_safety_quiz?: boolean
  passing_score?: number
  validity_months?: number
  renewal_training_hours?: string
  certification_fee?: string
  renewal_fee?: string
  prerequisites?: string | null
  training_materials_url?: string | null
  safety_video_url?: string | null
}

export interface CertificationTypeUpdate {
  name?: string | null
  description?: string | null
  training_duration_hours?: string | null
  requires_safety_quiz?: boolean | null
  passing_score?: number | null
  validity_months?: number | null
  renewal_training_hours?: string | null
  certification_fee?: string | null
  renewal_fee?: string | null
  prerequisites?: string | null
  training_materials_url?: string | null
  safety_video_url?: string | null
  is_active?: boolean | null
}

// ==================== Reservation Types ====================

export interface ReservationCheckIn {
  notes?: string | null
}

export interface ReservationCheckOut {
  notes?: string | null
  consumable_usage?: ConsumableUsageCreate[] | null
}

// ==================== Job Types ====================

export interface JobReview {
  approved: boolean
  notes?: string | null
  rejection_reason?: string | null
  estimated_print_time_minutes?: number | null
  estimated_material_grams?: string | null
  estimated_cost?: string | null
  priority?: JobPriority | null
}

export interface JobComplete {
  actual_print_time_minutes: number
  actual_material_grams: string
  notes?: string | null
  consumable_usage?: ConsumableUsageCreate[] | null
}

export interface JobPickup {
  notes?: string | null
}

// ==================== Consumable Types ====================

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
  description?: string | null
  sku?: string | null
  category?: string | null
  material_type?: string | null
  color?: string | null
  diameter_mm?: string | null
  unit?: ConsumableUnit
  quantity_in_stock?: string
  reorder_threshold?: string
  reorder_quantity?: string
  cost_per_unit?: string
  price_per_unit?: string
  supplier_name?: string | null
  supplier_sku?: string | null
  compatible_resources?: string | null
}

export interface ConsumableUpdate {
  name?: string | null
  description?: string | null
  sku?: string | null
  category?: string | null
  material_type?: string | null
  color?: string | null
  diameter_mm?: string | null
  unit?: ConsumableUnit | null
  quantity_in_stock?: string | null
  reorder_threshold?: string | null
  reorder_quantity?: string | null
  cost_per_unit?: string | null
  price_per_unit?: string | null
  supplier_name?: string | null
  supplier_sku?: string | null
  compatible_resources?: string | null
  is_active?: boolean | null
}

export interface ConsumableStockAdjustment {
  quantity: string
  reason: string
}

export interface ConsumableUsageCreate {
  consumable_id: number
  quantity_used: string
}

// ==================== Incident Types ====================

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
  resource_name?: string | null
}

export interface SafetyIncidentCreate {
  resource_id?: number | null
  incident_date: string
  severity?: IncidentSeverity
  title: string
  description: string
  location?: string | null
  injuries_reported?: boolean
  injury_description?: string | null
  equipment_damage?: boolean
  damage_description?: string | null
  immediate_action_taken?: string | null
  first_aid_administered?: boolean
  emergency_services_called?: boolean
  involved_user_id?: number | null
}

export interface SafetyIncidentUpdate {
  severity?: IncidentSeverity | null
  title?: string | null
  description?: string | null
  location?: string | null
  injuries_reported?: boolean | null
  injury_description?: string | null
  equipment_damage?: boolean | null
  damage_description?: string | null
  immediate_action_taken?: string | null
  first_aid_administered?: boolean | null
  emergency_services_called?: boolean | null
  investigation_notes?: string | null
  root_cause?: string | null
  corrective_actions?: string | null
  corrective_action_deadline?: string | null
  follow_up_required?: boolean | null
  follow_up_notes?: string | null
}

export interface SafetyIncidentResolve {
  resolution_notes?: string | null
}

// ==================== Maintenance Types ====================

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
  resource_name?: string | null
}

export interface MaintenanceCreate {
  resource_id: number
  maintenance_type?: MaintenanceType
  scheduled_date: string
  title: string
  description?: string | null
  checklist?: string | null
}

export interface MaintenanceComplete {
  findings?: string | null
  parts_replaced?: string | null
  parts_cost?: string
  labor_hours?: string
  notes?: string | null
  next_maintenance_date?: string | null
}

// ==================== Payment Types ====================

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
  reservation_id?: number | null
  job_id?: number | null
  notes?: string | null
}

export interface PaymentRefund {
  amount: string
  reason: string
}

// ==================== Paginated Response Types ====================

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
}

// ==================== Resource Management Functions ====================

export async function createResource(
  token: string,
  data: ResourceCreate
): Promise<MakerspaceResource> {
  return await fetchApi<MakerspaceResource>('/staff/makerspace/resources', {
    method: 'POST',
    token,
    body: data,
  })
}

export async function updateResource(
  token: string,
  resourceId: number,
  data: ResourceUpdate
): Promise<MakerspaceResource> {
  return await fetchApi<MakerspaceResource>(`/staff/makerspace/resources/${resourceId}`, {
    method: 'PUT',
    token,
    body: data,
  })
}

export async function updateResourceStatus(
  token: string,
  resourceId: number,
  status: ResourceStatus,
  notes?: string
): Promise<MakerspaceResource> {
  const params = new URLSearchParams()
  params.set('status', status)
  if (notes) params.set('notes', notes)

  return await fetchApi<MakerspaceResource>(
    `/staff/makerspace/resources/${resourceId}/status?${params.toString()}`,
    { method: 'PATCH', token }
  )
}

// ==================== Certification Type Management Functions ====================

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

export async function updateCertificationType(
  token: string,
  typeId: number,
  data: CertificationTypeUpdate
): Promise<CertificationType> {
  return await fetchApi<CertificationType>(`/staff/makerspace/certification-types/${typeId}`, {
    method: 'PUT',
    token,
    body: data,
  })
}

// ==================== Certification Management Functions ====================

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

// ==================== Reservation Management Functions ====================

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

// ==================== Job Queue Management Functions ====================

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
  data: JobComplete
): Promise<Job> {
  return await fetchApi<Job>(`/staff/makerspace/jobs/${jobId}/complete`, {
    method: 'POST',
    token,
    body: data,
  })
}

export async function markJobReadyForPickup(token: string, jobId: number): Promise<Job> {
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

export async function reorderJobs(token: string, jobIds: number[]): Promise<Job[]> {
  return await fetchApi<Job[]>('/staff/makerspace/jobs/reorder', {
    method: 'POST',
    token,
    body: jobIds,
  })
}

// ==================== Consumables Management Functions ====================

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

export async function updateConsumable(
  token: string,
  consumableId: number,
  data: ConsumableUpdate
): Promise<Consumable> {
  return await fetchApi<Consumable>(`/staff/makerspace/consumables/${consumableId}`, {
    method: 'PUT',
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

// ==================== Safety Incident Functions ====================

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

export async function updateIncident(
  token: string,
  incidentId: number,
  data: SafetyIncidentUpdate
): Promise<SafetyIncident> {
  return await fetchApi<SafetyIncident>(`/staff/makerspace/incidents/${incidentId}`, {
    method: 'PUT',
    token,
    body: data,
  })
}

export async function resolveIncident(
  token: string,
  incidentId: number,
  resolution?: SafetyIncidentResolve
): Promise<{ message: string }> {
  return await fetchApi<{ message: string }>(
    `/staff/makerspace/incidents/${incidentId}/resolve`,
    {
      method: 'POST',
      token,
      body: resolution || {},
    }
  )
}

// ==================== Maintenance Functions ====================

export async function createMaintenance(
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
  data?: MaintenanceComplete
): Promise<Maintenance> {
  return await fetchApi<Maintenance>(
    `/staff/makerspace/maintenance/${maintenanceId}/complete`,
    {
      method: 'POST',
      token,
      body: data || {},
    }
  )
}

// ==================== Payment Functions ====================

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
  data: PaymentRefund
): Promise<Payment> {
  return await fetchApi<Payment>(`/staff/makerspace/payments/${paymentId}/refund`, {
    method: 'POST',
    token,
    body: data,
  })
}

// ==================== Re-exports from makerspace-api ====================

export type {
  ResourceType,
  ResourceStatus,
  CertificationStatus,
  ReservationStatus,
  JobStatus,
  PaymentStatus,
  MakerspaceResource,
  CertificationType,
  Certification,
  Reservation,
  Job,
} from './makerspace-api'
