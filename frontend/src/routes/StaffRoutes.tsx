/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Suspense } from 'react'
import { Routes, Route, Navigate, useParams } from 'react-router-dom'
import RequireAuth from '../components/RequireAuth'
import RequireFeature from '../components/RequireFeature'
import { lazyWithRetry } from '../utils/lazyWithRetry'

const NotFoundPage = lazyWithRetry(() => import('../pages/NotFoundPage'), 'staff-not-found-page')
const StaffDashboardPage = lazyWithRetry(() => import('../pages/StaffDashboardPage'), 'staff-staff-dashboard-page')
const StaffCirculationPage = lazyWithRetry(() => import('../pages/staff/circulation/StaffCirculationPage'), 'staff-staff-circulation-page')
const PatronDisplayPage = lazyWithRetry(() => import('../pages/staff/circulation/PatronDisplayPage'), 'staff-patron-display-page')
const StreamlinedCheckoutPage = lazyWithRetry(() => import('../pages/StreamlinedCheckoutPage'), 'staff-streamlined-checkout-page')
const StaffHoldShelfPage = lazyWithRetry(() => import('../pages/staff/hold-shelf/StaffHoldShelfPage'), 'staff-staff-hold-shelf-page')
const StaffLexileBulkImportPage = lazyWithRetry(() => import('../pages/staff/StaffLexileBulkImportPage'), 'staff-staff-lexile-bulk-import-page')
const StaffCatalogingPage = lazyWithRetry(() => import('../pages/StaffCatalogingPage'), 'staff-staff-cataloging-page')
const StaffCatalogingDetailPage = lazyWithRetry(() => import('../pages/StaffCatalogingDetailPage'), 'staff-cataloging-detail-page')
const StaffCopyLifecyclePage = lazyWithRetry(() => import('../pages/StaffCopyLifecyclePage'), 'staff-copy-lifecycle-page')
const StaffWeedingCandidatePage = lazyWithRetry(() => import('../pages/StaffWeedingCandidatePage'), 'staff-weeding-candidate-page')
const AdminRationaleBackfillPage = lazyWithRetry(() => import('../pages/AdminRationaleBackfillPage'), 'staff-admin-rationale-backfill-page')
const AdminCollectionMemoryPage = lazyWithRetry(() => import('../pages/AdminCollectionMemoryPage'), 'staff-admin-collection-memory-page')
const StaffMangaCatalogingPage = lazyWithRetry(() => import('../pages/StaffMangaCatalogingPage'), 'staff-staff-manga-cataloging-page')
const StaffComicCatalogingPage = lazyWithRetry(() => import('../pages/StaffComicCatalogingPage'), 'staff-staff-comic-cataloging-page')
const StaffAcquisitionPage = lazyWithRetry(() => import('../pages/StaffAcquisitionPage'), 'staff-staff-acquisition-page')
const StaffInventoryPage = lazyWithRetry(() => import('../pages/StaffInventoryPage'), 'staff-staff-inventory-page')
const CirculationReportsPage = lazyWithRetry(() => import('../pages/CirculationReportsPage'), 'staff-circulation-reports-page')
const StaffAnalyticsPage = lazyWithRetry(() => import('../pages/StaffAnalyticsPage'), 'staff-staff-analytics-page')
const ReadingLogsReviewPage = lazyWithRetry(() => import('../pages/ReadingLogsReview'), 'staff-reading-logs-review-page')
const StaffPatronsPage = lazyWithRetry(() => import('../pages/StaffPatronsPage'), 'staff-patrons')
const PendingFineWaiversPage = lazyWithRetry(() => import('../pages/staff/fines/PendingFineWaiversPage'), 'pending-fine-waivers')
const StaffCardApplicationsPage = lazyWithRetry(() => import('../pages/StaffCardApplicationsPage'), 'staff-staff-card-applications-page')
const StaffTeacherApplicationsPage = lazyWithRetry(() => import('../pages/StaffTeacherApplicationsPage'), 'staff-staff-teacher-applications-page')
const StaffTrainingDashboard = lazyWithRetry(() => import('../pages/StaffTrainingDashboard'), 'staff-staff-training-dashboard')
const StaffStrategicPage = lazyWithRetry(() => import('../pages/StaffStrategicPage'), 'staff-staff-strategic-page')
const StaffRFIDPage = lazyWithRetry(() => import('../pages/StaffRFIDPage'), 'staff-staff-rfid-page')
const RFIDSimulatorPage = lazyWithRetry(() => import('../pages/RFIDSimulatorPage'), 'staff-rfid-simulator-page')
const StaffFeatureFlagsPage = lazyWithRetry(() => import('../components/staff/StaffFeatureFlagsPage'), 'staff-staff-feature-flags-page')
const StaffLibraryVisitsPage = lazyWithRetry(() => import('../components/staff/StaffLibraryVisitsPage'), 'staff-staff-library-visits-page')
const StaffStreamingPage = lazyWithRetry(() => import('../pages/StaffStreamingPage'), 'staff-staff-streaming-page')
const StreamingReportsPage = lazyWithRetry(() => import('../pages/StreamingReportsPage'), 'staff-streaming-reports-page')
const StaffPanicAlertsPage = lazyWithRetry(() => import('../pages/StaffPanicAlertsPage'), 'staff-staff-panic-alerts-page')
const StaffMedicalEmergencyPage = lazyWithRetry(() => import('../pages/StaffMedicalEmergencyPage'), 'staff-staff-medical-emergency-page')
const StaffKnowledgeBase = lazyWithRetry(() => import('../pages/StaffKnowledgeBase'), 'staff-staff-knowledge-base')
const StaffMakerspacePage = lazyWithRetry(() => import('../pages/StaffMakerspacePage'), 'staff-staff-makerspace-page')
const StaffLostDamagedPage = lazyWithRetry(() => import('../pages/StaffLostDamagedPage'), 'staff-staff-lost-damaged-page')
const StaffPicksPage = lazyWithRetry(() => import('../pages/StaffPicksPage'), 'staff-staff-picks-page')
const AdminReadingListsPage = lazyWithRetry(() => import('../pages/AdminReadingListsPage'), 'staff-admin-reading-lists-page')
const AdminHomePage = lazyWithRetry(() => import('../pages/AdminHomePage'), 'staff-admin-home-page')
const StaffRoomsPage = lazyWithRetry(() => import('../pages/staff/rooms/StaffRoomsPage'), 'staff-staff-rooms-page')
const StaffBranchClosuresPage = lazyWithRetry(() => import('../pages/StaffBranchClosuresPage'), 'staff-branch-closures-page')
const StaffPatronSegmentationPage = lazyWithRetry(() => import('../pages/StaffPatronSegmentationPage'), 'staff-staff-patron-segmentation-page')
const CohortAnalysisPage = lazyWithRetry(() => import("../pages/staff/CohortAnalysisPage"), 'staff-cohort-analysis-page')
const StaffAuditLogPage = lazyWithRetry(() => import('../pages/StaffAuditLogPage'), 'staff-staff-audit-log-page')
const StaffSIP2Page = lazyWithRetry(() => import('../pages/staff/sip2/StaffSIP2Page'), 'staff-staff-sip2-page')
const StaffContentFlagsPage = lazyWithRetry(() => import('../pages/StaffContentFlagsPage'), 'staff-staff-content-flags-page')
const StaffReviewResponsesPage = lazyWithRetry(() => import('../pages/StaffReviewResponsesPage'), 'staff-staff-review-responses-page')
const StaffEventReviewsPage = lazyWithRetry(() => import('../pages/StaffEventReviewsPage'), 'staff-staff-event-reviews-page')
const CashDrawerPage = lazyWithRetry(() => import("../pages/CashDrawerPage"), 'staff-cash-drawer-page')
const BookDropManagementPage = lazyWithRetry(() => import('../pages/BookDropManagementPage'), 'staff-book-drop-management-page')
const FastBookDropProcessPage = lazyWithRetry(() => import('../pages/FastBookDropProcessPage'), 'staff-fast-book-drop-process-page')
const LostDamagedReportsPage = lazyWithRetry(() => import('../pages/LostDamagedReportsPage'), 'staff-lost-damaged-reports-page')
const RoomReservationReportsPage = lazyWithRetry(() => import('../pages/RoomReservationReportsPage'), 'staff-room-reservation-reports-page')
const MarketingCampaignsPage = lazyWithRetry(() => import('../pages/MarketingCampaignsPage'), 'staff-marketing-campaigns-page')
const MarketingHubPage = lazyWithRetry(() => import('../pages/MarketingHubPage'), 'staff-marketing-hub-page')
const StaffEquipmentPage = lazyWithRetry(() => import('../pages/StaffEquipmentPage'), 'staff-staff-equipment-page')
const StaffLifecycleManagementPage = lazyWithRetry(() => import('../pages/StaffLifecycleManagementPage'), 'staff-staff-lifecycle-management-page')
const StaffOutreachPage = lazyWithRetry(() => import('../pages/StaffOutreachPage'), 'staff-staff-outreach-page')
const UsageStatisticsPage = lazyWithRetry(() => import('../pages/UsageStatisticsPage'), 'staff-usage-statistics-page')
const InventoryManagementPage = lazyWithRetry(() => import('../pages/InventoryManagementPage'), 'staff-inventory-management-page')
const AcquisitionFundsPage = lazyWithRetry(() => import('../pages/AcquisitionFundsPage'), 'staff-acquisition-funds-page')
const AcquisitionVendorsPage = lazyWithRetry(() => import('../pages/AcquisitionVendorsPage'), 'staff-acquisition-vendors-page')
const SelectionListPage = lazyWithRetry(() => import('../pages/SelectionListPage'), 'staff-selection-list-page')
const TrainingCohortsPage = lazyWithRetry(() => import('../pages/TrainingCohortsPage'), 'staff-training-cohorts-page')
const HomeDeliveryManagementPage = lazyWithRetry(() => import('../pages/HomeDeliveryManagementPage'), 'staff-home-delivery-management-page')
const HomeDeliveryDeliveryPage = lazyWithRetry(() => import('../pages/HomeDeliveryPage'), 'staff-home-delivery-delivery-page')
const HomeDeliveryVolunteersPage = lazyWithRetry(() => import('../pages/HomeDeliveryVolunteersPage'), 'staff-home-delivery-volunteers-page')
const HomeDeliveryReportsPage = lazyWithRetry(() => import('../pages/HomeDeliveryReportsPage'), 'staff-home-delivery-reports-page')
const StaffLinkedDataPage = lazyWithRetry(() => import('../pages/StaffLinkedDataPage'), 'staff-staff-linked-data-page')
const StaffSPARQLPage = lazyWithRetry(() => import('../pages/StaffSPARQLPage'), 'staff-staff-sparql-page')
const StaffLocalAuthoritiesPage = lazyWithRetry(() => import('../pages/StaffLocalAuthoritiesPage'), 'staff-staff-local-authorities-page')
const StaffAuditReversalPage = lazyWithRetry(() => import('../pages/StaffAuditReversalPage'), 'staff-staff-audit-reversal-page')
const ReleasesManagementPage = lazyWithRetry(() => import('../pages/ReleasesManagementPage'), 'staff-releases-management-page')
const ShiftSwapBoard = lazyWithRetry(() => import('../pages/ShiftSwapBoard'), 'staff-shift-swap-board')
const FairSchedulingDashboardPage = lazyWithRetry(() => import("../pages/FairSchedulingDashboardPage"), 'staff-fair-scheduling-dashboard-page')
const StaffPtoPage = lazyWithRetry(() => import('../pages/StaffPtoPage'), 'staff-pto-page')
const FairSchedulingGeneratePage = lazyWithRetry(() => import("../pages/FairSchedulingGeneratePage"), 'staff-fair-scheduling-generate-page')
const FairSchedulingExplanationsPage = lazyWithRetry(() => import("../pages/FairSchedulingExplanationsPage"), 'staff-fair-scheduling-explanations-page')
const FairSchedulingCallOutsPage = lazyWithRetry(() => import("../pages/FairSchedulingCallOutsPage"), 'staff-fair-scheduling-call-outs-page')
const FairSchedulingFatiguePage = lazyWithRetry(() => import("../pages/FairSchedulingFatiguePage"), 'staff-fair-scheduling-fatigue-page')
const FairSchedulingPayrollPage = lazyWithRetry(() => import("../pages/FairSchedulingPayrollPage"), 'staff-fair-scheduling-payroll-page')
const FairSchedulingProfilesPage = lazyWithRetry(() => import("../pages/FairSchedulingProfilesPage"), 'staff-fair-scheduling-profiles-page')
const FairSchedulingPreferencesPage = lazyWithRetry(() => import("../pages/FairSchedulingPreferencesPage"), 'staff-fair-scheduling-preferences-page')
const StaffWorkflowsPage = lazyWithRetry(() => import('../pages/StaffWorkflowsPage'), 'staff-staff-workflows-page')
const EndOfDayPage = lazyWithRetry(() => import('../pages/EndOfDayPage'), 'staff-end-of-day')
const StaffAudiobookReviewPage = lazyWithRetry(() => import('../pages/StaffAudiobookReviewPage'), 'staff-staff-audiobook-review-page')
const StaffBookChallengesPage = lazyWithRetry(() => import('../pages/StaffBookChallengesPage'), 'staff-staff-book-challenges-page')
const EndOfShiftPage = lazyWithRetry(() => import('../pages/staff/EndOfShiftPage'), 'staff-end-of-shift-page')
const StaffFoundItemsPage = lazyWithRetry(() => import("../pages/staff/StaffFoundItemsPage"), 'staff-staff-found-items-page')
const StaffPositivityHubPage = lazyWithRetry(() => import('../pages/StaffPositivityHubPage'), 'staff-staff-positivity-hub-page')
const AttendanceTrackingPage = lazyWithRetry(() => import('../pages/AttendanceTrackingPage'), 'staff-attendance-tracking-page')
const InterlibraryLoanPage = lazyWithRetry(() => import('../pages/InterlibraryLoanPage'), 'staff-interlibrary-loan-page')
const ProgramPlanningPage = lazyWithRetry(() => import('../pages/staff/program-planning/ProgramPlanningPage'), 'staff-program-planning-page')
const StaffPurchaseRequestsPage = lazyWithRetry(() => import('../pages/StaffPurchaseRequestsPage'), 'staff-staff-purchase-requests-page')
const StaffDonationsPage = lazyWithRetry(() => import('../pages/StaffDonationsPage'), 'staff-staff-donations-page')
const SelectorDashboardPage = lazyWithRetry(() => import('../pages/SelectorDashboardPage'), 'staff-selector-dashboard-page')
const StaffWeedingPage = lazyWithRetry(() => import('../pages/StaffWeedingPage'), 'staff-staff-weeding-page')
const RepairQueuePage = lazyWithRetry(() => import('../pages/staff/RepairQueuePage'), 'staff-repair-queue-page')
const StaffProcessingQueuePage = lazyWithRetry(() => import("../pages/StaffProcessingQueuePage"), 'staff-staff-processing-queue-page')
const StaffFineManagementPage = lazyWithRetry(() => import("../pages/StaffFineManagementPage"), 'staff-staff-fine-management-page')
const MobileInventoryScanPage = lazyWithRetry(() => import('../pages/MobileInventoryScanPage'), 'staff-mobile-inventory-scan-page')
const MobileAuditPage = lazyWithRetry(() => import("../pages/staff/MobileAuditPage"), 'staff-mobile-audit-page')
const StaffShelfReadingPage = lazyWithRetry(() => import('../pages/staff/StaffShelfReadingPage'), 'staff-staff-shelf-reading-page')
const StaffArchivalCollectionsPage = lazyWithRetry(() => import('../pages/staff/StaffArchivalCollectionsPage'), 'staff-staff-archival-collections-page')
const StaffMarcMacrosPage = lazyWithRetry(() => import('../pages/staff/StaffMarcMacrosPage'), 'staff-staff-marc-macros-page')
const ExportMarcPage = lazyWithRetry(() => import('../pages/staff/ExportMarcPage'), 'staff-export-marc-page')
const StaffMessageBoardPage = lazyWithRetry(() => import('../pages/StaffMessageBoardPage'), 'staff-staff-message-board-page')
const StaffPrintManagementPage = lazyWithRetry(() => import('../pages/StaffPrintManagementPage'), 'staff-staff-print-management-page')
const StaffReferenceChatPage = lazyWithRetry(() => import('../pages/StaffReferenceChatPage'), 'staff-staff-reference-chat-page')
const UnifiedReportsPage = lazyWithRetry(() => import('../pages/UnifiedReportsPage'), 'staff-unified-reports-page')
const CustomReportBuilderPage = lazyWithRetry(() => import('../pages/staff/CustomReportBuilderPage'), 'staff-custom-report-builder-page')
const ReportAuditLogPage = lazyWithRetry(() => import('../pages/staff/ReportAuditLogPage'), 'staff-report-audit-log-page')
const StaffHomepageManagerPage = lazyWithRetry(() => import('../pages/StaffHomepageManagerPage'), 'staff-staff-homepage-manager-page')
const StaffAmasPage = lazyWithRetry(() => import('../pages/StaffAmasPage'), 'staff-staff-amas-page')
const StaffBookClubsPage = lazyWithRetry(() => import('../pages/StaffBookClubsPage'), 'staff-staff-book-clubs-page')
const StaffStorytimePage = lazyWithRetry(() => import('../pages/StaffStorytimePage'), 'staff-staff-storytime-page')
const StaffFocusTimePage = lazyWithRetry(() => import('../pages/StaffFocusTimePage'), 'staff-staff-focus-time-page')
const StaffComputersPage = lazyWithRetry(() => import("../pages/StaffComputersPage"), 'staff-staff-computers-page')
const StaffVolunteerManagementPage = lazyWithRetry(() => import("../pages/StaffVolunteerManagementPage"), 'staff-staff-volunteer-management-page')
const StaffTeenVolunteersPage = lazyWithRetry(() => import("../pages/StaffTeenVolunteersPage"), 'staff-staff-teen-volunteers-page')
const StaffOnboardingPage = lazyWithRetry(() => import("../pages/StaffOnboardingPage"), 'staff-staff-onboarding-page')
const SerialsDashboardPage = lazyWithRetry(() => import('../pages/SerialsDashboardPage'), 'staff-serials-dashboard-page')
const SerialTitlesPage = lazyWithRetry(() => import('../pages/SerialTitlesPage'), 'staff-serial-titles-page')
const SerialIssuesPage = lazyWithRetry(() => import('../pages/SerialIssuesPage'), 'staff-serial-issues-page')

const SupportTicketsPage = lazyWithRetry(() => import("../pages/SupportTicketsPage"), 'staff-support-tickets-page')
const StaffSupportTriagePage = lazyWithRetry(() => import("../pages/staff/StaffSupportTriagePage"), 'staff-staff-support-triage-page')
// ─── Admin page imports (moved from AdminRoutes) ───
const AdminDashboardPage = lazyWithRetry(() => import('../pages/AdminDashboardPage'), 'staff-admin-dashboard-page')
const AdminDataExportPage = lazyWithRetry(() => import('../pages/AdminDataExportPage'), 'staff-admin-data-export-page')
const AdminAISettingsPage = lazyWithRetry(() => import('../pages/AdminAISettingsPage'), 'staff-admin-ai-settings-page')
const AdminIntegrationsPage = lazyWithRetry(() => import('../pages/AdminIntegrationsPage'), 'staff-admin-integrations-page')
const AdminComplianceDashboardPage = lazyWithRetry(() => import("../pages/AdminComplianceDashboardPage"), 'staff-admin-compliance-dashboard-page')
const AdminAboutUsPage = lazyWithRetry(() => import('../pages/AdminAboutUsPage'), 'staff-admin-about-us-page')
const AdminPersonalizationConfigPage = lazyWithRetry(() => import('../pages/AdminPersonalizationConfigPage'), 'staff-admin-personalization-config-page')
const AdminUsersPage = lazyWithRetry(() => import('../pages/AdminUsersPage'), 'staff-admin-users-page')
const EventManagementPage = lazyWithRetry(() => import('../pages/EventManagementPage'), 'staff-event-management-page')
const StaffProgramPartnersPage = lazyWithRetry(() => import('../pages/StaffProgramPartnersPage'), 'staff-staff-program-partners-page')
const EventRosterPage = lazyWithRetry(() => import('../pages/EventRosterPage'), 'staff-event-roster-page')
const AdminLearningPathsPage = lazyWithRetry(() => import('../pages/AdminLearningPathsPage'), 'staff-admin-learning-paths-page')
const AdminLearningPathFormPage = lazyWithRetry(() => import('../pages/AdminLearningPathFormPage'), 'staff-admin-learning-path-form-page')
const AdminSessionsPage = lazyWithRetry(() => import('../pages/AdminSessionsPage'), 'staff-admin-sessions-page')
const AdminCoursesPage = lazyWithRetry(() => import('../pages/AdminCoursesPage'), 'staff-admin-courses-page')
const AdminCourseFormPage = lazyWithRetry(() => import('../pages/AdminCourseFormPage'), 'staff-admin-course-form-page')
const AlternateFormatsRequestPage = lazyWithRetry(() => import('../pages/AlternateFormatsRequestPage'), 'staff-alternate-formats-request-page')
const AdminCourseTemplatesPage = lazyWithRetry(() => import('../pages/AdminCourseTemplatesPage'), 'staff-admin-course-templates-page')
const AdminCourseBulkImportPage = lazyWithRetry(() => import('../pages/AdminCourseBulkImportPage'), 'staff-admin-course-bulk-import-page')
const AdminCourseFeedbackPage = lazyWithRetry(() => import('../pages/AdminCourseFeedbackPage'), 'staff-admin-course-feedback-page')
const StrategicAdminPage = lazyWithRetry(() => import('../pages/StrategicAdminPage'), 'staff-strategic-admin-page')
const BoardManagementPage = lazyWithRetry(() => import('../pages/BoardManagementPage'), 'staff-board-management-page')
const BoardPublicCommentsAdminPage = lazyWithRetry(() => import('../pages/board/BoardPublicCommentsAdminPage'), 'staff-board-public-comments-admin-page')
const BoardAuditLogPage = lazyWithRetry(() => import('../pages/board/BoardAuditLogPage'), 'staff-board-audit-log-page')
const BoardDemoPage = lazyWithRetry(() => import("../pages/BoardDemoPage"), 'staff-board-demo-page')
const StaffManagementPage = lazyWithRetry(() => import('../pages/StaffManagementPage'), 'staff-staff-management-page')
const StaffTimesheetEditorPage = lazyWithRetry(() => import('../pages/staff/StaffTimesheetEditorPage'), 'staff-staff-timesheet-editor-page')
const StaffPayRatesPage = lazyWithRetry(() => import('../pages/staff/StaffPayRatesPage'), 'staff-staff-pay-rates-page')
const FinancialReportsPage = lazyWithRetry(() => import('../pages/FinancialReportsPage'), 'staff-financial-reports-page')
const AnnualReportsPage = lazyWithRetry(() => import('../pages/AnnualReportsPage'), 'staff-annual-reports-page')
const AcquisitionManagementPage = lazyWithRetry(() => import('../pages/AcquisitionManagementPage'), 'staff-acquisition-management-page')
const AdminDatabasesPage = lazyWithRetry(() => import('../pages/AdminDatabasesPage'), 'staff-admin-databases-page')
const AdminReadingProgramsPage = lazyWithRetry(() => import('../pages/AdminReadingProgramsPage'), 'staff-admin-reading-programs-page')
const SchoolImpactReportingPage = lazyWithRetry(() => import('../pages/SchoolImpactReportingPage'), 'staff-school-impact-reporting-page')
const CommunityOutcomesDashboardPage = lazyWithRetry(() => import('../pages/CommunityOutcomesDashboardPage'), 'staff-community-outcomes-dashboard-page')
const PartnershipTierManagementPage = lazyWithRetry(() => import('../pages/PartnershipTierManagementPage'), 'staff-partnership-tier-management-page')
const ReadingAmbassadorPage = lazyWithRetry(() => import('../pages/ReadingAmbassadorPage'), 'staff-reading-ambassador-page')
const ReadingBundleDistributionPage = lazyWithRetry(() => import('../pages/ReadingBundleDistributionPage'), 'staff-reading-bundle-distribution-page')
const AnalyticsDashboardPage = lazyWithRetry(() => import('../pages/AnalyticsDashboardPage'), 'staff-analytics-dashboard-page')
const AdminSharingAnalyticsPage = lazyWithRetry(() => import('../pages/AdminSharingAnalyticsPage'), 'staff-admin-sharing-analytics-page')
const WebsiteAnalyticsPage = lazyWithRetry(() => import('../pages/WebsiteAnalyticsPage'), 'staff-website-analytics-page')
const QrAnalyticsPage = lazyWithRetry(() => import('../pages/QrAnalyticsPage'), 'staff-qr-analytics-page')
const AdminLegalPage = lazyWithRetry(() => import('../pages/AdminLegalPage'), 'staff-admin-legal-page')
const AdminMetaTagsPage = lazyWithRetry(() => import('../pages/AdminMetaTagsPage'), 'staff-admin-meta-tags-page')
const AdminMoodCategoriesPage = lazyWithRetry(() => import('../pages/AdminMoodCategoriesPage'), 'staff-admin-mood-categories-page')
const AdminPatronCategoriesPage = lazyWithRetry(() => import('../pages/AdminPatronCategoriesPage'), 'staff-admin-patron-categories-page')
const AdminContentTranslationsPage = lazyWithRetry(() => import('../pages/staff/AdminContentTranslationsPage'), 'staff-admin-content-translations-page')
const AdminSocialSharingPage = lazyWithRetry(() => import('../pages/AdminSocialSharingPage'), 'staff-admin-social-sharing-page')
const AdminEDISettingsPage = lazyWithRetry(() => import('../pages/AdminEDISettingsPage'), 'staff-admin-edi-settings-page')
const AdminLinkHealthPage = lazyWithRetry(() => import('../pages/AdminLinkHealthPage'), 'staff-admin-link-health-page')
const ConsortiumManagementPage = lazyWithRetry(() => import('../pages/ConsortiumManagementPage'), 'staff-consortium-management-page')
const TreasurerDashboardPage = lazyWithRetry(() => import('../pages/TreasurerDashboardPage'), 'staff-treasurer-dashboard-page')
const BoardTreasurerDashboardPage = lazyWithRetry(() => import('../pages/BoardTreasurerDashboardPage'), 'staff-board-treasurer-dashboard-page')
const StrategicAnalyticsPage = lazyWithRetry(() => import('../pages/StrategicAnalyticsPage'), 'staff-strategic-analytics-page')
const AdminAudiobooksPage = lazyWithRetry(() => import('../pages/AdminAudiobooksPage'), 'staff-admin-audiobooks-page')
const JourneyAnalyticsDashboard = lazyWithRetry(() => import('../pages/JourneyAnalyticsDashboard'), 'staff-journey-analytics-dashboard')
const PredictiveAnalyticsPage = lazyWithRetry(() => import("../pages/staff/PredictiveAnalyticsPage"), 'staff-predictive-analytics-page')
const AdminSettingsHubPage = lazyWithRetry(() => import("../pages/AdminSettingsHubPage"), 'staff-admin-settings-hub-page')
const BoardHubPage = lazyWithRetry(() => import("../pages/BoardHubPage"), 'staff-board-hub-page')
const LibraryHubPage = lazyWithRetry(() => import("../pages/LibraryHubPage"), 'staff-library-hub-page')
const ReportHubPage = lazyWithRetry(() => import("../pages/staff/ReportHubPage"), 'staff-report-hub-page')
const CollectionHubPage = lazyWithRetry(() => import("../pages/CollectionHubPage"), 'staff-collection-hub-page')
const CollectionAnalyticsPage = lazyWithRetry(() => import("../pages/staff/CollectionAnalyticsPage"), 'staff-collection-analytics-page')
const CollectionDashboardPage = lazyWithRetry(() => import("../pages/staff/CollectionDashboardPage"), 'staff-collection-dashboard-page')
const FrontDeskHubPage = lazyWithRetry(() => import("../pages/FrontDeskHubPage"), 'staff-front-desk-hub-page')
const AdminSIP2SettingsPage = lazyWithRetry(() => import('../pages/AdminSIP2SettingsPage'), 'staff-admin-sip2-settings-page')
const AdminHomeDeliverySettingsPage = lazyWithRetry(() => import('../pages/AdminHomeDeliverySettingsPage'), 'staff-admin-home-delivery-settings-page')
const AdminHomepageQuotesPage = lazyWithRetry(() => import("../pages/AdminHomepageQuotesPage"), 'staff-admin-homepage-quotes-page')
const AdminSearchEngineSettingsPage = lazyWithRetry(() => import('../pages/AdminSearchEngineSettingsPage'), 'staff-admin-search-engine-settings-page')
const AdminZ3950SettingsPage = lazyWithRetry(() => import("../pages/AdminZ3950SettingsPage"), 'staff-admin-z3950-settings-page')
const AdminMigrationWizardPage = lazyWithRetry(() => import('../pages/AdminMigrationWizardPage'), 'staff-admin-migration-wizard-page')
const MigrationProjectPage = lazyWithRetry(() => import('../pages/MigrationProjectPage'), 'staff-migration-project-page')
const ParentOnboardingDashboardPage = lazyWithRetry(() => import('../pages/ParentOnboardingDashboardPage'), 'staff-parent-onboarding-dashboard-page')
const ParentOnboardingSessionPage = lazyWithRetry(() => import('../pages/ParentOnboardingSessionPage'), 'staff-parent-onboarding-session-page')
const ChildcarePage = lazyWithRetry(() => import('../pages/ChildcarePage'), 'staff-childcare-page')
const ParentHomeVisitsPage = lazyWithRetry(() => import('../pages/ParentHomeVisitsPage'), 'staff-parent-home-visits-page')
const ParentHomeVisitsTodayPage = lazyWithRetry(() => import('../pages/ParentHomeVisitsTodayPage'), 'staff-parent-home-visits-today-page')
const ParentConnectionGroupsPage = lazyWithRetry(() => import('../pages/ParentConnectionGroupsPage'), 'staff-parent-connection-groups-page')
const ConnectionGroupsApprovalsPage = lazyWithRetry(() => import('../pages/ConnectionGroupsApprovalsPage'), 'staff-connection-groups-approvals-page')
const ParentResourcesPage = lazyWithRetry(() => import('../pages/ParentResourcesPage'), 'staff-parent-resources-page')
const StaffResourceFlagsPage = lazyWithRetry(() => import('../pages/StaffResourceFlagsPage'), 'staff-staff-resource-flags-page')
const StaffTransitPage = lazyWithRetry(() => import('../pages/StaffTransitPage'), 'staff-staff-transit-page')
const AdminComputersPage = lazyWithRetry(() => import('../pages/AdminComputersPage'), 'staff-admin-computers-page')
const AdminSystemDashboardPage = lazyWithRetry(() => import('../pages/AdminSystemDashboardPage'), 'staff-admin-system-dashboard-page')
const AdminOutreachDashboardPage = lazyWithRetry(() => import('../pages/AdminOutreachDashboardPage'), 'staff-admin-outreach-dashboard-page')
const AdminCirculationPolicyDashboardPage = lazyWithRetry(() => import('../pages/AdminCirculationPolicyDashboardPage'), 'staff-admin-circulation-policy-dashboard-page')
const AdminLibraryConfigDashboardPage = lazyWithRetry(() => import('../pages/AdminLibraryConfigDashboardPage'), 'staff-admin-library-config-dashboard-page')
const AdminBrandingPage = lazyWithRetry(() => import('../pages/AdminBrandingPage'), 'staff-admin-branding-page')

function LessonRouteRedirect() {
  const { courseId, lessonId } = useParams<{ courseId: string; lessonId: string }>()
  return <Navigate to={`/staff/admin/courses/${courseId}/edit?lesson=${lessonId}`} replace />
}

const Auth = ({ children }: { children: React.ReactElement }) => (
  <RequireAuth requiredRoles={["staff", "admin", "director", "legal", "bookmobile", "homebond", "board_member"]}>{children}</RequireAuth>
)

const AdminAuth = ({ children }: { children: React.ReactElement }) => (
  <RequireAuth requiredRoles={['admin', 'director']}>{children}</RequireAuth>
)

export default function StaffRoutes(): React.ReactElement {
  return (
    <Routes>
      <Route index element={<Auth><StaffDashboardPage /></Auth>} />
      <Route path="circulation" element={<Auth><StaffCirculationPage /></Auth>} />
      <Route path="circulation/display" element={<RequireFeature feature="customer_display_enabled"><Auth><PatronDisplayPage /></Auth></RequireFeature>} />
      <Route path="checkout/streamlined" element={<Auth><StreamlinedCheckoutPage /></Auth>} />
      <Route path="holds/shelf" element={<Auth><StaffHoldShelfPage /></Auth>} />
      <Route path="cataloging" element={<Auth><StaffCatalogingPage /></Auth>} />
      <Route path="cataloging/lexile-import" element={<Auth><StaffLexileBulkImportPage /></Auth>} />
      <Route path="cataloging/:id" element={<Auth><StaffCatalogingDetailPage /></Auth>} />
      <Route path="marc-macros" element={<Auth><StaffMarcMacrosPage /></Auth>} />
      <Route path="export-marc" element={<Auth><ExportMarcPage /></Auth>} />
      <Route path="manga-cataloging" element={<Auth><StaffMangaCatalogingPage /></Auth>} />
      <Route path="comic-cataloging" element={<Auth><StaffComicCatalogingPage /></Auth>} />
      <Route path="acquisition" element={<RequireFeature feature="acquisition_enabled"><Auth><StaffAcquisitionPage /></Auth></RequireFeature>} />
      <Route path="acquisitions" element={<Navigate to="/staff/acquisition" replace />} />
      <Route path="inventory" element={<Auth><StaffInventoryPage /></Auth>} />
      <Route path="shelf-reading" element={<Auth><StaffShelfReadingPage /></Auth>} />
      <Route path="archival-collections" element={<Navigate to="/staff/admin/archival-collections" replace />} />
      <Route path="reports" element={<Auth><CirculationReportsPage /></Auth>} />
      <Route path="analytics" element={<Auth><StaffAnalyticsPage /></Auth>} />
      <Route path="analytics/cohorts" element={<Auth><CohortAnalysisPage /></Auth>} />
      <Route path="qr-scans" element={<Auth><QrAnalyticsPage /></Auth>} />
      <Route path="reading-review" element={<RequireFeature feature="gamification_enabled"><Auth><ReadingLogsReviewPage /></Auth></RequireFeature>} />
      <Route path="patrons" element={<Auth><StaffPatronsPage /></Auth>} />
      <Route path="card-applications" element={<Auth><StaffCardApplicationsPage /></Auth>} />
      <Route path="teacher-applications" element={<Auth><StaffTeacherApplicationsPage /></Auth>} />
      <Route path="training" element={<RequireFeature feature="training_modules_enabled"><Auth><StaffTrainingDashboard /></Auth></RequireFeature>} />
      <Route path="strategic" element={<RequireFeature feature="board_features_enabled"><Auth><StaffStrategicPage /></Auth></RequireFeature>} />
      <Route path="strategic/analytics" element={<Navigate to="/staff/admin/strategic/analytics" replace />} />
      <Route path="rfid" element={<Auth><StaffRFIDPage /></Auth>} />
      <Route path="rfid/simulator" element={<RequireAuth requiredRoles={['admin']}><RFIDSimulatorPage /></RequireAuth>} />
      <Route path="feature-flags" element={<Auth><StaffFeatureFlagsPage /></Auth>} />
      <Route path="library-visits" element={<RequireFeature feature="learning_platform_enabled"><Auth><StaffLibraryVisitsPage /></Auth></RequireFeature>} />
      <Route path="streaming" element={<RequireFeature feature="streaming_enabled"><Auth><StaffStreamingPage /></Auth></RequireFeature>} />
      <Route path="streaming/reports" element={<RequireFeature feature="streaming_enabled"><Auth><StreamingReportsPage /></Auth></RequireFeature>} />
      <Route path="panic-alerts" element={<RequireFeature feature="emergency_services_enabled"><Auth><StaffPanicAlertsPage /></Auth></RequireFeature>} />
      <Route path="medical-emergency" element={<RequireFeature feature="emergency_services_enabled"><Auth><StaffMedicalEmergencyPage /></Auth></RequireFeature>} />
      <Route path="knowledge-base" element={<Auth><StaffKnowledgeBase /></Auth>} />
      <Route path="makerspace" element={<RequireFeature feature="makerspace_enabled"><Auth><StaffMakerspacePage /></Auth></RequireFeature>} />
      <Route path="lost-damaged" element={<Auth><StaffLostDamagedPage /></Auth>} />
      <Route path="picks" element={<Auth><StaffPicksPage /></Auth>} />
      <Route path="reading-lists" element={<Auth><AdminReadingListsPage /></Auth>} />
      <Route path="home-page" element={<Auth><AdminHomePage /></Auth>} />
      <Route path="rooms" element={<RequireFeature feature="meeting_rooms_enabled"><Auth><StaffRoomsPage /></Auth></RequireFeature>} />
      <Route path="branch-closures" element={<Auth><StaffBranchClosuresPage /></Auth>} />
      <Route path="patron-segmentation" element={<Auth><StaffPatronSegmentationPage /></Auth>} />
      <Route path="audit-logs" element={<Auth><StaffAuditLogPage /></Auth>} />
      <Route path="sip2" element={<RequireFeature feature="sip2_rfid_enabled"><Auth><StaffSIP2Page /></Auth></RequireFeature>} />
      <Route path="content-flags" element={<Auth><StaffContentFlagsPage /></Auth>} />
      <Route path="review-responses" element={<Auth><StaffReviewResponsesPage /></Auth>} />
      <Route path="event-reviews" element={<Auth><StaffEventReviewsPage /></Auth>} />
      <Route path="book-drop" element={<Auth><BookDropManagementPage /></Auth>} />
      <Route path="book-drop/fast-process" element={<Auth><FastBookDropProcessPage /></Auth>} />
      <Route path="book-drop/:tab" element={<Auth><BookDropManagementPage /></Auth>} />
      <Route path="reports/lost-damaged" element={<Auth><LostDamagedReportsPage /></Auth>} />
      <Route path="reports/rooms" element={<RequireFeature feature="meeting_rooms_enabled"><Auth><RoomReservationReportsPage /></Auth></RequireFeature>} />
      <Route path="marketing" element={<RequireFeature feature="outreach_enabled"><Auth><MarketingCampaignsPage /></Auth></RequireFeature>} />
      {/* marketing-hub now serves both AI and non-AI surfaces; the page hides the Create/History tabs when ai_tools_enabled is off. */}
      <Route path="marketing-hub" element={<RequireFeature feature="marketing_enabled"><Auth><MarketingHubPage /></Auth></RequireFeature>} />
      <Route path="equipment" element={<RequireFeature feature="tech_services_enabled"><Auth><StaffEquipmentPage /></Auth></RequireFeature>} />
      <Route path="lifecycle" element={<Auth><StaffLifecycleManagementPage /></Auth>} />
      <Route path="lifecycle/copy/:copyId" element={<Auth><StaffCopyLifecyclePage /></Auth>} />
      <Route path="outreach" element={<RequireFeature feature="outreach_enabled"><Auth><StaffOutreachPage /></Auth></RequireFeature>} />
      <Route path="usage-statistics" element={<Auth><UsageStatisticsPage /></Auth>} />
      <Route path="inventory-management" element={<Auth><InventoryManagementPage /></Auth>} />
      <Route path="funds" element={<RequireFeature feature="acquisition_enabled"><Auth><AcquisitionFundsPage /></Auth></RequireFeature>} />
      <Route path="vendors" element={<RequireFeature feature="acquisition_enabled"><Auth><AcquisitionVendorsPage /></Auth></RequireFeature>} />
      <Route path="selection-list" element={<RequireFeature feature="acquisition_enabled"><Auth><SelectionListPage /></Auth></RequireFeature>} />
      <Route path="cohorts" element={<RequireFeature feature="training_modules_enabled"><Auth><TrainingCohortsPage /></Auth></RequireFeature>} />
      <Route path="home-delivery" element={<RequireFeature feature="home_delivery_enabled"><Auth><HomeDeliveryManagementPage /></Auth></RequireFeature>} />
      <Route path="home-delivery/deliveries" element={<RequireFeature feature="home_delivery_enabled"><Auth><HomeDeliveryDeliveryPage /></Auth></RequireFeature>} />
      <Route path="home-delivery/volunteers" element={<RequireFeature feature="home_delivery_enabled"><Auth><HomeDeliveryVolunteersPage /></Auth></RequireFeature>} />
      <Route path="home-delivery/reports" element={<RequireFeature feature="home_delivery_enabled"><Auth><HomeDeliveryReportsPage /></Auth></RequireFeature>} />
      <Route path="linked-data" element={<Auth><StaffLinkedDataPage /></Auth>} />
      <Route path="sparql" element={<Auth><StaffSPARQLPage /></Auth>} />
      <Route path="local-authorities" element={<Auth><StaffLocalAuthoritiesPage /></Auth>} />
      <Route path="audit-reversal" element={<Auth><StaffAuditReversalPage /></Auth>} />
      <Route path="releases" element={<Auth><ReleasesManagementPage /></Auth>} />
      <Route path="shift-swap" element={<RequireFeature feature="staff_scheduling_enabled"><Auth><ShiftSwapBoard /></Auth></RequireFeature>} />
      <Route path="fair-scheduling" element={<RequireFeature feature="staff_scheduling_enabled"><Auth><FairSchedulingDashboardPage /></Auth></RequireFeature>} />
      <Route path="pto" element={<RequireFeature feature="staff_scheduling_enabled"><Auth><StaffPtoPage /></Auth></RequireFeature>} />
      <Route path="fair-scheduling/generate" element={<RequireFeature feature="staff_scheduling_enabled"><Auth><FairSchedulingGeneratePage /></Auth></RequireFeature>} />
      <Route path="fair-scheduling/explanations" element={<RequireFeature feature="staff_scheduling_enabled"><Auth><FairSchedulingExplanationsPage /></Auth></RequireFeature>} />
      <Route path="fair-scheduling/call-outs" element={<RequireFeature feature="staff_scheduling_enabled"><Auth><FairSchedulingCallOutsPage /></Auth></RequireFeature>} />
      <Route path="fair-scheduling/fatigue" element={<RequireFeature feature="staff_scheduling_enabled"><Auth><FairSchedulingFatiguePage /></Auth></RequireFeature>} />
      <Route path="fair-scheduling/payroll" element={<RequireFeature feature="staff_scheduling_enabled"><Auth><FairSchedulingPayrollPage /></Auth></RequireFeature>} />
      <Route path="fair-scheduling/profiles" element={<RequireFeature feature="staff_scheduling_enabled"><Auth><FairSchedulingProfilesPage /></Auth></RequireFeature>} />
      <Route path="fair-scheduling/preferences" element={<RequireFeature feature="staff_scheduling_enabled"><Auth><FairSchedulingPreferencesPage /></Auth></RequireFeature>} />
      <Route path="focus-time" element={<RequireFeature feature="staff_wellness_enabled"><Auth><StaffFocusTimePage /></Auth></RequireFeature>} />
      <Route path="computers" element={<RequireFeature feature="tech_services_enabled"><Auth><StaffComputersPage /></Auth></RequireFeature>} />
      <Route path="volunteers" element={<RequireFeature feature="volunteers_enabled"><Auth><StaffVolunteerManagementPage /></Auth></RequireFeature>} />
      <Route path="teen-volunteers" element={<RequireFeature feature="volunteers_enabled"><Auth><StaffTeenVolunteersPage /></Auth></RequireFeature>} />
      <Route path="transit" element={<Auth><StaffTransitPage /></Auth>} />
      <Route path="admin/computers" element={<Auth><AdminComputersPage /></Auth>} />
      <Route path="onboarding" element={<Auth><StaffOnboardingPage /></Auth>} />
      <Route path="workflows" element={<Auth><StaffWorkflowsPage /></Auth>} />
      <Route path="end-of-day" element={<Auth><EndOfDayPage /></Auth>} />
      <Route path="cash-drawer" element={<Auth><CashDrawerPage /></Auth>} />
      <Route path="audiobooks/review" element={<Auth><StaffAudiobookReviewPage /></Auth>} />
      <Route path="book-challenges" element={<RequireFeature feature="banned_books_tracking_enabled"><Auth><StaffBookChallengesPage /></Auth></RequireFeature>} />
      <Route path="end-of-shift" element={<Auth><EndOfShiftPage /></Auth>} />
      <Route path="found-items" element={<Auth><StaffFoundItemsPage /></Auth>} />
      <Route path="positivity" element={<RequireFeature feature="staff_wellness_enabled"><Auth><StaffPositivityHubPage /></Auth></RequireFeature>} />
      <Route path="events" element={<RequireFeature feature="events_enabled"><Auth><EventManagementPage /></Auth></RequireFeature>} />
      <Route path="program-partners" element={<RequireFeature feature="events_enabled"><Auth><StaffProgramPartnersPage /></Auth></RequireFeature>} />
      <Route path="events/:eventId/roster" element={<RequireFeature feature="events_enabled"><Auth><EventRosterPage /></Auth></RequireFeature>} />
      <Route path="attendance" element={<RequireFeature feature="events_enabled"><Auth><AttendanceTrackingPage /></Auth></RequireFeature>} />
      <Route path="interlibrary-loan" element={<RequireFeature feature="ill_enabled"><Auth><InterlibraryLoanPage /></Auth></RequireFeature>} />
      <Route path="program-planning" element={<RequireFeature feature="events_enabled"><Auth><ProgramPlanningPage /></Auth></RequireFeature>} />
      <Route path="purchase-requests" element={<RequireFeature feature="acquisition_enabled"><Auth><StaffPurchaseRequestsPage /></Auth></RequireFeature>} />
      <Route path="selectors" element={<RequireFeature feature="acquisition_enabled"><Auth><SelectorDashboardPage /></Auth></RequireFeature>} />
      <Route path="donations" element={<RequireFeature feature="acquisition_enabled"><Auth><StaffDonationsPage /></Auth></RequireFeature>} />
      <Route path="weeding" element={<Auth><StaffWeedingPage /></Auth>} />
      <Route path="weeding/:id" element={<Auth><StaffWeedingCandidatePage /></Auth>} />
      <Route path="repair-queue" element={<Auth><RepairQueuePage /></Auth>} />
      <Route path="processing" element={<RequireFeature feature="processing_queue_enabled"><Auth><StaffProcessingQueuePage /></Auth></RequireFeature>} />
      <Route path="fines" element={<RequireFeature feature="financial_reports_enabled"><Auth><StaffFineManagementPage /></Auth></RequireFeature>} />
      <Route path="fines/pending-waivers" element={<RequireFeature feature="financial_reports_enabled"><Auth><PendingFineWaiversPage /></Auth></RequireFeature>} />
      <Route path="inventory/scan" element={<Auth><MobileInventoryScanPage /></Auth>} />
      <Route path="inventory/mobile-audit" element={<Auth><MobileAuditPage /></Auth>} />
      <Route path="message-board" element={<Auth><StaffMessageBoardPage /></Auth>} />
      <Route path="message-board/:postId" element={<Auth><StaffMessageBoardPage /></Auth>} />
      <Route path="print" element={<RequireFeature feature="printing_enabled"><Auth><StaffPrintManagementPage /></Auth></RequireFeature>} />
      <Route path="reports/unified" element={<Auth><UnifiedReportsPage /></Auth>} />
      <Route path="custom-reports" element={<Auth><CustomReportBuilderPage /></Auth>} />
      <Route path="reports/audit-log" element={<Auth><ReportAuditLogPage /></Auth>} />
      <Route path="reference-chat" element={<RequireFeature feature="ai_tools_enabled"><Auth><StaffReferenceChatPage /></Auth></RequireFeature>} />
      <Route path="support/triage" element={<Auth><StaffSupportTriagePage /></Auth>} />
      <Route path="support/tickets" element={<RequireFeature feature="ai_tools_enabled"><Auth><SupportTicketsPage /></Auth></RequireFeature>} />
      <Route path="homepage" element={<Auth><StaffHomepageManagerPage /></Auth>} />

      {/* ─── Admin routes (moved from /admin/*) ─── */}
      <Route path="admin" element={<AdminAuth><AdminDashboardPage /></AdminAuth>} />
      <Route path="admin/dashboard" element={<AdminAuth><AdminDashboardPage /></AdminAuth>} />
      <Route path="admin/settings" element={<AdminAuth><AdminSettingsHubPage /></AdminAuth>} />
      <Route path="admin/data-export" element={<AdminAuth><AdminDataExportPage /></AdminAuth>} />
      <Route path="board-hub" element={<RequireFeature feature="board_features_enabled"><Auth><BoardHubPage /></Auth></RequireFeature>} />
      <Route path="library-hub" element={<Auth><LibraryHubPage /></Auth>} />
      <Route path="collection-hub" element={<RequireFeature feature="collection_management_enabled"><Auth><CollectionHubPage /></Auth></RequireFeature>} />

      <Route path="report-hub" element={<Auth><ReportHubPage /></Auth>} />

      <Route path="collection-analytics" element={<RequireFeature feature="collection_management_enabled"><Auth><CollectionAnalyticsPage /></Auth></RequireFeature>} />

      <Route path="collection-dashboard" element={<RequireFeature feature="collection_management_enabled"><Auth><CollectionDashboardPage /></Auth></RequireFeature>} />
      <Route path="front-desk-hub" element={<RequireFeature feature="front_desk_enabled"><Auth><FrontDeskHubPage /></Auth></RequireFeature>} />
      {/* marketing-nav folded into MarketingHubPage (Directory tab) 2026-05-18; redirect preserves old bookmarks. */}
      <Route path="marketing-nav" element={<Navigate to="/staff/marketing-hub" replace />} />
      <Route path="admin/system" element={<AdminAuth><AdminSystemDashboardPage /></AdminAuth>} />
      <Route path="admin/outreach" element={<Auth><AdminOutreachDashboardPage /></Auth>} />
      <Route path="admin/circulation-policy" element={<AdminAuth><AdminCirculationPolicyDashboardPage /></AdminAuth>} />
      <Route path="admin/library-config" element={<AdminAuth><AdminLibraryConfigDashboardPage /></AdminAuth>} />
      <Route path="admin/branding" element={<AdminAuth><AdminBrandingPage /></AdminAuth>} />
      <Route path="admin/ai" element={<RequireFeature feature="ai_tools_enabled"><Auth><AdminAISettingsPage /></Auth></RequireFeature>} />
      <Route path="admin/ai/agents" element={<Navigate to="/staff/admin/ai#agents" replace />} />
      <Route path="admin/ai/training" element={<Navigate to="/staff/admin/ai#training" replace />} />
      <Route path="admin/integrations" element={<Auth><AdminIntegrationsPage /></Auth>} />
      <Route path="admin/about" element={<Auth><AdminAboutUsPage /></Auth>} />
      <Route path="admin/features" element={<Navigate to="/staff/admin/library-config#features" replace />} />
      <Route path="admin/personalization" element={<AdminAuth><AdminPersonalizationConfigPage /></AdminAuth>} />
      <Route path="admin/email-notifications" element={<Navigate to="/staff/admin/outreach#email-notifications" replace />} />
      <Route path="admin/financial-config" element={<Navigate to="/staff/admin/circulation-policy#financial" replace />} />
      <Route path="admin/site-settings" element={<Navigate to="/staff/admin/library-config#site-settings" replace />} />
      <Route path="admin/learning-paths" element={<RequireFeature feature="learning_platform_enabled"><Auth><AdminLearningPathsPage /></Auth></RequireFeature>} />
      <Route path="admin/learning-paths/new" element={<RequireFeature feature="learning_platform_enabled"><Auth><AdminLearningPathFormPage /></Auth></RequireFeature>} />
      <Route path="admin/sessions" element={<RequireFeature feature="learning_platform_enabled"><Auth><AdminSessionsPage /></Auth></RequireFeature>} />
      <Route path="admin/learning-paths/:id/edit" element={<RequireFeature feature="learning_platform_enabled"><Auth><AdminLearningPathFormPage /></Auth></RequireFeature>} />
      <Route path="admin/courses" element={<RequireFeature feature="learning_platform_enabled"><Auth><AdminCoursesPage /></Auth></RequireFeature>} />
      <Route path="admin/courses/new" element={<RequireFeature feature="learning_platform_enabled"><Auth><AdminCourseFormPage /></Auth></RequireFeature>} />
      <Route path="admin/courses/:id/edit" element={<RequireFeature feature="learning_platform_enabled"><Auth><AdminCourseFormPage /></Auth></RequireFeature>} />
      <Route path="admin/courses/:courseId/lessons/:lessonId" element={<RequireFeature feature="learning_platform_enabled"><Auth><LessonRouteRedirect /></Auth></RequireFeature>} />
      <Route path="admin/alternate-formats-request" element={<RequireFeature feature="learning_platform_enabled"><Auth><AlternateFormatsRequestPage /></Auth></RequireFeature>} />
      <Route path="admin/courses/templates" element={<RequireFeature feature="learning_platform_enabled"><Auth><AdminCourseTemplatesPage /></Auth></RequireFeature>} />
      <Route path="admin/courses/import" element={<RequireFeature feature="learning_platform_enabled"><Auth><AdminCourseBulkImportPage /></Auth></RequireFeature>} />
      <Route path="admin/courses/feedback" element={<RequireFeature feature="learning_platform_enabled"><Auth><AdminCourseFeedbackPage /></Auth></RequireFeature>} />
      <Route path="admin/strategic" element={<RequireFeature feature="board_features_enabled"><AdminAuth><StrategicAdminPage /></AdminAuth></RequireFeature>} />
      <Route path="admin/users" element={<AdminAuth><AdminUsersPage /></AdminAuth>} />
      <Route path="admin/events" element={<RequireFeature feature="events_enabled"><Auth><EventManagementPage /></Auth></RequireFeature>} />
      <Route path="admin/event-marketing" element={<Navigate to="/staff/admin/outreach#event-marketing" replace />} />
      <Route path="admin/board" element={<RequireFeature feature="board_features_enabled"><AdminAuth><BoardManagementPage /></AdminAuth></RequireFeature>} />
      <Route path="admin/board/public-comments" element={<RequireFeature feature="board_features_enabled"><AdminAuth><BoardPublicCommentsAdminPage /></AdminAuth></RequireFeature>} />
      <Route path="admin/board/audit-log" element={<RequireFeature feature="board_features_enabled"><AdminAuth><BoardAuditLogPage /></AdminAuth></RequireFeature>} />
      <Route path="board-demo" element={<RequireFeature feature="board_features_enabled"><Auth><BoardDemoPage /></Auth></RequireFeature>} />
      <Route path="admin/staff" element={<AdminAuth><StaffManagementPage /></AdminAuth>} />
      <Route path="admin/timesheets" element={<AdminAuth><StaffTimesheetEditorPage /></AdminAuth>} />
      <Route path="admin/pay-rates" element={<AdminAuth><StaffPayRatesPage /></AdminAuth>} />
      <Route path="admin/financial" element={<RequireFeature feature="board_features_enabled"><AdminAuth><FinancialReportsPage /></AdminAuth></RequireFeature>} />
      <Route path="admin/annual-reports" element={<RequireFeature feature="board_features_enabled"><RequireAuth requiredRoles={['admin', 'director', 'staff']}><AnnualReportsPage /></RequireAuth></RequireFeature>} />
      <Route path="admin/acquisition" element={<RequireFeature feature="acquisition_enabled"><Auth><AcquisitionManagementPage /></Auth></RequireFeature>} />
      <Route path="admin/rationale-backfill" element={<AdminAuth><AdminRationaleBackfillPage /></AdminAuth>} />
      <Route path="admin/collection-memory" element={<AdminAuth><AdminCollectionMemoryPage /></AdminAuth>} />
      <Route path="admin/databases" element={<Auth><AdminDatabasesPage /></Auth>} />
      <Route path="admin/migration" element={<RequireFeature feature="migration_enabled"><AdminAuth><AdminMigrationWizardPage /></AdminAuth></RequireFeature>} />
      <Route path="admin/migration-project" element={<RequireFeature feature="migration_enabled"><AdminAuth><MigrationProjectPage /></AdminAuth></RequireFeature>} />
      <Route path="admin/reading-programs" element={<RequireFeature feature="reading_programs_enabled"><Auth><AdminReadingProgramsPage /></Auth></RequireFeature>} />
      <Route path="admin/school-impact" element={<AdminAuth><SchoolImpactReportingPage /></AdminAuth>} />
      <Route path="admin/community-outcomes" element={<RequireFeature feature="community_outcomes_enabled"><Auth><CommunityOutcomesDashboardPage /></Auth></RequireFeature>} />
      <Route path="admin/partnership-tiers" element={<AdminAuth><PartnershipTierManagementPage /></AdminAuth>} />
      <Route path="admin/reading-ambassadors" element={<AdminAuth><ReadingAmbassadorPage /></AdminAuth>} />
      <Route path="admin/reading-bundles" element={<AdminAuth><ReadingBundleDistributionPage /></AdminAuth>} />
      <Route path="admin/analytics" element={<Auth><AnalyticsDashboardPage /></Auth>} />
      <Route path="admin/analytics/sharing" element={<Auth><AdminSharingAnalyticsPage /></Auth>} />
      <Route path="admin/website-analytics" element={<AdminAuth><WebsiteAnalyticsPage /></AdminAuth>} />
      <Route path="admin/analytics/journeys" element={<RequireFeature feature="outreach_enabled"><Auth><JourneyAnalyticsDashboard /></Auth></RequireFeature>} />
      <Route path="admin/analytics/predictive" element={<Auth><PredictiveAnalyticsPage /></Auth>} />
      <Route path="admin/legal" element={<RequireFeature feature="legal_services_enabled"><Auth><AdminLegalPage /></Auth></RequireFeature>} />
      <Route path="admin/compliance" element={<RequireFeature feature="compliance_enabled"><AdminAuth><AdminComplianceDashboardPage /></AdminAuth></RequireFeature>} />
      <Route path="admin/unified-compliance" element={<Navigate to="/staff/admin/compliance#audit" replace />} />
      <Route path="admin/cipa" element={<Navigate to="/staff/admin/compliance#cipa" replace />} />
      <Route path="admin/state-compliance" element={<Navigate to="/staff/admin/compliance#state" replace />} />
      <Route path="admin/law-enforcement" element={<Navigate to="/staff/admin/compliance#law-enforcement" replace />} />
      <Route path="admin/ban-tracker" element={<Navigate to="/staff/admin/compliance#ban-tracker" replace />} />
      <Route path="admin/public-records" element={<Navigate to="/staff/admin/compliance#public-records" replace />} />
      <Route path="admin/sms" element={<Navigate to="/staff/admin/outreach#sms" replace />} />
      <Route path="admin/meta-tags" element={<AdminAuth><AdminMetaTagsPage /></AdminAuth>} />
      <Route path="admin/mood-categories" element={<AdminAuth><AdminMoodCategoriesPage /></AdminAuth>} />
      <Route path="admin/patron-categories" element={<AdminAuth><AdminPatronCategoriesPage /></AdminAuth>} />
      <Route path="admin/content-translations" element={<AdminAuth><AdminContentTranslationsPage /></AdminAuth>} />
      <Route path="admin/social-sharing" element={<AdminAuth><AdminSocialSharingPage /></AdminAuth>} />
      <Route path="admin/edi" element={<RequireFeature feature="acquisition_enabled"><AdminAuth><AdminEDISettingsPage /></AdminAuth></RequireFeature>} />
      <Route path="admin/recommendations" element={<Navigate to="/staff/admin/ai#recommendations" replace />} />
      <Route path="admin/semantic-search" element={<Navigate to="/staff/admin/ai#search" replace />} />
      <Route path="admin/system-limits" element={<Navigate to="/staff/admin/circulation-policy#limits" replace />} />
      <Route path="admin/patron-settings" element={<Navigate to="/staff/admin/circulation-policy#patron-settings" replace />} />
      <Route path="admin/staff-settings" element={<Navigate to="/staff/admin/circulation-policy#staff-settings" replace />} />
      <Route path="admin/circulation-rules" element={<Navigate to="/staff/admin/circulation-policy#circulation-rules" replace />} />
      <Route path="admin/api-status" element={<Navigate to="/staff/admin/system#api-status" replace />} />
      <Route path="admin/system-health" element={<Navigate to="/staff/admin/system#health" replace />} />
      <Route path="admin/monitoring" element={<Navigate to="/staff/admin/system#monitoring" replace />} />
      <Route path="admin/cache" element={<Navigate to="/staff/admin/system#cache" replace />} />
      <Route path="admin/link-health" element={<AdminAuth><AdminLinkHealthPage /></AdminAuth>} />
      <Route path="admin/consortium" element={<RequireFeature feature="outreach_enabled"><AdminAuth><ConsortiumManagementPage /></AdminAuth></RequireFeature>} />
      <Route path="admin/treasurer" element={<RequireFeature feature="financial_reports_enabled"><RequireAuth requiredRoles={['admin', 'staff']}><TreasurerDashboardPage /></RequireAuth></RequireFeature>} />
      <Route path="admin/board-treasurer" element={<RequireFeature feature="board_features_enabled"><AdminAuth><BoardTreasurerDashboardPage /></AdminAuth></RequireFeature>} />
      <Route path="admin/strategic/analytics" element={<RequireFeature feature="board_features_enabled"><AdminAuth><StrategicAnalyticsPage /></AdminAuth></RequireFeature>} />
      <Route path="admin/audiobooks" element={<RequireFeature feature="streaming_enabled"><AdminAuth><AdminAudiobooksPage /></AdminAuth></RequireFeature>} />
      <Route path="admin/serials" element={<RequireFeature feature="serials_enabled"><Auth><SerialsDashboardPage /></Auth></RequireFeature>} />
      <Route path="admin/serials/titles" element={<RequireFeature feature="serials_enabled"><Auth><SerialTitlesPage /></Auth></RequireFeature>} />
      <Route path="admin/serials/issues" element={<RequireFeature feature="serials_enabled"><Auth><SerialIssuesPage /></Auth></RequireFeature>} />
      <Route path="admin/archival-collections" element={<RequireFeature feature="collection_management_enabled"><Auth><StaffArchivalCollectionsPage /></Auth></RequireFeature>} />
      <Route path="admin/releases" element={<RequireFeature feature="acquisition_enabled"><Auth><ReleasesManagementPage /></Auth></RequireFeature>} />
      <Route path="admin/attendance" element={<RequireFeature feature="events_enabled"><Auth><AttendanceTrackingPage /></Auth></RequireFeature>} />
      <Route path="admin/scheduler" element={<Navigate to="/staff/admin/system#scheduler" replace />} />
      <Route path="admin/security" element={<Navigate to="/staff/admin/system#security" replace />} />
      <Route path="admin/sip2" element={<RequireFeature feature="sip2_rfid_enabled"><AdminAuth><AdminSIP2SettingsPage /></AdminAuth></RequireFeature>} />
      <Route path="admin/z3950" element={<AdminAuth><AdminZ3950SettingsPage /></AdminAuth>} />
      <Route path="admin/home-delivery-settings" element={<RequireFeature feature="home_delivery_enabled"><AdminAuth><AdminHomeDeliverySettingsPage /></AdminAuth></RequireFeature>} />
      <Route path="admin/homepage-quotes" element={<AdminAuth><AdminHomepageQuotesPage /></AdminAuth>} />
      <Route path="admin/email-marketing" element={<Navigate to="/staff/admin/outreach#email-marketing" replace />} />
      <Route path="admin/virus-scan" element={<Navigate to="/staff/admin/system#virus-scan" replace />} />
      <Route path="admin/search-engine" element={<AdminAuth><AdminSearchEngineSettingsPage /></AdminAuth>} />
      <Route path="admin/storage" element={<Navigate to="/staff/admin/system#storage" replace />} />
      <Route path="admin/amas" element={<RequireFeature feature="ama_enabled"><Auth><StaffAmasPage /></Auth></RequireFeature>} />
      <Route path="admin/book-clubs" element={<RequireFeature feature="book_clubs_enabled"><Auth><StaffBookClubsPage /></Auth></RequireFeature>} />
      <Route path="storytime" element={<RequireFeature feature="storytime_enabled"><Auth><StaffStorytimePage /></Auth></RequireFeature>} />

      {/* Parent Onboarding */}
      <Route path="parent-onboarding" element={<RequireFeature feature="parent_onboarding_enabled"><Auth><ParentOnboardingDashboardPage /></Auth></RequireFeature>} />
      <Route path="parent-onboarding/sessions/:id" element={<RequireFeature feature="parent_onboarding_enabled"><Auth><ParentOnboardingSessionPage /></Auth></RequireFeature>} />
      <Route path="parent-onboarding/childcare" element={<RequireFeature feature="parent_onboarding_enabled"><Auth><ChildcarePage /></Auth></RequireFeature>} />
      <Route path="parent-onboarding/home-visits" element={<RequireFeature feature="parent_onboarding_enabled"><Auth><ParentHomeVisitsPage /></Auth></RequireFeature>} />
      {/* Today's route view. Gated on the day-plan flag (not just parent_onboarding) -- if a library turns it off, the page disappears entirely. */}
      <Route path="parent-onboarding/home-visits/today" element={<RequireFeature feature="home_visit_day_plan_enabled"><Auth><ParentHomeVisitsTodayPage /></Auth></RequireFeature>} />
      <Route path="parent-onboarding/connection-groups" element={<RequireFeature feature="parent_onboarding_enabled"><Auth><ParentConnectionGroupsPage /></Auth></RequireFeature>} />
      <Route path="parent-onboarding/connection-groups/approvals" element={<RequireFeature feature="parent_onboarding_enabled"><Auth><ConnectionGroupsApprovalsPage /></Auth></RequireFeature>} />
      <Route path="parent-onboarding/resources" element={<RequireFeature feature="parent_onboarding_enabled"><Auth><ParentResourcesPage /></Auth></RequireFeature>} />
      <Route path="parent-onboarding/resource-flags" element={<RequireFeature feature="parent_onboarding_enabled"><Auth><StaffResourceFlagsPage /></Auth></RequireFeature>} />

      {/* Catch-all 404 for staff routes */}
      <Route path="*" element={<Suspense fallback={null}><NotFoundPage /></Suspense>} />
    </Routes>
  )
}
