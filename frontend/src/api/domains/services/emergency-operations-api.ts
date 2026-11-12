/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Emergency Operations API Client
 *
 * Frontend service for managing library emergency operations including
 * offline mode, data synchronization, emergency communications, and recovery procedures.
 */

import { api } from "@/lib/api-client";

// ============ TYPES ============

interface OfflineModeCreate {
  reason: string;
  affected_services: string[];
  affected_branches?: number[] | null;
  recovery_priority?: string;
  estimated_restoration?: string;
}

interface OfflineModeResponse {
  id: number;
  status: string;
  activated_at: string;
  deactivated_at?: string | null;
  reason?: string | null;
  affected_services?: string[] | null;
  affected_branches?: number[] | null;
  estimated_restoration_time?: string | null;
}

interface OfflineModeStatus {
  is_offline: boolean;
  status: string;
  activated_at?: string | null;
  reason?: string | null;
  affected_services?: string[] | null;
  affected_branches?: number[] | null;
  estimated_restoration?: string | null;
  recovery_priority?: string | null;
  pending_sync_items: number;
  paper_submissions_pending: number;
}

interface PaperFormCreate {
  form_type: string;
  form_name: string;
  form_template: string;
  pages_required?: number;
  barcode_required?: boolean;
  signature_required?: boolean;
}

interface PaperSubmissionCreate {
  form_id: number;
  transaction_date: string;
  staff_initials: string;
  form_data: Record<string, unknown>;
  patron_id?: number | null;
  item_barcode?: string | null;
  patron_name?: string | null;
  notes?: string | null;
}

interface PaperSubmissionResponse {
  id: number;
  form_id: number;
  form_type: string;
  transaction_date: string;
  staff_initials: string;
  patron_id?: number | null;
  item_barcode?: string | null;
  synced: boolean;
  synced_at?: string | null;
  sync_resolution?: string | null;
  created_at: string;
}

interface DataSyncItemCreate {
  sync_source: string;
  entity_type: string;
  entity_data: Record<string, unknown>;
  priority?: number;
  entity_id?: string | null;
}

interface DataSyncItemResponse {
  id: number;
  sync_source: string;
  entity_type: string;
  entity_id?: string | null;
  status: string;
  priority: number;
  retry_count: number;
  last_error?: string | null;
  created_at: string;
  processed_at?: string | null;
}

interface SyncStatistics {
  total_items: number;
  pending: number;
  synced: number;
  failed: number;
  pending_percentage: number;
}

interface CascadeCreate {
  cascade_name: string;
  auto_trigger_events: string[];
  message_template: string;
  manual_approval_required?: boolean;
  max_contact_levels?: number;
}

interface CascadeContactCreate {
  level: number;
  contact_role: string;
  contact_name: string;
  contact_email?: string | null;
  contact_phone?: string | null;
  contact_method?: string;
  wait_time_seconds?: number;
  retry_attempts?: number;
}

interface CascadeResponse {
  id: number;
  cascade_name: string;
  cascade_description?: string | null;
  is_active: boolean;
  auto_trigger_events?: string[] | null;
  manual_approval_required: boolean;
  max_contact_levels: number;
  created_at: string;
}

interface CascadeExecutionResponse {
  id: number;
  cascade_id: number;
  trigger_reason: string;
  initiated_at: string;
  completed_at?: string | null;
  total_contacts_to_reach: number;
  total_contacts_reached: number;
  contacts_not_reached: number;
}

interface ClosureCreate {
  closure_reason: string;
  reason_details: string;
  closure_start: string;
  estimated_reopening?: string | null;
  branches_affected?: number[] | null;
  areas_affected?: string[] | null;
  severity_level?: string;
}

interface ClosureResponse {
  id: number;
  closure_reason: string;
  reason_details: string;
  closure_start: string;
  estimated_reopening?: string | null;
  actual_reopening?: string | null;
  is_active: boolean;
  severity_level: string;
  patrons_notified: boolean;
  staff_notified: boolean;
  services_affected?: string[] | null;
  interim_services?: string | null;
  created_at: string;
}

interface ServicePriorityCreate {
  service_name: string;
  service_description?: string | undefined;
  service_category: string;
  priority: string;
  rto_minutes: number;
  rpo_minutes: number;
  max_acceptable_downtime: number;
  manual_workaround?: string | null | undefined;
  required_staff_roles?: string[] | null | undefined;
  critical_forms?: string[] | null | undefined;
}

interface ServicePriorityResponse {
  id: number;
  service_name: string;
  service_description?: string | null;
  service_category: string;
  priority: string;
  rto_minutes: number;
  rpo_minutes: number;
  max_acceptable_downtime: number;
  has_paper_process: boolean;
  has_phone_process: boolean;
  manual_workaround?: string | null;
  estimated_manual_capacity?: string | null;
  required_staff_roles?: string[] | null;
  required_equipment?: string[] | null;
  critical_forms?: string[] | null;
}

interface ProjectCreate {
  project_name: string;
  disaster_type: string;
  disaster_date: string;
  affected_areas: string[];
  estimated_items_affected?: number | null;
  lead_staff_id?: number | null;
}

interface DamagedItemCreate {
  item_barcode: string;
  damage_type: string;
  damage_severity: string;
  damage_description: string;
  title?: string | null;
  author?: string | null;
}

interface ProjectResponse {
  id: number;
  project_name: string;
  project_description?: string | null;
  disaster_type: string;
  disaster_date: string;
  affected_areas: string[];
  estimated_items_affected?: number | null;
  total_items_assessed: number;
  items_salvaged: number;
  items_lost: number;
  is_active: boolean;
  created_at: string;
}

interface RecoveryStatistics {
  total_items: number;
  salvageable: number;
  unsalvageable: number;
  total_repair_cost: number;
  total_replacement_cost: number;
  salvage_rate: number;
}

interface HubCreate {
  hub_name: string;
  branch_id: number;
  location_description: string;
  hub_purposes: string[];
  emergency_types: string[];
  max_capacity: number;
  volunteer_coordinator_id?: number | null;
}

interface HubActivationRequest {
  activation_reason: string;
  activation_message: string;
}

interface HubResponse {
  id: number;
  hub_name: string;
  branch_id: number;
  location_description: string;
  hub_purposes: string[];
  emergency_types: string[];
  max_capacity: number;
  is_active: boolean;
  activated_at?: string | null;
  deactivated_at?: string | null;
  activation_reason?: string | null;
  activation_message?: string | null;
  current_capacity_used: number;
  visitors_served_count: number;
  supplies_stocked: boolean;
  equipment_tested: boolean;
  staff_trained: boolean;
  created_at: string;
}

export interface PaperFormResponse {
  id: number
  form_type: string
  form_name: string
  form_template: string
  pages_required: number
  barcode_required: boolean
  signature_required: boolean
  is_active: boolean
  created_at: string
  updated_at?: string | null
}

export interface CascadeContactResponse {
  id: number
  cascade_id: number
  level: number
  contact_role: string
  contact_name: string
  contact_email?: string | null
  contact_phone?: string | null
  contact_method: string
  wait_time_seconds: number
  retry_attempts: number
  is_active: boolean
  created_at: string
}

export interface DamagedItemResponse {
  id: number
  project_id: number
  item_barcode: string
  damage_type: string
  damage_severity: string
  damage_description: string
  title?: string | null
  author?: string | null
  assessment_status: string
  salvage_decision?: string | null
  repair_cost_estimate?: number | null
  replacement_cost_estimate?: number | null
  assessed_at?: string | null
  created_at: string
}

// ============ OFFLINE MODE API ============

export const offlineModeAPI = {
  async activateOfflineMode(
    data: OfflineModeCreate
  ): Promise<OfflineModeResponse> {
    return api.post("/emergency-operations/offline-mode/activate", data);
  },

  async deactivateOfflineMode(modeId: number): Promise<OfflineModeResponse> {
    return api.post(
      `/emergency-operations/offline-mode/${modeId}/deactivate`,
      {}
    );
  },

  async getOfflineModeStatus(): Promise<OfflineModeStatus> {
    return api.get("/emergency-operations/offline-mode/status");
  },
};

// ============ PAPER BACKUP API ============

export const paperBackupAPI = {
  async createPaperForm(data: PaperFormCreate): Promise<PaperFormResponse> {
    return api.post("/emergency-operations/paper-forms", data);
  },

  async submitPaperForm(
    data: PaperSubmissionCreate
  ): Promise<PaperSubmissionResponse> {
    return api.post("/emergency-operations/paper-submissions", data);
  },

  async getPendingSubmissions(
    formType?: string,
    limit?: number
  ): Promise<PaperSubmissionResponse[]> {
    const params = new URLSearchParams();
    if (formType) params.append("form_type", formType);
    if (limit) params.append("limit", limit.toString());
    return api.get(
      `/emergency-operations/paper-submissions/pending?${params}`
    );
  },
};

// ============ DATA SYNC API ============

export const dataSyncAPI = {
  async queueSyncItem(data: DataSyncItemCreate): Promise<DataSyncItemResponse> {
    return api.post("/emergency-operations/sync-queue", data);
  },

  async getPendingSyncItems(
    entityType?: string,
    limit?: number
  ): Promise<DataSyncItemResponse[]> {
    const params = new URLSearchParams();
    if (entityType) params.append("entity_type", entityType);
    if (limit) params.append("limit", limit.toString());
    return api.get(`/emergency-operations/sync-queue/pending?${params}`);
  },

  async markSyncComplete(itemId: number): Promise<DataSyncItemResponse> {
    return api.post(
      `/emergency-operations/sync-queue/${itemId}/complete`,
      {}
    );
  },

  async getSyncStatistics(): Promise<SyncStatistics> {
    return api.get("/emergency-operations/sync-statistics");
  },
};

// ============ EMERGENCY CONTACT CASCADE API ============

export const emergencyContactAPI = {
  async createCascade(data: CascadeCreate): Promise<CascadeResponse> {
    return api.post("/emergency-operations/cascades", data);
  },

  async addCascadeContact(
    cascadeId: number,
    data: CascadeContactCreate
  ): Promise<CascadeContactResponse> {
    return api.post(
      `/emergency-operations/cascades/${cascadeId}/contacts`,
      data
    );
  },

  async executeCascade(
    cascadeId: number,
    triggerReason: string
  ): Promise<CascadeExecutionResponse> {
    return api.post(
      `/emergency-operations/cascades/${cascadeId}/execute`,
      { trigger_reason: triggerReason }
    );
  },

  async getActiveCascades(): Promise<CascadeResponse[]> {
    return api.get("/emergency-operations/cascades");
  },
};

// ============ BUILDING CLOSURE API ============

export const buildingClosureAPI = {
  async createClosure(data: ClosureCreate): Promise<ClosureResponse> {
    return api.post("/emergency-operations/closures", data);
  },

  async notifyAboutClosure(
    closureId: number,
    message: string
  ): Promise<ClosureResponse> {
    return api.post(
      `/emergency-operations/closures/${closureId}/notify`,
      { message }
    );
  },

  async getActiveClosures(): Promise<ClosureResponse[]> {
    return api.get("/emergency-operations/closures/active");
  },
};

// ============ SERVICE CONTINUITY API ============

export const serviceContinuityAPI = {
  async createServicePriority(
    data: ServicePriorityCreate
  ): Promise<ServicePriorityResponse> {
    return api.post("/emergency-operations/service-priorities", data);
  },

  async getServicesByPriority(
    priority: string
  ): Promise<ServicePriorityResponse[]> {
    return api.get(
      `/emergency-operations/service-priorities/${priority}`
    );
  },
};

// ============ COLLECTION RECOVERY API ============

export const collectionRecoveryAPI = {
  async createProject(data: ProjectCreate): Promise<ProjectResponse> {
    return api.post("/emergency-operations/recovery-projects", data);
  },

  async addDamagedItem(
    projectId: number,
    data: DamagedItemCreate
  ): Promise<DamagedItemResponse> {
    return api.post(
      `/emergency-operations/recovery-projects/${projectId}/damaged-items`,
      data
    );
  },

  async getRecoveryStatistics(
    projectId: number
  ): Promise<RecoveryStatistics> {
    return api.get(
      `/emergency-operations/recovery-projects/${projectId}/statistics`
    );
  },
};

// ============ COMMUNITY RESOURCE HUB API ============

export const communityResourceHubAPI = {
  async createHub(data: HubCreate): Promise<HubResponse> {
    return api.post("/emergency-operations/community-hubs", data);
  },

  async activateHub(
    hubId: number,
    data: HubActivationRequest
  ): Promise<HubResponse> {
    return api.post(
      `/emergency-operations/community-hubs/${hubId}/activate`,
      data
    );
  },

  async deactivateHub(hubId: number): Promise<HubResponse> {
    return api.post(
      `/emergency-operations/community-hubs/${hubId}/deactivate`,
      {}
    );
  },

  async getActiveHubs(): Promise<HubResponse[]> {
    return api.get("/emergency-operations/community-hubs/active");
  },
};

// ============ CONSOLIDATED EXPORT ============

export const emergencyOperationsAPI = {
  offlineMode: offlineModeAPI,
  paperBackup: paperBackupAPI,
  dataSync: dataSyncAPI,
  emergencyContact: emergencyContactAPI,
  buildingClosure: buildingClosureAPI,
  serviceContinuity: serviceContinuityAPI,
  collectionRecovery: collectionRecoveryAPI,
  communityResourceHub: communityResourceHubAPI,
};

export default emergencyOperationsAPI;
