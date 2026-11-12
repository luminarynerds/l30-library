/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// Main API barrel exports.
export * from './types'
export { api } from './api'

export * from './domains/patron'
export * from './domains/circulation'
export * from './domains/catalog'
export * from './domains/staff'
export * from './domains/makerspace'
export * from './domains/admin'
export * from './domains/content'
export * from './domains/services'
export * from './domains/auth'
export * from './domains/analytics'
export * from './domains/learning'
export * from './domains/reference'
export * from './domains/operations'
export * from './domains/notifications'

// Disambiguate: both makerspace and learning export `WaitlistStatus`.
// Prefer the makerspace string-union; learning's interface is available via direct import.
export type { WaitlistStatus } from './domains/makerspace/makerspace-api'


// Core/shared APIs.
export * from './auth-api'
export * from './organization-features-api'
export * from './announcements-api'
export * from './notifications-api'
export * from './events-api'
export * from './community-api'
export * from './training-api'
export * from './panic-alert-api'
export * from './library-agents-api'
export * from './streaming-api'
export * from './tech-support-api'
export * from './branch-api'
export * from './legal-api'
export * from './book-challenges-api'
export * from './sms-api'
export * from './analytics-api'
export * from './inventory-api'
export * from './collections-api'
export * from './lifecycle-api'
export * from './learning-api'
export * from './learning-paths-api'
export * from './certificates-api'
export * from './courses-api'
export * from './databases-api'
export * from './consortium-api'
export * from './contentFlagService'
export * from './guide-feedback-api'
export * from './link-health-api'
export * from './marketing-api'
export * from './monitoring-api'
export * from "./staff-onboarding-api"
export * from './privacy-api'
export * from './releases-api'
export * from './reports-api'
export * from './knowledge-base-api'

// Prefer analytics-api versions for conflicts with reports-api.
export {
  type PopularItem,
  type OverdueItem,
  type HoldStats,
  type InventorySummary,
  type OverdueItemsResponse,
  getPopularItems,
  getCirculationTrends,
  getOverdueItems,
  getHoldStats,
  getInventorySummary,
} from './analytics-api'

// getVendors exists in both databases-api and domains/admin.
export { getVendors } from './domains/admin/acquisition-api'

// Additional conflict resolutions.
export { type PaginatedResponse } from './domains/catalog/linked-data-api'
export { type MessageResponse } from './types'

export { type Fine } from './staff-api'

export {
  type ReservationListResponse,
  approveReservation,
  cancelReservation,
  checkInReservation,
} from './domains/staff/staff-rooms-api'

export { type ClaimDisputeStatus, fileClaim } from './domains/patron/patron-claims-returned-api'

export { updateTag } from './domains/patron/patron-segmentation-api'

export {
  type PlatformBreakdown,
  type ShareTrendDataPoint,
  type SharedResource,
  type SharingDashboardResponse,
  type StatsMetadata,
  type TopSharer,
  type TrendData,
  getSharingDashboard,
} from './sharing-analytics-api'

export { type SparqlBinding, type SparqlResults } from './sparql-api'

// Explicit overrides for wildcard export conflicts.
export { type QuizQuestion, type QuizResult } from './learning-api'

export { type ProxyConfiguration, type ProxyType, createProxyConfig, updateProxyConfig, deleteProxyConfig } from './databases-api'

export { type LibrarySystem } from './branch-api'
export { type EventReviewEditRequest } from './events-api'
export { recordGuideHelpful } from './legal-api'

export { type AlertSeverity, ALERT_SEVERITIES, getSeverityColor } from './link-health-api'

export { type FinancialSummary } from './consortium-api'

export { followAuthor, unfollowAuthor, getFollowedAuthors } from './domains/operations'

export { type ModerationQueueItem } from './domains/operations'

export { type ContentRating } from './domains/catalog'
export { createCatalogItem } from './domains/catalog'
export { getPersonalizedRecommendations } from './domains/catalog'
export { type UnifiedSearchResponse } from './domains/catalog'
export { getSourceLabel } from './domains/catalog'

export { endSession } from './domains/circulation'
export { formatCurrency } from './domains/circulation'

export { getCostSummary } from './domains/staff'
export { getFinancialSummary } from './domains/staff'

export { deleteReview } from './domains/content'
export { type NotificationType } from './domains/admin'
export { createTemplate, listTemplates } from './domains/admin'
export { createVendor, updateVendor } from './domains/admin'

export { joinWaitlist } from './domains/makerspace'
export { createResource, updateResource } from './domains/makerspace'
export { getStatusColor } from './domains/makerspace'
export { acknowledgeAlert, resolveAlert } from './domains/makerspace'

export { type AuditLogResponse, REQUEST_TYPE_LABELS } from './domains/services'
export { createPartner } from './domains/services'

export { getMyApplications } from './domains/patron'

// Additional domain overrides
export { downloadReport } from './domains/admin'

// ==================== Cross-domain conflict resolutions ====================

// unifiedSearch: catalog vs staff → prefer catalog (primary search)
export { unifiedSearch } from './domains/catalog'

// TransactionListResponse: circulation vs staff → prefer circulation
export { type TransactionListResponse } from './domains/circulation'

// BulkActionResponse: patron vs staff → prefer patron
export { type BulkActionResponse } from './domains/patron'

// getSkillLevels: staff vs makerspace → prefer staff
export { getSkillLevels } from './domains/staff'

// ISBNLookupResult: catalog vs admin → prefer catalog
export { type ISBNLookupResult } from './domains/catalog'

// Z3950Source: catalog vs admin → prefer catalog (already resolved in catalog barrel)
export { type Z3950Source } from './domains/catalog'

// createIncident: makerspace vs admin → prefer makerspace
export { createIncident } from './domains/makerspace'

// DiscussionReply, DiscussionThread: admin vs content → prefer content (book clubs)
export { type DiscussionReply, type DiscussionThread } from './domains/content'

// PaginationInfo: circulation vs content → prefer circulation
export { type PaginationInfo } from './domains/circulation'

// ResourceType: makerspace vs content → prefer makerspace
export { type ResourceType } from './domains/makerspace'

// createReply: staff vs content → prefer staff
export { createReply } from './domains/staff'

// createPlan, getPlan, updatePlan: admin vs services → prefer admin (strategic)
export { createPlan, getPlan, updatePlan } from './domains/admin'

// deleteTemplate, getTemplate, updateTemplate: admin vs services → prefer admin (strategic)
export { deleteTemplate, getTemplate, updateTemplate } from './domains/admin'

// createEvaluation: staff vs services → prefer staff
export { createEvaluation } from './domains/staff'

// checkDuplicate: patron vs auth → prefer auth
export { checkDuplicate } from './domains/auth'

// TimelineEvent: admin vs reference → prefer admin (strategic)
export { type TimelineEvent } from './domains/admin'

// CourseEnrollment: learning vs reference → prefer learning
export { type CourseEnrollment } from './domains/learning'

// submitQuiz: makerspace vs learning → prefer learning
export { submitQuiz } from './domains/learning'

// FeedbackType: staff vs reference → prefer reference
export { type FeedbackType } from './domains/reference'

// Author: staff vs operations → prefer staff
export { type Author } from './domains/staff'

// KnowledgeBaseEntry: reference vs library-agents-api → prefer reference
export { type KnowledgeBaseEntry } from './domains/reference'

// SubscriptionStatus: admin vs marketing-api → prefer admin
export { type SubscriptionStatus } from './domains/admin'

export * from './sparql-api'
export * from './support-api'
export * from './usage-statistics-api'
export * from './walk-in-rooms-api'
