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

import HubStatusStrip from "../HubStatusStrip";

const STAFF_USER = { id: 1, role: "staff" as Role };
const PATRON_USER = { id: 2, role: "patron" as Role };

const SAMPLE_STATS = [
  { key: "emergency_hubs_active", value: 2, label: "Emergency hubs active", urgent: true },
  { key: "advocacy_awaiting_moderation", value: 5, label: "Advocacy stories awaiting moderation", urgent: false },
];

beforeEach(() => {
  apiGet.mockReset();
  mockState.user = null;
});

describe("HubStatusStrip", () => {
  it("renders chips when API returns stats", async () => {
    mockState.user = STAFF_USER;
    apiGet.mockResolvedValueOnce({ hub_slug: "library-hub", stats: SAMPLE_STATS });

    render(<HubStatusStrip hubSlug="library-hub" />);

    await waitFor(() => {
      expect(screen.getByTestId("hub-status-strip")).toBeTruthy();
    });
    expect(screen.getByTestId("hub-status-chip-emergency_hubs_active")).toBeTruthy();
    expect(screen.getByTestId("hub-status-chip-advocacy_awaiting_moderation")).toBeTruthy();
    expect(screen.getByText("Emergency hubs active")).toBeTruthy();
    expect(screen.getByText("Advocacy stories awaiting moderation")).toBeTruthy();
    expect(apiGet).toHaveBeenCalledWith(
      "/api/v1/hub-stats/library-hub",
      expect.objectContaining({ signal: expect.anything() }),
    );
  });

  it("renders nothing when API returns empty stats array", async () => {
    mockState.user = STAFF_USER;
    apiGet.mockResolvedValueOnce({ hub_slug: "library-hub", stats: [] });

    const { container } = render(<HubStatusStrip hubSlug="library-hub" />);

    await waitFor(() => {
      expect(apiGet).toHaveBeenCalled();
    });
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing while loading (before the promise resolves)", () => {
    mockState.user = STAFF_USER;
    // Never-resolving promise -> component stays in the loading state.
    apiGet.mockReturnValueOnce(new Promise(() => {}));

    const { container } = render(<HubStatusStrip hubSlug="library-hub" />);

    // Synchronous: nothing rendered while the request is in flight.
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing for patron-role users and does not fetch", () => {
    mockState.user = PATRON_USER;
    apiGet.mockResolvedValueOnce({ hub_slug: "library-hub", stats: SAMPLE_STATS });

    const { container } = render(<HubStatusStrip hubSlug="library-hub" />);

    expect(container.firstChild).toBeNull();
    expect(apiGet).not.toHaveBeenCalled();
  });

  it("renders nothing for unauthenticated users", () => {
    mockState.user = null;
    apiGet.mockResolvedValueOnce({ hub_slug: "library-hub", stats: SAMPLE_STATS });

    const { container } = render(<HubStatusStrip hubSlug="library-hub" />);

    expect(container.firstChild).toBeNull();
    expect(apiGet).not.toHaveBeenCalled();
  });

  it("renders nothing when API errors (silent failure)", async () => {
    mockState.user = STAFF_USER;
    apiGet.mockRejectedValueOnce(new Error("boom"));

    const { container } = render(<HubStatusStrip hubSlug="library-hub" />);

    await waitFor(() => {
      expect(apiGet).toHaveBeenCalled();
    });
    expect(container.firstChild).toBeNull();
  });

  it("applies urgent styling when urgent is true and neutral styling otherwise", async () => {
    mockState.user = STAFF_USER;
    apiGet.mockResolvedValueOnce({ hub_slug: "library-hub", stats: SAMPLE_STATS });

    render(<HubStatusStrip hubSlug="library-hub" />);

    const urgentChip = await screen.findByTestId("hub-status-chip-emergency_hubs_active");
    const neutralChip = await screen.findByTestId("hub-status-chip-advocacy_awaiting_moderation");

    expect(urgentChip.getAttribute("data-urgent")).toBe("true");
    expect(urgentChip.className).toMatch(/status-danger/);
    expect(neutralChip.getAttribute("data-urgent")).toBe("false");
    expect(neutralChip.className).not.toMatch(/status-danger/);
  });

  it("emits an aria-label summarizing the chip contents", async () => {
    mockState.user = STAFF_USER;
    apiGet.mockResolvedValueOnce({ hub_slug: "library-hub", stats: SAMPLE_STATS });

    render(<HubStatusStrip hubSlug="library-hub" />);

    const strip = await screen.findByTestId("hub-status-strip");
    expect(strip.getAttribute("aria-label")).toBe(
      "Hub status: 2 emergency hubs active, 5 advocacy stories awaiting moderation",
    );
  });

  it("fetches and renders for admin / super_admin / director roles", async () => {
    for (const role of ["admin", "super_admin", "director"] as Role[]) {
      apiGet.mockReset();
      mockState.user = { id: 1, role };
      apiGet.mockResolvedValueOnce({ hub_slug: "library-hub", stats: SAMPLE_STATS });

      const { unmount } = render(<HubStatusStrip hubSlug="library-hub" />);
      await waitFor(() => expect(apiGet).toHaveBeenCalledTimes(1));
      unmount();
    }
  });
});
