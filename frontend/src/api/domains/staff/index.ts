/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// ==================== Staff Domain APIs ====================
// APIs for staff operations including patron management, fines, rooms, shift swaps, and print notices

export * from '../../staff-api'
export * from './staff-fines-api'
export * from './staff-rooms-api'
export * from './shift-swap-api'
export * from './print-notices-api'
export * from './patron-account-api'
export * from './staff-search-api'
export * from './staff-message-board-api'
export * from './walk-in-rooms-api'
export * from './training-api'
export * from './staff-presence-api'

// ==================== Conflict Resolutions ====================
// Fine-related types/functions: ../../staff-api vs ./staff-fines-api → prefer staff-fines-api (domain-specific)
export {
  type Fine,
  type FineCreateRequest,
  type FinePaymentRequest,
  type FineStatus,
  type FineType,
  type PartialPaymentRequest,
  type PartialPaymentResponse,
  type PaymentHistory,
  type PaymentMethod,
  type PaymentPlan,
  type PaymentPlanFrequency,
  type PaymentPlanStatus,
  createFine,
  createPaymentPlan,
  makePartialPayment,
  payFine,
  waiveFine,
} from './staff-fines-api'

// FineWaiveRequest collision: new waiver shape (with optional amount + requires_approval)
// lives in staff-api and supersedes the legacy {reason}-only shape in staff-fines-api.
export type { FineWaiveRequest } from '../../staff-api'
