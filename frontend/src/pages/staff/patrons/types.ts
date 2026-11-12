/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Type definitions for StaffPatronsPage and related components
 */

import {
  Patron,
  PatronCheckout,
  Hold,
  PatronStatistics,
} from "../../../api/api"
import {
  Fine,
  PaymentPlan,
  FineHistoryResponse,
  FineAnalyticsResponse,
  ReceiptData,
  PaymentMethod,
  PaymentPlanFrequency,
  DuplicatePatron,
  MergePreview,
  MergeHistoryResponse,
  MergeAuditDetails,
  LibraryCardData,
  AccountSettings,
  AccountSettingsUpdate,
  MarkDeceasedRequest,
  EstateOutstandingResponse,
  PatronActivity,
  LinkedAccountInfo,
  PatronFamilyResponse,
} from "../../../api/staff-api"
import {
  PatronNote,
  PatronMessage,
  MessageTemplate,
  NoteCategory,
  MessageType,
  MessageChannel,
} from "../../../api/patron-communication-api"
import { BulkOperationResult } from "../../../components/staff"
import { StaffDeletionEligibility } from "../../../api/privacy-api"

export type StatusFilter = "all" | "active" | "blocked"
export type FinesSubTab = "unpaid" | "history" | "payments" | "plan" | "analytics"
export type CommunicationSubTab = "notes" | "messages" | "compose"

export interface PatronDetail extends Patron {
  checkouts?: PatronCheckout[]
  holds?: Hold[]
  fines?: Fine[]
  reading_history?: ReadingHistoryItem[]
}

export interface ReadingHistoryItem {
  id: number
  item_id: number
  item_title: string
  item_author: string | null
  checked_out_at: string
  returned_at: string
}

export interface PatronSearchState {
  searchQuery: string
  statusFilter: StatusFilter
  isSearching: boolean
  patrons: Patron[]
  totalPatrons: number
  currentPage: number
  perPage: number
}

export interface SelectedPatronState {
  selectedPatron: PatronDetail | null
  isLoadingPatron: boolean
  isEditing: boolean
  editForm: Partial<Patron>
  isSaving: boolean
  isTogglingBlock: boolean
}

export interface BulkOperationsState {
  isBulkMode: boolean
  bulkSelectedIds: number[]
  bulkOperationResult: BulkOperationResult | null
}

export interface StatisticsState {
  statistics: PatronStatistics | null
  isLoadingStats: boolean
  isDashboardExpanded: boolean
  activeAlertFilter: "none" | "overdue" | "fines" | "inactive"
}

export interface FinesManagementState {
  finesSubTab: FinesSubTab
  fineHistory: FineHistoryResponse | null
  fineAnalytics: FineAnalyticsResponse | null
  paymentPlan: PaymentPlan | null
  isLoadingFines: boolean
  selectedFineForPayment: Fine | null
  paymentAmount: string
  paymentMethod: PaymentMethod
  paymentNotes: string
  isProcessingPayment: boolean
  lastReceipt: ReceiptData | null
  showReceiptModal: boolean
  showPaymentPlanModal: boolean
  planAmount: string
  planInstallment: string
  planFrequency: PaymentPlanFrequency
  planReminders: boolean
  planNotes: string
  isCreatingPlan: boolean
}

export interface CommunicationState {
  communicationSubTab: CommunicationSubTab
  patronNotes: PatronNote[]
  patronMessages: PatronMessage[]
  messageTemplates: MessageTemplate[]
  isLoadingCommunication: boolean
  isSendingMessage: boolean
  isSavingNote: boolean
  showNoteForm: boolean
  editingNote: PatronNote | null
  noteContent: string
  noteCategory: NoteCategory
  selectedTemplate: MessageTemplate | null
  messageSubject: string
  messageBody: string
  messageChannel: MessageChannel
  messageType: MessageType
  viewingMessage: PatronMessage | null
}

export interface PatronMergeState {
  showDuplicatesModal: boolean
  duplicates: DuplicatePatron[]
  isLoadingDuplicates: boolean
  selectedDuplicate: DuplicatePatron | null
  showMergePreviewModal: boolean
  mergePreview: MergePreview | null
  isLoadingMergePreview: boolean
  isMerging: boolean
  mergeOptions: {
    merge_checkouts: boolean
    merge_holds: boolean
    merge_fines: boolean
    merge_history: boolean
  }
  showMergeHistoryModal: boolean
  mergeHistory: MergeHistoryResponse | null
  isLoadingMergeHistory: boolean
  selectedMergeAudit: MergeAuditDetails | null
  isLoadingAuditDetails: boolean
}

export interface LibraryCardPrintingState {
  showCardPreviewModal: boolean
  libraryCardData: LibraryCardData | null
  isLoadingCardData: boolean
  selectedCardType: "standard" | "youth" | "senior"
  isPrintingCard: boolean
  cardPrintReason: string
  isReplacementCard: boolean
}

export interface EstateManagementState {
  showDeceasedModal: boolean
  isMarkingDeceased: boolean
  deceasedForm: MarkDeceasedRequest
  showEstatePanel: boolean
  estateData: EstateOutstandingResponse | null
  isLoadingEstateData: boolean
  estateContactForm: {
    estate_contact_name: string
    estate_contact_email: string
    estate_contact_phone: string
    notes: string
  }
  isUpdatingEstateContact: boolean
  estateResolutionNotes: string
  isResolvingEstate: boolean
}

export interface AccountSettingsState {
  showSettingsPanel: boolean
  accountSettings: AccountSettings | null
  isLoadingSettings: boolean
  isSavingSettings: boolean
  settingsForm: AccountSettingsUpdate
}

export interface PatronDeletionState {
  showDeletionSection: boolean
  deletionEligibility: StaffDeletionEligibility | null
  deletionEligibilityLoading: boolean
  identityVerified: boolean
  deletionNotes: string
  isInitiatingDeletion: boolean
  isCancellingDeletion: boolean
}

export interface PhotoUploadState {
  isUploadingPhoto: boolean
  photoInputRef: React.RefObject<HTMLInputElement>
}

export interface ActivityTimelineState {
  showActivityTimeline: boolean
  activityHistory: PatronActivity[]
  isLoadingActivity: boolean
  selectedActivity: PatronActivity | null
}

export interface FamilyAccountsState {
  showFamilyPanel: boolean
  familyData: PatronFamilyResponse | null
  isLoadingFamily: boolean
  linkedAccounts: LinkedAccountInfo[]
}
