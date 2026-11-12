/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

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

import HubStatChips from "../HubStatChips";

const STAFF_USER = { id: 1, role: "staff" as Role };
const PATRON_USER = { id: 2, role: "patron" as Role };

const SAMPLE_STATS = [
  { key: "overdue_returns", value: 3, label: "Overdue returns", urgent: true },
  { key: "open_holds", value: 12, label: "Open holds", urgent: false },
];

beforeEach(() => {
  apiGet.mockReset();
  mockState.user = null;
});

describe("HubStatChips", () => {
  it("renders chips when API returns stats", async () => {
    mockState.user = STAFF_USER;
    apiGet.mockResolvedValueOnce({ hub_slug: "front-desk-hub", stats: SAMPLE_STATS });

    render(<HubStatChips hubSlug="front-desk-hub" />);

    await waitFor(() => {
      expect(screen.getByTestId("hub-stat-chips")).toBeTruthy();
    });
    expect(screen.getByTestId("hub-stat-chip-overdue_returns")).toBeTruthy();
    expect(screen.getByTestId("hub-stat-chip-open_holds")).toBeTruthy();
    expect(screen.getByText("Overdue returns")).toBeTruthy();
    expect(screen.getByText("Open holds")).toBeTruthy();
    expect(apiGet).toHaveBeenCalledWith(
      "/api/v1/hub-stats/front-desk-hub",
      expect.objectContaining({ signal: expect.anything() }),
    );
  });

  it("renders nothing when API returns empty stats array", async () => {
    mockState.user = STAFF_USER;
    apiGet.mockResolvedValueOnce({ hub_slug: "front-desk-hub", stats: [] });

    const { container } = render(<HubStatChips hubSlug="front-desk-hub" />);

    await waitFor(() => {
      expect(apiGet).toHaveBeenCalled();
    });
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing for patron-role users and does not fetch", () => {
    mockState.user = PATRON_USER;
    apiGet.mockResolvedValueOnce({ hub_slug: "front-desk-hub", stats: SAMPLE_STATS });

    const { container } = render(<HubStatChips hubSlug="front-desk-hub" />);

    expect(container.firstChild).toBeNull();
    expect(apiGet).not.toHaveBeenCalled();
  });

  it("renders nothing for unauthenticated users", () => {
    mockState.user = null;
    apiGet.mockResolvedValueOnce({ hub_slug: "front-desk-hub", stats: SAMPLE_STATS });

    const { container } = render(<HubStatChips hubSlug="front-desk-hub" />);

    expect(container.firstChild).toBeNull();
    expect(apiGet).not.toHaveBeenCalled();
  });

  it("renders nothing when API errors (silent failure)", async () => {
    mockState.user = STAFF_USER;
    apiGet.mockRejectedValueOnce(new Error("boom"));

    const { container } = render(<HubStatChips hubSlug="front-desk-hub" />);

    await waitFor(() => {
      expect(apiGet).toHaveBeenCalled();
    });
    expect(container.firstChild).toBeNull();
  });

  it("applies urgent styling when urgent is true and neutral styling otherwise", async () => {
    mockState.user = STAFF_USER;
    apiGet.mockResolvedValueOnce({ hub_slug: "front-desk-hub", stats: SAMPLE_STATS });

    render(<HubStatChips hubSlug="front-desk-hub" />);

    const urgentChip = await screen.findByTestId("hub-stat-chip-overdue_returns");
    const neutralChip = await screen.findByTestId("hub-stat-chip-open_holds");

    expect(urgentChip.getAttribute("data-urgent")).toBe("true");
    expect(urgentChip.className).toMatch(/status-danger/);
    expect(neutralChip.getAttribute("data-urgent")).toBe("false");
    expect(neutralChip.className).not.toMatch(/status-danger/);
  });

  it("emits a meaningful aria-label per chip (incl. urgency hint)", async () => {
    mockState.user = STAFF_USER;
    apiGet.mockResolvedValueOnce({ hub_slug: "front-desk-hub", stats: SAMPLE_STATS });

    render(<HubStatChips hubSlug="front-desk-hub" />);

    const urgentChip = await screen.findByTestId("hub-stat-chip-overdue_returns");
    const neutralChip = await screen.findByTestId("hub-stat-chip-open_holds");

    expect(urgentChip.getAttribute("aria-label")).toBe("3 Overdue returns (urgent)");
    expect(neutralChip.getAttribute("aria-label")).toBe("12 Open holds");
  });

  it("fetches and renders for admin / super_admin / director roles", async () => {
    for (const role of ["admin", "super_admin", "director"] as Role[]) {
      apiGet.mockReset();
      mockState.user = { id: 1, role };
      apiGet.mockResolvedValueOnce({ hub_slug: "front-desk-hub", stats: SAMPLE_STATS });

      const { unmount } = render(<HubStatChips hubSlug="front-desk-hub" />);
      await waitFor(() => expect(apiGet).toHaveBeenCalledTimes(1));
      unmount();
    }
  });
});
