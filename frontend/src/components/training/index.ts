/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// Training Components

// Skills
export { SkillsList } from './SkillsList';
export { SkillCreate } from './SkillCreate';
export { SkillEdit } from './SkillEdit';
export { SkillAssessment } from './SkillAssessment';
export { SkillUserProgress } from './SkillUserProgress';

// Learning Dashboard
export { ContinueLearningCard } from './ContinueLearningCard';
export { UserStatsCard } from './UserStatsCard';

// Quick Wins - Micro Lessons & Alerts
export { MicroLessonCard, MicroLessonList } from './MicroLessonCard';
export type { MicroLesson } from './MicroLessonCard';
export { WhatsNewBanner, useWhatsNewAnnouncements } from './WhatsNewBanner';
export type { TrainingAnnouncement, AnnouncementType } from './WhatsNewBanner';

// Lesson Experience
export { FormatPicker } from './FormatPicker';
export type { ContentFormat } from './FormatPicker';
export { LessonViewer } from './LessonViewer';
export { QuizPlayer } from './QuizPlayer';

// Course Thumbnails
export { default as CourseThumbnail } from './CourseThumbnail';

// External Resources
export { default as ExternalResourceCard } from './ExternalResourceCard';
export { default as ExternalResourcesSection } from './ExternalResourcesSection';

// Neurodivergent Features
export {
  GentleProgress,
  FocusMode,
  TextToSpeech,
  MicroTasks,
  PomodoroTimer,
} from './neurodivergent';

// API
export { skillsApi, learningApi, trainingApi } from './api';
export type { TeamMemberProgress } from './api';

// Types
export type {
  Skill,
  SkillCreatePayload,
  SkillUpdatePayload,
  UserSkillProgress,
  SkillAssessmentQuestion,
  ProficiencyLevel,
} from './types';

export type {
  Course,
  Module,
  Lesson,
  CourseProgress,
  UserStats,
} from './api';

// Training Tabs (Wave 0 split of StaffTrainingDashboard)
export { TrainingTabNav } from './tabs/TrainingTabNav';
export type { TrainingTabDescriptor, TrainingTabNavProps } from './tabs/TrainingTabNav';
export { tabIdFor, panelIdFor } from './tabs/tabIds';
export { CoursesTab } from './tabs/CoursesTab';
export { SkillsTab } from './tabs/SkillsTab';
export { CourseRow } from './tabs/CourseRow';
export type { CourseRowProps } from './tabs/CourseRow';
export { TeamTab } from './tabs/TeamTab';
export { TeamMemberRow } from './team/TeamMemberRow';
export type { TeamMemberRowProps } from './team/TeamMemberRow';
export { useTeamMembership } from './team/useTeamMembership';

// Training utils (Wave 1: real configurable deadlines)
export {
  getDueDate,
  getTrainingStatus,
  getDaysUntilDue,
} from './utils/dueDate';
export type {
  StatusFilter,
  SortField,
  SortDirection,
  TrainingTab,
  Alert as TrainingAlert,
  MonthlyCompletion,
} from './utils/dueDate';
