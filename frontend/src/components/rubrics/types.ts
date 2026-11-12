/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// Rubric Types

export interface RubricCriterion {
  id: number;
  rubric_id: number;
  name: string;
  description?: string;
  levels: Record<string, string[]>;  // e.g., {"4": ["bullet 1", "bullet 2"], "3": ["..."], ...}
  weight: number;
  sort_order: number;
}

export interface Rubric {
  id: number;
  title: string;
  description?: string;
  source_url?: string;
  source_attribution?: string;
  max_score: number;
  min_score: number;
  level_labels: Record<string, string>;  // e.g., {"4": "Excellent", "3": "Good", ...}
  category?: string;
  tags: string[];
  access_level: 'patron' | 'staff' | 'admin';
  is_published: boolean;
  is_featured: boolean;
  course_id?: number;
  lesson_id?: number;
  created_by_id?: number;
  created_at: string;
  updated_at?: string;
  criteria?: RubricCriterion[];
  criteria_count?: number;
}

export interface RubricAssessment {
  id: number;
  rubric_id: number;
  user_id: number;
  target_identifier: string;
  target_description?: string;
  scores: Record<string, number>;  // criterion_id: score
  notes: Record<string, string>;   // criterion_id: note
  overall_notes?: string;
  total_score?: number;
  max_possible_score?: number;
  percentage?: number;
  is_complete: boolean;
  completed_at?: string;
  created_at: string;
  updated_at?: string;
  rubric?: Rubric;
}

export interface RubricCreatePayload {
  title: string;
  description?: string;
  source_url?: string;
  source_attribution?: string;
  max_score?: number;
  min_score?: number;
  level_labels?: Record<string, string>;
  category?: string;
  tags?: string[];
  access_level?: string;
  criteria?: RubricCriterionCreatePayload[];
}

export interface RubricCriterionCreatePayload {
  name: string;
  description?: string;
  levels: Record<string, string[]>;
  weight?: number;
  sort_order?: number;
}

export interface RubricAssessmentCreatePayload {
  rubric_id: number;
  target_identifier: string;
  target_description?: string;
  scores?: Record<string, number>;
  notes?: Record<string, string>;
  overall_notes?: string;
}

export interface RubricAssessmentUpdatePayload {
  target_identifier?: string;
  target_description?: string;
  scores?: Record<string, number>;
  notes?: Record<string, string>;
  overall_notes?: string;
  is_complete?: boolean;
}

export interface RubricUsageStats {
  rubric_id: number;
  rubric_title: string;
  total_assessments: number;
  completed_assessments: number;
  average_score?: number;
  average_percentage?: number;
}
