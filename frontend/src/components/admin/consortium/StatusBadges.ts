/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { ConsortiumMemberStatus, BillingStatus } from '../../../api/consortium-api'

// Status badge styles
export const STATUS_STYLES: Record<ConsortiumMemberStatus, { bg: string; text: string }> = {
  pending: { bg: 'bg-status-warning-100 dark:bg-status-warning-900/30', text: 'text-status-warning-700 dark:text-status-warning-400' },
  active: { bg: 'bg-status-success-100 dark:bg-status-success-900/30', text: 'text-status-success-700 dark:text-status-success-400' },
  suspended: { bg: 'bg-status-danger-100 dark:bg-status-danger-900/30', text: 'text-status-danger-700 dark:text-status-danger-400' },
  withdrawn: { bg: 'bg-earth-100 dark:bg-earth-900/30', text: 'text-earth-700 dark:text-earth-300' },
  expelled: { bg: 'bg-status-danger-200 dark:bg-status-danger-900/50', text: 'text-status-danger-800 dark:text-status-danger-300' },
}

export const BILLING_STATUS_STYLES: Record<BillingStatus, { bg: string; text: string }> = {
  pending: { bg: 'bg-status-warning-100 dark:bg-status-warning-900/30', text: 'text-status-warning-700 dark:text-status-warning-400' },
  invoiced: { bg: 'bg-earth-100 dark:bg-earth-800/30', text: 'text-lsc-rose dark:text-lsc-rose-light' },
  paid: { bg: 'bg-status-success-100 dark:bg-status-success-900/30', text: 'text-status-success-700 dark:text-status-success-400' },
  overdue: { bg: 'bg-status-danger-100 dark:bg-status-danger-900/30', text: 'text-status-danger-700 dark:text-status-danger-400' },
  disputed: { bg: 'bg-status-warning-100 dark:bg-status-warning-900/30', text: 'text-status-warning-700 dark:text-status-warning-400' },
  cancelled: { bg: 'bg-earth-100 dark:bg-earth-900/30', text: 'text-earth-700 dark:text-earth-300' },
}

export const MEMBER_TYPE_LABELS: Record<string, string> = {
  FULL: 'Full Member',
  ASSOCIATE: 'Associate',
  AFFILIATE: 'Affiliate',
  FOUNDING: 'Founding Member',
}
