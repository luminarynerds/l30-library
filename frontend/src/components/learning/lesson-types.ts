/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export interface QuizQuestion {
  id: number;
  question_text: string;
  question_type: string;
  options: { text: string; is_correct: boolean }[];
  explanation: string | null;
}

export interface LessonVariant {
  id: number;
  variant_type: string;
  content: unknown;
}

export interface LessonProgressBrief {
  scroll_position?: number | null;
  status?: string | null;
}

export interface Lesson {
  id: number;
  module_id: number;
  title: string;
  lesson_type: 'article' | 'video' | 'quiz' | 'sandbox' | 'lab';
  content: unknown;
  estimated_minutes: number | null;
  sensory_notes: string | null;
  is_preview?: boolean;
  facilitator_notes?: string | null;
  variants: LessonVariant[];
  quiz_questions: QuizQuestion[];
  progress?: LessonProgressBrief | null;
}

export interface CourseLesson {
  id: number;
  title: string;
  module_id: number;
}

export interface CourseModule {
  id: number;
  title: string;
  lessons: CourseLesson[];
}

export interface CourseStructure {
  id: number;
  title: string;
  modules: CourseModule[];
}

export interface QuizResultFeedback {
  question_id: number;
  correct: boolean;
}

export interface QuizResult {
  passed: boolean;
  score: number;
  total_questions: number;
  percentage: number;
  weighted_score?: number
  feedback: QuizResultFeedback[];
}

export interface ArticleContent {
  body?: string;
  text?: string;
}

export interface VideoContent {
  video_url?: string;
  transcript?: string;
}

export interface SandboxContent {
  sandbox_type?: 'code' | 'prompt' | 'drag_drop' | 'fill_blank' | 'matching';
  instructions?: string;
  initial_code?: string;
  expected_output?: string;
  hints?: string[];
  prompt_template?: string;
  items?: { id: string; text: string; correct_zone?: string }[];
  zones?: { id: string; label: string }[];
  blanks?: { id: string; answer: string; options?: string[] }[];
  pairs?: { left: string; right: string }[];
  // Article-shaped fallback fields. Some legacy/seeded sandbox lessons in prod
  // were stored with article-shaped content (body + key_points + exercise_steps);
  // SandboxPlayer renders these via a read-only fallback when no
  // sandbox-discriminator field is present.
  body?: string;
  key_points?: string[];
  exercise_steps?: string[];
  sandbox_url?: string;
  sample_records?: string[];
}

import { Volume2, Eye, Type, FileText } from 'lucide-react';

export const VARIANT_ICONS: Record<string, React.ElementType> = {
  audio: Volume2,
  visual: Eye,
  text_only: Type,
  default: FileText,
};

export const DOMPURIFY_CONFIG = {
  ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'code', 'pre', 'div', 'span', 'section'],
  ALLOWED_ATTR: ['href', 'target', 'rel', 'class', 'id'],
  KEEP_CONTENT: true
};
