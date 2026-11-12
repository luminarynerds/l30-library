/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Unified Compliance Audit API Service
 *
 * Client for the unified compliance audit platform endpoints.
 */

import { fetchApi } from '@/lib/api-client';

const BASE = `/unified-compliance`;

// ============================================================================
// Utilities
// ============================================================================

function buildQueryString(params: Record<string, unknown>): string {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      searchParams.set(key, String(value));
    }
  }
  return searchParams.toString();
}

function buildUrl(base: string, params?: Record<string, unknown>): string {
  if (!params) return base;
  const qs = buildQueryString(params);
  return qs ? `${base}?${qs}` : base;
}

// ============================================================================
// Types
// ============================================================================

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ComplianceRequirement {
  id: number;
  regulation_type: string;
  regulation_citation: string | null;
  requirement_code: string;
  requirement_title: string;
  requirement_description: string;
  applies_to_minors: boolean;
  status: string;
  implementation_description: string | null;
  implementation_date: string | null;
  verification_method: string | null;
  last_verified_date: string | null;
  next_verification_due: string | null;
  verification_frequency_days: number;
  risk_score: number;
  state_code: string | null;
  is_active: boolean;
}

export interface ComplianceViolation {
  id: number;
  requirement_id: number;
  title: string;
  description: string;
  severity: string;
  status: string;
  detected_at: string | null;
  detected_by: string;
  scan_id: string | null;
  affected_records_count: number;
  involves_minors: boolean;
  assigned_to_id: number | null;
  remediation_plan: string | null;
  remediation_deadline: string | null;
  root_cause: string | null;
  risk_score: number;
}

export interface ComplianceIncidentSummary {
  id: number;
  incident_number: string;
  category: string;
  severity: string;
  status: string;
  title: string;
  description: string;
  discovery_date: string | null;
  reported_at: string | null;
  involves_minors: boolean;
  affected_records_count: number;
  affected_individuals_count: number;
  notification_required: boolean;
  notification_sent: boolean;
  notification_deadline: string | null;
  assigned_to_id: number | null;
  resolved_at: string | null;
}

export interface AuditTrailEntry {
  id: number;
  sequence_number: number;
  entry_hash: string;
  actor_id: number | null;
  actor_role: string | null;
  actor_email: string | null;
  action: string;
  action_category: string;
  resource_type: string;
  resource_id: string | null;
  resource_description: string | null;
  justification: string | null;
  data_category: string | null;
  involves_minor: boolean;
  involves_pii: boolean;
  ip_address: string | null;
  created_at: string | null;
}

export interface StaffAccessLogEntry {
  id: number;
  staff_id: number | null;
  staff_role: string | null;
  access_type: string | null;
  data_category: string | null;
  resource_type: string;
  resource_id: string | null;
  resource_description: string | null;
  target_patron_id: number | null;
  target_is_minor: boolean;
  justification: string | null;
  records_accessed_count: number;
  ip_address: string | null;
  is_after_hours: boolean;
  is_bulk_access: boolean;
  is_flagged: boolean;
  flag_reason: string | null;
  accessed_at: string | null;
}

export interface RetentionRule {
  id: number;
  rule_name: string;
  rule_description: string | null;
  data_category: string;
  target_table: string;
  retention_days: number;
  retention_basis: string | null;
  expiry_action: string;
  regulation_type: string | null;
  regulation_citation: string | null;
  state_code: string | null;
  is_active: boolean;
  last_executed_at: string | null;
  next_execution_at: string | null;
  execution_frequency_hours: number;
}

export interface ComplianceReportSummary {
  id: number;
  report_type: string;
  title: string;
  period_start: string;
  period_end: string;
  status: string;
  compliance_score: number;
  total_requirements: number;
  compliant_count: number;
  non_compliant_count: number;
  violations_count: number;
  incidents_count: number;
  generated_at: string | null;
  summary: string | null;
}

export interface OfficerDashboard {
  organization_id: number;
  generated_at: string;
  compliance_score: number;
  requirements: {
    total: number;
    by_status: Record<string, number>;
    by_regulation: Record<string, { total: number; compliant: number; score: number }>;
  };
  violations: {
    open_by_severity: Record<string, number>;
    total_open: number;
  };
  incidents: {
    open_by_severity: Record<string, number>;
    total_open: number;
    pending_notifications: number;
  };
  staff_access: {
    flagged_last_30_days: number;
  };
  law_enforcement: {
    pending_requests: number;
  };
  upcoming_deadlines: Array<{
    type: string;
    title: string;
    regulation: string;
    due_date: string;
    days_until: number;
    overdue: boolean;
  }>;
}

export interface ScanResult {
  scan_id: string;
  organization_id: number;
  scanned_at: string;
  violations_found: number;
  violations: Array<{
    type: string;
    severity: string;
    [key: string]: unknown;
  }>;
}

// ============================================================================
// API Functions
// ============================================================================

export async function getDashboard(): Promise<OfficerDashboard> {
  const res = await fetchApi<{ status: string; data: OfficerDashboard } | OfficerDashboard>(`${BASE}/dashboard`);
  // Backend wraps response in {status, data} envelope
  if ('data' in res && 'status' in res) return (res as { data: OfficerDashboard }).data;
  return res as OfficerDashboard;
}

// Requirements
export async function getRequirements(params?: {
  regulation_type?: string;
  status?: string;
  state_code?: string;
  is_active?: boolean;
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<ComplianceRequirement>> {
  const url = buildUrl(`${BASE}/requirements`, params);
  return fetchApi(url);
}

export async function createRequirement(data: Record<string, unknown>): Promise<{ id: number }> {
  return fetchApi(`${BASE}/requirements`, {
    method: 'POST',
    body: data,
  });
}

export async function updateRequirement(id: number, data: Record<string, unknown>): Promise<void> {
  await fetchApi(`${BASE}/requirements/${id}`, {
    method: 'PUT',
    body: data,
  });
}

export async function verifyRequirement(id: number, notes?: string): Promise<{ next_verification_due: string }> {
  const url = buildUrl(`${BASE}/requirements/${id}/verify`, notes ? { notes } : undefined);
  return fetchApi(url, {
    method: 'POST',
    body: null,
  });
}

// Audit Trail
export async function getAuditTrail(params?: {
  actor_id?: number;
  resource_type?: string;
  resource_id?: string;
  action_category?: string;
  data_category?: string;
  involves_minor?: boolean;
  start_date?: string;
  end_date?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<AuditTrailEntry>> {
  const url = buildUrl(`${BASE}/audit-trail`, params);
  return fetchApi(url);
}

export async function verifyAuditIntegrity(params?: {
  start_sequence?: number;
  end_sequence?: number;
}): Promise<{ valid: boolean; entries_checked: number; tampered_entries: unknown[] }> {
  const url = buildUrl(`${BASE}/audit-trail/verify-integrity`, params);
  return fetchApi(url);
}

// Scanning
export async function runComplianceScan(): Promise<ScanResult> {
  return fetchApi(`${BASE}/scan`, {
    method: 'POST',
    timeoutMs: 60000,
  });
}

// Violations
export async function getViolations(params?: {
  severity?: string;
  status?: string;
  requirement_id?: number;
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<ComplianceViolation>> {
  const url = buildUrl(`${BASE}/violations`, params);
  return fetchApi(url);
}

export async function updateViolation(id: number, data: Record<string, unknown>): Promise<void> {
  await fetchApi(`${BASE}/violations/${id}`, {
    method: 'PUT',
    body: data,
  });
}

// Retention Rules
export async function getRetentionRules(params?: {
  is_active?: boolean;
  data_category?: string;
}): Promise<{ items: RetentionRule[]; total: number }> {
  const url = buildUrl(`${BASE}/retention-rules`, params);
  return fetchApi(url);
}

export async function createRetentionRule(data: Record<string, unknown>): Promise<{ id: number }> {
  return fetchApi(`${BASE}/retention-rules`, {
    method: 'POST',
    body: data,
  });
}

export async function enforceRetentionPolicies(): Promise<{ rules_executed: number; actions: unknown[] }> {
  return fetchApi(`${BASE}/retention-rules/enforce`, {
    method: 'POST',
  });
}

// Staff Access
export async function getStaffAccessLogs(params?: {
  staff_id?: number;
  data_category?: string;
  access_type?: string;
  is_flagged?: boolean;
  target_patron_id?: number;
  start_date?: string;
  end_date?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<StaffAccessLogEntry>> {
  const url = buildUrl(`${BASE}/staff-access`, params);
  return fetchApi(url);
}

export async function getStaffAccessSummary(params?: {
  staff_id?: number;
  start_date?: string;
  end_date?: string;
}): Promise<Record<string, unknown>> {
  const url = buildUrl(`${BASE}/staff-access/summary`, params);
  return fetchApi(url);
}

// Incidents
export async function getIncidents(params?: {
  severity?: string;
  status?: string;
  category?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<ComplianceIncidentSummary>> {
  const url = buildUrl(`${BASE}/incidents`, params);
  return fetchApi(url);
}

export async function createIncident(data: Record<string, unknown>): Promise<{ id: number; incident_number: string }> {
  return fetchApi(`${BASE}/incidents`, {
    method: 'POST',
    body: data,
  });
}

export async function updateIncidentStatus(id: number, status: string, notes?: string): Promise<void> {
  await fetchApi(`${BASE}/incidents/${id}/status`, {
    method: 'PUT',
    body: { status, notes },
  });
}

// Reports
export async function getReports(params?: {
  report_type?: string;
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<ComplianceReportSummary>> {
  const url = buildUrl(`${BASE}/reports`, params);
  return fetchApi(url);
}

export async function generateReport(data: {
  report_type: string;
  period_start: string;
  period_end: string;
}): Promise<{ id: number; title: string; compliance_score: number }> {
  return fetchApi(`${BASE}/reports/generate`, {
    method: 'POST',
    body: data,
    timeoutMs: 60000,
  });
}

export async function getReportDetail(id: number): Promise<Record<string, unknown>> {
  return fetchApi(`${BASE}/reports/${id}`);
}