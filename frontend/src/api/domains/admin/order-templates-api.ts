/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '../../../utils/tokenStore'

// ============ Types ============

export interface TemplateItem {
  title: string
  author?: string | null
  isbn?: string | null
  quantity: number
  unit_price?: number | null
  notes?: string | null
}

export interface OrderTemplate {
  id: number
  name: string
  description?: string | null
  vendor_id?: number | null
  fund_id?: number | null
  created_by_id: number
  created_by_name?: string | null
  is_shared: boolean
  template_items: TemplateItem[]
  item_count: number
  vendor_name?: string | null
  fund_name?: string | null
  created_at: string
  updated_at?: string | null
}

export interface OrderTemplateCreate {
  name: string
  description?: string
  vendor_id?: number | null
  fund_id?: number | null
  is_shared?: boolean
  template_items?: TemplateItem[]
}

export interface OrderTemplateUpdate {
  name?: string
  description?: string
  vendor_id?: number | null
  fund_id?: number | null
  is_shared?: boolean
  template_items?: TemplateItem[]
}

export interface CreatePOFromTemplateRequest {
  vendor_id?: number | null
  fund_id?: number | null
  notes?: string
}

export interface CreatePOFromTemplateResponse {
  id: number
  po_number: string
  items_added: number
  total_amount: number
}

export interface SaveAsTemplateRequest {
  name: string
  description?: string
  is_shared?: boolean
}

// ============ API Functions ============

export async function getOrderTemplates(): Promise<OrderTemplate[]> {
  const token = getAccessToken()
  try {
    return await fetchApi<OrderTemplate[]>('/acquisition/order-templates', { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch order templates')
    }
    throw error
  }
}

export async function getOrderTemplate(id: number): Promise<OrderTemplate> {
  const token = getAccessToken()
  try {
    return await fetchApi<OrderTemplate>(`/acquisition/order-templates/${id}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch order template')
    }
    throw error
  }
}

export async function createOrderTemplate(data: OrderTemplateCreate): Promise<OrderTemplate> {
  const token = getAccessToken()
  try {
    return await fetchApi<OrderTemplate>('/acquisition/order-templates', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create order template')
    }
    throw error
  }
}

export async function updateOrderTemplate(id: number, data: OrderTemplateUpdate): Promise<OrderTemplate> {
  const token = getAccessToken()
  try {
    return await fetchApi<OrderTemplate>(`/acquisition/order-templates/${id}`, {
      method: 'PATCH',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update order template')
    }
    throw error
  }
}

export async function deleteOrderTemplate(id: number): Promise<void> {
  const token = getAccessToken()
  try {
    await fetchApi<void>(`/acquisition/order-templates/${id}`, {
      method: 'DELETE',
      ...(token ? { token } : {}),
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete order template')
    }
    throw error
  }
}

export async function createPOFromTemplate(
  templateId: number,
  data: CreatePOFromTemplateRequest
): Promise<CreatePOFromTemplateResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<CreatePOFromTemplateResponse>(
      `/acquisition/order-templates/${templateId}/create-po`,
      {
        method: 'POST',
        ...(token ? { token } : {}),
        body: data,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create PO from template')
    }
    throw error
  }
}

export async function savePOAsTemplate(
  poId: number,
  data: SaveAsTemplateRequest
): Promise<OrderTemplate> {
  const token = getAccessToken()
  try {
    return await fetchApi<OrderTemplate>(
      `/acquisition/purchase-orders/${poId}/save-as-template`,
      {
        method: 'POST',
        ...(token ? { token } : {}),
        body: data,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to save PO as template')
    }
    throw error
  }
}
