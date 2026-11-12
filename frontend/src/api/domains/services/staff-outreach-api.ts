/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Staff Outreach Management API Client
 *
 * Provides administrative operations for outreach program management including:
 * - Partner management and bulk operations
 * - Visit scheduling and tracking
 * - Bulk checkouts and deposits
 * - Institutional cards
 * - Notification templates and logs
 * - Reports, statistics, and audit functions
 * - Data export in CSV format
 */
import api from '@/lib/api-client';
import { API_BASE } from '@/api/types'

// ============================================================================
// Types - Partner Related
// ============================================================================

export type PartnerStatus = 'prospect' | 'active' | 'inactive' | 'suspended' | 'terminated';
export type PartnerType = 'school' | 'daycare' | 'senior_center' | 'community_center' | 'nonprofit' | 'correctional' | 'healthcare' | 'business' | 'government' | 'social_services';

export interface OutreachPartner {
  id: number;
  name: string;
  partner_type: PartnerType;
  status: PartnerStatus;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state?: string;
  zip_code?: string;
  primary_contact_name?: string;
  primary_contact_email?: string;
  primary_contact_phone?: string;
  school_level?: string;
  school_district?: string;
  student_count?: number;
  teacher_count?: number;
  partnership_start_date?: string;
  partnership_end_date?: string;
  allows_bulk_checkout: boolean;
  allows_institutional_card: boolean;
  requires_deposit: boolean;
  default_deposit_amount?: number;
  checkout_limit?: number;
  loan_period_days?: number;
  notes?: string;
  created_at: string;
  updated_at?: string;
}

export interface OutreachPartnerContact {
  id: number;
  partner_id: number;
  name: string;
  title?: string;
  email?: string;
  phone?: string;
  is_primary: boolean;
  notes?: string;
}

// ============================================================================
// Types - Visit Related
// ============================================================================

export type VisitStatus = 'scheduled' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled' | 'no_show' | 'rescheduled';
export type VisitType = 'storytime' | 'library_tour' | 'book_delivery' | 'card_signup' | 'classroom_visit' | 'presentation' | 'workshop' | 'collection_delivery' | 'collection_pickup' | 'assessment' | 'home_visit' | 'other';

export interface OutreachVisit {
  id: number;
  partner_id: number;
  partner_name?: string;
  visit_type: VisitType;
  status: VisitStatus;
  title?: string;
  description?: string;
  scheduled_date: string;
  scheduled_start_time?: string;
  scheduled_end_time?: string;
  actual_start_time?: string;
  actual_end_time?: string;
  location_name?: string;
  location_room?: string;
  expected_attendees?: number;
  actual_attendees?: number;
  age_group?: string;
  lead_staff_id?: number;
  lead_staff_name?: string;
  additional_staff?: string[];
  items_delivered?: number;
  items_picked_up?: number;
  new_cards_issued?: number;
  books_checked_out?: number;
  partner_rating?: number;
  staff_notes?: string;
  partner_feedback?: string;
  follow_up_needed: boolean;
  follow_up_notes?: string;
  cancellation_reason?: string;
  cancelled_by_id?: number;
  cancelled_at?: string;
  created_at: string;
  updated_at?: string;
}

// ============================================================================
// Types - Bulk Checkout Related
// ============================================================================

export type BulkCheckoutStatus = 'active' | 'returned' | 'partially_returned' | 'overdue' | 'lost';

export interface BulkCheckout {
  id: number;
  partner_id: number;
  partner_name?: string;
  checkout_name: string;
  status: BulkCheckoutStatus;
  requestor_name: string;
  requestor_email?: string;
  requestor_phone?: string;
  classroom_name?: string;
  grade_level?: string;
  checkout_date: string;
  due_date: string;
  returned_date?: string;
  total_items: number;
  items_returned: number;
  items_lost: number;
  items_damaged: number;
  deposit_required: boolean;
  deposit_amount?: number;
  deposit_collected: boolean;
  deposit_id?: number;
  staff_notes?: string;
  created_at: string;
  updated_at?: string;
}

export interface BulkCheckoutItem {
  id: number;
  bulk_checkout_id: number;
  item_id?: number;
  barcode: string;
  title: string;
  author?: string;
  status: string;
  checked_out_at: string;
  returned_at?: string;
  condition_notes?: string;
}

// ============================================================================
// Types - Deposit Related
// ============================================================================

export type DepositStatus = 'held' | 'partially_applied' | 'fully_applied' | 'refunded' | 'forfeited';
export type DepositType = 'classroom_checkout' | 'bulk_checkout' | 'institutional_card' | 'equipment' | 'special_collection';

export interface OutreachDeposit {
  id: number;
  partner_id: number;
  partner_name?: string;
  deposit_type: DepositType;
  status: DepositStatus;
  amount: number;
  amount_applied: number;
  amount_refunded: number;
  payment_method?: string;
  payment_reference?: string;
  receipt_number?: string;
  collected_date: string;
  refund_date?: string;
  expiry_date?: string;
  collected_by_id?: number;
  collected_by_name?: string;
  refunded_by_id?: number;
  refunded_by_name?: string;
  notes?: string;
  refund_reason?: string;
  created_at: string;
}

// ============================================================================
// Types - Institutional Card Related
// ============================================================================

export type InstitutionalCardStatus = 'active' | 'suspended' | 'expired' | 'cancelled';

export interface InstitutionalCard {
  id: number;
  partner_id: number;
  partner_name?: string;
  card_number: string;
  card_name: string;
  status: InstitutionalCardStatus;
  checkout_limit: number;
  hold_limit: number;
  loan_period_days: number;
  renewal_limit: number;
  exempt_from_fines: boolean;
  fine_cap?: number;
  deposit_required: boolean;
  deposit_amount?: number;
  deposit_id?: number;
  issued_date: string;
  expiry_date?: string;
  issued_by_id?: number;
  issued_by_name?: string;
  total_checkouts: number;
  current_checkouts: number;
  current_holds: number;
  current_fines: number;
  notes?: string;
  created_at: string;
}

// ============================================================================
// Types - Notification Related
// ============================================================================

export type NotificationType = 'visit_reminder' | 'due_date_reminder' | 'overdue_notice' | 'deposit_expiring' | 'card_expiring' | 'welcome' | 'thank_you';
export type NotificationChannel = 'email' | 'sms' | 'in_app';
export type NotificationLogStatus = 'pending' | 'sent' | 'delivered' | 'failed' | 'bounced';

export interface OutreachNotificationTemplate {
  id: number;
  name: string;
  notification_type: NotificationType;
  channel: NotificationChannel;
  subject?: string;
  body: string;
  html_body?: string;
  available_variables: string[];
  days_before_event?: number;
  send_time?: string;
  is_active: boolean;
  is_default: boolean;
  created_by_id?: number;
  updated_by_id?: number;
  created_at: string;
  updated_at?: string;
}

export interface OutreachNotificationLog {
  id: number;
  template_id?: number;
  notification_type: NotificationType;
  channel: NotificationChannel;
  status: NotificationLogStatus;
  recipient_email?: string;
  recipient_phone?: string;
  partner_id?: number;
  visit_id?: number;
  bulk_checkout_id?: number;
  subject?: string;
  body?: string;
  error_message?: string;
  sent_at?: string;
  delivered_at?: string;
  created_at: string;
}

// ============================================================================
// Types - Statistics Related
// ============================================================================

export interface OutreachStatistics {
  id: number;
  period_start: string;
  period_end: string;
  total_partners: number;
  active_partners: number;
  new_partners: number;
  total_visits: number;
  completed_visits: number;
  cancelled_visits: number;
  total_attendees: number;
  total_bulk_checkouts: number;
  total_items_checked_out: number;
  total_items_returned: number;
  total_items_lost: number;
  total_deposits_collected: number;
  total_deposits_refunded: number;
  total_deposits_forfeited: number;
  new_cards_issued: number;
  institutional_card_checkouts: number;
  generated_by_id?: number;
  generated_at: string;
}

// ============================================================================
// Types - Report Responses
// ============================================================================

export interface PartnerActivityReport {
  partner: {
    id: number;
    name: string;
    type: string;
    status: string;
  };
  period: {
    start_date: string;
    end_date: string;
  };
  visits: {
    total: number;
    completed: number;
    cancelled: number;
    total_attendees: number;
    cards_issued: number;
    average_attendance: number;
  };
  bulk_checkouts: {
    total: number;
    items_checked_out: number;
    items_returned: number;
    items_lost: number;
    return_rate: number;
  };
  deposits: {
    total_collected: number;
    total_refunded: number;
    total_applied: number;
    net_held: number;
  };
  institutional_cards: {
    count: number;
    active: number;
    total_checkouts: number;
  };
}

export interface OverdueSummary {
  total_overdue_checkouts: number;
  total_items_overdue: number;
  checkouts: Array<{
    checkout_id: number;
    checkout_name: string;
    partner_name: string;
    requestor: string;
    requestor_email?: string;
    due_date: string;
    days_overdue: number;
    total_items: number;
    items_returned: number;
    items_outstanding: number;
  }>;
}

export interface DepositSummary {
  total_deposits_held: number;
  total_amount_held: number;
  expired_deposits: Array<{
    deposit_id: number;
    partner_name: string;
    amount: number;
    remaining: number;
    collected_date: string;
    expiry_date?: string;
    days_expired: number;
  }>;
  expiring_within_30_days: Array<{
    deposit_id: number;
    partner_name: string;
    amount: number;
    remaining: number;
    collected_date: string;
    expiry_date?: string;
    days_until_expiry: number;
  }>;
}

export interface VisitCompletionAudit {
  period: {
    start_date: string;
    end_date: string;
  };
  staff_performance: Array<{
    staff_id: number | null;
    staff_name: string;
    total_visits: number;
    completed: number;
    cancelled: number;
    no_show: number;
    completion_rate: number;
    total_attendees: number;
    avg_attendance: number;
  }>;
}

export interface PartnerEngagementAudit {
  period_months: number;
  total_partners: number;
  engagement_breakdown: {
    high: number;
    medium: number;
    low: number;
    none: number;
  };
  partners: Array<{
    partner_id: number;
    partner_name: string;
    partner_type: string;
    visits_completed: number;
    bulk_checkouts: number;
    engagement_score: number;
    last_activity?: string;
    days_since_activity?: number;
  }>;
}

export interface NotificationStats {
  total_notifications: number;
  delivery_rate: number;
  failure_rate: number;
  by_type: Record<string, { sent: number; delivered: number; failed: number }>;
  by_channel: Record<string, number>;
  by_status: Record<string, number>;
}

// ============================================================================
// Bulk Operations API
// ============================================================================

export async function bulkUpdatePartnerStatus(
  partnerIds: number[],
  newStatus: PartnerStatus
): Promise<{ updated_count: number; new_status: string }> {
  const response = await api.post(`${API_BASE}/staff/outreach/partners/bulk-status-update`, {
    partner_ids: partnerIds,
    new_status: newStatus,
  });
  return response;
}

export async function bulkCancelVisits(
  visitIds: number[],
  cancellationReason: string
): Promise<{ cancelled_count: number }> {
  const response = await api.post(`${API_BASE}/staff/outreach/visits/bulk-cancel`, {
    visit_ids: visitIds,
    cancellation_reason: cancellationReason,
  });
  return response;
}

export async function bulkExtendDueDates(
  checkoutIds: number[],
  extensionDays: number
): Promise<{ extended_count: number; extension_days: number }> {
  const response = await api.post(`${API_BASE}/staff/outreach/bulk-checkouts/bulk-extend?extension_days=${extensionDays}`, {
    checkout_ids: checkoutIds,
  });
  return response;
}

export async function bulkForfeitDeposits(
  depositIds: number[],
  reason: string
): Promise<{ forfeited_count: number; total_amount_forfeited: number }> {
  const response = await api.post(`${API_BASE}/staff/outreach/deposits/bulk-forfeit`, {
    deposit_ids: depositIds,
    reason,
  });
  return response;
}

// ============================================================================
// Export API
// ============================================================================

export function getPartnersExportUrl(params?: {
  status?: PartnerStatus;
  partner_type?: PartnerType;
}): string {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set('status', params.status);
  if (params?.partner_type) searchParams.set('partner_type', params.partner_type);
  return `${API_BASE}/staff/outreach/export/partners?${searchParams.toString()}`;
}

export function getVisitsExportUrl(params?: {
  start_date?: string;
  end_date?: string;
  status?: VisitStatus;
}): string {
  const searchParams = new URLSearchParams();
  if (params?.start_date) searchParams.set('start_date', params.start_date);
  if (params?.end_date) searchParams.set('end_date', params.end_date);
  if (params?.status) searchParams.set('status', params.status);
  return `${API_BASE}/staff/outreach/export/visits?${searchParams.toString()}`;
}

export function getBulkCheckoutsExportUrl(params?: {
  start_date?: string;
  end_date?: string;
  status?: BulkCheckoutStatus;
  include_items?: boolean;
}): string {
  const searchParams = new URLSearchParams();
  if (params?.start_date) searchParams.set('start_date', params.start_date);
  if (params?.end_date) searchParams.set('end_date', params.end_date);
  if (params?.status) searchParams.set('status', params.status);
  if (params?.include_items) searchParams.set('include_items', 'true');
  return `${API_BASE}/staff/outreach/export/bulk-checkouts?${searchParams.toString()}`;
}

export function getDepositsExportUrl(params?: {
  start_date?: string;
  end_date?: string;
  status?: DepositStatus;
}): string {
  const searchParams = new URLSearchParams();
  if (params?.start_date) searchParams.set('start_date', params.start_date);
  if (params?.end_date) searchParams.set('end_date', params.end_date);
  if (params?.status) searchParams.set('status', params.status);
  return `${API_BASE}/staff/outreach/export/deposits?${searchParams.toString()}`;
}

export function getInstitutionalCardsExportUrl(params?: {
  status?: InstitutionalCardStatus;
}): string {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set('status', params.status);
  return `${API_BASE}/staff/outreach/export/institutional-cards?${searchParams.toString()}`;
}

// ============================================================================
// Statistics & Reports API
// ============================================================================

export async function regenerateStatistics(
  periodStart: string,
  periodEnd: string
): Promise<OutreachStatistics> {
  const response = await api.post(`${API_BASE}/staff/outreach/statistics/regenerate?period_start=${periodStart}&period_end=${periodEnd}`, {});
  return response;
}

export async function getPartnerActivityReport(
  partnerId: number,
  params?: { start_date?: string; end_date?: string }
): Promise<PartnerActivityReport> {
  const searchParams = new URLSearchParams();
  if (params?.start_date) searchParams.set('start_date', params.start_date);
  if (params?.end_date) searchParams.set('end_date', params.end_date);
  const response = await api.get(`${API_BASE}/staff/outreach/reports/partner-activity?partner_id=${partnerId}&${searchParams.toString()}`);
  return response;
}

export async function getOverdueSummary(): Promise<OverdueSummary> {
  const response = await api.get(`${API_BASE}/staff/outreach/reports/overdue-summary`);
  return response;
}

export async function getDepositSummary(): Promise<DepositSummary> {
  const response = await api.get(`${API_BASE}/staff/outreach/reports/deposit-summary`);
  return response;
}

// ============================================================================
// Audit & Compliance API
// ============================================================================

export async function getVisitCompletionAudit(
  startDate: string,
  endDate: string
): Promise<VisitCompletionAudit> {
  const response = await api.get(`${API_BASE}/staff/outreach/audit/visit-completion-rate?start_date=${startDate}&end_date=${endDate}`);
  return response;
}

export async function getPartnerEngagementAudit(months?: number): Promise<PartnerEngagementAudit> {
  const params = months ? `?months=${months}` : '';
  const response = await api.get(`${API_BASE}/staff/outreach/audit/partner-engagement${params}`);
  return response;
}

// ============================================================================
// Notification Templates API
// ============================================================================

export async function listNotificationTemplates(params?: {
  notification_type?: NotificationType;
  channel?: NotificationChannel;
  is_active?: boolean;
  limit?: number;
  offset?: number;
}): Promise<{ templates: OutreachNotificationTemplate[]; total: number; limit: number; offset: number }> {
  const searchParams = new URLSearchParams();
  if (params?.notification_type) searchParams.set('notification_type', params.notification_type);
  if (params?.channel) searchParams.set('channel', params.channel);
  if (params?.is_active !== undefined) searchParams.set('is_active', params.is_active.toString());
  if (params?.limit) searchParams.set('limit', params.limit.toString());
  if (params?.offset) searchParams.set('offset', params.offset.toString());
  const response = await api.get(`${API_BASE}/staff/outreach/notification-templates?${searchParams.toString()}`);
  return response;
}

export async function getNotificationTemplate(templateId: number): Promise<OutreachNotificationTemplate> {
  const response = await api.get(`${API_BASE}/staff/outreach/notification-templates/${templateId}`);
  return response;
}

export async function createNotificationTemplate(data: {
  name: string;
  notification_type: NotificationType;
  channel: NotificationChannel;
  subject?: string;
  body: string;
  html_body?: string;
  available_variables?: string[];
  days_before_event?: number;
  send_time?: string;
  is_active?: boolean;
  is_default?: boolean;
}): Promise<OutreachNotificationTemplate> {
  const response = await api.post(`${API_BASE}/staff/outreach/notification-templates`, data);
  return response;
}

export async function updateNotificationTemplate(
  templateId: number,
  data: Partial<{
    name: string;
    notification_type: NotificationType;
    channel: NotificationChannel;
    subject?: string;
    body: string;
    html_body?: string;
    available_variables?: string[];
    days_before_event?: number;
    send_time?: string;
    is_active?: boolean;
    is_default?: boolean;
  }>
): Promise<OutreachNotificationTemplate> {
  const response = await api.put(`${API_BASE}/staff/outreach/notification-templates/${templateId}`, data);
  return response;
}

export async function deleteNotificationTemplate(templateId: number): Promise<void> {
  await api.delete(`${API_BASE}/staff/outreach/notification-templates/${templateId}`);
}

export async function setDefaultTemplate(templateId: number): Promise<OutreachNotificationTemplate> {
  const response = await api.post(`${API_BASE}/staff/outreach/notification-templates/${templateId}/set-default`, {});
  return response;
}

export async function previewNotification(params: {
  template_id: number;
  partner_id?: number;
  visit_id?: number;
  bulk_checkout_id?: number;
  custom_variables?: Record<string, string>;
}): Promise<{ subject: string; body: string; html_body?: string; variables_used: Record<string, string> }> {
  const response = await api.post(`${API_BASE}/staff/outreach/notification-templates/preview`, params);
  return response;
}

// ============================================================================
// Notification Logs API
// ============================================================================

export async function listNotificationLogs(params?: {
  notification_type?: NotificationType;
  channel?: NotificationChannel;
  status?: NotificationLogStatus;
  partner_id?: number;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}): Promise<{ logs: OutreachNotificationLog[]; total: number; limit: number; offset: number }> {
  const searchParams = new URLSearchParams();
  if (params?.notification_type) searchParams.set('notification_type', params.notification_type);
  if (params?.channel) searchParams.set('channel', params.channel);
  if (params?.status) searchParams.set('status', params.status);
  if (params?.partner_id) searchParams.set('partner_id', params.partner_id.toString());
  if (params?.start_date) searchParams.set('start_date', params.start_date);
  if (params?.end_date) searchParams.set('end_date', params.end_date);
  if (params?.limit) searchParams.set('limit', params.limit.toString());
  if (params?.offset) searchParams.set('offset', params.offset.toString());
  const response = await api.get(`${API_BASE}/staff/outreach/notification-logs?${searchParams.toString()}`);
  return response;
}

export async function getNotificationStats(params?: {
  start_date?: string;
  end_date?: string;
}): Promise<NotificationStats> {
  const searchParams = new URLSearchParams();
  if (params?.start_date) searchParams.set('start_date', params.start_date);
  if (params?.end_date) searchParams.set('end_date', params.end_date);
  const response = await api.get(`${API_BASE}/staff/outreach/notification-logs/stats?${searchParams.toString()}`);
  return response;
}