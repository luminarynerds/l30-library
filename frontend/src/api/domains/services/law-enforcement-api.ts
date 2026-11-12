/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Law Enforcement API Service
 *
 * SECURITY NOTICE: These endpoints are STRICTLY restricted to users with
 * DIRECTOR, LEGAL, ADMIN, or SUPER_ADMIN roles. Access attempts by other
 * roles will be logged and rejected.
 *
 * This module provides:
 * - Law enforcement request tracking and management
 * - Legal review workflow
 * - Patron data export for compliance
 * - Immutable audit logging
 * - Transparency reporting
 */

import { fetchApi } from '@/lib/api-client'
import { API_BASE } from '@/api/types'

// ==================== Enum Types ====================

export type RequestType =
  | 'subpoena'
  | 'warrant'
  | 'national_security_letter'
  | 'court_order'
  | 'informal_request'

export type LegalReviewStatus =
  | 'pending_review'
  | 'under_review'
  | 'approved'
  | 'rejected'
  | 'requires_modification'
  | 'appealing'

export type WorkflowStatus =
  | 'received'
  | 'validating'
  | 'legal_review'
  | 'patron_notification'
  | 'preparing_response'
  | 'response_sent'
  | 'completed'
  | 'rejected'
  | 'withdrawn'

export type ChecklistItemType =
  | 'receive_request'
  | 'verify_validity'
  | 'verify_jurisdiction'
  | 'verify_scope'
  | 'legal_review'
  | 'director_approval'
  | 'notify_patron'
  | 'prepare_response'
  | 'minimize_data'
  | 'document_compliance'
  | 'send_response'
  | 'final_review'

export type AuditActionType =
  | 'request_created'
  | 'request_updated'
  | 'status_changed'
  | 'legal_review_updated'
  | 'checklist_updated'
  | 'document_attached'
  | 'document_removed'
  | 'patron_notified'
  | 'response_prepared'
  | 'response_sent'
  | 'data_exported'
  | 'note_added'
  | 'viewed'

// ==================== Request/Response Types ====================

export interface PatronSummary {
  id: number
  first_name: string
  last_name: string
  library_card: string | null
}

export interface ChecklistProgress {
  completed: number
  total: number
  percent: number
}

export interface LawEnforcementRequest {
  id: number
  tracking_number: string
  requesting_agency: string
  agency_contact_name: string | null
  agency_contact_phone: string | null
  agency_contact_email: string | null
  agency_case_number: string | null
  request_type: RequestType
  date_received: string
  date_due: string | null
  patron_id: number | null
  patron: PatronSummary | null
  patron_name_on_request: string | null
  patron_identifiers: string | null
  data_requested: string
  data_date_range_start: string | null
  data_date_range_end: string | null
  legal_review_status: LegalReviewStatus
  legal_reviewer_id: number | null
  legal_review_date: string | null
  legal_review_notes: string | null
  workflow_status: WorkflowStatus
  response_date: string | null
  responding_staff_id: number | null
  response_method: string | null
  response_summary: string | null
  data_provided_summary: string | null
  patron_notification_permitted: boolean
  patron_notification_date: string | null
  patron_notification_method: string | null
  gag_order_until: string | null
  internal_notes: string | null
  created_by_id: number | null
  created_at: string
  updated_at: string | null
  checklist_progress: ChecklistProgress | null
}

export interface LawEnforcementRequestListItem {
  id: number
  tracking_number: string
  requesting_agency: string
  request_type: RequestType
  date_received: string
  date_due: string | null
  patron_name_on_request: string | null
  legal_review_status: LegalReviewStatus
  workflow_status: WorkflowStatus
  created_at: string
}

export interface LawEnforcementRequestListResponse {
  items: LawEnforcementRequestListItem[]
  total: number
  skip: number
  limit: number
}

export interface LawEnforcementRequestCreate {
  requesting_agency: string
  agency_contact_name?: string | null
  agency_contact_phone?: string | null
  agency_contact_email?: string | null
  agency_case_number?: string | null
  request_type: RequestType
  date_received: string
  date_due?: string | null
  patron_id?: number | null
  patron_name_on_request?: string | null
  patron_identifiers?: string | null
  data_requested: string
  data_date_range_start?: string | null
  data_date_range_end?: string | null
  patron_notification_permitted?: boolean
  gag_order_until?: string | null
  internal_notes?: string | null
}

export interface LawEnforcementRequestUpdate {
  requesting_agency?: string | null
  agency_contact_name?: string | null
  agency_contact_phone?: string | null
  agency_contact_email?: string | null
  agency_case_number?: string | null
  date_due?: string | null
  patron_id?: number | null
  patron_name_on_request?: string | null
  patron_identifiers?: string | null
  data_requested?: string | null
  data_date_range_start?: string | null
  data_date_range_end?: string | null
  patron_notification_permitted?: boolean | null
  gag_order_until?: string | null
  internal_notes?: string | null
}

// ==================== Legal Review Types ====================

export interface LegalReviewUpdate {
  legal_review_status: LegalReviewStatus
  legal_review_notes?: string | null
}

// ==================== Workflow Types ====================

export interface WorkflowStatusUpdate {
  workflow_status: WorkflowStatus
  notes?: string | null
}

export interface ChecklistItemResponse {
  id: number
  item_type: ChecklistItemType
  item_description: string
  is_completed: boolean
  is_required: boolean
  is_applicable: boolean
  completed_by_id: number | null
  completed_by_name: string | null
  completed_at: string | null
  completion_notes: string | null
  sort_order: number
}

export interface ChecklistItemUpdate {
  is_completed?: boolean | null
  is_applicable?: boolean | null
  completion_notes?: string | null
}

// ==================== Response/Compliance Types ====================

export interface ResponseUpdate {
  response_method: string
  response_summary: string
  data_provided_summary?: string | null
}

export interface PatronNotificationRecord {
  notification_method: string
  notification_notes?: string | null
}

// ==================== Audit Log Types ====================

export interface AuditLogResponse {
  id: number
  action: AuditActionType
  performed_by_id: number | null
  performed_by_name: string | null
  details: Record<string, unknown> | null
  ip_address: string | null
  created_at: string
}

export interface AddNoteRequest {
  note: string
}

// ==================== Template Types ====================

export interface ResponseTemplateCreate {
  name: string
  description?: string | null
  template_type: string
  applicable_request_types?: string[] | null
  subject_template?: string | null
  body_template: string
}

export interface ResponseTemplateUpdate {
  name?: string | null
  description?: string | null
  template_type?: string | null
  applicable_request_types?: string[] | null
  subject_template?: string | null
  body_template?: string | null
  is_active?: boolean | null
}

export interface ResponseTemplateResponse {
  id: number
  name: string
  description: string | null
  template_type: string
  applicable_request_types: string[] | null
  subject_template: string | null
  body_template: string
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export interface RenderedTemplate {
  subject: string | null
  body: string
}

// ==================== Data Export Types ====================

export interface PatronDataExportRequest {
  request_id: number
  include_profile?: boolean
  include_checkouts?: boolean
  include_holds?: boolean
  include_fines?: boolean
  include_reading_history?: boolean
  date_range_start?: string | null
  date_range_end?: string | null
}

export interface PatronDataExportResponse {
  request_id: number
  patron_id: number
  exported_at: string
  data_categories_included: string[]
  profile: Record<string, unknown> | null
  checkouts: Record<string, unknown>[] | null
  holds: Record<string, unknown>[] | null
  fines: Record<string, unknown>[] | null
  reading_history: Record<string, unknown>[] | null
}

// ==================== Transparency Report Types ====================

export interface TransparencyReportRequest {
  year: number
  include_details?: boolean
}

export interface TransparencyReportSummary {
  year: number
  total_requests: number
  requests_by_type: Record<string, number>
  requests_by_status: Record<string, number>
  requests_by_legal_outcome: Record<string, number>
  average_response_time_days: number | null
  requests_with_patron_notification: number
  requests_with_gag_order: number
  requests_fully_complied: number
  requests_partially_complied: number
  requests_rejected: number
  requests_withdrawn: number
  unique_patrons_affected: number
}

export interface TransparencyReportDetail {
  tracking_number: string
  request_type: RequestType
  requesting_agency: string
  date_received: string
  response_date: string | null
  legal_outcome: LegalReviewStatus
  workflow_status: WorkflowStatus
  patron_notified: boolean
  data_types_provided: string | null
}

export interface TransparencyReport {
  report_generated_at: string
  summary: TransparencyReportSummary
  details: TransparencyReportDetail[] | null
}

// ==================== Statistics Types ====================

export interface LawEnforcementStatsResponse {
  total_requests: number
  pending_review: number
  in_progress: number
  completed: number
  this_year: number
}

// ==================== Filter Types ====================

export interface LawEnforcementRequestFilters {
  skip?: number
  limit?: number
  request_type?: RequestType
  workflow_status?: WorkflowStatus
  legal_review_status?: LegalReviewStatus
  year?: number
  patron_id?: number
}

// ==================== API Functions ====================

const BASE_PATH = `${API_BASE}/law-enforcement`

export async function createLawEnforcementRequest(
  data: LawEnforcementRequestCreate
): Promise<LawEnforcementRequest> {
  return fetchApi<LawEnforcementRequest>(`${BASE_PATH}/requests`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function listLawEnforcementRequests(
  filters?: LawEnforcementRequestFilters
): Promise<LawEnforcementRequestListResponse> {
  const params = new URLSearchParams()
  if (filters?.skip !== undefined) params.set('skip', String(filters.skip))
  if (filters?.limit !== undefined) params.set('limit', String(filters.limit))
  if (filters?.request_type) params.set('request_type', filters.request_type)
  if (filters?.workflow_status) params.set('workflow_status', filters.workflow_status)
  if (filters?.legal_review_status) params.set('legal_review_status', filters.legal_review_status)
  if (filters?.year !== undefined) params.set('year', String(filters.year))
  if (filters?.patron_id !== undefined) params.set('patron_id', String(filters.patron_id))

  const query = params.toString()
  return fetchApi<LawEnforcementRequestListResponse>(
    `${BASE_PATH}/requests${query ? `?${query}` : ''}`
  )
}

export async function getLawEnforcementRequest(
  requestId: number
): Promise<LawEnforcementRequest> {
  return fetchApi<LawEnforcementRequest>(`${BASE_PATH}/requests/${requestId}`)
}

export async function updateLawEnforcementRequest(
  requestId: number,
  data: LawEnforcementRequestUpdate
): Promise<LawEnforcementRequest> {
  return fetchApi<LawEnforcementRequest>(`${BASE_PATH}/requests/${requestId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

// ==================== Legal Review Functions ====================

export async function updateLegalReview(
  requestId: number,
  data: LegalReviewUpdate
): Promise<LawEnforcementRequest> {
  return fetchApi<LawEnforcementRequest>(`${BASE_PATH}/requests/${requestId}/legal-review`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ==================== Workflow Functions ====================

export async function updateWorkflowStatus(
  requestId: number,
  data: WorkflowStatusUpdate
): Promise<LawEnforcementRequest> {
  return fetchApi<LawEnforcementRequest>(`${BASE_PATH}/requests/${requestId}/workflow-status`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getChecklist(
  requestId: number
): Promise<ChecklistItemResponse[]> {
  return fetchApi<ChecklistItemResponse[]>(`${BASE_PATH}/requests/${requestId}/checklist`)
}

export async function updateChecklistItem(
  requestId: number,
  itemType: ChecklistItemType,
  data: ChecklistItemUpdate
): Promise<ChecklistItemResponse> {
  return fetchApi<ChecklistItemResponse>(
    `${BASE_PATH}/requests/${requestId}/checklist/${itemType}`,
    {
      method: 'PATCH',
      body: JSON.stringify(data),
    }
  )
}

// ==================== Response/Compliance Functions ====================

export async function recordResponse(
  requestId: number,
  data: ResponseUpdate
): Promise<LawEnforcementRequest> {
  return fetchApi<LawEnforcementRequest>(`${BASE_PATH}/requests/${requestId}/response`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function recordPatronNotification(
  requestId: number,
  data: PatronNotificationRecord
): Promise<LawEnforcementRequest> {
  return fetchApi<LawEnforcementRequest>(
    `${BASE_PATH}/requests/${requestId}/patron-notification`,
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  )
}

// ==================== Data Export Functions ====================

export async function exportPatronData(
  requestId: number,
  data: PatronDataExportRequest
): Promise<PatronDataExportResponse> {
  return fetchApi<PatronDataExportResponse>(
    `${BASE_PATH}/requests/${requestId}/export-patron-data`,
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  )
}

// ==================== Audit Log Functions ====================

export async function getAuditLog(
  requestId: number,
  options?: { skip?: number; limit?: number }
): Promise<AuditLogResponse[]> {
  const params = new URLSearchParams()
  if (options?.skip !== undefined) params.set('skip', String(options.skip))
  if (options?.limit !== undefined) params.set('limit', String(options.limit))

  const query = params.toString()
  return fetchApi<AuditLogResponse[]>(
    `${BASE_PATH}/requests/${requestId}/audit-log${query ? `?${query}` : ''}`
  )
}

export async function addNote(
  requestId: number,
  data: AddNoteRequest
): Promise<AuditLogResponse> {
  return fetchApi<AuditLogResponse>(`${BASE_PATH}/requests/${requestId}/notes`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ==================== Transparency Report Functions ====================

export async function generateTransparencyReport(
  data: TransparencyReportRequest
): Promise<TransparencyReport> {
  return fetchApi<TransparencyReport>(`${BASE_PATH}/reports/transparency`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getTransparencyReport(
  year: number,
  includeDetails?: boolean
): Promise<TransparencyReport> {
  const params = new URLSearchParams()
  if (includeDetails !== undefined) params.set('include_details', String(includeDetails))

  const query = params.toString()
  return fetchApi<TransparencyReport>(
    `${BASE_PATH}/reports/transparency/${year}${query ? `?${query}` : ''}`
  )
}

// ==================== Template Functions ====================

export async function listTemplates(params?: {
  template_type?: string
  active_only?: boolean
}): Promise<ResponseTemplateResponse[]> {
  const searchParams = new URLSearchParams()
  if (params?.template_type) searchParams.set('template_type', params.template_type)
  if (params?.active_only !== undefined) searchParams.set('active_only', String(params.active_only))

  const query = searchParams.toString()
  return fetchApi<ResponseTemplateResponse[]>(`${BASE_PATH}/templates${query ? `?${query}` : ''}`)
}

export async function createTemplate(
  data: ResponseTemplateCreate
): Promise<ResponseTemplateResponse> {
  return fetchApi<ResponseTemplateResponse>(`${BASE_PATH}/templates`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function renderTemplate(
  templateId: number,
  requestId: number
): Promise<RenderedTemplate> {
  return fetchApi<RenderedTemplate>(
    `${BASE_PATH}/templates/${templateId}/render/${requestId}`
  )
}

// ==================== Statistics Functions ====================

export async function getLawEnforcementStats(): Promise<LawEnforcementStatsResponse> {
  return fetchApi<LawEnforcementStatsResponse>(`${BASE_PATH}/stats`)
}

// ==================== Utility Constants ====================

/**
 * Human-readable labels for request types
 */
export const REQUEST_TYPE_LABELS: Record<RequestType, string> = {
  subpoena: 'Subpoena',
  warrant: 'Warrant',
  national_security_letter: 'National Security Letter',
  court_order: 'Court Order',
  informal_request: 'Informal Request',
}

/**
 * Human-readable labels for legal review statuses
 */
export const LEGAL_REVIEW_STATUS_LABELS: Record<LegalReviewStatus, string> = {
  pending_review: 'Pending Review',
  under_review: 'Under Review',
  approved: 'Approved',
  rejected: 'Rejected',
  requires_modification: 'Requires Modification',
  appealing: 'Appealing',
}

/**
 * Human-readable labels for workflow statuses
 */
export const WORKFLOW_STATUS_LABELS: Record<WorkflowStatus, string> = {
  received: 'Received',
  validating: 'Validating',
  legal_review: 'Legal Review',
  patron_notification: 'Patron Notification',
  preparing_response: 'Preparing Response',
  response_sent: 'Response Sent',
  completed: 'Completed',
  rejected: 'Rejected',
  withdrawn: 'Withdrawn',
}

/**
 * Human-readable labels for checklist item types
 */
export const CHECKLIST_ITEM_TYPE_LABELS: Record<ChecklistItemType, string> = {
  receive_request: 'Receive Request',
  verify_validity: 'Verify Validity',
  verify_jurisdiction: 'Verify Jurisdiction',
  verify_scope: 'Verify Scope',
  legal_review: 'Legal Review',
  director_approval: 'Director Approval',
  notify_patron: 'Notify Patron',
  prepare_response: 'Prepare Response',
  minimize_data: 'Minimize Data',
  document_compliance: 'Document Compliance',
  send_response: 'Send Response',
  final_review: 'Final Review',
}

/**
 * Human-readable labels for audit action types
 */
export const AUDIT_ACTION_TYPE_LABELS: Record<AuditActionType, string> = {
  request_created: 'Request Created',
  request_updated: 'Request Updated',
  status_changed: 'Status Changed',
  legal_review_updated: 'Legal Review Updated',
  checklist_updated: 'Checklist Updated',
  document_attached: 'Document Attached',
  document_removed: 'Document Removed',
  patron_notified: 'Patron Notified',
  response_prepared: 'Response Prepared',
  response_sent: 'Response Sent',
  data_exported: 'Data Exported',
  note_added: 'Note Added',
  viewed: 'Viewed',
}

/**
 * Request type options for form selects
 */
export const REQUEST_TYPE_OPTIONS = Object.entries(REQUEST_TYPE_LABELS).map(
  ([value, label]) => ({ value: value as RequestType, label })
)

/**
 * Legal review status options for form selects
 */
export const LEGAL_REVIEW_STATUS_OPTIONS = Object.entries(LEGAL_REVIEW_STATUS_LABELS).map(
  ([value, label]) => ({ value: value as LegalReviewStatus, label })
)

/**
 * Workflow status options for form selects
 */
export const WORKFLOW_STATUS_OPTIONS = Object.entries(WORKFLOW_STATUS_LABELS).map(
  ([value, label]) => ({ value: value as WorkflowStatus, label })
)