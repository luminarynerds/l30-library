/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Admin System Integrations API
 * Read-only status + manual probe trigger for external services
 * (email, SMS, payments, storage, observability, auth, AI).
 */

import api from '@/lib/api-client'

export type IntegrationCategory =
  | 'Email'
  | 'SMS'
  | 'Payments'
  | 'Storage'
  | 'Observability'
  | 'Auth'
  | 'AI'
  | 'Other'

export type IntegrationStatus = 'ok' | 'error' | 'never' | 'unconfigured'

export interface IntegrationRow {
  integration_id: string
  name: string
  category: IntegrationCategory
  configured: boolean
  status: IntegrationStatus
  last_probe_at: string | null
  last_probe_detail: string | null
}

export interface ListIntegrationsResponse {
  integrations: IntegrationRow[]
}

export interface SendTestEmailResponse {
  ok: boolean
  detail: string
  sent_to: string
}

export async function listIntegrations(): Promise<ListIntegrationsResponse> {
  return api.get<ListIntegrationsResponse>('/admin/integrations')
}

export async function probeIntegration(integrationId: string): Promise<IntegrationRow> {
  return api.post<IntegrationRow>(
    `/admin/integrations/${encodeURIComponent(integrationId)}/probe`
  )
}

export async function sendTestEmail(): Promise<SendTestEmailResponse> {
  return api.post<SendTestEmailResponse>('/admin/integrations/email/send-test')
}
