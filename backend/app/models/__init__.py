# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
# Core library models - all models referenced via SQLAlchemy relationships
from .known_device import KnownDevice
from .api_key import APIKey
# must be imported here so the mapper can resolve string-based references.

from app.core.database import Base
# patron_categories is FK'd from users.patron_category_id (PR #1215). The
# referenced model MUST register on Base.metadata before `User`, or
# SQLAlchemy's create_all in test bootstrap raises NoReferencedTableError.
from .patron_category import PatronCategory
from .user import User, UserRole, RefreshToken
# PatronCategory must be imported before users.patron_category_id FK can
# resolve at metadata-collection time. PR #1215 added the column but missed
# the export here — surfaced as `NoReferencedTableError` in any test that
# creates tables from Base.metadata.
from .patron_category import PatronCategory
from .catalog import CatalogItem, ItemType, ItemStatus, CatalogingStatus
from .catalog_authority import AuthorityTerm, AuthorityTermRelation
from .subject import Subject, CatalogItemSubject
from .multipart import MultiPartSet, MultiPartSetType
from .archival import (
    ArchivalCollection, ArchivalComponent,
    ArchivalLevel, FindingAidStatus,
)
from .event_program_partner import EventProgramPartner
from .event import Event
from .event_registration import EventRegistration, EventRegistrationStatus
from .event_review import EventReview, ReviewModerationStatus
from .event_waitlist import EventWaitlistEntry, WaitlistStatus, ACTIVE_WAITLIST_STATUSES
from .review_response import EventReviewResponse
from .ebook_access_card import (
    EbookAccessCard, EbookCardStatus, EbookCardTier, EbookCardTierConfig
)
from .digital_access import (
    DigitalAccessOrder, DigitalAccessCard,
    OrderStatus, CardStatus,
)
from .overflow_purchase import OverflowPurchase, OverflowPurchaseStatus
from .collectible_card import CollectibleCard, CardEdition
from .circulation import Checkout, Hold, CheckoutStatus, HoldStatus
from .circulation_policy import CirculationPolicy, BookBinding
from .community_resource import CommunityResourceLink
from .z3950_source import Z3950Source
from .fine import Fine, FineStatus, FineType
from .fine_waiver import FineWaiver, FineWaiverStatus
from .homepage_quote import HomepageQuote
from .favorite import Favorite
from .reading_status import ReadingStatus, ShelfStatus
from .reading_progress import ReadingProgress
from .reading_activity import ReadingActivity
from .reading_milestone import ReadingMilestone
from .patron_shelf_preferences import PatronShelfPreferences
from .review import Review
from .reading_list import ReadingList, ListItem
from .inventory import ItemCopy, ConditionChange, InventoryAudit
from .acquisition import Vendor, Fund, PurchaseOrder, PurchaseOrderItem
from .purchase_request import PatronPurchaseRequest, DeclineReasonTemplate, PurchaseRequestStatus, RequestMaterialType
from .donation import DonationRecord, DonationStatus
from .database_subscription import DatabaseSubscription, SUSHICredential
from .edi import VendorEDIProfile
from .equipment import (
    Equipment, EquipmentType, EquipmentStatus, EquipmentCondition, EquipmentCheckout,
    EquipmentAgreement, AgreementStatus, EquipmentMaintenance, EquipmentMaintenanceType,
    EquipmentMaintenanceStatus, EquipmentReservation, EquipmentReservationStatus, EquipmentConditionLog,
    EquipmentAlert
)
from .patron_account import (
    PatronAccount, PatronTransaction,
    TransactionType, TransactionStatus, AccountPaymentMethod
)
from .permission import Permission, RolePermission, RoleSettings
from .emergency_operations import OfflineMode, OfflineModeStatus, PaperBackupForm
from .ebook_checkout_log import EbookCheckoutLog
from .ebook_curation import EbookFeatured, EbookCollection, EbookCollectionItem, CollectionStatus
from .weeding import WeedingCandidate, WeedingRule
from .lifecycle import ItemLifecycleEvent
from .program import Program, ProgramRegistration, LibraryProgramType, ProgramAudience, ProgramStatus, ProgramRegistrationStatus
from .multi_branch import Branch, BranchType, BranchStatus
from .outreach import (
    OutreachPartner, OutreachPartnerContact, OutreachDeposit, DepositApplication,
    OutreachVisit, InstitutionalCard, InstitutionalCheckout,
    BulkCheckout, BulkCheckoutItem, OutreachStatistics,
    OutreachNotificationTemplate, OutreachNotificationLog,
    PartnershipTier,
)
from .bibframe import (
    BibframeWork, BibframeInstance, BibframeItem,
    BibframeContributor, BibframeSubject, AuthorityLink,
)
from .local_authority import LocalAuthority, LocalAuthorityType, LocalAuthorityStatus
from .social_sharing import ShareEvent, ShareableResourceType, SharePlatform, ShareStatistics, SocialSharingConfig
from .genealogy_research import (
    GenealogyResearchProject, GenealogyPerson, FamilyRelationship,
    GenealogyDocument, ResearchNote, TimelineEvent,
    RelationshipType, DocumentType, DocumentStatus
)
from .acquisition import SelectionListItem, SelectionPriority
from .acquisition import (
    OrderTemplate,
    FundStatus,
    PurchaseOrderStatus,
    SelectionSource,
)
from .serial import (
    SerialTitle, SerialPredictionPattern, SerialSubscription,
    SerialIssue, SerialClaimLog,
    PublicationFrequency, SubscriptionRenewalStatus, SerialIssueStatus,
    ClaimType, ClaimResolution,
)
from .marc_batch import MarcBatchJob, MarcBatchJobType, MarcBatchJobStatus
from .marc_macro import MarcMacro, MarcMacroVisibility
from .repair import (
    RepairRecord, RepairType, RepairStatus, VALID_REPAIR_TRANSITIONS,
)
from .announcements import Announcement, AnnouncementPriority, AnnouncementBanner
from .audit_log import AuditLog, AuditAction
from .operations_audit_log import (
    OperationsAuditLog, OperationCategory, OperationType,
    PolicyChangeLog,
)
from .privacy_ledger import (
    ConsentRecord, ConsentType, ConsentMethod, ConsentStatus,
    DataSharingLog, DataSharingPurpose,
    DataCorrectionLog, CorrectionStatus,
)
from .collection import ArchivalLevel, Collection, CollectionItem
from .community import StaffBio
from .room import Room, RoomAmenity
from .signage import (
    SignageDisplay, SignageContent, SignageTemplate,
    SignageSchedule, SignageEmergencyMessage,
    SignageAnalytics, SignageEventPromotion,
    SignageBranchContent, SignageWayfinderNode,
    SignageDisplayType, SignageDisplayStatus,
    SignageContentType, SignageApprovalStatus,
    SignageScheduleType
)
from .shift_swap import (
    ShiftSwapListing, ShiftSwapListingType, ShiftSwapListingStatus,
    ShiftSwapClaim, ShiftSwapClaimStatus,
    StaffPreferenceProfile,
    SwapperReliabilityScore,
    ShiftSwapMatch, SwapMatchStatus,
    ShiftSwapNotification, ShiftSwapNotificationType,
    ShiftSwapAudit,
    ShiftType
)
from .board.member import BoardMember
from .book_club import (
    BookClubKit,
    KitContents,
    KitCheckout,
    GroupHold,
    DiscussionStatus,
    BookClubDiscussion,
    BookClubMemberImport,
    BookClubWaitlistEntry,
)
from .emergency_operations import (
    PaperBackupSubmission,
    DataSyncQueue,
    EmergencyContactCascade,
    OperationContactCascade,
    CascadeExecutionLog,
    CascadeContactNotification,
    BuildingClosure,
    ServiceContinuityPriority,
    CollectionRecoveryProject,
    DamagedItem,
    InsuranceDocumentation,
    PostDisasterAssessment,
    CommunityResourceHub,
    BuildingClosureReason,
    ServicePriority,
    DamageAssessmentStatus,
    DisasterAssessmentPhase,
)
from .end_of_day import (
    EODSession, EODSessionStatus, EODTask, EODTaskStatus,
    EODTemplate, EODSecurityCheck, EODStatistics,
    EODTaskType, SecurityCheckType,
)
from .tech_booking import (
    TechAssistanceStaff, TechAssistanceBooking, TechSessionNote,
    TechFollowUpBooking, TechResourceHandout, TechSkillImpact,
    TechVolunteerTutor,
    TechTopic, SkillLevel, BookingStatus, TechFollowUpStatus,
)
from .tech_support import (
    TechHelpResource, TechClass, TechHelpOption, TechQuickLink, TechFacility,
    TechResourceCategory, TechClassLevel, TechFacilityKind
)
from .gamification import (
    Achievement,
    UserAchievement,
    UserStats,
    LearningLab,
    LabCompletion,
    AchievementCategory,
    LabType,
    Difficulty,
)
from .genealogy_research import (
    ProjectCollaborator,
    PersonDocumentLink,
    RecordLink,
    DNAProfile,
    DNAMatch,
    ResearchGuidanceSuggestion,
    ExternalRecordReference,
    ProjectRole,
    PersonGender,
    TimelineEventType,
    ResearchNoteType,
    RecordLinkStatus,
    DNATestType,
    DNAMatchStatus,
    ResearchGuidanceType,
    ExternalDatabaseSource,
)
from .home_delivery import (
    HomeDeliveryApplication,
    HomeDeliveryEnrollment,
    ReadingPreferenceProfile,
    DeliveryVolunteer,
    VolunteerSchedule,
    VolunteerHourLog,
    DeliveryRoute,
    Delivery,
    DeliveryItem,
    DeliveryFeedback,
    HomeDeliveryItemRequest,
    HomeDeliveryApplicationStatus,
    HomeDeliveryEnrollmentStatus,
    DeliveryFrequency,
    DeliveryVolunteerStatus,
    DeliveryStatus,
    DeliveryItemStatus,
    ReadingFormatPreference,
    RouteStatus,
    DeliveryRequest,
    DeliveryRequestStatus,
)
from .notification import (
    Notification,
    NotificationType,
    NotificationQueue,
    NotificationHistory,
    NotificationPreferences,
    PatronNotification,
    PatronNotificationCategory,
    TrainingAnnouncement,
    TrainingAnnouncementDismissal,
    NotificationStatus,
    TrainingAnnouncementType,
)
from .patron_communication import (
    PatronNote,
    PatronMessage,
    NoteAudit,
    NoteTemplate,
    PatronPreference,
    NoteCategory,
    NotePriority,
    MessageType,
    MessageChannel,
    MessageStatus,
)
from .reading import (
    ReadingProgram,
    ReadingStats,
    ReadingExport,
    ReadingRegistration,
    ReadingLogEntry,
    ReadingAchievement,
    SharedReadingList,
    SharedReadingListItem,
    ReadingListRequest,
    SchoolBadge,
    SchoolBadgeEarned,
    FamilyReadingChallenge,
    FamilyChallengeRegistration,
    TakeHomeReadingBundle,
    BundleDistribution,
    TeacherTrainingModule,
    TrainingCompletion,
    LibraryVisitRequest,
    ReadingAmbassadorCertification,
    LibrarianConsultationSlot,
    ConsultationAttendee,
    ReadingProgramType,
    # Prize/Reward System
    ReadingPrize,
    PrizeRedemption,
    PrizeType,
    RedemptionStatus,
    # Completion Certificates
    CertificateTemplate,
    CompletionCertificate,
    # Leaderboards
    Leaderboard,
    LeaderboardEntry,
    LeaderboardHistory,
    LeaderboardType,
    LeaderboardPeriod,
)
from .sip2 import SIP2Transaction, SIP2Terminal, SIP2CommandType
from .storytime import (
    StorytimeSeries, StorytimeSession, StorytimeAttendance,
    StorytimeTheme, StorytimeBook, StorytimeSong, StorytimeRhyme,
    StorytimeCraft, AgeGroup, StorytimeSessionStatus,
    StorytimeSeriesType, AttendeeType, CraftComplexity
)
from .storytime import (
    RepeatAttendee,
    CraftSupplyInventory,
    CaregiverContact,
    CaregiverCommunication,
    StorytimeSubLeader,
    SubLeaderAssignment,
    StorytimeAnnualPlan,
    StorytimeMonthlyPlan,
    WeatherAlert,
    CommunicationType,
    CommunicationTemplate,
    RepeatAttendeeStatus,
    SubLeaderStatus,
    StorytimeResourceType,
)
from .user import (
    PasswordHistory,
    DeletedEmail,
    NoticePreference,
    AddressStatus,
    PatronStatus,
)
from .volunteer import (
    Volunteer,
    VolunteerApplication,
    VolunteerReference,
    BackgroundCheck,
    TrainingType,
    TrainingRecord,
    AvailabilityPreference,
    VolunteerShift,
    ShiftSignup,
    VolunteerSkill,
    SkillOpportunity,
    SkillMatch,
    GeneralVolunteerHourLog,
    VolunteerMilestone,
    RecognitionAward,
    VolunteerCommunication,
    ReferenceLetter,
    AppreciationRecord,
    VolunteerApplicationStatus,
    VolunteerRoleCategory,
    VolunteerStatus,
    BackgroundCheckStatus,
    TrainingStatus,
    AvailabilityType,
    ShiftSignupStatus,
    HourLogStatus,
    MilestoneType,
    AppreciationType,
)
from .manga_cataloging import MangaCatalogingTemplate, MangaVolumeRecord
from .ai_config import AIConfiguration
from .learning import (
    Course, Module, Lesson, LessonResource, LessonVariant, QuizQuestion,
    Enrollment, LessonProgress, UserPreferences, Certificate, QuizAttempt,
    Skill, UserSkill, RoleRequiredSkill, SkillAssessmentQuestion,
    ExternalResource, ExternalResourceEnrollment, CourseFeedback,
    # Enums
    AccessLevel, LessonType, ProgressStatus, FocusMode, Difficulty, LearningResourceType,
    SkillCategory, LearningFeedbackType, LearningFeedbackStatus
)
from .learning_path import (
    LearningPath, PathCourse, PathEnrollment,
    # Enums
    PathStatus, EnrollmentStatus
)
from .legal import (
    LegalTopic, LegalGuide, LegalForm, LegalFormPacket, LegalFormPacketItem,
    LegalServiceProvider, LegalClinic, LegalClinicRegistration,
    LegalGlossaryTerm, EmergencyResource, CourtLocation,
    KnowYourRightsGuide, LegalContentFeedback, LegalStaffGuideline,
    LegalCollection, DeadlineRule, DeadlineCalculation,
    FormCompletionSession, FormFinderWizardSession, FormFinderQuestion,
    FeeWaiverEligibility, ExpungementEligibility, ComplianceRequirement,
    LegalSearchLog, LegalContentAuditLog, LegalResourceStatistics,
    LegalFormLinkCheck, FormFinderRule, LegalCatalogLink,
)
from .legal_compliance import (
    LegalDocument, DocumentVersion, LegalComplianceRequirement,
    ComplianceDocumentLink, ComplianceChecklistItem, DocumentReviewCycle,
    DocumentReview, DocumentAuditLog, ComplianceDashboardMetric,
    ComplianceAlert, RegulatoryChange, PolicyEnforcementTracking,
    # Enums
    LegalDocumentType, DocumentCategory, LegalDocumentStatus,
    ComplianceStatus, RequirementType, ReviewFrequency, ReviewStatus,
    LegalAlertSeverity, AlertStatus, LegalChangeType,
    EnforcementAction, AuditEventType
)
from .legal_clinic_notify import LegalClinicNotify  # noqa: F401
from .learning_platform_enhanced import (
    # Phase 1: Progress Tracking
    Milestone, UserMilestone, LearningObjective,
    # Phase 2: Engagement Features
    LearningStreak, StudySession, ProgressCheckpoint, UserCheckpoint,
    # Phase 3: Assessments & Recognition
    Assessment, AssessmentQuestion, AssessmentAttempt, Badge, UserBadge,
    # Phase 4: Personalization & Recommendations
    CourseRecommendation, LearningPathRecommendation, UserInterest,
    # Phase 5: Analytics & Reporting
    PlatformMetric, CourseAnalytics, UserLearningReport, EngagementEvent,
    # Enums
    LearningMilestoneType, ObjectiveStatus, CheckpointType, AssessmentType, QuestionType,
    BadgeType, BadgeRarity, RecommendationType, RecommendationSource, InterestLevel,
    MetricType, AnalyticsPeriod, EventType
)
from .engagement import (
    Survey, SurveyQuestion, SurveyResponse, UserDemographics, SurveyOutcome,
    SurveyPlacement, SurveyQuestionType, SurveyResponseStatus,
)
from .strategic import (
    # Core models
    StrategicPlan, StrategicGoal, StrategicMilestone, StrategicComment,
    StrategicNotification, StrategicAttachment, StrategicMetric,
    StrategicMetricHistory, StrategicGoalTemplate, StrategicAuditLog,
    # Phase 1: Strategic Initiatives
    StrategicInitiative, InitiativeMilestone, BoardDecisionLink,
    # Phase 2: KPIs
    StrategicKPI, KPIValue, KPIDashboard, KPIAlert,
    # Phase 3: Budgets
    StrategicBudget, BudgetItem, BudgetAllocation, BudgetTransaction,
    # Phase 4: Risks
    StrategicRisk, RiskAssessment, RiskMitigationStrategy, RiskReview,
    # Phase 5: Executive Dashboards
    ExecutiveDashboard, DashboardWidget, ExecutiveReport, ReportSchedule,
    # Enums
    PlanStatus, GoalStatus, InitiativeStatus, RiskLevel, RiskStatus,
    KPIFrequency, StrategicAlertSeverity, BudgetStatus, BudgetTransactionType, ReportFrequency
)
from .print import (
    # Models
    PrintJob, Printer, PrintReleaseStation, PrintPricing, PrintQuota,
    PrintRefund, ScanToEmail, PrinterAlert,
    # Enums
    PrintJobStatus, ColorMode, PaperSize, PrinterStatus,
    ScanToEmailStatus, PrintRefundStatus
)
from .perfectionism_antidotes import (
    # Models
    PerfectionismAntidote, UserAntidote, CoachingSession,
    ProgressMilestone, DailyReminder, ManagerCoachingModel,
    # Enums
    AntidoteType, SessionStatus, AdoptionStatus
)
from .immigrant_services import (
    # Core Models
    CitizenshipResource, ESLClass, ESLEnrollment,
    ConversationCircle, ConversationCircleSession, ConversationCircleParticipant,
    CulturalProgram, CulturalProgramRegistration,
    TranslationService, TranslationRequest,
    CommunityLiaisonContact,
    MultilingualResource,
    WelcomePacket, WelcomePacketAssembly, WelcomePacketDistribution,
    PartnerOrganization,
    ImpactStory,
    # Enums
    ResourceCategory, ESLLevel, ClassScheduleStatus, CircleType,
    ProgramType, TranslationServiceType, TranslationStatus, ContactRole,
    PacketType, ImpactStoryStatus, PartnerStatus
)
from .household import HouseholdLink, HouseholdLinkStatus
from .positivity import PositivityEntry, PositivityEntryType, PositivitySource, ModerationStatus
from .staff_message_board import BoardPost, BoardReply, MessageBoardCategory
from .notification_failure import (
    FailedNotificationRecord,
    NotificationMetrics,
    NotificationChannel,
    NotificationFailureStatus,
)
from .notification_preference import UserNotificationPreference
from .job_failure import (
    FailedJobRecord,
    JobExecutionLog,
    JobAlertThreshold,
    FailedJobStatus,
    JobSeverity,
)
from .book_challenge import (
    BookChallenge,
    BookChallengeNote,
    IntellectualFreedomResource,
    ChallengeStatus,
    ChallengeOutcome,
    ChallengeReason,
)
from .panic_alert import (
    PanicAlert,
    PanicAlertHistory,
    PanicAlertNotificationPreferences,
    PanicAlertStatus,
    PanicAlertSource,
)
from .journey_instrumentation import (
    JourneyEvent,
    JourneyMetrics,
    JourneyDropOff,
    JourneyAlert,
    JOURNEY_TYPES,
)
from .attendance import (
    AttendanceSession,
    AttendanceCheckIn,
    AttendanceTrend,
    CheckInMethod,
    AgeRange,
    AttendanceSessionStatus,
    SurveyStatus,
)
from .interlibrary_loan import (
    PartnerLibrary,
    ILLRequest,
    ILLTrackingUpdate,
    ILLCostRecord,
    ILLRequestStatus,
    ILLRequestType,
    PartnerLibraryStatus,
    ShippingMethod,
    ILLCostCategory,
)
from .system_status import (
    SystemStatusLog, SystemHealthMetrics, SystemStatus, IssueComponent,
    StaffNotificationType, PaperBackupType, StaffStatusNotification,
    PaperBackupProcedure, OfflineModeSession, AutoSaveEntry,
)
from .lost_damaged import (
    LostItemRecord, DamagedItemRecord, LostItemStatus, LostItemType,
    DamagedItemStatus, DamageSeverity, ClaimDisputeStatus,
    ClaimsReturnedDispute, MendingQueue, LostDamagedSettings,
)
from .release_tracker import (
    TrackerAuthor, TrackerBook, UserFollow,
    AgeRating, ReleaseStatus, ProfileType,
)
from .support_ticket import SupportTicket, SupportTicketStatus, SupportTicketContactMethod
from .knowledge_base import (
    KnowledgeEntry, KnowledgeContentFlag, FAQChatbotConversation,
    FAQPattern, FAQAnalytics, StaffQA, PatronChatbotContext,
    ArticleBookmark, ArticleVersion,
)
from .knowledge_version import KnowledgeVersion
from .patron_training_opt_out import PatronTrainingOptOut
from .training_example import TrainingExample
from .makerspace import (
    MakerspaceResource, MakerspaceReservation, MakerspaceWorkshop,
    WorkshopRegistration, MakerspaceCertificationType,
    MakerspaceCertification, MakerspaceJob, MakerspaceEquipmentMaintenance,
    MakerspacePayment, MakerspaceWaitlist,
    ConsumableItem, ConsumableUsage,
    SafetyIncident,
)
from .program_planning import (
    ProgramTemplate,
    TemplateBudgetItem,
    TemplateSupplyItem,
    TemplateMarketingMilestone,
    ProgramPlan,
    ProgramBudgetItem,
    ProgramSupplyItem,
    ProgramRoomBooking,
    ProgramEquipmentBooking,
    ProgramMarketingMilestone,
    ProgramVolunteerAssignment,
    ProgramEvaluation,
    TemplateCategory,
    BudgetItemCategory,
    SupplyItemStatus,
    VenueBookingStatus,
    MarketingMilestoneType,
    VolunteerAssignmentStatus,
    EvaluationRating,
)
# --- Previously unregistered models (registered for schema sync) ---
from .partner_collaboration import (
    SharedEvent, ResourceSharingRequest, CoSponsoredProgram, ProgramSession,
    PartnerContactDirectory, PartnershipMeeting, PartnershipAgreement,
    AgreementAmendment, JointGrantOpportunity, PartnerImpactReport,
    ImpactMetric, PartnerRecognition, ThankYouMessage,
    SharedEventType, SharedEventStatus, ResourceRequestType, ResourceRequestStatus,
    CoSponsoredProgramStatus, MeetingType, MOUStatus, GrantOpportunityStatus,
    ImpactMetricType, RecognitionType as CollabRecognitionType,
)
from .compliance_tracking import (
    ADACompliance, CIPACompliance, COPPACompliance,
    PCICompliance, StateLibraryRequirement, InsurancePolicy, LiabilityIncident,
    SafetyInspection, StaffCertification, PolicyReview,
    AuditReadinessChecklist, ComplianceDeadlineAlert,
    StateComplianceStatus as TrackingComplianceStatus, ADAStatus, CIPAStatus, COPPAStatus,
    PCIStatus, StateComplianceStatus, InsuranceType, SafetyInspectionType,
    CertificationType, PolicyReviewStatus, AuditItemStatus,
)
from .teen_volunteer import (
    TeenVolunteer, ParentGuardianConsent, TeenVolunteerHourLog, TeenVolunteerTask,
    SchoolVerificationLetter, MentorshipPairing, CollegeApplicationSupport,
    TeenAdvisoryBoardMember, TeenAchievement, SummerReadingHelperAssignment,
    TeenVolunteerStatus, TeenConsentStatus, TaskDifficulty,
    TaskType, MentorshipStatus, AchievementType, SchoolVerificationLetterStatus,
)
from .state_compliance import (
    StateComplianceConfig, StateConfidentialityException, StateReportTemplate,
    LocalComplianceConfig, RegulationMonitor, RegulationAlert,
    VPATReport, VPATCriterion, ComplianceDashboardConfig,
    ConfidentialityStrength, RegulationMonitoringSource, RegulationChangeStatus,
    VPATConformanceLevel, ComplianceDashboardWidget,
)
from .professional_judgment import (
    PolicyOverride, StaffCommittee, StaffCommitteeMember, StaffProject,
    PolicyFeedback, StaffExpertise, ExpertiseRecognition,
    ProfessionalDevelopmentPlan, ProfessionalDevelopmentActivity,
    OverrideCategory, OverrideStatus, ExceptionOutcome, CommitteeStatus,
    CommitteeMemberRole, MembershipStatus, ProjectStatus, PolicyFeedbackType,
    PolicyFeedbackStatus, ExpertiseLevel, DevelopmentCategory,
    DevelopmentActivityType, ProfessionalRecognitionType,
)
from .comic_cataloging import (
    ComicSeries, ComicIssue, VariantCover, ComicIssueCreator,
    StoryArc, ComicPublisherImprint, ComicContentAdvisory,
    ReadingOrderEvent, ReadingOrderEventIssue,
    ComicFormat, ComicContentWarning, VariantCoverType,
)
from .emergency_routing import (
    BuildingStatusLog, EmergencyIncident, EmergencyContact,
    OnCallSchedule, EmergencyNotification, IncidentFollowUp,
    SystemSecurityCheck,
    BuildingStatus, IncidentType, IncidentSeverity, ResponseType, ContactType,
    FollowUpStatus as IncidentTechFollowUpStatus,
)
from .threat_response import (
    ThreatAlert, StaffCheckIn, EvacuationRoute, RallyPoint,
    EvacuationEvent, ReunificationEvent, MediaResponseProtocol,
    AllClearAnnouncement, ThreatResponsePlan,
    ThreatLevel, ThreatType,
)
from .publisher_data import (
    Publisher, MangaMagazine, MangaSerialization, PublisherSeries, MangaMetadata,
    PublisherType, PublisherRegion, OutOfPrintStatus, ContentRatingSystem,
)
from .security_integration import (
    SecuritySystem, CameraSystem, CameraRecording, DoorLock, DoorLockEvent,
    AlarmSystemIntegration, EmergencyLight, PASystem, HVACControl,
    VisitorManagement, SecuritySystemLog, SecurityIntegrationLog,
    SystemType, IntegrationStatus,
)
from .cipa_compliance import (
    InternetPolicyAcceptance, FilterBypassRequest, ComputerSession, CIPAComplianceReport,
    PolicyType, BypassReason, BypassStatus, ComputerSessionStatus,
)
from .embeddings import (
    TextEmbedding, AuthorEmbedding, HiddenGemScore, EmbeddingMetadata, SemanticSearchCache,
    EmbeddingEntityType, SearchType, EmbeddingStatus,
)
from .library_document import LibraryDocument, LibraryDocumentChunk, LibraryDocumentType
from .print_notice import (
    PrintNotice, PrintNoticeBatch, PrintNoticeCostConfig, PrintNoticeHistory,
    PrintNoticeType, PrintNoticeStatus, PrintNoticeBatchStatus,
)
from .patron_boundaries import (
    PatronBoundary, OutOfScopeRequest, BoundaryTemplate, BoundaryPolicy,
    UnreasonableDemandLog, BoundaryEscalation,
    BoundaryType, BoundaryStatus, AppealStatus, EscalationLevel,
)
from .link_health import (
    LinkHealthCheck, LinkHealthSummary, LinkHealthConfig, LinkHealthAlert,
    LinkStatus, LinkSource,
)
from .monitoring import (
    PrivacyAlert, ModerationAlert, AlertThreshold, SystemHealth,
    MonitoringAlertSeverity, PrivacyChangeType,
)
from .signage_advanced import (
    SignageWeatherTrigger, SignageWeatherData, SignageOccupancySensor,
    SignageOccupancyTrigger, SignageContentOptimization,
    WeatherCondition, OccupancyLevel,
)
from .gutenberg import (
    GutenbergBook, GutenbergDownload, GutenbergFavorite, GutenbergSyncStatus,
    GutenbergFormat, GutenbergBookshelf,
)
from .open_library import (
    OpenLibraryBook, OpenLibraryDownload, OpenLibraryFavorite, OpenLibrarySyncStatus,
)
from .standard_ebooks import (
    StandardEbook, StandardEbookDownload, StandardEbookFavorite, StandardEbookSyncStatus,
)
from .librivox import (
    LibriVoxBookType, LibriVoxAudiobook, LibriVoxListen, LibriVoxFavorite, LibriVoxSyncStatus,
)
from .feedbooks import (
    FeedbooksBook, FeedbooksDownload, FeedbooksFavorite, FeedbooksSyncStatus,
)
from .manybooks import (
    ManyBooksBook, ManyBooksDownload, ManyBooksFavorite, ManyBooksSyncStatus,
)
from .patron_activity import PatronActivity, PatronActivityType
from .patron_onboarding import (
    PatronOnboardingProgress, OnboardingAnalyticsEvent,
    ReadingGoal,  # Note: this is the Enum, not the DB model
)
from .parent_onboarding import (
    ParentOnboardingSession, CareCoordinatorAssignment, CareCoordinatorCheckIn,
    ParentResourceGuideSection, ParentResourceGuideItem,
    ChildcareSession, ChildcareRegistration,
    ParentConnectionGroup, ParentConnectionGroupMember,
    ServiceEnrollmentFacilitation, ParentHomeVisit,
    HomeVisitAccessNotes, HomeVisitGeocodeCache,
    ParentOnboardingStatus, CareAssignmentStatus, CheckInFrequency,
    RiskLevel, CareCheckInType, ChildcareSessionStatus,
    ChildcareRegistrationStatus, ConnectionGroupType, GroupMemberStatus,
    MeetingFrequency, EnrollmentFacilitationStatus, HomeVisitPurpose,
    HomeVisitStatus,
    # Session follow-ups + referrals (feat/session-followup-referrals):
    ParentOnboardingFollowup, ParentOnboardingReferral, PartnerAgency,
    FollowupStatus, FollowupPriority, ReferralStatus,
    # Session resource handouts (feat/session-catalog-handout):
    ResourceHandout, ParentOnboardingSessionHandout,
    SessionHandoutDeliveryMethod,
    # Resource guide verification trail
    # (feat/parent-resources-verification-trail). Registered here so
    # parent_resource_guide_items.verified_by_id FK target is in metadata
    # and create_all picks it up in tests (feedback_l30_models_init_fk_target_missing).
    ParentResourceGuideFlag,
    ResourceGuideFlagStatus, ResourceGuideFlagReason, ResourceGuideFlagResolution,
)
# Weekly summary export audit log. Registering with Base.metadata so the
# table is picked up by test conftest's Base.metadata.create_all and by
# `alembic check` against this branch's migration.
from .parent_onboarding_export_log import ParentOnboardingExportLog  # noqa: F401
# PR #1215 added PatronCategory + users.patron_category_id FK but didn't
# register the class with Base.metadata via this __init__. Without that
# registration, `alembic check`, `Base.metadata.create_all`, and the
# test conftest all raise NoReferencedTableError on the FK. One-line fix:
from .patron_category import PatronCategory
# PIIAccessLog lives in app.core.pii_audit (re-exported via
# app.models.pii_access_log) but isn't imported anywhere that triggers
# Base.metadata registration -- which means tests that exercise the
# granular pii_access_log write path (like the home-visit day plan and
# the staff support triage routes) fail with "no such table" in SQLite.
# Importing it here ensures it lands in Base.metadata at app start.
from .pii_access_log import PIIAccessLog
from .reading_goal import ReadingGoal as ReadingGoalModel  # DB model for yearly targets
from .generated_content import ContentType, GeneratedContent
from .collection_alert import (
    CollectionAlert, AlertType,
    CollectionAlertSeverity,
    CollectionAlertStatus,
)
from .cohort import (
    Cohort, CohortMember, CohortTraining,
    CohortMemberRole, CohortMemberStatus,
)
from .end_of_shift import (
    ShiftChecklistSession, ChecklistItem, DailyWin, ChecklistTemplate,
    ChecklistCategory, ChecklistItemStatus,
)
from .staff_presence import StaffPresence, PresenceStatus
from .staff_time_entry import StaffTimeEntry, TimeEntryType
from .staff_pay_rate import StaffPayRate
from .joy_capture import (
    BrightSpot, PatronThankYou, JoyJarEntry,
    JoyVisibility, MoodType, JoyMomentType,
)
from .organization_features import OrganizationFeatures
from .recent_search import RecentSearch
from .search_analytics import SearchClickLog, SearchQueryLog

# --- Batch registration: 44 previously unregistered model files ---

# Group A — No cross-file dependencies
from .ai_agents import (
    LibraryAgent, AgentConversation, AgentKnowledgeBase, AgentAnalytics,
    AgentDepartment, AgentPersonality,
)
from .ai_tools import AITool
from .ai_guardrails import AIGuardrail, AIModelAllowlist, AIUsageLimit, AIUsageLog
from .annual_report import (
    AnnualReport, AnnualReportValidationRule, AnnualReportHistory,
    ReportStatus as AnnualReportStatus,
)
from .board_audit_log import BoardAuditLog, BoardAuditAction
from .card_application import LibraryCardApplication, CardApplicationStatus
from .computer import (
    Computer, ComputerReservation,
    # ComputerSession skipped — same table as cipa_compliance.ComputerSession
    ComputerWaitlist, GuestPass, SessionExtensionRequest,
    ComputerUsageStats, ComputerSystemLog,
    ComputerType, ComputerStatus,
    ComputerReservationStatus,
    ComputerWaitlistStatus, ExtensionStatus,
)
from .content_flag import ContentFlag, FlagAnalysisResult, FlagType, FlagStatus
from .emergency_alert import (
    MedicalEmergencyAlert, StaffMedicalTraining, PatronMedicalInfo,
    AEDLocation, FirstAidKitLocation,
    EmergencyAlertType, EmergencyAlertSeverity, EmergencyAlertStatus,
)
from .event_marketing import (
    EventMarketingCampaign, EventDistribution, SocialMediaConfig,
    EventFlyer, EventGraphic, EventRegistrationSource, EventFeedback,
    DistributionChannel, DistributionStatus, CalendarProvider,
    FlyerSize, GraphicFormat, ArchiveStatus,
)
from .fair_scheduling import (
    ScheduleGeneration, ScheduleExplanation, LearnedPreference,
    StaffFatigueRecord, CalloutCoverageRequest, PayrollRecord,
    PayrollExportBatch, PayrollPolicy, StaffSchedulingProfile,
    ScheduleGenerationStatus, ScheduleExplanationType, FatigueLevel,
    CalloutStatus, CalloutUrgency, PayrollExportStatus, EmploymentType,
)
from .focus_time import (
    FocusTimeBlock, FocusTimeApproval, FocusTimeOverride,
    FocusTimeTracking, FocusTimeSettings,
    FocusTimeStatus, FocusWorkType,
    ApprovalStatus as FocusApprovalStatus,
    OverrideReason,
)
from .found_items import (
    FoundItem, FoundItemPhoto, FoundItemStorageLocation,
    FoundItemMatch, FoundItemClaimVerification,
    FoundItemStatus, MatchConfidenceLevel, ClaimVerificationStatus, DisposalMethod,
)
from .genealogy import (
    GenealogyInquiry, GenealogyTrainingCourse,
    CourseEnrollment as GenealogyEnrollment,
    CommunityArchiveSubmission,
    ResearchTopics, CourseLevel,
)
from .import_job import (
    ImportJob, ImportRecord,
    ImportJobType, ImportJobStatus, ImportFileFormat,
    DuplicateAction, ImportRecordStatus,
)
from .migration_job import (
    MigrationJob,
    MigrationJobStatus, MigrationSourceSystem,
)
from .migration_project import (
    MigrationProject, MigrationProjectPhase,
    MigrationPhase, MigrationPhaseStatus,
    MigrationProjectStatus, CutoverStrategy,
)
from .law_enforcement_request import (
    LawEnforcementRequest, LawEnforcementAuditLog,
    LawEnforcementChecklist, LawEnforcementResponseTemplate,
    RequestType as LERequestType, LegalReviewStatus,
    WorkflowStatus as LEWorkflowStatus,
    ChecklistItemType as LEChecklistItemType,
    AuditActionType as LEAuditActionType,
)
from .marketing import (
    NewsletterSubscription, InterestCategory, SubscriberInterest,
    NewArrivalAlert, EmailUnsubscribeToken,
    MarketingCampaign, CampaignRecipient,
    NewsletterFrequency, SubscriptionStatus, UnsubscribeReason,
    MarketingConsentSource, MailchimpSyncStatus,
)
from .onboarding import (
    StaffOnboarding, PreArrivalChecklistItem, OrientationSchedule,
    TrainingModule as OnboardingTrainingModule,
    TrainingModuleAssignment, Policy, PolicyAcknowledgment,
    SystemAccess, SystemAccessProvisioning, CheckInMeeting,
    IntroductionAnnouncement, OnboardingFeedback,
    OnboardingStatus,
    OnboardingChecklistItemStatus,
    TrainingModuleStatus, SystemAccessStatus, CheckInPeriod,
    ProbationStatus, FeedbackType as OnboardingFeedbackType,
)
from .patron_merge_audit import PatronMergeAudit
from .patron_segmentation import (
    Tag, PatronTag, PatronGroup, PatronGroupMember, TagColor,
)
from .pto import (
    PTORequest, PTOApproval, PTOBalance, PTOReminder,
    PTOVacationCelebration, PTORecurrence, PTOCoverage,
    PTOConflict, PTOStatusHistory,
    PTORequestStatus, PTOType, PartialDayType,
)
from .public_records_request import (
    PublicRecordsRequest, PublicRecordsAuditLog, PublicRecordsRedaction,
    PublicRecordsRequestType, PublicRecordsRequestStatus,
    ExemptionType, JurisdictionType, PublicRecordsAuditAction,
)
from .rfid import (
    RFIDReader, RFIDTag, RFIDSession, RFIDScan,
    SecurityAlert as RFIDSecurityAlert,
    RFIDReaderType, RFIDReaderStatus, RFIDProtocol,
    RFIDSessionType, SecurityAlertType as RFIDSecurityAlertType,
)
from .rubric import Rubric, RubricCriterion, RubricAssessment
from .series_management import (
    SeriesReadingOrder, PatronReadingHistory, SeriesCompletion,
    SeriesWaitlist, SeriesRecommendation, SeriesNotificationRule,
    SeriesPopularity,
    SeriesType, NotificationTrigger,
    WaitlistStatus as SeriesWaitlistStatus,
    RecommendationReason,
)
from .shelf_reading import (
    ShelfReadingSession, ShelfReadingScan, ShelfReadingSchedule,
    ShelfReadingStatus, ScanResult, ScheduleFrequency,
)
from .sms import (
    SMSQueue, SMSDeliveryLog, SMSCostRecord, SMSTemplate,
    SMSOptOut, DoNotDisturbHours, PhoneVerification,
    SMSDeliveryStatus, SMSNotificationType,
)
from .staff_picks import StaffPicksList, StaffPicksItem
from .staff_shelves import StaffShelf, ShelfAudience
from .curated_recommendations import CuratedRecommendation
from .staff_safety import (
    StaffPanicAlert, StaffIncidentReport, AnonymousIncidentPattern,
    RetaliationPreventionPolicy, StaffProtectionMeasure,
    StaffSupportResource, DataRetentionPolicy,
    StaffPanicAlertStatus,
    SafetyIncidentType,
    SafetyIncidentSeverity,
    IncidentStatus as SafetyIncidentStatus,
    AnonymityLevel,
)
from .staff_schedule_fairness import (
    StaffShift, ShiftPreference, FairnessPolicy,
    PolicyException, ShiftConstraintViolation, ScheduleBalanceMetrics,
    FairnessShiftType,
    ShiftStatus as FairnessShiftStatus,
    PreferenceType, FairnessPolicyType, ViolationType,
)
from .streaming import (
    StreamingServiceConfig, StreamingBudget, PatronStreamingLimit,
    StreamingCatalogItem, StreamingCheckout, StreamingUsageStats,
    DefaultPatronStreamingLimit,
    StreamingService, StreamingContentType,
    StreamingCheckoutStatus,
)
from .task_batching import (
    TaskBatchSuggestion, BatchProcessingSession,
    TaskBatchType, BatchSuggestReason, TaskPriorityLevel,
)
from .unified_compliance_audit import (
    UnifiedComplianceRequirement, ImmutableAuditEntry,
    ComplianceViolation, RetentionPolicyRule, ComplianceIncident,
    StaffAccessLog, ComplianceReport,
    RegulationType, RequirementStatus as ComplianceRequirementStatus,
    VerificationMethod, ViolationSeverity, ViolationStatus,
    RetentionAction,
    ComplianceIncidentSeverity,
    IncidentStatus as ComplianceIncidentStatus,
    IncidentCategory,
    AccessType, DataCategory,
    ReportType as ComplianceReportType,
    ReportStatus as ComplianceReportStatus,
)
from .usage_statistics import (
    CirculationStatistics, CollectionStatistics, PatronStatistics,
    ProgramStatistics, ComputerUsageStatistics,
    ReferenceQuestion, ReferenceStatistics,
    VisitCount, VisitStatistics,
    PeerComparisonLibrary, PeerComparisonData,
    StatisticalReport, UsageStatisticsSettings,
    PeriodType, ContactMethod, CountSource,
    QuestionType as ReferenceQuestionType,
    ReportType as UsageReportType,
    ReportStatus as UsageReportStatus,
)
from .version_history import (
    VersionHistory,
    EntityType as VersionEntityType,
    ChangeType as VersionChangeType,
)
from .work_relationships import (
    WorkRelationship, CrossFormatDiscovery, FormatSuggestion,
    RelationshipType as WorkRelationshipType,
    RelationshipDirection,
)
from .workflows import (
    Workflow, WorkflowStep, WorkflowExecution,
    TriggerType, StepType, ActionType,
    ExecutionStatus, StepResultStatus,
)

# Group B — Literacy module cluster (internal cross-deps)
from .literacy_tutor import (
    TutorProfile, LiteracyTutorQualification,
    LiteracyTutorTrainingRecord, LiteracyTutorAvailability,
    TutorStatus, QualificationType, TrainingTopic,
)
from .literacy_learner import (
    LiteracyLearner, LiteracyAssessmentRecord, LiteracyGoal,
    LiteracyMilestone, LiteracyCelebration, LiteracyProgress,
    LiteracyLearnerStatus,
    AssessmentType as LiteracyAssessmentType,
    LearnerAssessmentLevel,
    GoalType as LiteracyGoalType,
    GoalStatus as LiteracyGoalStatus,
)
from .literacy_matching import (
    LiteracyTutorMatch, LiteracySessionSchedule,
    LiteracySessionLog, LiteracySessionNotes,
    MatchStatus as LiteracyMatchStatus,
    MatchReason,
    LiteracySessionStatus,
    AttendanceStatus as LiteracyAttendanceStatus,
)
from .literacy_outcomes import (
    LiteracyOutcome, LiteracyProgramOutcomeMetrics,
    LiteracyCohort, LiteracyLearnerCohort,
    OutcomeType, OutcomeCategory, ReportingPeriod,
)
from .literacy_resources import (
    LiteracyResource, LiteracyResourceRecommendation,
    LiteracyCollection, LiteracyCollectionItem,
    ResourceTheme as LiteracyResourceType,
    ResourceFormat, AssessmentLevel, ResourceTheme,
)
from .literacy_confidentiality import (
    LiteracyAuditLog, LiteracyConsentRecord,
    LiteracyConfidentialityMask, LiteracyDataAccessPolicy,
    LiteracyAccessRequest,
    LiteracyAuditAction,
    LiteracyConsentType,
    LiteracyConsentStatus,
)

from .ban_tracker import BanReport, BanAlertNotification, AdvocacyLetterTemplate, BanType, BanSource
from .cash_drawer import (
    CashDrawer, CashDrawerSession, CashTransaction,
    DrawerMode, CashSessionStatus,
    TransactionDirection, TransactionCategory,
)

# Demo Sandbox
from .demo_tenant import DemoTenant, LibrarySize

# Group C — Cross-file dependencies (sip2 already registered above)
from .watermark_record import WatermarkRecord
from .pod_order import PodOrder, PodTitleConfig, PodOrderStatus
from .dmca import DmcaNotice, DmcaCounterNotice, DmcaStrike, DmcaAuditLog, DmcaNoticeStatus
from .identity_evidence import AuthorIdentityEvidence, EvidenceType, EvidenceStatus
from .download_event import DownloadEvent, DownloadAnomaly, AnomalyType, AnomalyStatus
from .homepage_content import HomepageQuickLink, LibraryHours, LibraryHoursOverride
from .page_meta_tag import PageMetaTag
from .mood_category import MoodCategory

from .book_drop import (
    BookDrop, SIP2Device, CheckInSession, CheckInResult,
    CheckInStatistic, CheckInException,
    BookDropStatus, BackdateMode, CheckInSessionStatus,
    CheckInResultStatus, ExceptionType,
    SIP2DeviceStatus, SortDestination,
)
from .catalog_state_event import CatalogStateEvent

from .availability_watch import AvailabilityWatch
from .catalog_demand_signal import CatalogDemandSignal, DemandSignalType, DemandSignalResolution
from .shelf_note import ShelfNote, ShelfNoteCategory

__all__ = [
    'AvailabilityWatch',
    'CatalogDemandSignal',
    'DemandSignalType',
    'DemandSignalResolution',
    'ShelfNote',
    'ShelfNoteCategory',
    # Base
    'Base',
    # User and Auth
    'User', 'UserRole', 'RefreshToken',
    'PasswordHistory',
    'DeletedEmail',
    'NoticePreference',
    'AddressStatus',
    'PatronStatus',
    # Catalog
    'CatalogItem', 'ItemType', 'ItemStatus', 'CatalogingStatus',
    'AuthorityTerm', 'AuthorityTermRelation',
    # Events
    'Event', 'EventRegistration', 'EventRegistrationStatus', 'EventReview', 'ReviewModerationStatus', 'EventReviewResponse',
    # Circulation
    'Checkout', 'Hold', 'CheckoutStatus', 'HoldStatus',
    # Fines
    'Fine', 'FineStatus', 'FineType',
    'FineWaiver', 'FineWaiverStatus',
    # Reading Progress & Shelf Dashboard
    'ReadingProgress',
    'ReadingActivity',
    'ReadingMilestone',
    'PatronShelfPreferences',
    # Favorites and Reading Lists
    'Favorite', 'ReadingList', 'ListItem',
    # Inventory
    'ItemCopy', 'ConditionChange', 'InventoryAudit',
    # Acquisitions
    'Vendor', 'Fund', 'PurchaseOrder', 'PurchaseOrderItem', 'VendorEDIProfile',
    'DatabaseSubscription',
    'OrderTemplate',
    'FundStatus',
    'PurchaseOrderStatus',
    'SelectionSource',
    # Equipment
    'Equipment', 'EquipmentType', 'EquipmentStatus', 'EquipmentCondition',
    'EquipmentCheckout', 'EquipmentAgreement', 'AgreementStatus',
    'EquipmentMaintenance', 'EquipmentMaintenanceType', 'EquipmentMaintenanceStatus',
    'EquipmentReservation', 'EquipmentReservationStatus', 'EquipmentConditionLog',
    'EquipmentAlert',
    # Patron Account & Billing
    'PatronAccount', 'PatronTransaction',
    'TransactionType', 'TransactionStatus', 'AccountPaymentMethod',
    # Permissions
    'Permission', 'RolePermission', 'RoleSettings',
    # Emergency Operations
    'OfflineMode', 'OfflineModeStatus', 'PaperBackupForm',
    'PaperBackupSubmission',
    'DataSyncQueue',
    'EmergencyContactCascade',
    'OperationContactCascade',
    'CascadeExecutionLog',
    'CascadeContactNotification',
    'BuildingClosure',
    'ServiceContinuityPriority',
    'CollectionRecoveryProject',
    'DamagedItem',
    'InsuranceDocumentation',
    'PostDisasterAssessment',
    'CommunityResourceHub',
    'BuildingClosureReason',
    'ServicePriority',
    'DamageAssessmentStatus',
    'DisasterAssessmentPhase',
    # Weeding
    'WeedingCandidate',
    # Lifecycle
    'ItemLifecycleEvent',
    # Programs
    'Program', 'ProgramRegistration', 'LibraryProgramType', 'ProgramAudience', 'ProgramStatus', 'ProgramRegistrationStatus',
    # Multi-Branch
    'Branch', 'BranchType', 'BranchStatus',
    # Outreach
    'OutreachPartner', 'BulkCheckout', 'PartnershipTier',
    # Digital Access Cards (Indie Vault)
    'DigitalAccessOrder', 'DigitalAccessCard',
    'OrderStatus', 'CardStatus',
    # Social Sharing
    'ShareEvent', 'ShareableResourceType', 'SharePlatform', 'ShareStatistics', 'SocialSharingConfig',
    # Genealogy Research
    'GenealogyResearchProject', 'GenealogyPerson', 'FamilyRelationship',
    'GenealogyDocument', 'ResearchNote', 'TimelineEvent',
    'RelationshipType', 'DocumentType', 'DocumentStatus',
    'ProjectCollaborator',
    'PersonDocumentLink',
    'RecordLink',
    'DNAProfile',
    'DNAMatch',
    'ResearchGuidanceSuggestion',
    'ExternalRecordReference',
    'ProjectRole',
    'PersonGender',
    'TimelineEventType',
    'ResearchNoteType',
    'RecordLinkStatus',
    'DNATestType',
    'DNAMatchStatus',
    'ResearchGuidanceType',
    'ExternalDatabaseSource',
    # Acquisition Selection
    'SelectionListItem', 'SelectionPriority',
    # Storytime
    'StorytimeSeries', 'StorytimeSession', 'StorytimeAttendance',
    'StorytimeTheme', 'StorytimeBook', 'StorytimeSong', 'StorytimeRhyme',
    'StorytimeCraft', 'AgeGroup', 'StorytimeSessionStatus',
    'StorytimeSeriesType', 'AttendeeType', 'CraftComplexity',
    'RepeatAttendee',
    'CraftSupplyInventory',
    'CaregiverContact',
    'CaregiverCommunication',
    'StorytimeSubLeader',
    'SubLeaderAssignment',
    'StorytimeAnnualPlan',
    'StorytimeMonthlyPlan',
    'WeatherAlert',
    'CommunicationType',
    'CommunicationTemplate',
    'RepeatAttendeeStatus',
    'SubLeaderStatus',
    'ResourceType',
    # Manga Cataloging
    'MangaCatalogingTemplate', 'MangaVolumeRecord',
    # AI Configuration
    'AIConfiguration',
    # Announcements
    'Announcement',
    'AnnouncementBanner',
    'AnnouncementPriority',
    # Audit Log
    'AuditLog',
    'AuditAction',
    # Operations Audit
    'OperationsAuditLog', 'OperationCategory', 'OperationType',
    'PolicyChangeLog',
    # Collections
    'Collection',
    'CollectionItem',
    'ArchivalLevel',
    # Community
    'StaffBio',
    # Rooms
    'Room',
    'RoomAmenity',
    # Signage
    'SignageDisplay',
    'SignageContent',
    'SignageTemplate',
    'SignageSchedule',
    'SignageEmergencyMessage',
    'SignageAnalytics',
    'SignageEventPromotion',
    'SignageBranchContent',
    'SignageWayfinderNode',
    'SignageDisplayType',
    'SignageDisplayStatus',
    'SignageContentType',
    'SignageApprovalStatus',
    'SignageScheduleType',
    # Shift Swap
    'ShiftSwapListing',
    'ShiftSwapListingType',
    'ShiftSwapListingStatus',
    'ShiftSwapClaim',
    'ShiftSwapClaimStatus',
    'StaffPreferenceProfile',
    'SwapperReliabilityScore',
    'ShiftSwapMatch',
    'SwapMatchStatus',
    'ShiftSwapNotification',
    'NotificationType',
    'ShiftSwapAudit',
    'ShiftType',
    # Board
    'BoardMember',
    # Book Club
    'BookClubKit',
    'KitContents',
    'KitCheckout',
    'GroupHold',
    'DiscussionStatus',
    'BookClubMemberImport',
    'BookClubWaitlistEntry',
    # Gamification
    'Achievement',
    'UserAchievement',
    'UserStats',
    'LearningLab',
    'LabCompletion',
    'AchievementCategory',
    'LabType',
    'Difficulty',
    # HomeDelivery
    'HomeDeliveryApplication',
    'HomeDeliveryEnrollment',
    'ReadingPreferenceProfile',
    'DeliveryVolunteer',
    'VolunteerSchedule',
    'VolunteerHourLog',
    'DeliveryRoute',
    'Delivery',
    'DeliveryItem',
    'DeliveryFeedback',
    'HomeDeliveryItemRequest',
    'HomeDeliveryApplicationStatus',
    'HomeDeliveryEnrollmentStatus',
    'DeliveryFrequency',
    'VolunteerStatus',
    'DeliveryStatus',
    'DeliveryItemStatus',
    'ReadingFormatPreference',
    'RouteStatus',
    # Notification
    'Notification',
    'NotificationType',
    'NotificationQueue',
    'NotificationHistory',
    'NotificationPreferences',
    'PatronNotification',
    'PatronNotificationCategory',
    'TrainingAnnouncement',
    'TrainingAnnouncementDismissal',
    'NotificationStatus',
    'TrainingAnnouncementType',
    # Patron Communication
    'PatronNote',
    'PatronMessage',
    'NoteAudit',
    'NoteTemplate',
    'PatronPreference',
    'NoteCategory',
    'NotePriority',
    'MessageType',
    'MessageChannel',
    'MessageStatus',
    # Reading
    'ReadingProgram',
    'ReadingStats',
    'ReadingExport',
    'ReadingRegistration',
    'ReadingLogEntry',
    'ReadingAchievement',
    'SharedReadingList',
    'SharedReadingListItem',
    'ReadingListRequest',
    'SchoolBadge',
    'SchoolBadgeEarned',
    'FamilyReadingChallenge',
    'FamilyChallengeRegistration',
    'TakeHomeReadingBundle',
    'BundleDistribution',
    'TeacherTrainingModule',
    'TrainingCompletion',
    'LibraryVisitRequest',
    'ReadingAmbassadorCertification',
    'LibrarianConsultationSlot',
    'ConsultationAttendee',
    'ReadingProgramType',
    # Prize/Reward System
    'ReadingPrize',
    'PrizeRedemption',
    'PrizeType',
    'RedemptionStatus',
    # Completion Certificates
    'CertificateTemplate',
    'CompletionCertificate',
    # Leaderboards
    'Leaderboard',
    'LeaderboardEntry',
    'LeaderboardHistory',
    'LeaderboardType',
    'LeaderboardPeriod',
    # Sip2
    'SIP2Transaction',
    'SIP2Terminal',
    'SIP2CommandType',
    # Volunteer
    'Volunteer',
    'VolunteerApplication',
    'VolunteerReference',
    'BackgroundCheck',
    'TrainingType',
    'TrainingRecord',
    'AvailabilityPreference',
    'VolunteerShift',
    'ShiftSignup',
    'VolunteerSkill',
    'SkillOpportunity',
    'SkillMatch',
    'GeneralVolunteerHourLog',
    'VolunteerMilestone',
    'RecognitionAward',
    'VolunteerCommunication',
    'ReferenceLetter',
    'AppreciationRecord',
    'VolunteerApplicationStatus',
    'VolunteerRoleCategory',
    'VolunteerStatus',
    'BackgroundCheckStatus',
    'TrainingStatus',
    'AvailabilityType',
    'ShiftSignupStatus',
    'HourLogStatus',
    'MilestoneType',
    'AppreciationType',
    # Learning Center - Courses
    'Course', 'Module', 'Lesson', 'LessonResource', 'LessonVariant', 'QuizQuestion',
    'Enrollment', 'LessonProgress', 'UserPreferences', 'Certificate', 'QuizAttempt',
    'AccessLevel', 'LessonType', 'ProgressStatus', 'FocusMode', 'Difficulty', 'ResourceType',
    # Learning Center - Skills
    'Skill', 'UserSkill', 'RoleRequiredSkill', 'SkillAssessmentQuestion',
    'SkillCategory',
    # Learning Center - External Resources
    'ExternalResource', 'ExternalResourceEnrollment',
    # Learning Paths
    'LearningPath', 'PathCourse', 'PathEnrollment',
    'PathStatus', 'EnrollmentStatus',
    # Learning Platform Enhanced - Phase 1
    'Milestone', 'UserMilestone', 'LearningObjective',
    # Learning Platform Enhanced - Phase 2
    'LearningStreak', 'StudySession', 'ProgressCheckpoint', 'UserCheckpoint',
    # Learning Platform Enhanced - Phase 3
    'Assessment', 'AssessmentQuestion', 'AssessmentAttempt', 'Badge', 'UserBadge',
    # Learning Platform Enhanced - Phase 4
    'CourseRecommendation', 'LearningPathRecommendation', 'UserInterest',
    # Learning Platform Enhanced - Phase 5
    'PlatformMetric', 'CourseAnalytics', 'UserLearningReport', 'EngagementEvent',
    # Learning Platform Enhanced - Enums
    'LearningMilestoneType', 'ObjectiveStatus', 'CheckpointType', 'AssessmentType', 'QuestionType',
    'BadgeType', 'BadgeRarity', 'RecommendationType', 'RecommendationSource', 'InterestLevel',
    'MetricType', 'AnalyticsPeriod', 'EventType',
    # Engagement Surveys
    'Survey', 'SurveyQuestion', 'SurveyResponse', 'UserDemographics', 'SurveyOutcome',
    'SurveyPlacement', 'SurveyQuestionType', 'SurveyResponseStatus',
    # Strategic Leadership - Core
    'StrategicPlan', 'StrategicGoal', 'StrategicMilestone', 'StrategicComment',
    'StrategicNotification', 'StrategicAttachment', 'StrategicMetric',
    'StrategicMetricHistory', 'StrategicGoalTemplate', 'StrategicAuditLog',
    # Strategic Leadership - Phase 1
    'StrategicInitiative', 'InitiativeMilestone', 'BoardDecisionLink',
    # Strategic Leadership - Phase 2
    'StrategicKPI', 'KPIValue', 'KPIDashboard', 'KPIAlert',
    # Strategic Leadership - Phase 3
    'StrategicBudget', 'BudgetItem', 'BudgetAllocation', 'BudgetTransaction',
    # Strategic Leadership - Phase 4
    'StrategicRisk', 'RiskAssessment', 'RiskMitigationStrategy', 'RiskReview',
    # Strategic Leadership - Phase 5
    'ExecutiveDashboard', 'DashboardWidget', 'ExecutiveReport', 'ReportSchedule',
    # Strategic Leadership - Enums
    'PlanStatus', 'GoalStatus', 'InitiativeStatus', 'RiskLevel', 'RiskStatus',
    'KPIFrequency', 'StrategicAlertSeverity', 'BudgetStatus', 'BudgetTransactionType', 'ReportFrequency',
    # Legal Compliance
    'LegalDocument', 'DocumentVersion', 'LegalComplianceRequirement',
    'ComplianceDocumentLink', 'ComplianceChecklistItem', 'DocumentReviewCycle',
    'DocumentReview', 'DocumentAuditLog', 'ComplianceDashboardMetric',
    'ComplianceAlert', 'RegulatoryChange', 'PolicyEnforcementTracking',
    # Legal Compliance - Enums
    'LegalDocumentType', 'DocumentCategory', 'LegalDocumentStatus',
    'ComplianceStatus', 'RequirementType', 'ReviewFrequency', 'ReviewStatus',
    'LegalAlertSeverity', 'AlertStatus', 'LegalChangeType',
    'EnforcementAction', 'AuditEventType',
    # Print Management - Models
    'PrintJob', 'Printer', 'PrintReleaseStation', 'PrintPricing', 'PrintQuota',
    'PrintRefund', 'ScanToEmail', 'PrinterAlert',
    # Print Management - Enums
    'PrintJobStatus', 'ColorMode', 'PaperSize', 'PrinterStatus',
    'ScanToEmailStatus', 'PrintRefundStatus',
    # Perfectionism Antidotes - Models
    'PerfectionismAntidote', 'UserAntidote', 'CoachingSession',
    'ProgressMilestone', 'DailyReminder', 'ManagerCoachingModel',
    # Perfectionism Antidotes - Enums
    'AntidoteType', 'SessionStatus', 'AdoptionStatus',
    # Immigrant Services - Core Models
    'CitizenshipResource', 'ESLClass', 'ESLEnrollment',
    'ConversationCircle', 'ConversationCircleSession', 'ConversationCircleParticipant',
    'CulturalProgram', 'CulturalProgramRegistration',
    'TranslationService', 'TranslationRequest',
    'CommunityLiaisonContact',
    'MultilingualResource',
    'WelcomePacket', 'WelcomePacketAssembly', 'WelcomePacketDistribution',
    'PartnerOrganization',
    'ImpactStory',
    # Immigrant Services - Enums
    'ResourceCategory', 'ESLLevel', 'ClassScheduleStatus', 'CircleType',
    'ProgramType', 'TranslationServiceType', 'TranslationStatus', 'ContactRole',
    'PacketType', 'ImpactStoryStatus', 'PartnerStatus',
    # Staff Message Board
    'BoardPost', 'BoardReply', 'MessageBoardCategory',
    # Staff Positivity
    'PositivityEntry', 'PositivityEntryType', 'PositivitySource', 'ModerationStatus',
    # Notification Failure Tracking
    'FailedNotificationRecord', 'NotificationMetrics',
    'NotificationChannel', 'NotificationFailureStatus',
    # Job Failure Tracking
    'FailedJobRecord', 'JobExecutionLog', 'JobAlertThreshold',
    'FailedJobStatus', 'JobSeverity',
    # Book Challenges & Intellectual Freedom
    'BookChallenge', 'BookChallengeNote', 'IntellectualFreedomResource',
    'ChallengeStatus', 'ChallengeOutcome', 'ChallengeReason',
    # Free Ebook Sources
    'OpenLibraryBook', 'OpenLibraryDownload', 'OpenLibraryFavorite', 'OpenLibrarySyncStatus',
    'StandardEbook', 'StandardEbookDownload', 'StandardEbookFavorite', 'StandardEbookSyncStatus',
    'LibriVoxBookType', 'LibriVoxAudiobook', 'LibriVoxListen', 'LibriVoxFavorite', 'LibriVoxSyncStatus',
    'FeedbooksBook', 'FeedbooksDownload', 'FeedbooksFavorite', 'FeedbooksSyncStatus',
    'ManyBooksBook', 'ManyBooksDownload', 'ManyBooksFavorite', 'ManyBooksSyncStatus',
    # Panic Alerts
    'PanicAlert', 'PanicAlertHistory', 'PanicAlertNotificationPreferences',
    'PanicAlertStatus', 'PanicAlertSource',
    # Journey Instrumentation Analytics
    'JourneyEvent', 'JourneyMetrics', 'JourneyDropOff', 'JourneyAlert',
    'JOURNEY_TYPES',
    # Attendance Tracking
    'AttendanceSession', 'AttendanceCheckIn', 'AttendanceTrend',
    'CheckInMethod', 'AgeRange', 'AttendanceSessionStatus', 'SurveyStatus',
    # Interlibrary Loan
    'PartnerLibrary', 'ILLRequest', 'ILLTrackingUpdate', 'ILLCostRecord',
    'ILLRequestStatus', 'ILLRequestType', 'PartnerLibraryStatus',
    'ShippingMethod', 'ILLCostCategory',
    # System Status Monitoring
    'SystemStatusLog', 'SystemHealthMetrics', 'SystemStatus', 'IssueComponent',
    'StaffNotificationType', 'PaperBackupType', 'StaffStatusNotification',
    'PaperBackupProcedure', 'OfflineModeSession', 'AutoSaveEntry',
    # Lost and Damaged Items
    'LostItemRecord', 'DamagedItemRecord', 'LostItemStatus', 'LostItemType',
    'DamagedItemStatus', 'DamageSeverity', 'ClaimDisputeStatus',
    'ClaimsReturnedDispute', 'MendingQueue', 'LostDamagedSettings',
    # Release Tracker
    'TrackerAuthor', 'TrackerBook', 'UserFollow',
    'AgeRating', 'ReleaseStatus', 'ProfileType',
    # Program Planning Tools
    'ProgramTemplate', 'TemplateBudgetItem', 'TemplateSupplyItem',
    'TemplateMarketingMilestone', 'ProgramPlan', 'ProgramBudgetItem',
    'ProgramSupplyItem', 'ProgramRoomBooking', 'ProgramEquipmentBooking',
    'ProgramMarketingMilestone', 'ProgramVolunteerAssignment',
    'ProgramEvaluation', 'TemplateCategory', 'BudgetItemCategory',
    'SupplyItemStatus', 'VenueBookingStatus', 'MarketingMilestoneType',
    'VolunteerAssignmentStatus', 'EvaluationRating',
    # Ban Tracker & Advocacy Hub
    'BanReport', 'BanAlertNotification', 'AdvocacyLetterTemplate', 'BanType', 'BanSource',
    # Cash Drawer
    'CashDrawer', 'CashDrawerSession', 'CashTransaction',
    'DrawerMode', 'CashSessionStatus', 'TransactionDirection', 'TransactionCategory',
    # Community Resources
    'CommunityResourceLink',
]

from .session import ModuleSession, SessionRSVP  # noqa: F401

from .blog import BlogPost, BlogPostStatus, BlogPostTag, BlogPostVersion, BlogPostView, BlogTag
from .blog_bookmark import BlogPostBookmark  # noqa: F401
from .blog_subscription import BlogEmailSubscription  # noqa: F401

from .home import HomeHeroPick, HomeShelf, HomePageConfig, HomeShelfQueryKind  # noqa: F401

from .indie_bookmark import IndieBookmark  # noqa: F401
from .indie_reading_list import IndieReadingList, IndieReadingListItem  # noqa: F401

from .indie_author import IndieAuthor  # noqa: F401
from .indie_author_follow import IndieAuthorFollow  # noqa: F401
from .indie_author_release_notification import IndieAuthorReleaseNotification  # noqa: F401

from .indie_ebook_borrow import IndieEbook, IndieEbookBorrow, IndieEbookWaitlist, BorrowStatus  # noqa: F401
from .indie_reading_progress import IndieReadingProgress  # noqa: F401
from .royalty_transaction import RoyaltyTransaction, RoyaltyTransactionStatus  # noqa: F401

from .carbon_metrics import CarbonMetric  # noqa: F401

from .offline_sync import OfflineSyncSession, ProcessedOfflineOp  # noqa: F401

from .report_audit import ReportGenerationLog  # noqa: F401

from .report_schedule import UnifiedReportSchedule  # noqa: F401
from .learning_path_waitlist import LearningPathWaitlist  # noqa: F401
from .learning_path_cohort import (  # noqa: F401
    LearningPathCohortMember,
    LearningPathDiscussionPost,
)

from .indie_content_preference import IndieContentPreference  # noqa: F401

from .program_family import ProgramFamilyGroup, ProgramFamilyMember, AgeRange  # noqa: F401

from .reading import EventReadingProgramCredit  # noqa: F401

from .acquisition_rationale import (  # noqa: F401
    BehaviorTag,
    AcquisitionRationale,
    SignalType,
    WeedingCondition,
)

from .user_hub import UserHubFavorite, UserHubVisit  # noqa: F401

from .impact import OutcomeIndicator, TheoryOfChangeClaim  # noqa: F401

# Patron consent records (family-snapshot pane, future expansion).
# Imported here so ``Base.metadata.create_all`` in test bootstrap sees
# the table -- see ``feedback_l30_models_init_fk_target_missing``.
from .patron_consent import PatronConsent  # noqa: F401

# Patron waiting-list signups (invite-only /register flow).
from .waitlist import WaitlistSignup  # noqa: F401

# Legal clinic email opt-ins (PII: encrypted at rest, row deleted after send).
from .legal_clinic_notify import LegalClinicNotify  # noqa: F401

# Singleton library identity/branding row (GET /branding, demo seeder). Was
# never imported here, so Base.metadata never saw it and no fresh install
# ever created the table -- app/api/v1/branding.py's GET /branding 500'd on
# every fresh install with "relation library_branding does not exist"
# (found while verifying Task 5's demo seeder end-to-end).
from .library_branding import LibraryBranding  # noqa: F401
