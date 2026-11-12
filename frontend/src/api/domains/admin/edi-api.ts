/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * EDI (Electronic Data Interchange) API client
 * Handles vendor EDI profiles, transactions, invoices, and reconciliation
 */

import { fetchApi } from '@/lib/api-client'
import { getAccessToken } from '../../../utils/tokenStore'

// ============ Types ============

export type EDIStandard = 'edifact' | 'x12'
export type TransportProtocol = 'ftp' | 'sftp' | 'ftps' | 'as2' | 'email'
export type EDIMessageType = 'orders' | 'ordrsp' | 'desadv' | 'invoic'
export type EDITransactionStatus = 'pending' | 'sent' | 'acknowledged' | 'processed' | 'failed' | 'retry'
export type EDIInvoiceStatus = 'pending' | 'matched' | 'partial_match' | 'disputed' | 'approved' | 'paid'

export interface VendorEDIProfile {
  id: number
  vendor_id: number
  vendor_name: string | null
  is_enabled: boolean
  edi_standard: EDIStandard
  sender_id: string | null
  sender_qualifier: string
  receiver_id: string | null
  receiver_qualifier: string
  transport_protocol: TransportProtocol
  transport_host: string | null
  transport_port: number | null
  transport_username: string | null
  transport_directory_outbound: string
  transport_directory_inbound: string
  supports_orders: boolean
  supports_ordrsp: boolean
  supports_desadv: boolean
  supports_invoic: boolean
  max_retries: number
  retry_interval_minutes: number
  auto_send_orders: boolean
  auto_process_responses: boolean
  auto_approve_invoices: boolean
  invoice_tolerance_percent: number
  is_test_mode: boolean
  has_password: boolean
  has_ssh_key: boolean
  vendor_settings: Record<string, unknown> | null
  created_at: string
  updated_at: string | null
  last_transmission_at: string | null
  last_successful_transmission_at: string | null
}

export interface VendorEDIProfileCreate {
  vendor_id: number
  is_enabled?: boolean
  edi_standard?: EDIStandard
  sender_id?: string
  sender_qualifier?: string
  receiver_id?: string
  receiver_qualifier?: string
  transport_protocol?: TransportProtocol
  transport_host?: string
  transport_port?: number
  transport_username?: string
  transport_password?: string
  transport_directory_outbound?: string
  transport_directory_inbound?: string
  ssh_private_key?: string
  supports_orders?: boolean
  supports_ordrsp?: boolean
  supports_desadv?: boolean
  supports_invoic?: boolean
  max_retries?: number
  retry_interval_minutes?: number
  auto_send_orders?: boolean
  auto_process_responses?: boolean
  auto_approve_invoices?: boolean
  invoice_tolerance_percent?: number
  is_test_mode?: boolean
  vendor_settings?: Record<string, unknown>
}

export type VendorEDIProfileUpdate = Partial<VendorEDIProfileCreate>

export interface EDITransaction {
  id: number
  vendor_edi_profile_id: number | null
  purchase_order_id: number | null
  message_type: EDIMessageType
  direction: 'outbound' | 'inbound'
  interchange_control_number: string | null
  message_reference_number: string | null
  status: EDITransactionStatus
  filename: string | null
  retry_count: number
  next_retry_at: string | null
  last_error: string | null
  created_at: string
  sent_at: string | null
  received_at: string | null
  processed_at: string | null
  vendor_name: string | null
  po_number: string | null
}

export interface EDITransactionDetail extends EDITransaction {
  raw_message: string | null
  parsed_data: Record<string, unknown> | null
}

export interface EDIInvoiceLineItem {
  line_number: number
  isbn: string | null
  title: string | null
  quantity: number
  unit_price: number
  line_total: number
  po_item_id: number | null
  match_status: string | null
}

export interface EDIInvoice {
  id: number
  edi_transaction_id: number | null
  purchase_order_id: number | null
  vendor_id: number | null
  invoice_number: string
  invoice_date: string | null
  due_date: string | null
  subtotal: number | null
  tax_amount: number
  shipping_amount: number
  discount_amount: number
  total_amount: number
  currency_code: string
  status: EDIInvoiceStatus
  po_total: number | null
  variance_amount: number | null
  variance_reason: string | null
  matched_line_items: number
  total_line_items: number
  approved_by_id: number | null
  approved_at: string | null
  rejection_reason: string | null
  notes: string | null
  created_at: string
  updated_at: string | null
  vendor_name: string | null
  po_number: string | null
  approved_by_name: string | null
}

export interface EDIInvoiceDetail extends EDIInvoice {
  line_items: EDIInvoiceLineItem[]
}

export interface EDIOrderResponse {
  id: number
  edi_transaction_id: number | null
  purchase_order_id: number | null
  vendor_id: number | null
  vendor_order_number: string | null
  response_date: string | null
  response_code: string | null
  response_description: string | null
  items_accepted: number
  items_rejected: number
  items_backordered: number
  items_substituted: number
  expected_ship_date: string | null
  expected_delivery_date: string | null
  is_processed: boolean
  processed_at: string | null
  created_at: string
  vendor_name: string | null
  po_number: string | null
}

export interface EDIShipmentNotice {
  id: number
  edi_transaction_id: number | null
  purchase_order_id: number | null
  vendor_id: number | null
  shipment_number: string | null
  ship_date: string | null
  expected_delivery_date: string | null
  carrier_name: string | null
  carrier_code: string | null
  tracking_number: string | null
  package_count: number
  total_weight: number | null
  weight_unit: string
  total_items_shipped: number
  is_processed: boolean
  processed_at: string | null
  created_at: string
  vendor_name: string | null
  po_number: string | null
}

export interface ReconciliationResult {
  invoice_id: number
  purchase_order_id: number | null
  status: string
  matched_items: number
  total_items: number
  po_total: number | null
  invoice_total: number | null
  variance_amount: number | null
  variance_percent: number | null
  discrepancies: Array<{
    type: string
    message?: string
    line_number?: number
    isbn?: string
    title?: string
  }>
  recommendations: string[]
}

export interface EDIStatistics {
  total_transactions: number
  pending_transactions: number
  failed_transactions: number
  successful_transactions: number
  pending_invoices: number
  disputed_invoices: number
  total_invoice_amount: number
  average_processing_time_seconds: number | null
  last_24h_transactions: number
  by_message_type: Record<string, number>
  by_vendor: Record<string, number>
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
}

// ============ EDI Profile API ============

export async function getEDIProfiles(params?: {
  vendor_id?: number
  enabled_only?: boolean
}): Promise<VendorEDIProfile[]> {
  const token = getAccessToken()
  const query = new URLSearchParams()
  if (params?.vendor_id) query.set('vendor_id', String(params.vendor_id))
  if (params?.enabled_only) query.set('enabled_only', 'true')
  const queryString = query.toString()

  return await fetchApi<VendorEDIProfile[]>(
    `/edi/profiles${queryString ? `?${queryString}` : ''}`,
    { ...(token ? { token } : {}) }
  )
}

export async function getEDIProfile(profileId: number): Promise<VendorEDIProfile> {
  const token = getAccessToken()
  return await fetchApi<VendorEDIProfile>(`/edi/profiles/${profileId}`, {
    ...(token ? { token } : {}),
  })
}

export async function getVendorEDIProfile(vendorId: number): Promise<VendorEDIProfile | null> {
  const token = getAccessToken()
  return await fetchApi<VendorEDIProfile | null>(`/edi/profiles/vendor/${vendorId}`, {
    ...(token ? { token } : {}),
  })
}

export async function createEDIProfile(data: VendorEDIProfileCreate): Promise<VendorEDIProfile> {
  const token = getAccessToken()
  return await fetchApi<VendorEDIProfile>('/edi/profiles', {
    method: 'POST',
    ...(token ? { token } : {}),
    body: JSON.stringify(data),
  })
}

export async function updateEDIProfile(
  profileId: number,
  data: VendorEDIProfileUpdate
): Promise<VendorEDIProfile> {
  const token = getAccessToken()
  return await fetchApi<VendorEDIProfile>(`/edi/profiles/${profileId}`, {
    method: 'PATCH',
    ...(token ? { token } : {}),
    body: JSON.stringify(data),
  })
}

export async function deleteEDIProfile(profileId: number): Promise<{ message: string }> {
  const token = getAccessToken()
  return await fetchApi<{ message: string }>(`/edi/profiles/${profileId}`, {
    method: 'DELETE',
    ...(token ? { token } : {}),
  })
}

// ============ Connection Testing ============

export async function testEDIConnection(vendorId: number): Promise<{
  success: boolean
  message: string
  details: Record<string, unknown> | null
}> {
  const token = getAccessToken()
  return await fetchApi('/edi/test-connection', {
    method: 'POST',
    ...(token ? { token } : {}),
    body: JSON.stringify({ vendor_id: vendorId }),
  })
}

// ============ Send Orders ============

export async function sendEDIOrder(purchaseOrderId: number): Promise<{
  success: boolean
  transaction_id: number | null
  interchange_control_number: string | null
  message: string
  error: string | null
}> {
  const token = getAccessToken()
  return await fetchApi('/edi/send-order', {
    method: 'POST',
    ...(token ? { token } : {}),
    body: JSON.stringify({ purchase_order_id: purchaseOrderId }),
  })
}

// ============ Transaction Management ============

export async function getEDITransactions(params?: {
  vendor_id?: number
  purchase_order_id?: number
  message_type?: EDIMessageType
  status?: EDITransactionStatus
  direction?: 'outbound' | 'inbound'
  page?: number
  per_page?: number
}): Promise<PaginatedResponse<EDITransaction>> {
  const token = getAccessToken()
  const query = new URLSearchParams()
  if (params?.vendor_id) query.set('vendor_id', String(params.vendor_id))
  if (params?.purchase_order_id) query.set('purchase_order_id', String(params.purchase_order_id))
  if (params?.message_type) query.set('message_type', params.message_type)
  if (params?.status) query.set('status', params.status)
  if (params?.direction) query.set('direction', params.direction)
  if (params?.page) query.set('page', String(params.page))
  if (params?.per_page) query.set('per_page', String(params.per_page))
  const queryString = query.toString()

  return await fetchApi<PaginatedResponse<EDITransaction>>(
    `/edi/transactions${queryString ? `?${queryString}` : ''}`,
    { ...(token ? { token } : {}) }
  )
}

export async function getEDITransaction(transactionId: number): Promise<EDITransactionDetail> {
  const token = getAccessToken()
  return await fetchApi<EDITransactionDetail>(`/edi/transactions/${transactionId}`, {
    ...(token ? { token } : {}),
  })
}

export async function retryEDITransaction(transactionId: number): Promise<{
  success: boolean
  transaction_id: number
  new_status: EDITransactionStatus
  message: string
  error: string | null
}> {
  const token = getAccessToken()
  return await fetchApi(`/edi/transactions/${transactionId}/retry`, {
    method: 'POST',
    ...(token ? { token } : {}),
  })
}

// ============ Process Inbound ============

export async function processInboundMessages(vendorId?: number): Promise<{
  vendors_processed: number
  files_processed: number
  transactions_created: number
  errors: Array<{ vendor_id?: number; filename?: string; error: string }>
}> {
  const token = getAccessToken()
  return await fetchApi('/edi/process-inbound', {
    method: 'POST',
    ...(token ? { token } : {}),
    body: JSON.stringify({ vendor_id: vendorId }),
  })
}

// ============ Invoice Management ============

export async function getEDIInvoices(params?: {
  vendor_id?: number
  purchase_order_id?: number
  status?: EDIInvoiceStatus
  page?: number
  per_page?: number
}): Promise<PaginatedResponse<EDIInvoice>> {
  const token = getAccessToken()
  const query = new URLSearchParams()
  if (params?.vendor_id) query.set('vendor_id', String(params.vendor_id))
  if (params?.purchase_order_id) query.set('purchase_order_id', String(params.purchase_order_id))
  if (params?.status) query.set('status', params.status)
  if (params?.page) query.set('page', String(params.page))
  if (params?.per_page) query.set('per_page', String(params.per_page))
  const queryString = query.toString()

  return await fetchApi<PaginatedResponse<EDIInvoice>>(
    `/edi/invoices${queryString ? `?${queryString}` : ''}`,
    { ...(token ? { token } : {}) }
  )
}

export async function getEDIInvoice(invoiceId: number): Promise<EDIInvoiceDetail> {
  const token = getAccessToken()
  return await fetchApi<EDIInvoiceDetail>(`/edi/invoices/${invoiceId}`, {
    ...(token ? { token } : {}),
  })
}

export async function reconcileInvoice(invoiceId: number): Promise<ReconciliationResult> {
  const token = getAccessToken()
  return await fetchApi<ReconciliationResult>(`/edi/invoices/${invoiceId}/reconcile`, {
    method: 'POST',
    ...(token ? { token } : {}),
  })
}

export async function batchReconcileInvoices(invoiceIds?: number[]): Promise<{
  total_processed: number
  matched: number
  partial_match: number
  disputed: number
  errors: number
  results: ReconciliationResult[]
}> {
  const token = getAccessToken()
  return await fetchApi('/edi/invoices/batch-reconcile', {
    method: 'POST',
    ...(token ? { token } : {}),
    body: JSON.stringify({ invoice_ids: invoiceIds || [] }),
  })
}

export async function approveInvoice(invoiceId: number, notes?: string): Promise<{ message: string }> {
  const token = getAccessToken()
  return await fetchApi<{ message: string }>(`/edi/invoices/${invoiceId}/approve`, {
    method: 'POST',
    ...(token ? { token } : {}),
    body: JSON.stringify({ notes }),
  })
}

export async function disputeInvoice(invoiceId: number, reason: string): Promise<{ message: string }> {
  const token = getAccessToken()
  return await fetchApi<{ message: string }>(`/edi/invoices/${invoiceId}/dispute`, {
    method: 'POST',
    ...(token ? { token } : {}),
    body: JSON.stringify({ reason }),
  })
}

export async function autoApproveInvoices(vendorId?: number): Promise<{
  processed: number
  approved: number
  skipped: number
  details: Array<{
    invoice_id: number
    status: string
    reason?: string
    variance_percent?: string
  }>
}> {
  const token = getAccessToken()
  const query = vendorId ? `?vendor_id=${vendorId}` : ''
  return await fetchApi(`/edi/invoices/auto-approve${query}`, {
    method: 'POST',
    ...(token ? { token } : {}),
  })
}

// ============ Order Responses ============

export async function getOrderResponses(params?: {
  vendor_id?: number
  purchase_order_id?: number
  page?: number
  per_page?: number
}): Promise<PaginatedResponse<EDIOrderResponse>> {
  const token = getAccessToken()
  const query = new URLSearchParams()
  if (params?.vendor_id) query.set('vendor_id', String(params.vendor_id))
  if (params?.purchase_order_id) query.set('purchase_order_id', String(params.purchase_order_id))
  if (params?.page) query.set('page', String(params.page))
  if (params?.per_page) query.set('per_page', String(params.per_page))
  const queryString = query.toString()

  return await fetchApi<PaginatedResponse<EDIOrderResponse>>(
    `/edi/order-responses${queryString ? `?${queryString}` : ''}`,
    { ...(token ? { token } : {}) }
  )
}

// ============ Shipment Notices ============

export async function getShipmentNotices(params?: {
  vendor_id?: number
  purchase_order_id?: number
  page?: number
  per_page?: number
}): Promise<PaginatedResponse<EDIShipmentNotice>> {
  const token = getAccessToken()
  const query = new URLSearchParams()
  if (params?.vendor_id) query.set('vendor_id', String(params.vendor_id))
  if (params?.purchase_order_id) query.set('purchase_order_id', String(params.purchase_order_id))
  if (params?.page) query.set('page', String(params.page))
  if (params?.per_page) query.set('per_page', String(params.per_page))
  const queryString = query.toString()

  return await fetchApi<PaginatedResponse<EDIShipmentNotice>>(
    `/edi/shipment-notices${queryString ? `?${queryString}` : ''}`,
    { ...(token ? { token } : {}) }
  )
}

// ============ Statistics ============

export async function getEDIStatistics(vendorId?: number): Promise<EDIStatistics> {
  const token = getAccessToken()
  const query = vendorId ? `?vendor_id=${vendorId}` : ''
  return await fetchApi<EDIStatistics>(`/edi/statistics${query}`, {
    ...(token ? { token } : {}),
  })
}
