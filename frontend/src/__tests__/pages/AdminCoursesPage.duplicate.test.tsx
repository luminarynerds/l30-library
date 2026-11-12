/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="vitest/globals" />
/**
 * Wave 2 / W2-D: Duplicate course row action.
 *
 * The Wave-2 plan asked for a fire-and-forget Duplicate row button. The codebase
 * already shipped a richer flow in PR #859: the row button opens a modal that
 * lets the user customize the new title before the clone fires. That is a strict
 * UX superset of the plan's spec (Trish's persona ask — "let me duplicate this
 * course" — is met, plus she gets to rename it). This test locks the existing
 * wire in so a future refactor doesn't regress it back to either:
 *   - no row action at all, or
 *   - fire-and-forget clone without a title prompt.
 *
 * See `feedback_l30_kill_or_build_437_438_overruled` for the "plan obsolete
 * because the feature already exists" pattern.
 */
import React from "react"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

vi.mock("@/components/shells", () => ({
  AdminShell: ({
    title,
    actions,
    children,
  }: {
    title?: string
    actions?: React.ReactNode
    children: React.ReactNode
  }) => (
    <div data-testid="admin-shell">
      {title ? <h1>{title}</h1> : null}
      {actions}
      {children}
    </div>
  ),
}))

vi.mock("@/lib/sentry-lazy", () => ({
  init: vi.fn(),
  captureException: vi.fn(),
  captureMessage: vi.fn(),
  addBreadcrumb: vi.fn(),
}))

const { stableI18n } = vi.hoisted(() => {
  const t = (key: string, fallback?: string | Record<string, unknown>) =>
    typeof fallback === "string" ? fallback : key
  const setLanguage = () => {}
  return { stableI18n: { t, language: "en", setLanguage, isRTL: false } }
})
vi.mock("@/i18n", () => ({ useTranslation: () => stableI18n }))

vi.mock("../../components/ConfirmDialog", () => ({ default: () => null }))
vi.mock("@/components/ConfirmDialog", () => ({ default: () => null }))

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({ user: { id: 1, role: "super_admin" }, isAuthenticated: true }),
}))

const cloneCourseMock = vi.fn()

vi.mock("@/api/domains/learning/courses-api", () => ({
  getAllCoursesAdmin: vi.fn().mockResolvedValue([
    {
      id: 42,
      title: "My Course",
      slug: "my-course",
      description: "",
      difficulty: "beginner",
      lifecycle_stage: "published",
      created_by_id: 1,
      enrollment_count: 0,
      completion_count: 0,
      in_progress_count: 0,
      last_activity_at: null,
      last_reviewed_at: null,
      review_due_at: null,
      last_reviewed_by: null,
      is_review_due: false,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ]),
  cloneCourse: (...args: unknown[]) => cloneCourseMock(...args),
  deleteCourse: vi.fn(),
  transitionCourseStage: vi.fn(),
  getCourseReviewQueue: vi.fn().mockResolvedValue({ courses: [], total: 0 }),
  CourseStageTransitionError: class extends Error {},
}))

vi.mock("react-hot-toast", () => ({
  default: { success: vi.fn(), error: vi.fn(), dismiss: vi.fn() },
  toast: { success: vi.fn(), error: vi.fn(), dismiss: vi.fn() },
}))

import AdminCoursesPage from "@/pages/AdminCoursesPage"

describe("AdminCoursesPage Duplicate row action (W2-D)", () => {
  beforeEach(() => {
    cloneCourseMock.mockReset()
  })

  it("each row exposes a Duplicate button that names its course (a11y)", async () => {
    render(
      <MemoryRouter>
        <AdminCoursesPage />
      </MemoryRouter>,
    )
    // i18n mock returns the key when no string fallback is provided. The
    // existing template is `aria.adminCourses.duplicateCourse` with a `title`
    // interpolation; the mock returns the bare key. Match on it loosely so we
    // still assert per-row a11y-labeled buttons exist (one for table view, one
    // for mobile card list).
    const dupBtns = await screen.findAllByRole("button", {
      name: /duplicateCourse|duplicate my course/i,
    })
    expect(dupBtns.length).toBeGreaterThanOrEqual(1)
  })

  it("clicking Duplicate opens a title-prompt modal (does not fire clone immediately)", async () => {
    cloneCourseMock.mockResolvedValue({
      id: 99,
      title: "My Course (copy)",
      lifecycle_stage: "draft",
    })
    render(
      <MemoryRouter>
        <AdminCoursesPage />
      </MemoryRouter>,
    )
    const dupBtn = (await screen.findAllByRole("button", {
      name: /duplicateCourse|duplicate my course/i,
    }))[0]!
    fireEvent.click(dupBtn)

    // Modal opens; clone has NOT been called yet (UX upgrade over plan spec:
    // user gets to pick the new title before the network call fires).
    const dialog = await screen.findByRole("dialog")
    expect(dialog).toBeInTheDocument()
    expect(cloneCourseMock).not.toHaveBeenCalled()
  })

  it("submitting the modal calls cloneCourse with the source id + chosen title", async () => {
    cloneCourseMock.mockResolvedValue({
      id: 99,
      title: "Renamed Copy",
      lifecycle_stage: "draft",
    })
    render(
      <MemoryRouter>
        <AdminCoursesPage />
      </MemoryRouter>,
    )
    const dupBtn = (await screen.findAllByRole("button", {
      name: /duplicateCourse|duplicate my course/i,
    }))[0]!
    fireEvent.click(dupBtn)

    await screen.findByRole("dialog")
    // The new-title input is keyed by aria-label (i18n key, since no string
    // fallback in source). Find by role + name (loose match on the key).
    const input = await screen.findByRole("textbox", {
      name: /duplicateNewTitleField/i,
    })
    fireEvent.change(input, { target: { value: "Renamed Copy" } })

    // Submit by clicking the modal's Duplicate button (the form submit). There
    // are now multiple buttons named `Duplicate` (one per row + one in the
    // modal) — submitting the form via form-submit is the most robust path.
    const form = input.closest("form")
    expect(form).not.toBeNull()
    fireEvent.submit(form!)

    await waitFor(() =>
      expect(cloneCourseMock).toHaveBeenCalledWith(42, {
        new_title: "Renamed Copy",
        include_unpublished_lessons: true,
      }),
    )
  })
})
