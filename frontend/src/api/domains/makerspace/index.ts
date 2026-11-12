/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// ==================== Makerspace Domain APIs ====================
// APIs for makerspace operations including equipment, RFID, tech bookings, and staff makerspace management

export * from './makerspace-api'
export * from './formatters'
export * from './equipment-api'
export * from './rfid-api'
export * from './rfid-simulator-api'
export * from './staff-makerspace-api'

// ==================== Conflict Resolutions ====================
// Resolve duplicate exports between makerspace API files
// When conflicts exist, explicitly choose the canonical source

// Shared utility types - explicitly choose one source for PaginatedResponse to avoid conflicts
// Prefer makerspace-api as the canonical source for this domain
export { type PaginatedResponse } from './makerspace-api'

// Reservation operations - prefer staff-makerspace-api for admin operations
export {
  // type ReservationCreate, // Not in staff-makerspace-api
  type ReservationStatus,
  type ReservationCheckIn,
  type ReservationCheckOut,
  // createReservation, // Not in staff-makerspace-api
  // cancelReservation, // Not in staff-makerspace-api
  approveReservation,
  checkInReservation,
  checkOutReservation,
  markReservationNoShow,
} from './staff-makerspace-api'

// Maintenance operations - prefer staff-makerspace-api
export {
  type Maintenance,
  type MaintenanceCreate,
  type MaintenanceComplete,
  type MaintenanceStatus,
  type MaintenanceType,
  // scheduleMaintenance, // Not in staff-makerspace-api
  startMaintenance,
  completeMaintenance,
} from './staff-makerspace-api'

// RFID operations - prefer rfid-api for core RFID functionality
export {
  type RFIDProtocol,
  type RFIDReaderType,
  type RFIDReaderStatus,
  type RFIDSessionType,
  type RFIDTagProgramRequest,
  type RFIDTagProgramResponse,
  type SecurityAlertType,
  type BatchCheckinRequest,
  type BatchCheckinResponse,
  type BatchCheckinItemResult,
  type BatchCheckoutRequest,
  type BatchCheckoutResponse,
  type BatchCheckoutItemResult,
  type InventoryScanRequest,
  type MissingItemsRequest,
  type MissingItemResponse,
  type ShelfReadRequest,
  batchCheckin,
  batchCheckout,
  programTag,
  setTagSecurity,
  reportMissingItems,
  startInventorySession,
  startShelfRead,
  readerHeartbeat,
  getReaderTypeLabel,
} from './rfid-api'

// Safety and security - prefer staff-makerspace-api
export {
  type SafetyIncident,
  type SafetyIncidentCreate,
  type SafetyIncidentResolve,
  type IncidentSeverity,
  createIncident,
  resolveIncident,
  // createSecurityAlert, // Not in staff-makerspace-api
  // resolveSecurityAlert, // Not in staff-makerspace-api
} from './staff-makerspace-api'

// Consumables - prefer staff-makerspace-api
export {
  type Consumable,
  type ConsumableCreate,
  type ConsumableUnit,
  type ConsumableUsageCreate,
  type ConsumableStockAdjustment,
  createConsumable,
  adjustConsumableStock,
} from './staff-makerspace-api'

// Payments - prefer staff-makerspace-api
export {
  type Payment,
  type PaymentCreate,
  type PaymentRefund,
  createPayment,
  refundPayment,
} from './staff-makerspace-api'

// Jobs - prefer staff-makerspace-api
export {
  type JobPriority,
  type JobPickup,
  type JobComplete,
  type JobReview,
  startJob,
  failJob,
  completeJob,
  markJobReadyForPickup,
  markJobPickedUp,
  reviewJob,
} from './staff-makerspace-api'

// Certifications - prefer staff-makerspace-api
export {
  type CertificationTypeCreate,
  createCertificationType,
  certifyUser,
  suspendCertification,
  reinstateCertification,
} from './staff-makerspace-api'

// Resources - prefer staff-makerspace-api for resource management
export { createResource } from './staff-makerspace-api'

// Session management - endSession not in tech-booking-api
// export { endSession } from './tech-booking-api'

// Utility functions - not in staff-makerspace-api, already exported from makerspace-api
// export { formatStatus, getStatusColor } from './staff-makerspace-api'

// User reservations - prefer makerspace-api for patron-facing operations
export { getMyReservations } from './makerspace-api'

// Additional overrides for remaining conflicts
export { type ReservationCreate, createReservation, cancelReservation } from './makerspace-api'
export { scheduleMaintenance } from './makerspace-api'
export { formatStatus, getStatusColor } from './formatters'
export { endSession } from './rfid-api'
export { createSecurityAlert, resolveSecurityAlert } from './rfid-api'

// AvailabilityResponse: makerspace-api vs tech-booking-api → prefer makerspace-api
export { type AvailabilityResponse } from './makerspace-api'
