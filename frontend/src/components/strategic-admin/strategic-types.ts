/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export interface TimelineEvent {
  year: number;
  title: string;
  description?: string;
  image_url?: string;
}

export interface Milestone {
  id?: number;
  plan_id?: number;
  title: string;
  description?: string;
  achieved_date?: string;
  celebration_text?: string;
  impact_story?: string;
  photo_url?: string;
  is_public: boolean;
  is_featured: boolean;
  display_order: number;
  milestone_type: string;
}

export interface Goal {
  id?: number;
  title: string;
  description?: string;
  public_description?: string;
  category?: string;
  department?: string;
  target_date?: string;
  progress: number;
  status: string;
  priority: number;
  is_public: boolean;
  staff_can_update: boolean;
  metrics?: { name: string; current: number; target: number; unit?: string }[];
  comment_count?: number;
  display_order?: number;
}

export interface Plan {
  id?: number;
  title: string;
  description?: string;
  period_start: string;
  period_end: string;
  mission?: string;
  vision?: string;
  values: string[];
  status: string;
  hero_image_url?: string;
  story_intro?: string;
  history_timeline: TimelineEvent[];
  goals?: Goal[];
  milestones?: Milestone[];
}

export const statusOptions = [
  { value: "draft", label: "Draft" },
  { value: "active", label: "Active" },
  { value: "completed", label: "Completed" },
  { value: "archived", label: "Archived" },
];

export const milestoneTypes = [
  { value: "achievement", label: "Achievement" },
  { value: "anniversary", label: "Anniversary" },
  { value: "event", label: "Event" },
  { value: "launch", label: "Launch" },
];
