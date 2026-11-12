/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * State Compliance API Service
 *
 * Provides access to state-specific compliance requirements including:
 * - Patron confidentiality laws
 * - Data retention periods
 * - Law enforcement response requirements
 * - State library reporting
 * - ID verification requirements
 * - VPAT accessibility conformance
 */

import { fetchApi } from '@/lib/api-client'

// =============================================================================
// Types
// =============================================================================

// State Configuration Types

export interface ConfiguredState {
  state_code: string
  state_name: string
  confidentiality_strength: string
  confidentiality_statute: string | null
  last_reviewed: string | null
}

export interface StateComplianceSummary {
  state_code: string
  state_name: string
  configured: boolean
  last_reviewed: string | null
  confidentiality: Record<string, unknown> | null
  retention: Record<string, unknown> | null
  law_enforcement: Record<string, unknown> | null
  reporting: Record<string, unknown> | null
  id_verification: Record<string, unknown> | null
  accessibility: Record<string, unknown> | null
}

// Disclosure Validation Types

export interface DisclosureValidationRequest {
  state_code: string
  request_type: 'subpoena' | 'warrant' | 'court_order' | 'informal' | string
  record_type?: 'circulation' | 'registration' | 'internet' | 'programs' | string
  has_court_order?: boolean
  has_subpoena?: boolean
  has_warrant?: boolean
  is_grand_jury?: boolean
}

export interface DisclosureValidationResponse {
  valid: boolean
  reason: string
  state_code: string
  confidentiality_statute: string | null
  confidentiality_strength: string | null
  record_protected: boolean
  requires_court_order: boolean
  patron_notification_required: boolean
  patron_notification_allowed: boolean
  notification_delay_days: number
  applicable_exceptions: Record<string, unknown>[]
}

// Retention Types

export interface RetentionPeriods {
  checkout_record_retention_years: number
  financial_record_retention_years: number
  patron_data_retention_after_closure_days: number
  system_log_retention_days: number
}

// Law Enforcement Types

export interface LawEnforcementRequirements {
  state_code: string
  requires_court_order: boolean
  accepts_subpoena: boolean
  accepts_warrant: boolean
  patron_notification_required: boolean
  patron_notification_allowed: boolean
  notification_delay_days: number
  confidentiality_statute: string | null
  confidentiality_strength: string
  exceptions: Record<string, unknown>[]
  response_procedure: string | null
  designated_responder: string | null
  [key: string]: unknown
}

// Patron Notification Types

export interface PatronNotificationRequirements {
  notification_required: boolean
  notification_allowed: boolean
  delay_days: number
  state_code: string | null
  confidentiality_strength: string | null
}

// Reporting Types

export interface ReportingRequirements {
  state_library_name: string | null
  state_library_id: string | null
  annual_report_due: string | null
  required_statistics: string[]
  report_template: string | null
  state_code: string
}

export interface UpcomingDeadline {
  state_code: string
  state_name: string
  state_library_name: string | null
  due_date: string
  days_until_due: number
  report_template: string | null
}

// ID Verification Types

export interface IdVerificationRequirements {
  state_code: string
  photo_id_required: boolean
  accepted_photo_ids: string[]
  residency_proof_required: boolean
  accepted_residency_proofs: string[]
  minor_requirements: Record<string, unknown>
  card_validity_years: number
  [key: string]: unknown
}

// Registration Validation Types

export interface RegistrationValidationRequest {
  state_code: string
  age: number
  has_photo_id?: boolean
  photo_id_type?: string
  has_residency_proof?: boolean
  residency_proof_type?: string
}

export interface RegistrationValidationResponse {
  valid: boolean
  missing_requirements: string[]
  is_adult: boolean
  state_code: string
  card_validity_years: number
}

// Accessibility Types

export interface AccessibilityRequirements {
  state_code: string
  has_state_law: boolean
  state_law_name: string | null
  state_law_citation: string | null
  requirements_beyond_ada: string[]
  notes: string | null
  [key: string]: unknown
}

// Local Compliance Types

export interface LocalComplianceConfig {
  id: number
  jurisdiction_type: string
  jurisdiction_name: string
  jurisdiction_code: string
  has_privacy_override: boolean
  has_retention_override: boolean
  sanctuary_city: boolean
  is_active: boolean
}

export interface EffectiveCompliance {
  state_code: string
  jurisdiction: string | null
  confidentiality: Record<string, unknown>
  retention: Record<string, unknown>
  law_enforcement: Record<string, unknown>
  id_verification: Record<string, unknown>
  accessibility: Record<string, unknown>
  local_overrides_applied: boolean
  [key: string]: unknown
}

// Regulation Monitoring Types

export type RegulationStatus = 'proposed' | 'pending' | 'enacted' | 'effective' | 'repealed'

export interface Regulation {
  id: number
  regulation_name: string
  regulation_number: string | null
  jurisdiction_type: string
  jurisdiction_code: string | null
  source: string
  status: RegulationStatus
  effective_date: string | null
  priority: string
  requires_action: boolean
  action_deadline: string | null
}

export interface RegulationRequiringAction {
  id: number
  regulation_name: string
  regulation_number: string | null
  jurisdiction_type: string
  priority: string
  action_deadline: string | null
  action_notes: string | null
  affects: {
    patron_privacy: boolean
    data_retention: boolean
    law_enforcement: boolean
    accessibility: boolean
  }
}

export interface RegulationDeadline {
  id: number
  regulation_name: string
  regulation_number: string | null
  action_deadline: string
  days_until_deadline: number
  is_overdue: boolean
  priority: string
  action_notes: string | null
}

// Alert Types

export interface RegulationAlert {
  id: number
  regulation_monitor_id: number
  alert_type: string
  title: string
  description: string | null
  priority: string
  assigned_to_id: number | null
  created_at: string | null
}

export interface ResolveAlertResponse {
  message: string
  alert_id: number
  resolved_at: string
}

// Dashboard Types

export interface ComplianceDashboard {
  upcoming_deadlines: UpcomingDeadline[]
  unresolved_alerts: RegulationAlert[]
  regulations_requiring_action: RegulationRequiringAction[]
  compliance_scores: Record<string, unknown>
  recent_changes: Record<string, unknown>[]
  [key: string]: unknown
}

export interface DashboardConfig {
  enabled_widgets: string[]
  email_alerts_enabled: boolean
  alert_frequency: string
  default_state_filter: string | null
  default_date_range_days: number
}

export interface DashboardConfigUpdateRequest {
  enabled_widgets?: string[]
  email_alerts_enabled?: boolean
  alert_frequency?: string
  default_state_filter?: string
  default_date_range_days?: number
}

export interface DashboardConfigUpdateResponse {
  message: string
  enabled_widgets: string[]
  email_alerts_enabled: boolean
  alert_frequency: string
}

// VPAT Types

export type VPATConformanceLevel =
  | 'supports'
  | 'partially_supports'
  | 'does_not_support'
  | 'not_applicable'
  | 'not_evaluated'

export interface VPATReport {
  id: number
  report_name: string
  report_version: string
  product_name: string
  product_version: string | null
  evaluation_date: string
  overall_conformance: VPATConformanceLevel
  wcag_version: string
  wcag_level: string
  is_current: boolean
}

export interface VPATDocument {
  id: number
  report_name: string
  report_version: string
  product_name: string
  product_version: string | null
  evaluation_date: string
  evaluator_name: string | null
  evaluator_organization: string | null
  overall_conformance: VPATConformanceLevel
  wcag_version: string
  wcag_level: string
  criteria: VPATCriterion[]
  [key: string]: unknown
}

export interface CreateVPATRequest {
  report_name: string
  report_version: string
  evaluation_date: string
  product_version?: string
  evaluator_name?: string
  evaluator_organization?: string
  wcag_version?: string
  wcag_level?: string
  initialize_criteria?: boolean
}

export interface CreateVPATResponse {
  id: number
  report_name: string
  report_version: string
  criteria_initialized: number
  message: string
}

export interface VPATCriterion {
  id: number
  standard: string
  criterion_id: string
  criterion_name: string
  level: string
  conformance_level: VPATConformanceLevel
  remarks: string | null
}

export interface UpdateVPATCriterionRequest {
  conformance_level: VPATConformanceLevel
  remarks?: string
}

export interface UpdateVPATCriterionResponse {
  id: number
  criterion_id: string
  conformance_level: VPATConformanceLevel
  remarks: string | null
  message: string
}

// Initialize Defaults Response

export interface InitializeDefaultsResponse {
  message: string
  created_count: number
}

// =============================================================================
// API Functions - State Configuration
// =============================================================================

export async function listConfiguredStates(): Promise<ConfiguredState[]> {
  return fetchApi<ConfiguredState[]>('/state-compliance/states')
}

export async function getStateComplianceSummary(stateCode: string): Promise<StateComplianceSummary> {
  return fetchApi<StateComplianceSummary>(`/state-compliance/states/${stateCode.toUpperCase()}`)
}

export async function initializeDefaultConfigurations(): Promise<InitializeDefaultsResponse> {
  return fetchApi<InitializeDefaultsResponse>('/state-compliance/initialize-defaults', {
    method: 'POST',
  })
}

// =============================================================================
// API Functions - Disclosure Validation
// =============================================================================

export async function validateDisclosureRequest(
  request: DisclosureValidationRequest
): Promise<DisclosureValidationResponse> {
  return fetchApi<DisclosureValidationResponse>('/state-compliance/validate-disclosure', {
    method: 'POST',
    body: request,
  })
}

// =============================================================================
// API Functions - Retention Periods
// =============================================================================

export async function getRetentionPeriods(stateCode: string): Promise<RetentionPeriods> {
  return fetchApi<RetentionPeriods>(`/state-compliance/states/${stateCode.toUpperCase()}/retention`)
}

// =============================================================================
// API Functions - Law Enforcement
// =============================================================================

export async function getLawEnforcementRequirements(
  stateCode: string
): Promise<LawEnforcementRequirements> {
  return fetchApi<LawEnforcementRequirements>(
    `/state-compliance/states/${stateCode.toUpperCase()}/law-enforcement`
  )
}

export async function getPatronNotificationRequirements(
  stateCode: string
): Promise<PatronNotificationRequirements> {
  return fetchApi<PatronNotificationRequirements>(
    `/state-compliance/states/${stateCode.toUpperCase()}/notification`
  )
}

// =============================================================================
// API Functions - Reporting
// =============================================================================

export async function getReportingRequirements(stateCode: string): Promise<ReportingRequirements> {
  return fetchApi<ReportingRequirements>(
    `/state-compliance/states/${stateCode.toUpperCase()}/reporting`
  )
}

export async function getUpcomingReportDeadlines(params?: {
  days_ahead?: number
}): Promise<UpcomingDeadline[]> {
  const searchParams = new URLSearchParams()
  if (params?.days_ahead !== undefined) {
    searchParams.set('days_ahead', String(params.days_ahead))
  }
  const query = searchParams.toString()
  return fetchApi<UpcomingDeadline[]>(`/state-compliance/deadlines${query ? `?${query}` : ''}`)
}

// =============================================================================
// API Functions - ID Verification
// =============================================================================

export async function getIdVerificationRequirements(
  stateCode: string
): Promise<IdVerificationRequirements> {
  return fetchApi<IdVerificationRequirements>(
    `/state-compliance/states/${stateCode.toUpperCase()}/id-verification`
  )
}

export async function validateRegistrationDocuments(
  request: RegistrationValidationRequest
): Promise<RegistrationValidationResponse> {
  return fetchApi<RegistrationValidationResponse>('/state-compliance/validate-registration', {
    method: 'POST',
    body: request,
  })
}

// =============================================================================
// API Functions - Accessibility
// =============================================================================

export async function getAccessibilityRequirements(
  stateCode: string
): Promise<AccessibilityRequirements> {
  return fetchApi<AccessibilityRequirements>(
    `/state-compliance/states/${stateCode.toUpperCase()}/accessibility`
  )
}

// =============================================================================
// API Functions - Local Compliance
// =============================================================================

export async function listLocalConfigsForState(stateCode: string): Promise<LocalComplianceConfig[]> {
  return fetchApi<LocalComplianceConfig[]>(`/state-compliance/local/${stateCode.toUpperCase()}`)
}

export async function getEffectiveCompliance(
  stateCode: string,
  jurisdiction?: string
): Promise<EffectiveCompliance> {
  const searchParams = new URLSearchParams()
  if (jurisdiction) {
    searchParams.set('jurisdiction', jurisdiction)
  }
  const query = searchParams.toString()
  return fetchApi<EffectiveCompliance>(
    `/state-compliance/effective/${stateCode.toUpperCase()}${query ? `?${query}` : ''}`
  )
}

// =============================================================================
// API Functions - Regulation Monitoring
// =============================================================================

export async function listRegulations(params?: {
  jurisdiction_type?: 'federal' | 'state' | 'local'
  jurisdiction_code?: string
  status?: RegulationStatus
}): Promise<Regulation[]> {
  const searchParams = new URLSearchParams()
  if (params?.jurisdiction_type) {
    searchParams.set('jurisdiction_type', params.jurisdiction_type)
  }
  if (params?.jurisdiction_code) {
    searchParams.set('jurisdiction_code', params.jurisdiction_code)
  }
  if (params?.status) {
    searchParams.set('status', params.status)
  }
  const query = searchParams.toString()
  return fetchApi<Regulation[]>(`/state-compliance/regulations${query ? `?${query}` : ''}`)
}

export async function listRegulationsRequiringAction(): Promise<RegulationRequiringAction[]> {
  return fetchApi<RegulationRequiringAction[]>('/state-compliance/regulations/requiring-action')
}

export async function getRegulationDeadlines(params?: {
  days_ahead?: number
}): Promise<RegulationDeadline[]> {
  const searchParams = new URLSearchParams()
  if (params?.days_ahead !== undefined) {
    searchParams.set('days_ahead', String(params.days_ahead))
  }
  const query = searchParams.toString()
  return fetchApi<RegulationDeadline[]>(
    `/state-compliance/regulations/deadlines${query ? `?${query}` : ''}`
  )
}

// =============================================================================
// API Functions - Alerts
// =============================================================================

export async function listUnresolvedAlerts(params?: {
  priority?: 'critical' | 'high' | 'medium' | 'low'
}): Promise<RegulationAlert[]> {
  const searchParams = new URLSearchParams()
  if (params?.priority) {
    searchParams.set('priority', params.priority)
  }
  const query = searchParams.toString()
  return fetchApi<RegulationAlert[]>(`/state-compliance/alerts${query ? `?${query}` : ''}`)
}

export async function resolveRegulationAlert(
  alertId: number,
  resolutionNotes?: string
): Promise<ResolveAlertResponse> {
  const searchParams = new URLSearchParams()
  if (resolutionNotes) {
    searchParams.set('resolution_notes', resolutionNotes)
  }
  const query = searchParams.toString()
  return fetchApi<ResolveAlertResponse>(
    `/state-compliance/alerts/${alertId}/resolve${query ? `?${query}` : ''}`,
    { method: 'POST' }
  )
}

// =============================================================================
// API Functions - Compliance Dashboard
// =============================================================================

export async function getComplianceDashboard(params?: {
  state_code?: string
}): Promise<ComplianceDashboard> {
  const searchParams = new URLSearchParams()
  if (params?.state_code) {
    searchParams.set('state_code', params.state_code.toUpperCase())
  }
  const query = searchParams.toString()
  return fetchApi<ComplianceDashboard>(`/state-compliance/dashboard${query ? `?${query}` : ''}`)
}

export async function updateDashboardConfig(
  config: DashboardConfigUpdateRequest
): Promise<DashboardConfigUpdateResponse> {
  return fetchApi<DashboardConfigUpdateResponse>('/state-compliance/dashboard/config', {
    method: 'PUT',
    body: config,
  })
}

// =============================================================================
// API Functions - VPAT (Accessibility Conformance)
// =============================================================================

export async function getCurrentVPAT(): Promise<VPATReport> {
  return fetchApi<VPATReport>('/state-compliance/vpat/current')
}

export async function getVPATDocument(vpatId: number): Promise<VPATDocument> {
  return fetchApi<VPATDocument>(`/state-compliance/vpat/${vpatId}/document`)
}

export async function createVPATReport(request: CreateVPATRequest): Promise<CreateVPATResponse> {
  return fetchApi<CreateVPATResponse>('/state-compliance/vpat', {
    method: 'POST',
    body: request,
  })
}

export async function getVPATCriteria(vpatId: number): Promise<VPATCriterion[]> {
  return fetchApi<VPATCriterion[]>(`/state-compliance/vpat/${vpatId}/criteria`)
}

export async function updateVPATCriterion(
  criterionId: number,
  request: UpdateVPATCriterionRequest
): Promise<UpdateVPATCriterionResponse> {
  return fetchApi<UpdateVPATCriterionResponse>(`/state-compliance/vpat/criteria/${criterionId}`, {
    method: 'PUT',
    body: request,
  })
}
