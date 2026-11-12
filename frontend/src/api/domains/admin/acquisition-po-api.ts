/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '../../../utils/tokenStore'
import { API_BASE } from '@/api/types'

// ============ Enums ============

export type PurchaseOrderStatus =
  | 'draft'
  | 'pending_approval'
  | 'approved'
  | 'rejected'
  | 'submitted'
  | 'partially_received'
  | 'received'
  | 'cancelled'

// ============ PO Item Types ============

export interface POItemCreate {
  title: string
  author?: string
  isbn?: string
  quantity?: number
  unit_price?: number
  notes?: string
}

export interface POItemUpdate {
  title?: string
  author?: string
  isbn?: string
  quantity?: number
  unit_price?: number
  notes?: string
}

export interface POItemResponse {
  id: number
  purchase_order_id: number
  title: string
  author: string | null
  isbn: string | null
  quantity: number
  unit_price: number
  received_quantity: number
  line_total: number
  is_fully_received: boolean
  catalog_item_id: number | null
  notes: string | null
  created_at: string
}

// ============ Purchase Order Types ============

export interface PurchaseOrderCreate {
  vendor_id?: number
  fund_id?: number
  order_date?: string
  expected_delivery?: string
  notes?: string
  items?: POItemCreate[]
}

export interface PurchaseOrderUpdate {
  vendor_id?: number
  fund_id?: number
  order_date?: string
  expected_delivery?: string
  notes?: string
}

export interface PurchaseOrderResponse {
  id: number
  po_number: string
  status: PurchaseOrderStatus
  vendor_id: number | null
  fund_id: number | null
  order_date: string | null
  expected_delivery: string | null
  actual_delivery: string | null
  notes: string | null
  total_amount: number
  total_items: number
  vendor_name: string | null
  fund_name: string | null
  approved_by_id: number | null
  approved_at: string | null
  rejection_notes: string | null
  created_by_id: number
  created_at: string
}

export interface PurchaseOrderDetail extends PurchaseOrderResponse {
  items: POItemResponse[]
}

export interface PurchaseOrderListResponse {
  items: PurchaseOrderResponse[]
  total: number
  page: number
  per_page: number
}

// ============ Workflow Types ============

export interface RejectionRequest {
  notes: string
}

export interface ReceiveItemRequest {
  item_id: number
  received_quantity: number
}

export interface ReceiveItemsRequest {
  items: ReceiveItemRequest[]
}

// ============ Budget Validation Types ============

export interface FundSuggestion {
  id: number
  code: string
  name: string
  available_amount: number
}

export interface BudgetValidationResponse {
  is_valid: boolean
  fund_id: number | null
  fund_code: string | null
  fund_name: string | null
  available_amount: number
  order_total: number
  remaining_after_order: number
  usage_percentage: number
  warning_level: 'none' | 'warning' | 'danger'
  message: string
  exceeds_budget_by?: number
  suggested_funds: FundSuggestion[]
}

// ============ Email Response ============

export interface EmailVendorResponse {
  message: string
}

// ============ Purchase Order CRUD API Functions ============

export async function getPurchaseOrders(params?: {
  status?: PurchaseOrderStatus
  vendor_id?: number
  fund_id?: number
  page?: number
  per_page?: number
}): Promise<PurchaseOrderListResponse> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set('status', params.status)
  if (params?.vendor_id) searchParams.set('vendor_id', params.vendor_id.toString())
  if (params?.fund_id) searchParams.set('fund_id', params.fund_id.toString())
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.per_page) searchParams.set('per_page', params.per_page.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<PurchaseOrderListResponse>(`/acquisition/purchase-orders${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch purchase orders')
    }
    throw error
  }
}

export async function getPurchaseOrder(poId: number): Promise<PurchaseOrderDetail> {
  const token = getAccessToken()
  try {
    return await fetchApi<PurchaseOrderDetail>(`/acquisition/purchase-orders/${poId}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch purchase order')
    }
    throw error
  }
}

export async function createPurchaseOrder(data: PurchaseOrderCreate): Promise<PurchaseOrderResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<PurchaseOrderResponse>('/acquisition/purchase-orders', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create purchase order')
    }
    throw error
  }
}

export async function updatePurchaseOrder(poId: number, data: PurchaseOrderUpdate): Promise<PurchaseOrderResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<PurchaseOrderResponse>(`/acquisition/purchase-orders/${poId}`, {
      method: 'PATCH',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update purchase order')
    }
    throw error
  }
}

// ============ PO Items API Functions ============

export async function addPOItem(poId: number, data: POItemCreate): Promise<POItemResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<POItemResponse>(`/acquisition/purchase-orders/${poId}/items`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to add item to purchase order')
    }
    throw error
  }
}

export async function removePOItem(poId: number, itemId: number): Promise<void> {
  const token = getAccessToken()
  try {
    await fetchApi<void>(`/acquisition/purchase-orders/${poId}/items/${itemId}`, {
      method: 'DELETE',
      ...(token ? { token } : {}),
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to remove item from purchase order')
    }
    throw error
  }
}

export async function updatePOItem(poId: number, itemId: number, data: POItemUpdate): Promise<POItemResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<POItemResponse>(`/acquisition/purchase-orders/${poId}/items/${itemId}`, {
      method: 'PATCH',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update purchase order item')
    }
    throw error
  }
}

// ============ Workflow API Functions ============

export async function submitPOForApproval(poId: number): Promise<PurchaseOrderResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<PurchaseOrderResponse>(`/acquisition/purchase-orders/${poId}/submit-for-approval`, {
      method: 'PATCH',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to submit purchase order for approval')
    }
    throw error
  }
}

export async function approvePurchaseOrder(poId: number): Promise<PurchaseOrderResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<PurchaseOrderResponse>(`/acquisition/purchase-orders/${poId}/approve`, {
      method: 'PATCH',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to approve purchase order')
    }
    throw error
  }
}

export async function rejectPurchaseOrder(poId: number, data: RejectionRequest): Promise<PurchaseOrderResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<PurchaseOrderResponse>(`/acquisition/purchase-orders/${poId}/reject`, {
      method: 'PATCH',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to reject purchase order')
    }
    throw error
  }
}

export async function submitPurchaseOrder(poId: number): Promise<PurchaseOrderResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<PurchaseOrderResponse>(`/acquisition/purchase-orders/${poId}/submit`, {
      method: 'PATCH',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to submit purchase order to vendor')
    }
    throw error
  }
}

export async function receivePurchaseOrder(poId: number, data: ReceiveItemsRequest): Promise<PurchaseOrderResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<PurchaseOrderResponse>(`/acquisition/purchase-orders/${poId}/receive`, {
      method: 'PATCH',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to receive purchase order items')
    }
    throw error
  }
}

// ============ Budget Validation API Functions ============

export async function validatePOBudget(poId: number): Promise<BudgetValidationResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<BudgetValidationResponse>(`/acquisition/purchase-orders/${poId}/budget-validation`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to validate purchase order budget')
    }
    throw error
  }
}

export async function checkFundBudget(fundId: number, orderTotal?: number): Promise<BudgetValidationResponse> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (orderTotal !== undefined) searchParams.set('order_total', orderTotal.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<BudgetValidationResponse>(`/acquisition/funds/${fundId}/budget-check${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to check fund budget')
    }
    throw error
  }
}

// ============ PDF and Email API Functions ============

export async function downloadPurchaseOrderPDF(poId: number): Promise<Blob> {
  const token = getAccessToken()
  try {
    const response = await fetch(`${API_BASE}/acquisition/purchase-orders/${poId}/pdf`, {
      method: 'GET',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Failed to download purchase order PDF')
    }
    return await response.blob()
  } catch (error: unknown) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Failed to download purchase order PDF')
  }
}

export async function emailPurchaseOrderToVendor(poId: number): Promise<EmailVendorResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<EmailVendorResponse>(`/acquisition/purchase-orders/${poId}/email-vendor`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to email purchase order to vendor')
    }
    throw error
  }
}