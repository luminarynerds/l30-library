/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Routes, Route } from "react-router-dom"
import RequireAuth from "../components/RequireAuth"
import RequireFeature from "../components/RequireFeature"
import BoardLayout from "../components/board/BoardLayout"
import { lazyWithRetry } from '../utils/lazyWithRetry'

const BoardDashboardPage = lazyWithRetry(() => import("../pages/board/BoardDashboardPage"), 'board-board-dashboard-page')
const BoardMembersPage = lazyWithRetry(() => import("../pages/board/BoardMembersPage"), 'board-board-members-page')
const BoardMeetingsPage = lazyWithRetry(() => import("../pages/board/BoardMeetingsPage"), 'board-board-meetings-page')
const MeetingDetailPage = lazyWithRetry(() => import("../pages/board/MeetingDetailPage"), 'board-meeting-detail-page')
const BoardDocumentsPage = lazyWithRetry(() => import("../pages/board/BoardDocumentsPage"), 'board-board-documents-page')
const BoardMinutesPage = lazyWithRetry(() => import("../pages/board/BoardMinutesPage"), 'board-board-minutes-page')
const BoardMotionsPage = lazyWithRetry(() => import("../pages/board/BoardMotionsPage"), 'board-board-motions-page')
const BoardMotionDetailPage = lazyWithRetry(() => import("../pages/board/BoardMotionDetailPage"), 'board-board-motion-detail-page')
const BoardCommittees = lazyWithRetry(() => import("../pages/board/BoardCommittees"), 'board-board-committees')
const BoardCommitteeDetail = lazyWithRetry(() => import("../pages/board/BoardCommitteeDetail"), 'board-board-committee-detail')
const PublicCommentsPage = lazyWithRetry(() => import("../pages/board/PublicCommentsPage"), 'board-public-comments-page')
const MeetingPrepPage = lazyWithRetry(() => import("../pages/board/MeetingPrepPage"), 'board-meeting-prep-page')
const BoardReportsPage = lazyWithRetry(() => import("../pages/board/BoardReportsPage"), 'board-board-reports-page')
const BoardReportTemplatesPage = lazyWithRetry(() => import("../pages/board/BoardReportTemplatesPage"), 'board-board-report-templates-page')
const BoardReportSchedulesPage = lazyWithRetry(() => import("../pages/board/BoardReportSchedulesPage"), 'board-board-report-schedules-page')

export default function BoardRoutes(): React.ReactElement {
  return (
    <RequireFeature feature="board_features_enabled">
      <Routes>
        <Route element={<BoardLayout />}>
          <Route index element={<BoardDashboardPage />} />
          <Route path="members" element={<BoardMembersPage />} />
          <Route path="meetings" element={<BoardMeetingsPage />} />
          <Route path="meetings/:meetingId" element={<MeetingDetailPage />} />
          <Route path="meetings/:meetingId/prep" element={<RequireAuth requiredRoles={["admin", "board_member"]}><MeetingPrepPage /></RequireAuth>} />
          <Route path="documents" element={<BoardDocumentsPage />} />
          <Route path="minutes" element={<BoardMinutesPage />} />
          <Route path="motions" element={<BoardMotionsPage />} />
          <Route path="motions/:motionId" element={<BoardMotionDetailPage />} />
          <Route path="committees" element={<BoardCommittees />} />
          <Route path="committees/:committeeId" element={<BoardCommitteeDetail />} />
          <Route path="public-comments" element={<PublicCommentsPage />} />
          <Route path="public-comments/:meetingId" element={<PublicCommentsPage />} />
          <Route path="reports" element={<RequireAuth requiredRoles={["admin", "staff"]}><BoardReportsPage /></RequireAuth>} />
          <Route path="reports/templates" element={<RequireAuth requiredRoles={["admin", "staff"]}><BoardReportTemplatesPage /></RequireAuth>} />
          <Route path="reports/schedules" element={<RequireAuth requiredRoles={["admin", "staff"]}><BoardReportSchedulesPage /></RequireAuth>} />
        </Route>
      </Routes>
    </RequireFeature>
  )
}
