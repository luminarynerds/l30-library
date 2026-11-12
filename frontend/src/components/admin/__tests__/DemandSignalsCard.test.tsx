/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";

vi.mock("@/i18n", () => ({
  useTranslation: () => ({
    t: (_key: string, fallback?: string) => fallback ?? _key,
  }),
}));

// Use a singleton api mock; assign the next return value via setNext().
const apiState: { next?: Promise<unknown> } = {};
vi.mock("@/lib/api-client", () => {
  const get = vi.fn(() => apiState.next ?? Promise.resolve({ items: [] }));
  const api = { get, post: vi.fn(), put: vi.fn(), patch: vi.fn(), del: vi.fn() };
  return {
    __esModule: true,
    default: api,
    api,
    apiClient: vi.fn(),
    fetchApi: vi.fn(),
    get,
    isApiError: () => false,
  };
});

// Import AFTER mocks are set up.
import DemandSignalsCard from "@/components/admin/DemandSignalsCard";

beforeEach(() => {
  apiState.next = undefined;
});

afterEach(() => {
  cleanup();
});

describe("DemandSignalsCard", () => {
  it("renders rows when the backend returns data", async () => {
    apiState.next = Promise.resolve({
      days: 30,
      limit: 10,
      signal_type: null,
      items: [
        {
          key: "9780134685991",
          normalized_isbn: "9780134685991",
          normalized_title: "The Pragmatic Programmer",
          signal_type: "failed_search",
          count: 7,
          weighted_count: 11.0,
          most_recent: "2026-05-19T12:00:00+00:00",
        },
        {
          key: "Atomic Habits",
          normalized_isbn: null,
          normalized_title: "Atomic Habits",
          signal_type: "failed_search",
          count: 3,
          weighted_count: 4.5,
          most_recent: "2026-05-18T09:00:00+00:00",
        },
      ],
    });

    render(<DemandSignalsCard />);
    expect(
      await screen.findByText("The Pragmatic Programmer"),
    ).toBeInTheDocument();
    expect(await screen.findByText("Atomic Habits")).toBeInTheDocument();
  });

  it("shows the empty state when no items are returned", async () => {
    apiState.next = Promise.resolve({
      days: 30,
      limit: 10,
      signal_type: null,
      items: [],
    });
    render(<DemandSignalsCard />);
    expect(
      await screen.findByText(/No demand signals captured yet/i),
    ).toBeInTheDocument();
  });

  it("shows an error message when the request fails", async () => {
    apiState.next = Promise.reject(new Error("boom"));
    render(<DemandSignalsCard />);
    expect(
      await screen.findByText(/Could not load demand signals/i),
    ).toBeInTheDocument();
  });

  it("renders the heading", () => {
    apiState.next = new Promise(() => {});
    render(<DemandSignalsCard />);
    expect(
      screen.getByRole("heading", { name: /Collection gap signals/i }),
    ).toBeInTheDocument();
  });
});
