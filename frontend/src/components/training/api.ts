/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// Training Skills API

import { fetchApi } from '@/api/fetchApi';
import type {
  Skill,
  SkillCreatePayload,
  SkillUpdatePayload,
  UserSkillProgress,
  SkillAssessmentQuestion
} from './types';

const TRAINING_PREFIX = '/training';
const LEARNING_PREFIX = '/learning';

export const skillsApi = {
  async listSkills(filters?: { category?: string; search?: string }): Promise<Skill[]> {
    const params = new URLSearchParams();
    if (filters?.category) params.append('category', filters.category);
    if (filters?.search) params.append('search', filters.search);
    const query = params.toString();
    return fetchApi(`${TRAINING_PREFIX}/skills${query ? `?${query}` : ''}`);
  },

  async getSkill(id: string): Promise<Skill> {
    return fetchApi(`${TRAINING_PREFIX}/skills/${id}`);
  },

  async createSkill(payload: SkillCreatePayload): Promise<Skill> {
    return fetchApi(`${TRAINING_PREFIX}/skills`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async updateSkill(id: string, payload: Partial<SkillUpdatePayload>): Promise<Skill> {
    return fetchApi(`${TRAINING_PREFIX}/skills/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  },

  async deleteSkill(id: string): Promise<void> {
    await fetchApi(`${TRAINING_PREFIX}/skills/${id}`, { method: 'DELETE' });
  },

  async getUserProgress(skillId: string): Promise<UserSkillProgress[]> {
    return fetchApi(`${TRAINING_PREFIX}/skills/${skillId}/users`);
  },

  async getQuestions(skillId: string): Promise<SkillAssessmentQuestion[]> {
    return fetchApi(`${TRAINING_PREFIX}/skills/${skillId}/questions`);
  },

  async addQuestion(skillId: string, question: SkillAssessmentQuestion): Promise<SkillAssessmentQuestion> {
    return fetchApi(`${TRAINING_PREFIX}/skills/${skillId}/questions`, {
      method: 'POST',
      body: JSON.stringify(question),
    });
  },

  async deleteQuestion(skillId: string, questionId: string): Promise<void> {
    await fetchApi(`${TRAINING_PREFIX}/skills/${skillId}/questions/${questionId}`, { method: 'DELETE' });
  },

  async reorderQuestions(skillId: string, orderMap: Record<string, number>): Promise<void> {
    await fetchApi(`${TRAINING_PREFIX}/skills/${skillId}/questions/reorder`, {
      method: 'POST',
      body: JSON.stringify(orderMap),
    });
  },
};

// Learning Course API Types

export interface SkillBrief {
  id: number;
  name: string;
  /** 1–5 scale; rendered as "L3" in the chip and "Level taught: 3" in lists. */
  level_taught: number;
}

export interface CourseBrief {
  id: number;
  title: string;
  level_taught: number;
}

export interface Course {
  id: number;
  title: string;
  description: string | null;
  thumbnail_url: string | null;
  access_level: 'patron' | 'staff' | 'admin';
  is_published: boolean;
  estimated_minutes: number | null;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  xp_reward: number;
  /** Days a learner has to complete after enrollment; null = no deadline. */
  duration_days: number | null;
  /**
   * Wave 5: skills this course builds. Always present on responses; empty
   * when no associations exist yet (so chip renderers can no-op safely).
   */
  skills: SkillBrief[];
}

export interface Module {
  id: number;
  course_id: number;
  title: string;
  description: string | null;
  sort_order: number;
  lessons: Lesson[];
}

export interface Lesson {
  id: number;
  module_id: number;
  title: string;
  lesson_type: string;
  content: Record<string, unknown>;
  estimated_minutes: number | null;
  xp_reward: number;
  sort_order: number;
}

export interface Enrollment {
  enrolled_at: string;
  completed_at: string | null;
  /** Configured deadline; null = no deadline. */
  due_at: string | null;
  /**
   * Wave 4: required vs recommended split. True when a manager assigned
   * the training; false (the column default) for self-enrolled rows.
   * Drives the Required / Recommended split in the staff trainings table.
   */
  is_required: boolean;
  /** User id of the manager who assigned, or null for self-enroll. */
  assigned_by_id: number | null;
}

export interface CourseProgress {
  course: Course;
  progress_percentage: number;
  completed_lessons: number;
  total_lessons: number;
  enrollment: Enrollment;
}

export interface AssignCourseRequest {
  user_id: number;
  course_id: number;
  /** ISO 8601 string. Omit to fall back to course.duration_days. */
  due_at?: string | null;
  is_required?: boolean;
}

export interface EnrollmentResponse {
  id: number;
  user_id: number;
  course_id: number;
  enrolled_at: string;
  completed_at: string | null;
  due_at: string | null;
  is_required: boolean;
  assigned_by_id: number | null;
}

export interface UserStats {
  total_xp: number;
  current_streak: number;
  longest_streak: number;
  lessons_completed: number;
  courses_completed: number;
  labs_completed: number;
  level: number;
}

export interface CertificateSummary {
  id: number;
  user_id: number;
  course_id: number;
  certificate_number: string;
  issued_at: string;
  course_title: string;
}

export interface MyCertCountResponse {
  count: number;
}

export interface MySkillsSummaryResponse {
  skills_covered: number;
}

export interface CourseListItem {
  id: number;
  title: string;
  description: string | null;
  thumbnail_url: string | null;
  access_level: 'patron' | 'staff' | 'admin';
  is_published: boolean;
  estimated_minutes: number | null;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  module_count: number;
  lesson_count: number;
  /** Days a learner has to complete after enrollment; null = no deadline. */
  duration_days: number | null;
  /** Wave 5: skills this course builds (chip strip on the trainings table). */
  skills: SkillBrief[];
}

export interface TeamMemberProgress {
  user_id: number;
  /** Display name; full name if set, email fallback. */
  name: string;
  email: string;
  courses_total: number;
  courses_completed: number;
  overdue_count: number;
  /** Open enrollments due within 7 days. */
  due_soon_count: number;
  /** Percentage 0–100. */
  completion_rate: number;
}

export const learningApi = {
  async getMyCourses(): Promise<CourseProgress[]> {
    return fetchApi(`${LEARNING_PREFIX}/my-courses`);
  },

  async getCourse(id: number): Promise<{ course: Course; modules: Module[] }> {
    return fetchApi(`${LEARNING_PREFIX}/courses/${id}`);
  },

  async getLesson(id: number): Promise<Lesson> {
    return fetchApi(`${LEARNING_PREFIX}/lessons/${id}`);
  },

  async completeLesson(id: number): Promise<{ xp_earned: number }> {
    return fetchApi(`${LEARNING_PREFIX}/lessons/${id}/complete`, { method: 'POST' });
  },

  async getMyStats(): Promise<UserStats> {
    return fetchApi(`${LEARNING_PREFIX}/gamification/stats`);
  },

  async getAchievements(): Promise<Array<{ id: number; slug: string; name: string; description: string; icon: string; xp_value: number; earned_at?: string; category?: string }>> {
    return fetchApi(`${LEARNING_PREFIX}/gamification/my-achievements`);
  },

  async getAllAchievements(): Promise<Array<{ id: number; slug: string; name: string; description: string; icon: string; xp_value: number; category: string }>> {
    return fetchApi(`${LEARNING_PREFIX}/gamification/achievements`);
  },

  async getAllCourses(): Promise<CourseListItem[]> {
    return fetchApi(`${LEARNING_PREFIX}/courses`);
  },

  async enrollInCourse(courseId: number): Promise<{ message: string; enrollment_id: number }> {
    return fetchApi(`${LEARNING_PREFIX}/courses/${courseId}/enroll`, { method: 'POST' });
  },

  async getMyCertCount(): Promise<MyCertCountResponse> {
    // Reuses the existing GET /learning/certificates list endpoint and counts
    // client-side; avoids an extra backend route for a single integer.
    const certs = await fetchApi(`${LEARNING_PREFIX}/certificates`) as CertificateSummary[];
    return { count: Array.isArray(certs) ? certs.length : 0 };
  },

  async getMySkillsSummary(): Promise<MySkillsSummaryResponse> {
    // Hits the training-skills router (different prefix than learning).
    return fetchApi(`${TRAINING_PREFIX}/skills/me/summary`);
  },

  async assignCourse(payload: AssignCourseRequest): Promise<EnrollmentResponse> {
    return fetchApi(`${LEARNING_PREFIX}/enrollments/assign`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async getCoursesForSkill(skillId: number): Promise<CourseBrief[]> {
    return fetchApi(`${LEARNING_PREFIX}/skills/${skillId}/courses`);
  },

  async getTeamProgress(): Promise<TeamMemberProgress[]> {
    try {
      return await fetchApi(`${LEARNING_PREFIX}/team/progress`);
    } catch (err) {
      // Caller isn't staff — treat as "no team" so the Team tab stays hidden.
      if ((err as { status?: number })?.status === 403) {
        return [];
      }
      throw err;
    }
  },
};

/**
 * Alias for the new training-management surface introduced in Wave 2+.
 * Kept as a separate export so future waves (assign workflow, etc.) can
 * grow `trainingApi` without bloating the broader `learningApi` shape.
 */
export const trainingApi = {
  getTeamProgress: () => learningApi.getTeamProgress(),
  assignCourse: (payload: AssignCourseRequest) => learningApi.assignCourse(payload),
};
