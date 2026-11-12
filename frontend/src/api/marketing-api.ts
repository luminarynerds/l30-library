/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Marketing API Service
 *
 * Handles marketing communication endpoints:
 * - Newsletter subscription management
 * - Interest categories
 * - New arrival alerts
 * - Email preferences
 * - Marketing analytics
 */

import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Enums ====================

export type NewsletterFrequency = 'daily' | 'weekly' | 'biweekly' | 'monthly'
export type SubscriptionStatus = 'active' | 'pending' | 'unsubscribed' | 'bounced'
export type ConsentSource = 'newsletter_form' | 'account_settings' | 'checkout' | 'event_registration' | 'import'
export type UnsubscribeReason = 'too_many_emails' | 'not_relevant' | 'never_signed_up' | 'other' | 'one_click'
export type DeliveryMethod = 'email' | 'sms' | 'both'

// ==================== Interest Category Types ====================

export interface InterestCategory {
  id: number
  name: string
  slug: string
  description: string | null
  icon: string | null
  color: string | null
  parent_id: number | null
  is_active?: boolean
  display_order?: number
  subscriber_count?: number
}

export interface InterestCategoryCreate {
  name: string
  slug: string
  description?: string
  icon?: string
  color?: string
  parent_id?: number
}

// ==================== Newsletter Subscription Types ====================

export interface NewsletterSignupRequest {
  email: string
  first_name?: string
  last_name?: string
  frequency?: NewsletterFrequency
  interest_ids?: number[]
  consent_source?: ConsentSource
}

export interface NewsletterStatusResponse {
  subscribed: boolean
  status: SubscriptionStatus | null
  frequency?: NewsletterFrequency
  confirmed?: boolean
  interests?: InterestCategory[]
}

// ==================== New Arrival Alert Types ====================

export interface NewArrivalAlert {
  id: number
  user_id: number
  category_id: number | null
  category_name: string | null
  search_query: string | null
  author_name: string | null
  series_name: string | null
  delivery_method: DeliveryMethod
  frequency: NewsletterFrequency
  is_active: boolean
  created_at: string
}

export interface NewArrivalAlertCreate {
  category_id?: number
  search_query?: string
  author_name?: string
  series_name?: string
  delivery_method?: DeliveryMethod
  frequency?: NewsletterFrequency
}

// ==================== Analytics Types ====================

export interface MarketingAnalytics {
  total_subscribers: number
  active_subscribers: number
  new_subscribers_this_month: number
  unsubscribed_this_month: number
  subscriber_growth_rate: number
  average_open_rate: number
  average_click_rate: number
  subscribers_by_frequency: Record<NewsletterFrequency, number>
  subscribers_by_interest: { interest: string; count: number }[]
  subscriber_trend: { date: string; count: number }[]
}

// ==================== Newsletter API Functions ====================

export async function subscribeToNewsletter(
  data: NewsletterSignupRequest
): Promise<{ message: string; status: string }> {
  try {
    return await fetchApi<{ message: string; status: string }>('/marketing/newsletter/subscribe', {
      method: 'POST',
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to subscribe to newsletter')
    }
    throw error
  }
}

export async function confirmNewsletterSubscription(
  token: string
): Promise<{ message: string; status: string }> {
  try {
    return await fetchApi<{ message: string; status: string }>('/marketing/newsletter/confirm', {
      method: 'POST',
      body: { token },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to confirm subscription')
    }
    throw error
  }
}

export async function getNewsletterStatus(
  authToken: string
): Promise<NewsletterStatusResponse> {
  try {
    return await fetchApi<NewsletterStatusResponse>('/marketing/newsletter/status', {
      token: authToken,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get newsletter status')
    }
    throw error
  }
}

export async function unsubscribeFromNewsletter(
  authToken: string
): Promise<{ message: string }> {
  try {
    return await fetchApi<{ message: string }>('/marketing/newsletter/unsubscribe', {
      method: 'DELETE',
      token: authToken,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to unsubscribe')
    }
    throw error
  }
}

// ==================== Interest Categories API Functions ====================

export async function getInterestCategories(): Promise<InterestCategory[]> {
  try {
    return await fetchApi<InterestCategory[]>('/marketing/interests')
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch interest categories')
    }
    throw error
  }
}

export async function getMyInterests(
  authToken: string
): Promise<{ interests: InterestCategory[] }> {
  try {
    return await fetchApi<{ interests: InterestCategory[] }>('/marketing/interests/mine', {
      token: authToken,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch interests')
    }
    throw error
  }
}

export async function updateMyInterests(
  authToken: string,
  interestIds: number[]
): Promise<{ message: string; interests: string[] }> {
  try {
    return await fetchApi<{ message: string; interests: string[] }>('/marketing/interests/mine', {
      method: 'PUT',
      token: authToken,
      body: { interest_ids: interestIds },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update interests')
    }
    throw error
  }
}

export async function createInterestCategory(
  authToken: string,
  data: InterestCategoryCreate
): Promise<InterestCategory> {
  try {
    const params = new URLSearchParams()
    params.set('name', data.name)
    params.set('slug', data.slug)
    if (data.description) params.set('description', data.description)
    if (data.icon) params.set('icon', data.icon)
    if (data.color) params.set('color', data.color)
    if (data.parent_id) params.set('parent_id', data.parent_id.toString())
    return await fetchApi<InterestCategory>(`/marketing/admin/interests?${params.toString()}`, {
      method: 'POST',
      token: authToken,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create interest category')
    }
    throw error
  }
}

// ==================== New Arrival Alerts API Functions ====================

export async function getMyAlerts(
  authToken: string
): Promise<{ alerts: NewArrivalAlert[] }> {
  try {
    return await fetchApi<{ alerts: NewArrivalAlert[] }>('/marketing/alerts', {
      token: authToken,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch alerts')
    }
    throw error
  }
}

export async function createArrivalAlert(
  authToken: string,
  data: NewArrivalAlertCreate
): Promise<{ message: string; alert_id: number }> {
  try {
    return await fetchApi<{ message: string; alert_id: number }>('/marketing/alerts', {
      method: 'POST',
      token: authToken,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create alert')
    }
    throw error
  }
}

export async function deleteArrivalAlert(
  authToken: string,
  alertId: number
): Promise<{ message: string }> {
  try {
    return await fetchApi<{ message: string }>(`/marketing/alerts/${alertId}`, {
      method: 'DELETE',
      token: authToken,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete alert')
    }
    throw error
  }
}

// ==================== Unsubscribe API Functions (Token-based) ====================

export async function processUnsubscribe(
  unsubscribeToken: string,
  reason?: UnsubscribeReason,
  feedback?: string
): Promise<{ success: boolean; message: string }> {
  try {
    return await fetchApi<{ success: boolean; message: string }>('/marketing/unsubscribe', {
      method: 'POST',
      body: {
        token: unsubscribeToken,
        reason,
        feedback,
      },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to process unsubscribe')
    }
    throw error
  }
}

export async function getPreferencesByToken(
  preferencesToken: string
): Promise<{
  email: string
  newsletter_enabled: boolean
  frequency: NewsletterFrequency
  interests: InterestCategory[]
  available_interests: InterestCategory[]
}> {
  try {
    return await fetchApi(`/marketing/preferences?token=${encodeURIComponent(preferencesToken)}`)
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get preferences')
    }
    throw error
  }
}

export async function updatePreferencesByToken(
  preferencesToken: string,
  data: {
    newsletter_enabled?: boolean
    frequency?: NewsletterFrequency
    interest_ids?: number[]
  }
): Promise<{ message: string }> {
  try {
    return await fetchApi<{ message: string }>('/marketing/preferences', {
      method: 'PUT',
      body: {
        token: preferencesToken,
        ...data,
      },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update preferences')
    }
    throw error
  }
}

// ==================== Admin Analytics API Functions ====================

export async function getMarketingAnalytics(
  authToken: string,
  options?: {
    days?: number
  }
): Promise<MarketingAnalytics> {
  const params = new URLSearchParams()
  if (options?.days) params.set('days', options.days.toString())
  const queryString = params.toString() ? `?${params.toString()}` : ''
  try {
    return await fetchApi<MarketingAnalytics>(`/marketing/admin/analytics${queryString}`, {
      token: authToken,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch marketing analytics')
    }
    throw error
  }
}



