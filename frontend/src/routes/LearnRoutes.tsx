/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Routes, Route } from 'react-router-dom'
import RequireAuth from '../components/RequireAuth'
import { lazyWithRetry } from '../utils/lazyWithRetry'

const LearnPage = lazyWithRetry(() => import('../pages/LearnPage'), 'learn-learn-page')
const LearnCatalogPage = lazyWithRetry(() => import('../pages/LearnCatalogPage'), 'learn-learn-catalog-page')
const CourseDetailPage = lazyWithRetry(() => import('../pages/CourseDetailPage'), 'learn-course-detail-page')
const LessonViewerPage = lazyWithRetry(() => import('../pages/LessonViewerPage'), 'learn-lesson-viewer-page')
const SurveyPage = lazyWithRetry(() => import('../pages/SurveyPage'), 'learn-survey-page')
const AchievementsPage = lazyWithRetry(() => import('../pages/AchievementsPage'), 'learn-achievements-page')
const LearningAnalyticsPage = lazyWithRetry(() => import('../pages/LearningAnalyticsPage'), 'learn-learning-analytics-page')
const LabsPage = lazyWithRetry(() => import('../pages/LabsPage'), 'learn-labs-page')
const AISaidWhatLab = lazyWithRetry(() => import('../pages/labs/AISaidWhatLab'), 'learn-ai-said-what-lab')
const WhoWroteThisLab = lazyWithRetry(() => import('../pages/labs/WhoWroteThisLab'), 'learn-who-wrote-this-lab')
const FixThisPromptLab = lazyWithRetry(() => import('../pages/labs/FixThisPromptLab'), 'learn-fix-this-prompt-lab')
const RealOrFakeLab = lazyWithRetry(() => import('../pages/labs/RealOrFakeLab'), 'learn-real-or-fake-lab')

export default function LearnRoutes(): React.ReactElement {
  return (
    <Routes>
      <Route index element={<LearnPage />} />
      <Route path="catalog" element={<LearnCatalogPage />} />
      <Route path="course" element={<LearnCatalogPage />} />
      <Route path="course/:id" element={<CourseDetailPage />} />
      <Route path="course/:id/lesson/:lessonId" element={<LessonViewerPage />} />
      <Route path="surveys/:id" element={<SurveyPage />} />
      <Route path="achievements" element={<RequireAuth><AchievementsPage /></RequireAuth>} />
      <Route path="analytics" element={<RequireAuth><LearningAnalyticsPage /></RequireAuth>} />
      <Route path="labs" element={<LabsPage />} />
      <Route path="labs/ai-said-what" element={<AISaidWhatLab />} />
      <Route path="labs/who-wrote-this" element={<WhoWroteThisLab />} />
      <Route path="labs/fix-this-prompt" element={<FixThisPromptLab />} />
      <Route path="labs/real-or-fake" element={<RealOrFakeLab />} />
    </Routes>
  )
}
