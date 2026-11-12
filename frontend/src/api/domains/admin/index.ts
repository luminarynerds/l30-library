/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// ==================== Admin Domain APIs ====================
// APIs for administrative operations including board management, analytics, strategic planning, acquisition, compliance, and volunteer management

export * from './admin-analytics-api'
export * from './board-api'
export * from './board-committees-api'
export * from './board-motions-api'
export * from './board-public-comments-api'
export * from './strategic-api'
export * from './annual-reports-api'
export * from './financial-reports-api'
export * from './audit-log-api'
export * from './board-audit-log-api'
export * from './acquisition-api'
export * from './acquisition-po-api'
export * from './material-cost-api'
export * from './edi-api'
export * from './state-compliance-api'
export * from './volunteer-api'
export * from './databases-api'
export * from './consortium-api'
export * from './z3950-admin-api'
export * from './unified-compliance-api'
export * from './community-resources-api'

// ==================== Conflict Resolutions ====================
// Resolve duplicate exports between admin API files

// deleteComment, updateComment: board-public-comments-api vs strategic-api
export { deleteComment, updateComment } from './board-public-comments-api'

// Fund: financial-reports-api vs acquisition-api
export { type Fund } from './financial-reports-api'

// getPurchaseOrder, getPurchaseOrders: acquisition-api vs acquisition-po-api
export { getPurchaseOrder, getPurchaseOrders } from './acquisition-api'

// UpcomingDeadline: strategic-api vs state-compliance-api
export { type UpcomingDeadline } from './strategic-api'

// createVendor, updateVendor: acquisition-api vs databases-api
export { createVendor, updateVendor } from './acquisition-api'

// getDashboard: databases-api vs unified-compliance-api
export { getDashboard } from './databases-api'

// PaginatedResponse: edi-api vs unified-compliance-api
export { type PaginatedResponse } from './edi-api'
