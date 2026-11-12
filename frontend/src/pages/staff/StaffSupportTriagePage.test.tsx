/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, expect, it, vi, beforeEach } from "vitest"
import { render, screen, waitFor, fireEvent } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import StaffSupportTriagePage from "./StaffSupportTriagePage"

vi.mock("react-hot-toast", () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

vi.mock("../../components/shells/AdminShell", () => ({
  AdminShell: ({ children, title }: { children: React.ReactNode; title: string }) => (
    <div data-testid="admin-shell">
      <h1>{title}</h1>
      {children}
    </div>
  ),
}))

vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({
    user: { id: 42, email: "staff@example.org", role: "admin" },
  }),
}))

const mockTicket = {
  id: 7,
  ticket_number: "SUPPORT-2026-AAA00001",
  name: "Jamie Patron",
  email: "jamie@example.com",
  phone: null,
  guide_title: null,
  step_number: null,
  total_steps: null,
  issue_description: "I cannot renew my book online.",
  contact_method: "email",
  status: "open" as const,
  category: "circulation",
  submitted_at: "2026-05-16T12:00:00Z",
  updated_at: "2026-05-16T12:00:00Z",
  resolved_at: null,
  assigned_to_id: null,
  internal_notes: null,
  sla_business_days: 1,
  age_business_days: 1,
  sla_breached: false,
}

const listTriageTickets = vi.fn()
const patchTriageTicket = vi.fn()
const listTriageEvents = vi.fn()
const postTriageResponse = vi.fn()

vi.mock("../../api/support-api", async () => {
  const actual =
    await vi.importActual<typeof import("../../api/support-api")>(
      "../../api/support-api"
    )
  return {
    ...actual,
    listTriageTickets: (...args: unknown[]) => listTriageTickets(...args),
    patchTriageTicket: (...args: unknown[]) => patchTriageTicket(...args),
    listTriageEvents: (...args: unknown[]) => listTriageEvents(...args),
    postTriageResponse: (...args: unknown[]) => postTriageResponse(...args),
  }
})

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <StaffSupportTriagePage />
    </QueryClientProvider>
  )
}

describe("StaffSupportTriagePage", () => {
  beforeEach(() => {
    listTriageTickets.mockReset()
    patchTriageTicket.mockReset()
    listTriageEvents.mockReset()
    postTriageResponse.mockReset()
  })

  it("renders unassigned tickets by default", async () => {
    listTriageTickets.mockResolvedValue({ tickets: [mockTicket], total: 1 })
    renderPage()
    await waitFor(() => {
      expect(
        screen.getByText("I cannot renew my book online.")
      ).toBeInTheDocument()
    })
    expect(screen.getByText("SUPPORT-2026-AAA00001")).toBeInTheDocument()
    expect(listTriageTickets).toHaveBeenCalledWith(
      expect.objectContaining({ status_filter: "unassigned" })
    )
  })

  it("switches tab updates the filter", async () => {
    listTriageTickets.mockResolvedValue({ tickets: [], total: 0 })
    renderPage()
    await waitFor(() => expect(listTriageTickets).toHaveBeenCalled())

    fireEvent.click(screen.getByRole("tab", { name: "In progress" }))

    await waitFor(() => {
      expect(listTriageTickets).toHaveBeenLastCalledWith(
        expect.objectContaining({ status_filter: "in_progress" })
      )
    })
  })

  it("clicking Claim calls patchTriageTicket with current user id", async () => {
    listTriageTickets.mockResolvedValue({ tickets: [mockTicket], total: 1 })
    patchTriageTicket.mockResolvedValue({
      ...mockTicket,
      assigned_to_id: 42,
      status: "in_progress",
    })
    renderPage()
    await waitFor(() =>
      expect(screen.getByText("SUPPORT-2026-AAA00001")).toBeInTheDocument()
    )
    fireEvent.click(screen.getByRole("button", { name: "Claim" }))
    await waitFor(() => {
      expect(patchTriageTicket).toHaveBeenCalledWith(
        7,
        expect.objectContaining({ assigned_to_id: 42, status: "in_progress" })
      )
    })
  })

  it("row click opens the detail drawer", async () => {
    listTriageTickets.mockResolvedValue({ tickets: [mockTicket], total: 1 })
    listTriageEvents.mockResolvedValue([])
    renderPage()
    await waitFor(() =>
      expect(screen.getByText("SUPPORT-2026-AAA00001")).toBeInTheDocument()
    )
    fireEvent.click(screen.getByText("I cannot renew my book online."))
    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument()
    })
    // Drawer fetches its own detail asynchronously; wait for it to render.
    expect(await screen.findByText("jamie@example.com")).toBeInTheDocument()
  })
})
