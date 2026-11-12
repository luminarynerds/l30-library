/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type {
  PartnerStatus,
  BulkCheckoutStatus,
  DepositStatus,
  OutreachNotificationTemplate,
  NotificationType,
  NotificationChannel,
} from '../../../api/staff-outreach-api'

export type { PartnerStatus, BulkCheckoutStatus, DepositStatus, OutreachNotificationTemplate, NotificationType, NotificationChannel }

export type TabId = "overview" | "partners" | "visits" | "checkouts" | "deposits" | "cards" | "templates" | "reports"

export type BulkActionType = "partner_status" | "cancel_visits" | "extend_due" | "forfeit_deposits"

export interface TemplateFormState {
  name: string
  notification_type: NotificationType
  channel: NotificationChannel
  subject: string
  body: string
  is_active: boolean
  is_default: boolean
}
