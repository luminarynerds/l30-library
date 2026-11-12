/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="vitest/globals" />
import React from "react"
import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

// AdminShell pulls in AuthContext + Preferences + sidebar config -- stub it
// so the page renders its actions slot in isolation.
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

vi.mock("@/api/domains/learning/courses-api", () => ({
  getAllCoursesAdmin: vi.fn().mockResolvedValue([]),
  cloneCourse: vi.fn(),
  deleteCourse: vi.fn(),
  transitionCourseStage: vi.fn(),
  getCourseReviewQueue: vi.fn().mockResolvedValue({ courses: [], total: 0 }),
  CourseStageTransitionError: class extends Error {},
}))

vi.mock("react-hot-toast", () => ({
  default: { success: vi.fn(), error: vi.fn() },
  toast: { success: vi.fn(), error: vi.fn() },
}))

import AdminCoursesPage from "@/pages/AdminCoursesPage"

describe("AdminCoursesPage templates CTA (W2-C)", () => {
  it("shows a Use template header CTA linking to the templates page", async () => {
    render(
      <MemoryRouter>
        <AdminCoursesPage />
      </MemoryRouter>,
    )
    const cta = await screen.findByRole("link", { name: /use template/i })
    expect(cta).toHaveAttribute("href", "/staff/admin/courses/templates")
  })
})
