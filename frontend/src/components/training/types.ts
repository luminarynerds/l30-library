/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// Training Skills Types

export type ProficiencyLevel = 'beginner' | 'intermediate' | 'advanced';

export interface Skill {
  id: string;
  name: string;
  description: string;
  category: string;
  proficiency_levels: ProficiencyLevel[];
  assessments_count: number;
  associated_courses: string[];
  created_at: string;
  updated_at: string;
}

export interface SkillCreatePayload {
  name: string;
  description: string;
  category: string;
  proficiency_levels: ProficiencyLevel[];
  course_ids?: string[];
}

export interface SkillUpdatePayload {
  id: string;
  name: string;
  description: string;
  category: string;
  proficiency_levels: ProficiencyLevel[];
  course_ids?: string[];
}

export interface UserSkillProgress {
  user_id: string;
  user_name: string;
  skill_id: string;
  current_proficiency: ProficiencyLevel;
  assessments_passed: number;
  total_assessments: number;
  score: number;
  last_assessed: string | null;
}

export interface SkillAssessmentQuestion {
  id?: string;
  skill_id?: string;
  question: string;
  correct_answer: string;
  explanation: string;
  order?: number;
}
