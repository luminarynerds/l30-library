/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export interface MedicalEmergencyAlert {
  id: number;
  emergency_type: string;
  location: string;
  severity: string;
  created_at: string;
  caller_description?: string;
  emergency_services_called: boolean;
}

export interface ActiveEmergenciesResponse {
  total_active: number;
  life_threatening_count: number;
  emergencies: MedicalEmergencyAlert[];
}

export interface ResponsePackage {
  patron_medical_info?: {
    allergies?: string;
    medical_conditions?: string;
    medications?: string;
  };
  nearest_aeds: Array<{
    id: number;
    location_description: string;
    access_instructions?: string;
  }>;
  trained_staff: Array<{
    id: number;
    name: string;
    qualifications: string[];
  }>;
}

export interface TrainedStaff {
  id: number;
  name: string;
  phone?: string;
  qualifications: string[];
}

export interface AEDLocation {
  id: number;
  location_description: string;
  room_number?: string;
  access_instructions?: string;
  visible_signage?: boolean;
  directional_signage?: boolean;
}

export interface FirstAidKit {
  id: number;
  location_description: string;
  room_number?: string;
  kit_type: string;
  access_instructions?: string;
  staff_trained?: boolean;
}

export interface EmergencyTriggerData {
  emergency_type: string;
  location: string;
  patron_id: number | null;
  medical_context: {
    symptoms: string[];
    consciousness_level: string;
    notes?: string;
  };
}
