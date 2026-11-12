/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import "@testing-library/jest-dom/vitest"
import { MemoryRouter } from "react-router-dom"
import { loadLanguage } from "@/i18n/translations"

// Provide a staff user so the page doesn't redirect-to-/account.
vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: { id: 1, email: "staff@example.org", role: "admin" },
    token: "test-token",
    isLoading: false,
    isAuthenticated: true,
  }),
}))

// Stub OrganizationFeatures. Defaults to ON for every flag so existing tests
// behave as before; individual tests can flip a specific flag off by writing
// to mockDisabledFeatures.
const mockDisabledFeatures: Set<string> = new Set()
vi.mock("@/contexts/OrganizationFeaturesContext", () => ({
  useOrganizationFeatures: () => ({
    isFeatureEnabled: (key: string) => !mockDisabledFeatures.has(key),
  }),
}))

// Stub AdminShell to avoid pulling in Layout/nav. Renders `actions` so tests
// that assert on header-area elements (e.g. the patron-display link) can find
// them — the real shell renders actions in its header bar.
vi.mock("@/components/shells/AdminShell", () => ({
  AdminShell: ({ children, actions }: { children: React.ReactNode; actions?: React.ReactNode }) => (
    <div>
      {actions ? <div data-testid="admin-shell-actions">{actions}</div> : null}
      {children}
    </div>
  ),
}))

// Stub the journey + keyboard hooks (no behavior under test).
vi.mock("@/hooks/useJourneyTracker", () => ({
  useJourneyTracker: () => ({ trackStage: vi.fn() }),
}))
vi.mock("@/hooks/usePatronKeyboardShortcuts", () => ({
  usePatronKeyboardShortcuts: () => undefined,
}))
vi.mock("@/hooks/useKeyboardPreferences", () => ({
  useKeyboardPreferences: () => ({ bindings: {} }),
}))

vi.mock("@/i18n", () => ({
  useTranslation: () => ({ t: (key: string) => key, language: 'en' }),
}))


// Stub api calls used at mount.
vi.mock("@/api/api", async () => {
  const actual = await vi.importActual<typeof import("@/api/api")>("@/api/api")
  return {
    ...actual,
    getPatronCheckouts: vi.fn().mockResolvedValue([]),
    searchPatrons: vi.fn().mockResolvedValue({ patrons: [] }),
  }
})

const fakePatron = {
  id: 99,
  first_name: "Felicity",
  last_name: "Tester",
  email: "felicity@example.org",
  phone: null,
  is_active: true,
  card_number: "C-99",
  role: "patron",
}

// usePatronSearch is replaced per-test to control selectedPatron.
let mockSelectedPatron: typeof fakePatron | null = null
vi.mock("@/pages/staff/circulation/hooks/usePatronSearch", () => ({
  usePatronSearch: () => ({
    patronQuery: "",
    setPatronQuery: vi.fn(),
    searchResults: [],
    selectedResultIndex: -1,
    isSearching: false,
    selectedPatron: mockSelectedPatron,
    recentPatrons: [],
    handlePatronSearch: vi.fn(),
    selectPatron: vi.fn(),
    clearPatron: vi.fn(),
    handleNavigateUp: vi.fn(),
    handleNavigateDown: vi.fn(),
    handleEnter: vi.fn(),
    handleEscape: vi.fn(),
  }),
}))

import StaffCirculationPage from "@/pages/staff/circulation/StaffCirculationPage"

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/staff/circulation"]}>
      <StaffCirculationPage />
    </MemoryRouter>,
  )
}

describe("StaffCirculationPage — ActivityFeed + QuickMessagePanel wiring", () => {

  beforeEach(() => {
    mockSelectedPatron = null
    mockDisabledFeatures.clear()
  })

  it("renders neither ActivityFeed nor QuickMessagePanel without a selected patron", () => {
    mockSelectedPatron = null
    renderPage()
    expect(screen.queryByTestId("activity-feed-details")).not.toBeInTheDocument()
    expect(screen.queryByTestId("quick-message-details")).not.toBeInTheDocument()
  })

  it("renders ActivityFeed expanded when a patron is selected", () => {
    mockSelectedPatron = fakePatron
    renderPage()
    const details = screen.getByTestId("activity-feed-details") as HTMLDetailsElement
    expect(details).toBeInTheDocument()
    expect(details.open).toBe(true)
  })

  it("renders QuickMessagePanel collapsed when a patron is selected", () => {
    mockSelectedPatron = fakePatron
    renderPage()
    const details = screen.getByTestId("quick-message-details") as HTMLDetailsElement
    expect(details).toBeInTheDocument()
    expect(details.open).toBe(false)
  })
})

describe("StaffCirculationPage — customer_display_enabled gate", () => {
  beforeAll(async () => {
    await loadLanguage("en")
  })

  beforeEach(() => {
    mockSelectedPatron = null
    mockDisabledFeatures.clear()
  })

  it("shows the patron-display header link when customer_display_enabled is true", () => {
    renderPage()
    expect(
      screen.getByRole("link", { name: "staffCirculation.openPatronDisplay" }),
    ).toBeInTheDocument()
  })

  it("hides the patron-display header link when customer_display_enabled is false", () => {
    mockDisabledFeatures.add("customer_display_enabled")
    renderPage()
    expect(
      screen.queryByRole("link", { name: "staffCirculation.openPatronDisplay" }),
    ).not.toBeInTheDocument()
  })
})
