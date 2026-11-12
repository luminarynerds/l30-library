/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client';
import type {
  MedicalEmergencyAlert,
  ActiveEmergenciesResponse,
  ResponsePackage,
  TrainedStaff,
  AEDLocation,
  FirstAidKit,
  EmergencyTriggerData,
} from './types';

export const medicalEmergencyApi = {
  triggerEmergency: async (data: EmergencyTriggerData) => {
    return await fetchApi<MedicalEmergencyAlert>('/staff/medical-emergency', {
      method: 'POST',
      body: data,
    });
  },

  callEmergencyServices: async (alertId: number, etaMinutes?: number) => {
    return await fetchApi<MedicalEmergencyAlert>(`/staff/medical-emergency/${alertId}/call-911`, {
      method: 'POST',
      body: { alert_id: alertId, eta_minutes: etaMinutes },
    });
  },

  getResponsePackage: async (alertId: number) => {
    return await fetchApi<ResponsePackage>(`/staff/medical-emergency/${alertId}/response-package`);
  },

  getActiveEmergencies: async (branchId?: number) => {
    const params = new URLSearchParams();
    if (branchId) params.append('branch_id', String(branchId));
    const queryString = params.toString();
    return await fetchApi<ActiveEmergenciesResponse>(`/staff/medical-emergency/active${queryString ? `?${queryString}` : ''}`);
  },

  getTrainedStaff: async (branchId?: number) => {
    const params = new URLSearchParams();
    if (branchId) params.append('branch_id', String(branchId));
    const queryString = params.toString();
    return await fetchApi<TrainedStaff[]>(`/staff/medical-training/staff${queryString ? `?${queryString}` : ''}`);
  },

  getAEDLocations: async (branchId?: number) => {
    const params = new URLSearchParams();
    if (branchId) params.append('branch_id', String(branchId));
    const queryString = params.toString();
    return await fetchApi<AEDLocation[]>(`/staff/aed-locations${queryString ? `?${queryString}` : ''}`);
  },

  getFirstAidKits: async (branchId?: number) => {
    const params = new URLSearchParams();
    if (branchId) params.append('branch_id', String(branchId));
    const queryString = params.toString();
    return await fetchApi<FirstAidKit[]>(`/staff/first-aid-kit-locations${queryString ? `?${queryString}` : ''}`);
  },

  resolveEmergency: async (alertId: number, status: string) => {
    return await fetchApi<MedicalEmergencyAlert>(`/staff/medical-emergency/${alertId}/resolve`, {
      method: 'POST',
      body: { status },
    });
  },

  recordAEDUsage: async (alertId: number, aedLocationId: number) => {
    return await fetchApi<void>(
      `/staff/medical-emergency/${alertId}/record-aed-usage?aed_location_id=${aedLocationId}`,
      { method: 'POST' }
    );
  },
};
