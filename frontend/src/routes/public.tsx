/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Navigate, Route } from 'react-router-dom'
import { lazyWithRetry } from '../utils/lazyWithRetry'
import { withAuth, withAuthFeature, withFeature, withPlatform, withStreamingFeature } from "./routeGuards"

const HomePage = lazyWithRetry(() => import('../pages/HomePage'), 'home-page')
const ForLibrariesPage = lazyWithRetry(() => import('../pages/ForLibrariesPage'), 'for-libraries-page')

const EventsPage = lazyWithRetry(() => import('../pages/EventsPage'), 'events-page')
const EventDetailPage = lazyWithRetry(() => import('../pages/EventDetailPage'), 'event-detail-page')
const EventSeriesPage = lazyWithRetry(() => import('../pages/EventSeriesPage'), 'event-series-page')
const AmasPage = lazyWithRetry(() => import('../pages/AmasPage'), 'amas-page')
const AmaDetailPage = lazyWithRetry(() => import('../pages/AmaDetailPage'), 'ama-detail-page')
const ReadingProgramsPage = lazyWithRetry(() => import('../pages/ReadingProgramsPage'), 'reading-programs-page')
const PaperLogRedeemPage = lazyWithRetry(() => import('../pages/programs/PaperLogRedeemPage'), 'paper-log-redeem-page')
const ReadingLogsPage = lazyWithRetry(() => import('../pages/ReadingLogsPage'), 'reading-logs-page')
const ReadingMinutesPage = lazyWithRetry(() => import('../pages/ReadingMinutesPage'), 'reading-minutes-page')
const TeacherReadingDashboardPage = lazyWithRetry(() => import('../pages/TeacherReadingDashboardPage'), 'teacher-reading-dashboard-page')
const TeacherHomePage = lazyWithRetry(() => import('../pages/TeacherHomePage'), 'teacher-home-page')
const DigitalResourcesPage = lazyWithRetry(() => import('../pages/DigitalResourcesPage'), 'digital-resources-page')
const AIToolsPage = lazyWithRetry(() => import('../pages/AIToolsPage'), 'ai-tools-page')
const AIToolsHowItWorksPage = lazyWithRetry(() => import('../pages/AIToolsHowItWorksPage'), 'ai-tools-how-it-works-page')
const AccountPage = lazyWithRetry(() => import('../pages/AccountPage'), 'account-page')
const BanTrackerSubscriptionsPage = lazyWithRetry(() => import('../pages/account/BanTrackerSubscriptionsPage'), 'account-ban-tracker-subscriptions')
const BusinessResourcesPage = lazyWithRetry(() => import('../pages/BusinessResourcesPage'), 'business-resources-page')
// CommunityResourcesPage merged into LifeSituationsPage - redirect below
// AboutUsPage merged into AboutPage - redirect below
const AccessibilityPage = lazyWithRetry(() => import('../pages/AccessibilityPage'), 'accessibility-page')
const AccessibilitySettingsPage = lazyWithRetry(() => import('../pages/AccessibilitySettingsPage'), 'accessibility-settings-page')
const SecurityPage = lazyWithRetry(() => import('../pages/SecurityPage'), 'security-page')
const TechSupportPage = lazyWithRetry(() => import('../pages/TechSupportPage'), 'tech-support-page')
const TechPosterPage = lazyWithRetry(() => import('../pages/TechPosterPage'), 'tech-poster-page')
const MyEquipmentPage = lazyWithRetry(() => import("../pages/MyEquipmentPage"), 'my-equipment-page')
const WiFiPage = lazyWithRetry(() => import('../pages/WiFiPage'), 'wi-fi-page')
const ComputersPage = lazyWithRetry(() => import("../pages/ComputersPage"), 'computers-page')
const RoomBookingPage = lazyWithRetry(() => import('../pages/RoomBookingPage'), 'room-booking-page')
const ContactPage = lazyWithRetry(() => import('../pages/ContactPage'), 'contact-page')
const PrivacyPage = lazyWithRetry(() => import('../pages/PrivacyPage'), 'privacy-page')
const TermsOfServicePage = lazyWithRetry(() => import('../pages/TermsOfServicePage'), 'terms-of-service-page')
const NotFoundPage = lazyWithRetry(() => import('../pages/NotFoundPage'), 'not-found-page')
const LearningPathsPage = lazyWithRetry(() => import('../pages/LearningPathsPage'), 'learning-paths-page')
const VolunteerApplyPage = lazyWithRetry(() => import("../pages/VolunteerApplyPage"), 'volunteer-apply-page')
const LearningPathDetailPage = lazyWithRetry(() => import('../pages/LearningPathDetailPage'), 'learning-path-detail-page')
const AboutPage = lazyWithRetry(() => import('../pages/AboutPage'), 'about-page')
const AiLegalPage = lazyWithRetry(() => import('../pages/AiLegalPage'), 'ai-legal-page')
const DonatePage = lazyWithRetry(() => import('../pages/DonatePage'), 'donate-page')
const ReleaseRadarPage = lazyWithRetry(() => import('../pages/ReleaseRadarPage'), 'release-radar-page')
const ComingSoonPage = lazyWithRetry(() => import('../pages/ComingSoonPage'), 'coming-soon-page')
const StrategicPlanPage = lazyWithRetry(() => import('../pages/StrategicPlanPage'), 'strategic-plan-page')
const AskLibrarianPage = lazyWithRetry(() => import('../pages/AskLibrarianPage'), 'ask-librarian-page')
const YouthPage = lazyWithRetry(() => import('../pages/YouthPage'), 'youth-page')
const TeenPage = lazyWithRetry(() => import('../pages/TeenPage'), 'teen-page')
const AnnouncementsPage = lazyWithRetry(() => import('../pages/AnnouncementsPage'), 'announcements-page')
const NotificationsPage = lazyWithRetry(() => import('../pages/NotificationsPage'), 'notifications-page')
const KnowledgeBasePage = lazyWithRetry(() => import('../pages/KnowledgeBasePage'), 'knowledge-base-page')
const ReadToReducePage = lazyWithRetry(() => import('../pages/ReadToReducePage'), 'read-to-reduce-page')
const ReadingGamificationPage = lazyWithRetry(() => import('../pages/ReadingGamificationPage'), 'reading-gamification-page')
const ReadingLeaderboardsPage = lazyWithRetry(() => import('../pages/ReadingLeaderboardsPage'), 'reading-leaderboards-page')
const CertificateVerificationPage = lazyWithRetry(() => import('../pages/CertificateVerificationPage'), 'certificate-verification-page')
const ReadingCertificatesPage = lazyWithRetry(() => import("../pages/ReadingCertificatesPage"), 'reading-certificates-page')
const PublicReadingListsPage = lazyWithRetry(() => import('../pages/PublicReadingListsPage'), 'public-reading-lists-page')
const PublicReadingListDetailPage = lazyWithRetry(() => import('../pages/PublicReadingListDetailPage'), 'public-reading-list-detail-page')
const StaffReviewsPage = lazyWithRetry(() => import('../pages/StaffReviewsPage'), 'staff-reviews-page')
const StreamingPage = lazyWithRetry(() => import('../pages/StreamingPage'), 'streaming-page')
const GutenbergPage = lazyWithRetry(() => import('../pages/GutenbergPage'), 'gutenberg-page')
const RubricsPage = lazyWithRetry(() => import('../pages/RubricsPage'), 'rubrics-page')
const RubricDetailPage = lazyWithRetry(() => import('../pages/RubricDetailPage'), 'rubric-detail-page')
const RubricAssessPage = lazyWithRetry(() => import('../pages/RubricAssessPage'), 'rubric-assess-page')
const BranchesPage = lazyWithRetry(() => import('../pages/BranchesPage'), 'branches-page')
const DatabasesPage = lazyWithRetry(() => import('../pages/DatabasesPage'), 'databases-page')
// SelfServiceTechSupportHub merged into TechSupportPage - redirect below
const WirelessPrintingGuide = lazyWithRetry(() => import('../pages/guides/WirelessPrintingGuide'), 'wireless-printing-guide')
const MyPrintJobsPage = lazyWithRetry(() => import("../pages/MyPrintJobsPage"), 'my-print-jobs-page')
const EmailAccountGuide = lazyWithRetry(() => import('../pages/guides/EmailAccountGuide'), 'email-account-guide')
const WiFiTroubleshootingGuide = lazyWithRetry(() => import('../pages/guides/WiFiTroubleshootingGuide'), 'wi-fi-troubleshooting-guide')
const PasswordResetGuide = lazyWithRetry(() => import('../pages/guides/PasswordResetGuide'), 'password-reset-guide')
const EmailOnPhoneGuide = lazyWithRetry(() => import('../pages/guides/EmailOnPhoneGuide'), 'email-on-phone-guide')
const LibraryCardGuide = lazyWithRetry(() => import('../pages/guides/LibraryCardGuide'), 'library-card-guide')
const ScamRecognitionGuide = lazyWithRetry(() => import('../pages/guides/ScamRecognitionGuide'), 'scam-recognition-guide')
const CheckPrintJobsGuide = lazyWithRetry(() => import('../pages/guides/CheckPrintJobsGuide'), 'check-print-jobs-guide')
const PlacingHoldsGuide = lazyWithRetry(() => import('../pages/guides/PlacingHoldsGuide'), 'placing-holds-guide')
const GuidesIndexPage = lazyWithRetry(() => import("../pages/GuidesIndexPage"), 'guides-index-page')
const GetStartedPage = lazyWithRetry(() => import('../pages/GetStartedPage'), 'get-started-page')
const CareersPage = lazyWithRetry(() => import('../pages/CareersPage'), 'careers-page')
const DemoLandingPage = lazyWithRetry(() => import('../pages/DemoLandingPage'), 'demo-landing-page')
const StatusPage = lazyWithRetry(() => import('../pages/StatusPage'), 'status-page')
const SystemStatusPage = lazyWithRetry(() => import('../pages/SystemStatusPage'), 'system-status-page')
const MaterialCostComparisonPage = lazyWithRetry(() => import('../pages/MaterialCostComparisonPage'), 'material-cost-comparison-page')
const TransparencyPage = lazyWithRetry(() => import('../pages/transparency/TransparencyPage'), 'transparency-page')
const PublicRecordsRequestPage = lazyWithRetry(() => import('../pages/transparency/PublicRecordsRequestPage'), 'public-records-request-page')
const CardApplicationPage = lazyWithRetry(() => import('../pages/CardApplicationPage'), 'card-application-page')
const TeacherApplicationPage = lazyWithRetry(() => import('../pages/TeacherApplicationPage'), 'teacher-application-page')
const CardApplicationStatusPage = lazyWithRetry(() => import('../pages/CardApplicationStatusPage'), 'card-application-status-page')
const YouthHomeworkHelpPage = lazyWithRetry(() => import('../pages/YouthHomeworkHelpPage'), 'youth-homework-help-page')
const YouthCodingTracksPage = lazyWithRetry(() => import('../pages/YouthCodingTracksPage'), 'youth-coding-tracks-page')
const YouthTeenMentorsPage = lazyWithRetry(() => import('../pages/YouthTeenMentorsPage'), 'youth-teen-mentors-page')
const YouthCommunityArchivesPage = lazyWithRetry(() => import('../pages/YouthCommunityArchivesPage'), 'youth-community-archives-page')
const TeacherReadingListsPage = lazyWithRetry(() => import('../pages/TeacherReadingListsPage'), 'teacher-reading-lists-page')
const ProfessionalDevelopmentPage = lazyWithRetry(() => import('../pages/ProfessionalDevelopmentPage'), 'professional-development-page')
const LibrarianConsultationPage = lazyWithRetry(() => import('../pages/LibrarianConsultationPage'), 'librarian-consultation-page')
const FamilyReadingChallengesPage = lazyWithRetry(() => import('../pages/FamilyReadingChallengesPage'), 'family-reading-challenges-page')
const LibraryVisitSchedulingPage = lazyWithRetry(() => import('../pages/LibraryVisitSchedulingPage'), 'library-visit-scheduling-page')
const ShiftSwapBoard = lazyWithRetry(() => import('../pages/ShiftSwapBoard'), 'shift-swap-board')
const PatronPositivityPage = lazyWithRetry(() => import('../pages/PatronPositivityPage'), 'patron-positivity-page')
const MyReadingInsightsPage = lazyWithRetry(() => import('../pages/MyReadingInsightsPage'), 'my-reading-insights-page')
const InterlibraryLoanPage = lazyWithRetry(() => import('../pages/InterlibraryLoanPage'), 'interlibrary-loan-page')
const BookClubsPage = lazyWithRetry(() => import('../pages/BookClubsPage'), 'book-clubs-page')
const BookClubDetailPage = lazyWithRetry(() => import('../pages/BookClubDetailPage'), 'book-club-detail-page')
const BookClubDiscussionPage = lazyWithRetry(() => import('../pages/BookClubDiscussionPage'), 'book-club-discussion-page')
const NotificationPreferencesPage = lazyWithRetry(() => import('../pages/NotificationPreferencesPage'), 'notification-preferences-page')
const EmergencyOperationsDashboardPage = lazyWithRetry(() => import('../pages/EmergencyOperationsDashboardPage'), 'emergency-operations-dashboard-page')
const EmergencyOperationsOfflineModePage = lazyWithRetry(() => import('../pages/EmergencyOperationsOfflineModePage'), 'emergency-operations-offline-mode-page')
const EmergencyOperationsPaperBackupPage = lazyWithRetry(() => import('../pages/EmergencyOperationsPaperBackupPage'), 'emergency-operations-paper-backup-page')
const EmergencyOperationsDataSyncPage = lazyWithRetry(() => import('../pages/EmergencyOperationsDataSyncPage'), 'emergency-operations-data-sync-page')
const EmergencyOperationsCascadePage = lazyWithRetry(() => import('../pages/EmergencyOperationsCascadePage'), 'emergency-operations-cascade-page')
const EmergencyOperationsClosurePage = lazyWithRetry(() => import('../pages/EmergencyOperationsClosurePage'), 'emergency-operations-closure-page')
const EmergencyOperationsServicePriorityPage = lazyWithRetry(() => import('../pages/EmergencyOperationsServicePriorityPage'), 'emergency-operations-service-priority-page')
const EmergencyOperationsRecoveryPage = lazyWithRetry(() => import('../pages/EmergencyOperationsRecoveryPage'), 'emergency-operations-recovery-page')
const EmergencyOperationsInsurancePage = lazyWithRetry(() => import('../pages/EmergencyOperationsInsurancePage'), 'emergency-operations-insurance-page')
const EmergencyOperationsAssessmentPage = lazyWithRetry(() => import('../pages/EmergencyOperationsAssessmentPage'), 'emergency-operations-assessment-page')
const EmergencyOperationsCommunityHubPage = lazyWithRetry(() => import('../pages/EmergencyOperationsCommunityHubPage'), 'emergency-operations-community-hub-page')
const PurchaseRequestPage = lazyWithRetry(() => import('../pages/PurchaseRequestPage'), 'purchase-request-page')
const ForgotPasswordPage = lazyWithRetry(() => import('../pages/ForgotPasswordPage'), 'forgot-password-page')
const ResetPasswordPage = lazyWithRetry(() => import('../pages/ResetPasswordPage'), 'reset-password-page')
const AcceptInvitePage = lazyWithRetry(() => import('../pages/AcceptInvitePage'), 'accept-invite-page')
const VerifyEmailPage = lazyWithRetry(() => import('../pages/VerifyEmailPage'), 'verify-email-page')
const MagicLinkVerifyPage = lazyWithRetry(() => import('../pages/MagicLinkVerifyPage'), 'magic-link-verify-page')
const ConsentPage = lazyWithRetry(() => import('../pages/ConsentPage'), 'consent-page')
const LoginPage = lazyWithRetry(() => import('../pages/LoginPage'), 'login-page')
const TwoFactorVerifyPage = lazyWithRetry(() => import('../pages/TwoFactorVerifyPage'), 'two-factor-verify-page')
const RegisterPage = lazyWithRetry(() => import('../pages/RegisterPage'), 'register-page')
const OnboardingWelcomePage = lazyWithRetry(() => import('../pages/onboarding/WelcomePage'), 'onboarding-welcome-page')
const OnboardingPreferencesPage = lazyWithRetry(() => import('../pages/onboarding/PreferencesPage'), 'onboarding-preferences-page')
const OnboardingBranchPage = lazyWithRetry(() => import('../pages/onboarding/BranchPage'), 'onboarding-branch-page')
const OnboardingTourPage = lazyWithRetry(() => import('../pages/onboarding/TourPage'), 'onboarding-tour-page')
const OnboardingCompletePage = lazyWithRetry(() => import('../pages/onboarding/CompletePage'), 'onboarding-complete-page')
const OnboardingMigrationPage = lazyWithRetry(() => import('../pages/OnboardingMigrationPage'), 'onboarding-migration-page')
const PatronHomeDeliveryPage = lazyWithRetry(() => import('../pages/PatronHomeDeliveryPage'), 'patron-home-delivery-page')
const BetaFeedbackPage = lazyWithRetry(() => import("../pages/BetaFeedbackPage"), 'beta-feedback-page')
const LibrarianConnectPage = lazyWithRetry(() => import('../pages/LibrarianConnectPage'), 'librarian-connect-page')
const BookRequestPage = lazyWithRetry(() => import('../pages/BookRequestPage'), 'book-request-page')
const PatronReportsDashboardPage = lazyWithRetry(() => import('../pages/PatronReportsDashboardPage'), 'patron-reports-dashboard-page')
const ParentMentorsPage = lazyWithRetry(() => import('../pages/ParentMentorsPage'), 'parent-mentors-page')
const ParentMentorRequestPage = lazyWithRetry(() => import('../pages/ParentMentorRequestPage'), 'parent-mentor-request-page')
const ParentMentorVolunteerPage = lazyWithRetry(() => import('../pages/ParentMentorVolunteerPage'), 'parent-mentor-volunteer-page')
const LifeSituationsPage = lazyWithRetry(() => import('../pages/LifeSituationsPage'), 'life-situations-page')
const FaqChatbotPage = lazyWithRetry(() => import("../pages/FaqChatbotPage"), 'faq-chatbot-page')
const GetHelpPage = lazyWithRetry(() => import('../pages/GetHelpPage'), 'get-help-page')
const SustainabilityPage = lazyWithRetry(() => import("../pages/SustainabilityPage"), 'sustainability-page')

export const publicAuthRoutes: React.ReactElement = (
  <>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/2fa-verify" element={<TwoFactorVerifyPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/staff/accept-invite" element={<AcceptInvitePage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/auth/magic-link" element={<MagicLinkVerifyPage />} />
      <Route path="/consent" element={<ConsentPage />} />

      <Route path="/onboarding/welcome" element={withAuth(<OnboardingWelcomePage />)} />
      <Route path="/onboarding/preferences" element={withAuth(<OnboardingPreferencesPage />)} />
      <Route path="/onboarding/branch" element={withAuth(<OnboardingBranchPage />)} />
      <Route path="/onboarding/migration" element={withAuth(<OnboardingMigrationPage />, ['admin', 'super_admin', 'director'])} />
      <Route path="/onboarding/tour" element={withAuth(<OnboardingTourPage />)} />
      <Route path="/onboarding/complete" element={withAuth(<OnboardingCompletePage />)} />
  </>
)

export const publicLayoutRoutes: React.ReactElement = (
  <>
      <Route index element={<HomePage />} />
      <Route path="events" element={withFeature('events_enabled', <EventsPage />)} />
      {/* Dedicated per-series enroll page. Must register BEFORE :seriesSlug
          and detail/:eventId routes so the literal "series" segment wins. */}
      <Route path="events/series/:seriesId" element={withFeature('events_enabled', <EventSeriesPage />)} />
      <Route path="events/:seriesSlug" element={withFeature('events_enabled', <EventsPage />)} />
      <Route path="events/detail/:eventId" element={withFeature('events_enabled', <EventDetailPage />)} />
      <Route path="amas" element={withFeature('ama_enabled', <AmasPage />)} />
      <Route path="amas/:sessionId" element={withFeature('ama_enabled', <AmaDetailPage />)} />
      <Route path="programs" element={withFeature('reading_programs_enabled', <ReadingProgramsPage />)} />
      <Route path="programs/redeem" element={withAuthFeature('reading_programs_paper_log_enabled', <PaperLogRedeemPage />)} />
      <Route path="reading-logs" element={withFeature('gamification_enabled', <ReadingLogsPage />)} />
      <Route path="reading-minutes" element={withFeature('gamification_enabled', withAuth(<ReadingMinutesPage />))} />
      <Route path="releases" element={<ReleaseRadarPage />} />
      <Route path="coming-soon" element={<ComingSoonPage />} />
      <Route path="digital" element={withFeature('collection_management_enabled', <DigitalResourcesPage />)} />
      <Route path="streaming" element={withStreamingFeature(<StreamingPage />)} />
      <Route path="databases" element={withFeature('collection_management_enabled', <DatabasesPage />)} />
      <Route path="gutenberg" element={withFeature('free_ebooks_enabled', <GutenbergPage />)} />
      <Route path="ai" element={withFeature('ai_tools_enabled', <AIToolsPage />)} />
      <Route path="ai/how-it-works" element={withFeature('ai_tools_enabled', <AIToolsHowItWorksPage />)} />
      <Route path="ai/legal" element={withFeature('ai_tools_enabled', <AiLegalPage />)} />
      <Route path="ai/agents" element={<Navigate to="/ask-librarian" replace />} />
      <Route path="accessibility" element={<AccessibilityPage />} />
      <Route path="accessibility/settings" element={<AccessibilitySettingsPage />} />
      <Route path="security" element={<SecurityPage />} />
      <Route path="account" element={withAuth(<AccountPage />)} />
      <Route path="account/ban-tracker-subscriptions" element={withAuth(<BanTrackerSubscriptionsPage />)} />
      <Route path="account/preferences" element={withAuth(<Navigate to="/account?tab=settings" replace />)} />
      <Route path="account/settings" element={withAuth(<Navigate to="/account?tab=settings" replace />)} />
      <Route path="account/settings/accessibility" element={<Navigate to="/accessibility/settings" replace />} />
      <Route path="account/notifications" element={withAuth(<Navigate to="/account?tab=notifications" replace />)} />
      <Route path="my-account" element={<Navigate to="/account" replace />} />
      <Route path="my-account/checkouts" element={<Navigate to="/account?tab=checkouts" replace />} />
      <Route path="my-account/holds" element={<Navigate to="/account?tab=holds" replace />} />
      <Route path="my-account/fines" element={<Navigate to="/account?tab=overview" replace />} />
      <Route path="my-account/settings" element={<Navigate to="/account?tab=settings" replace />} />
      <Route path="home-delivery" element={withFeature('home_delivery_enabled', withAuth(<PatronHomeDeliveryPage />))} />
      <Route path="suggest-purchase" element={withAuth(<PurchaseRequestPage />)} />
      <Route path="notifications" element={withFeature('notifications_enabled', withAuth(<NotificationsPage />))} />
      <Route path="my-reading-insights" element={withFeature('gamification_enabled', withAuth(<MyReadingInsightsPage />))} />
      <Route path="book-clubs" element={withFeature('book_clubs_enabled', <BookClubsPage />)} />
      <Route path="book-clubs/:id" element={withFeature('book_clubs_enabled', <BookClubDetailPage />)} />
      <Route path="book-clubs/:id/discuss/:meetingId" element={withFeature('book_clubs_enabled', <BookClubDiscussionPage />)} />
      <Route path="notifications/preferences" element={withFeature('notifications_enabled', withAuth(<NotificationPreferencesPage />))} />
      <Route path="business" element={<BusinessResourcesPage />} />
      <Route path="community" element={<Navigate to="/help-guide#community" replace />} />
      <Route path="about" element={<AboutPage />} />
      <Route path="about-us" element={<Navigate to="/about" replace />} />
      <Route path="about/our-story" element={<Navigate to="/about?tab=story" replace />} />
      <Route path="about/library" element={<Navigate to="/about" replace />} />
      <Route path="about/digital-transition" element={<Navigate to="/about?tab=approach" replace />} />
      <Route path="about/ai-policy" element={<Navigate to="/about?tab=approach" replace />} />
      <Route path="tech/poster" element={withAuth(<TechPosterPage />, ['staff', 'admin', 'director', 'legal', 'bookmobile', 'homebond', 'board_member'])} />
      <Route path="tech" element={<TechSupportPage />} />
      <Route path="equipment" element={withFeature('tech_services_enabled', withAuth(<MyEquipmentPage />))} />
      <Route path="laptops" element={<Navigate to="/equipment" replace />} />
      <Route path="wifi" element={<WiFiPage />} />
      <Route path="rooms" element={withFeature('meeting_rooms_enabled', <RoomBookingPage />)} />
      <Route path="computers" element={withFeature('tech_services_enabled', withAuth(<ComputersPage />))} />
      <Route path="branches" element={<BranchesPage />} />
      <Route path="locations" element={<BranchesPage />} />
      <Route path="contact" element={<ContactPage />} />
      <Route path="feedback" element={<BetaFeedbackPage />} />
      <Route path="donate" element={<DonatePage />} />
      <Route path="careers" element={<CareersPage />} />
      <Route path="faq" element={<Navigate to="/help" replace />} />
      <Route path="hours" element={<Navigate to="/branches" replace />} />
      <Route path="privacy" element={<PrivacyPage />} />
      <Route path="terms" element={<TermsOfServicePage />} />
      <Route path="announcements" element={withFeature('notifications_enabled', <AnnouncementsPage />)} />
      <Route path="help" element={<KnowledgeBasePage />} />
      <Route path="knowledge" element={<Navigate to="/help" replace />} />
      <Route path="knowledge-base" element={<KnowledgeBasePage />} />
      <Route path="strategic-plan" element={withFeature('strategic_planning_enabled', <StrategicPlanPage />)} />
      <Route path="get-help" element={<GetHelpPage />} />
      <Route path="help/chat" element={<FaqChatbotPage />} />
      <Route path="ask-librarian" element={<AskLibrarianPage />} />
      <Route path="transparency" element={<TransparencyPage />} />
      <Route path="sustainability" element={<SustainabilityPage />} />
      <Route path="transparency/material-costs" element={<MaterialCostComparisonPage />} />
      <Route path="transparency/records-requests" element={<PublicRecordsRequestPage />} />
      <Route path="apply-for-card" element={<Navigate to="/card-application" replace />} />
      <Route path="card" element={<Navigate to="/card-application" replace />} />
      <Route path="card-application" element={<CardApplicationPage />} />
      <Route path="teacher/apply" element={<TeacherApplicationPage />} />
      {/* Issue #1028 — token-gated public status link emailed at submit. */}
      <Route path="card-application/status/:token" element={<CardApplicationStatusPage />} />
      <Route path="resources" element={<Navigate to="/digital" replace />} />
      <Route path="resources/digital" element={<Navigate to="/digital" replace />} />
      <Route path="status" element={<StatusPage />} />
      <Route path="system-status" element={<SystemStatusPage />} />
      {/* Emergency operations routes moved to publicStaffShellRoutes (below) — they use StaffLayout */}
      <Route path="youth" element={withFeature('community_features_enabled', <YouthPage />)} />
      <Route path="teen" element={withFeature('community_features_enabled', <TeenPage />)} />
      <Route path="youth/homework-help" element={withFeature('community_features_enabled', <YouthHomeworkHelpPage />)} />
      <Route path="youth/coding-tracks" element={withFeature('community_features_enabled', <YouthCodingTracksPage />)} />
      <Route path="youth/teen-mentors" element={withFeature('community_features_enabled', <YouthTeenMentorsPage />)} />
      <Route path="youth/archives" element={withFeature('community_features_enabled', <YouthCommunityArchivesPage />)} />
      <Route path="teacher" element={withAuthFeature('for_teachers_enabled', <TeacherHomePage />, ['teacher', 'staff', 'admin', 'super_admin', 'director'])} />
      <Route path="teacher/reading-dashboard" element={withAuthFeature('for_teachers_enabled', <TeacherReadingDashboardPage />, ['teacher', 'staff', 'admin', 'super_admin', 'director'])} />
      <Route path="teacher/reading-lists" element={withAuthFeature('for_teachers_enabled', <TeacherReadingListsPage />)} />
      <Route path="teacher/professional-development" element={withAuthFeature('for_teachers_enabled', <ProfessionalDevelopmentPage />)} />
      <Route path="teacher/library-consultations" element={withAuthFeature('for_teachers_enabled', <LibrarianConsultationPage />)} />
      <Route path="teacher/family-challenges" element={withAuthFeature('for_teachers_enabled', <FamilyReadingChallengesPage />)} />
      <Route path="teacher/library-visits" element={withAuthFeature('for_teachers_enabled', <LibraryVisitSchedulingPage />)} />
      <Route path="learning-paths" element={withFeature('learning_platform_enabled', <LearningPathsPage />)} />
      <Route path="learning" element={<Navigate to="/learn" replace />} />
      <Route path="learning-paths/:id" element={withFeature('learning_platform_enabled', <LearningPathDetailPage />)} />
      <Route path="rubrics" element={withFeature('learning_platform_enabled', <RubricsPage />)} />
      <Route path="rubrics/:rubricId" element={withFeature('learning_platform_enabled', <RubricDetailPage />)} />
      <Route path="rubrics/:rubricId/assess" element={withFeature('learning_platform_enabled', <RubricAssessPage />)} />
      <Route path="rubrics/:rubricId/assess/:assessmentId" element={withFeature('learning_platform_enabled', <RubricAssessPage />)} />
      <Route path="read-to-reduce" element={withFeature('gamification_enabled', <ReadToReducePage />)} />
      <Route path="reading-challenge" element={withFeature('gamification_enabled', <ReadingGamificationPage />)} />
      <Route path="reading-leaderboards" element={withFeature('gamification_enabled', <ReadingLeaderboardsPage />)} />
      <Route path="certificates" element={withFeature('gamification_enabled', <CertificateVerificationPage />)} />
      <Route path="certificates/verify" element={withFeature('gamification_enabled', <CertificateVerificationPage />)} />
      {/* Public certificate verification — branded share link surfaced via QR on PDF. */}
      <Route path="verify/:certNumber" element={<CertificateVerificationPage />} />
      <Route path="reading/certificates" element={withFeature('gamification_enabled', withAuth(<ReadingCertificatesPage />))} />
      <Route path="public-reading-lists" element={withFeature('reading_shelf_enabled', <PublicReadingListsPage />)} />
      <Route path="public-reading-lists/:id" element={withFeature('reading_shelf_enabled', <PublicReadingListDetailPage />)} />
      <Route path="staff-reviews" element={withFeature('reading_shelf_enabled', <StaffReviewsPage />)} />
      <Route path="tech-support" element={<Navigate to="/tech" replace />} />
      <Route path="tech-help" element={<Navigate to="/tech" replace />} />
      <Route path="self-service-tech" element={<Navigate to="/tech" replace />} />
      <Route path="legal-help" element={<Navigate to="/legal" replace />} />
      <Route path="hotspot" element={<Navigate to="/catalog?q=hotspot" replace />} />
      <Route path="guides" element={<GuidesIndexPage />} />
      <Route path="guides/wireless-printing" element={<WirelessPrintingGuide />} />
      <Route path="my-prints" element={withFeature("printing_enabled", withAuth(<MyPrintJobsPage />))} />
      <Route path="printing" element={<Navigate to="/my-prints" replace />} />
      <Route path="guides/email-account" element={<EmailAccountGuide />} />
      <Route path="guides/wifi-troubleshooting" element={<WiFiTroubleshootingGuide />} />
      <Route path="guides/password-reset" element={<PasswordResetGuide />} />
      <Route path="guides/email-on-phone" element={<EmailOnPhoneGuide />} />
      <Route path="guides/library-card" element={<LibraryCardGuide />} />
      <Route path="guides/scam-recognition" element={<ScamRecognitionGuide />} />
      <Route path="guides/check-print-jobs" element={<CheckPrintJobsGuide />} />
      <Route path="guides/placing-holds" element={<PlacingHoldsGuide />} />
      <Route path="get-started" element={<GetStartedPage />} />
      <Route path="new-patron" element={<Navigate to="/get-started" replace />} />
      {/* interlibrary-loan and shift-swap use StaffLayout and live in publicStaffShellRoutes (below) */}
      <Route path="ill" element={<Navigate to="/interlibrary-loan" replace />} />
      <Route path="share-experience" element={<PatronPositivityPage />} />
      <Route path="my-reports" element={withAuth(<PatronReportsDashboardPage />)} />
      <Route path="about/stats" element={<Navigate to="/about?tab=stats" replace />} />
      <Route path="library-stats" element={<Navigate to="/about?tab=stats" replace />} />
      <Route path="help-guide" element={<LifeSituationsPage />} />
      <Route path="life-situations" element={<Navigate to="/help-guide" replace />} />
      <Route path="board-management" element={<Navigate to="/board/meetings" replace />} />
      <Route path="board-demo" element={<Navigate to="/staff/board-demo" replace />} />
      <Route path="parent-mentors" element={withFeature('community_features_enabled', <ParentMentorsPage />)} />
      <Route path="parent-mentors/request" element={withFeature('community_features_enabled', <ParentMentorRequestPage />)} />
      <Route path="parent-mentors/volunteer" element={withFeature('community_features_enabled', <ParentMentorVolunteerPage />)} />
      <Route path="volunteer/apply" element={withAuthFeature("volunteers_enabled", <VolunteerApplyPage />)} />
      <Route path="connect" element={withPlatform(<LibrarianConnectPage />)} />
      <Route path="demo" element={withPlatform(<DemoLandingPage />)} />
      <Route path="request/:ebookId" element={<BookRequestPage />} />
      <Route path="*" element={<NotFoundPage />} />
  </>
)

/**
 * Public URLs that render with the staff shell because their pages use <StaffLayout>.
 * These are mounted under a `<Layout staffShell />` parent in AppRoutes.tsx so the
 * StaffLayout sidebar renders flush-left without the patron site chrome constraining it.
 */
export const publicStaffShellRoutes: React.ReactElement = (
  <>
      <Route path="emergency-operations" element={withFeature('emergency_services_enabled', withAuth(<EmergencyOperationsDashboardPage />))} />
      <Route path="emergency-operations/status" element={withFeature('emergency_services_enabled', withAuth(<EmergencyOperationsDashboardPage />))} />
      <Route path="emergency-operations/offline-mode" element={withFeature('emergency_services_enabled', withAuth(<EmergencyOperationsOfflineModePage />))} />
      <Route path="emergency-operations/paper-backup" element={withFeature('emergency_services_enabled', withAuth(<EmergencyOperationsPaperBackupPage />))} />
      <Route path="emergency-operations/data-sync" element={withFeature('emergency_services_enabled', withAuth(<EmergencyOperationsDataSyncPage />))} />
      <Route path="emergency-operations/cascades" element={withFeature('emergency_services_enabled', withAuth(<EmergencyOperationsCascadePage />))} />
      <Route path="emergency-operations/closures" element={withFeature('emergency_services_enabled', withAuth(<EmergencyOperationsClosurePage />))} />
      <Route path="emergency-operations/service-priorities" element={withFeature('emergency_services_enabled', withAuth(<EmergencyOperationsServicePriorityPage />))} />
      <Route path="emergency-operations/recovery" element={withFeature('emergency_services_enabled', withAuth(<EmergencyOperationsRecoveryPage />))} />
      <Route path="emergency-operations/insurance" element={withFeature('emergency_services_enabled', withAuth(<EmergencyOperationsInsurancePage />))} />
      <Route path="emergency-operations/assessment" element={withFeature('emergency_services_enabled', withAuth(<EmergencyOperationsAssessmentPage />))} />
      <Route path="emergency-operations/community-hubs" element={withFeature('emergency_services_enabled', withAuth(<EmergencyOperationsCommunityHubPage />))} />
      <Route path="interlibrary-loan" element={withFeature('ill_enabled', withAuth(<InterlibraryLoanPage />))} />
      <Route path="shift-swap" element={withFeature('staff_scheduling_enabled', withAuth(<ShiftSwapBoard />, ['staff', 'admin']))} />
  </>
)

export const publicPlatformShellRoutes: React.ReactElement = (
  <>
      <Route path="for-libraries" element={withPlatform(<ForLibrariesPage />)} />
  </>
)
