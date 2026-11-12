/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// ==================== Community Services Domain APIs ====================
// APIs for community services including home delivery, outreach programs, emergency operations, and law enforcement coordination

export * from './homeDeliveryApi'
export * from './law-enforcement-api'
export * from './emergency-operations-api'

// Export all from outreach-api except the conflicting types (resolved below by staff-outreach-api)
export type {
  SchoolLevel,
  OutreachPartnerContactCreate,
  OutreachPartnerCreate,
  OutreachPartnerUpdate,
  OutreachPartnerListResponse,
  OutreachDepositCreate,
  OutreachDepositRefund,
  DepositApplicationCreate,
  DepositApplication,
  InstitutionalCardCreate,
  InstitutionalCardUpdate,
  InstitutionalCardListResponse,
  BulkCheckoutCreate,
  BulkCheckoutItemReturn,
  BulkCheckoutListResponse,
  OutreachVisitCreate,
  OutreachVisitUpdate,
  OutreachVisitListResponse,
  OutreachReportRequest,
  OutreachReport,
} from './outreach-api'

export {
  createPartner,
  updatePartner,
  deletePartner,
  addPartnerContact,
  createDeposit,
  refundDeposit,
  applyDeposit,
  createVisit,
  updateVisit,
  completeVisit,
  cancelVisit,
  createInstitutionalCard,
  updateInstitutionalCard,
  institutionalCheckout,
  createBulkCheckout,
  addBulkCheckoutItems,
  returnBulkCheckoutItem,
  returnAllBulkCheckoutItems,
  generateOutreachReport,
} from './outreach-api'

// Export all from staff-outreach-api (takes precedence for shared types)
export * from './staff-outreach-api'
export * from './events-api'
export * from './community-api'
export * from './program-planning-api'
export * from './panic-alert-api'
export * from './attendance-api'
export * from './community-resources-api'
export * from './pii-access-log-api'

// ==================== Conflict Resolutions ====================
// createTemplate, listTemplates: law-enforcement-api vs program-planning-api → prefer program-planning-api
export { createTemplate, listTemplates } from './program-planning-api'

export * from './parent-onboarding-childcare-api'
