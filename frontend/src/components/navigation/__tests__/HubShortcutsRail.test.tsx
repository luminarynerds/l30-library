/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

type Role =
  | "patron"
  | "child"
  | "staff"
  | "admin"
  | "super_admin"
  | "director"
  | "legal"
  | "teacher"
  | "bookmobile"
  | "homebond";

const mockState = vi.hoisted(() => ({
  user: null as null | { id: number; role: Role },
}));

const apiGet = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api-client", () => ({
  api: {
    get: apiGet,
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({ user: mockState.user }),
}));

// Stub the registry so the test does not depend on the real RAW_HUBS list
// (which would require keeping these test paths in lockstep with prod data).
vi.mock("../hubRegistry", () => ({
  buildHubRegistry: () => [
    {
      hubSlug: "library-hub",
      hubLabel: "Library Hub",
      categoryId: "programs",
      categoryTitle: "Programs",
      itemLabel: "Events",
      itemPath: "/staff/events",
    },
    {
      hubSlug: "library-hub",
      hubLabel: "Library Hub",
      categoryId: "programs",
      categoryTitle: "Programs",
      itemLabel: "Reading Programs",
      itemPath: "/staff/admin/reading-programs",
    },
  ],
}));

import HubShortcutsRail from "../HubShortcutsRail";

const STAFF_USER = { id: 1, role: "staff" as Role };
const PATRON_USER = { id: 2, role: "patron" as Role };

const SAMPLE = [
  { item_path: "/staff/events", visit_count: 7, last_visited_at: "2026-05-18T12:00:00Z" },
  { item_path: "/staff/admin/reading-programs", visit_count: 3, last_visited_at: "2026-05-17T08:00:00Z" },
];

function wrap(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

beforeEach(() => {
  apiGet.mockReset();
  mockState.user = null;
});

describe("HubShortcutsRail", () => {
  it("renders pill links when API returns shortcuts", async () => {
    mockState.user = STAFF_USER;
    apiGet.mockResolvedValueOnce({ hub_slug: "library-hub", shortcuts: SAMPLE });

    wrap(<HubShortcutsRail hubSlug="library-hub" />);

    await waitFor(() => {
      expect(screen.getByTestId("hub-shortcuts-rail")).toBeTruthy();
    });
    expect(screen.getByText("Events")).toBeTruthy();
    expect(screen.getByText("Reading Programs")).toBeTruthy();
    // Visit-count badge
    expect(screen.getByText("7")).toBeTruthy();
    expect(screen.getByText("3")).toBeTruthy();
    // Linked correctly
    const link = screen.getByText("Events").closest("a");
    expect(link).toBeTruthy();
    expect(link?.getAttribute("href")).toBe("/staff/events");
    expect(apiGet).toHaveBeenCalledWith(
      "/api/v1/hub-shortcuts/library-hub",
      expect.objectContaining({ params: { limit: 5 }, signal: expect.anything() }),
    );
  });

  it("renders nothing when API returns an empty list", async () => {
    mockState.user = STAFF_USER;
    apiGet.mockResolvedValueOnce({ hub_slug: "library-hub", shortcuts: [] });

    const { container } = wrap(<HubShortcutsRail hubSlug="library-hub" />);
    await waitFor(() => expect(apiGet).toHaveBeenCalled());
    expect(container.querySelector("[data-testid='hub-shortcuts-rail']")).toBeNull();
  });

  it("renders nothing while loading (before the API resolves)", () => {
    mockState.user = STAFF_USER;
    apiGet.mockReturnValue(new Promise(() => {})); // never resolves

    const { container } = wrap(<HubShortcutsRail hubSlug="library-hub" />);
    expect(container.querySelector("[data-testid='hub-shortcuts-rail']")).toBeNull();
  });

  it("renders nothing for patron-role users (and does NOT fetch)", () => {
    mockState.user = PATRON_USER;

    const { container } = wrap(<HubShortcutsRail hubSlug="library-hub" />);
    expect(container.querySelector("[data-testid='hub-shortcuts-rail']")).toBeNull();
    expect(apiGet).not.toHaveBeenCalled();
  });

  it("renders nothing on API error (silent failure)", async () => {
    mockState.user = STAFF_USER;
    apiGet.mockRejectedValueOnce(new Error("boom"));

    const { container } = wrap(<HubShortcutsRail hubSlug="library-hub" />);
    await waitFor(() => expect(apiGet).toHaveBeenCalled());
    expect(container.querySelector("[data-testid='hub-shortcuts-rail']")).toBeNull();
  });

  it("skips items whose path is not in the registry", async () => {
    mockState.user = STAFF_USER;
    apiGet.mockResolvedValueOnce({
      hub_slug: "library-hub",
      shortcuts: [
        { item_path: "/staff/events", visit_count: 4, last_visited_at: "2026-05-18T12:00:00Z" },
        // Path NOT in the stubbed registry; must be filtered out (not rendered as raw path).
        { item_path: "/staff/unknown-thing", visit_count: 9, last_visited_at: "2026-05-18T11:00:00Z" },
      ],
    });

    wrap(<HubShortcutsRail hubSlug="library-hub" />);

    await waitFor(() => expect(screen.getByTestId("hub-shortcuts-rail")).toBeTruthy());
    expect(screen.getByText("Events")).toBeTruthy();
    expect(screen.queryByText("/staff/unknown-thing")).toBeNull();
  });
});
