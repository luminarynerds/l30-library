/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent, waitFor } from "@testing-library/react";

vi.mock("@/i18n", () => ({
  useTranslation: () => ({
    t: (_key: string, fallback?: string) => fallback ?? _key,
  }),
}));

interface ApiState {
  next?: Promise<unknown>;
  byBucket?: Record<string, unknown>;
  calls: string[];
}
const apiState: ApiState = { calls: [] };

vi.mock("@/lib/api-client", () => {
  const get = vi.fn((url: string) => {
    apiState.calls.push(url);
    if (apiState.byBucket) {
      const found = Object.entries(apiState.byBucket).find(([k]) =>
        url.includes(`bucket=${k}`),
      );
      if (found) return Promise.resolve(found[1]);
    }
    return apiState.next ?? Promise.resolve({ count: 0, items: [] });
  });
  const api = { get, post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() };
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

import CollectionVelocityCard from "@/components/admin/CollectionVelocityCard";

beforeEach(() => {
  apiState.next = undefined;
  apiState.byBucket = undefined;
  apiState.calls = [];
});

afterEach(() => {
  cleanup();
});

describe("CollectionVelocityCard", () => {
  it("renders the weed bucket by default with returned rows", async () => {
    apiState.next = Promise.resolve({
      bucket: "weed",
      limit: 10,
      count: 1,
      items: [
        {
          catalog_item_id: 1,
          title: "Cold Book",
          author: "A. Author",
          isbn: "9780000000001",
          checkouts_30d: 0,
          checkouts_90d: 0,
          checkouts_365d: 0,
          days_since_last_checkout: 720.4,
          holds_active: 0,
          holds_per_copy: null,
          total_copies: 4,
          last_refreshed_at: "2026-05-20T03:30:00+00:00",
        },
      ],
    });

    render(<CollectionVelocityCard />);
    await waitFor(() => {
      expect(screen.getByText("Cold Book")).toBeTruthy();
    });
    // Weed-bucket display shows copies + days since
    expect(screen.getByText(/Days since/)).toBeTruthy();
    // First call is for the default bucket=weed
    expect(apiState.calls[0]).toContain("bucket=weed");
  });

  it("switches bucket when buy_more tab is clicked", async () => {
    apiState.byBucket = {
      weed: { bucket: "weed", limit: 10, count: 0, items: [] },
      buy_more: {
        bucket: "buy_more",
        limit: 10,
        count: 1,
        items: [
          {
            catalog_item_id: 2,
            title: "Hot Title",
            author: "B. Author",
            isbn: null,
            checkouts_30d: 12,
            checkouts_90d: 30,
            checkouts_365d: 90,
            days_since_last_checkout: 1.0,
            holds_active: 9,
            holds_per_copy: 3.0,
            total_copies: 3,
            last_refreshed_at: "2026-05-20T03:30:00+00:00",
          },
        ],
      },
    };

    render(<CollectionVelocityCard />);
    // Wait for initial load (weed = empty)
    await waitFor(() => {
      expect(screen.getByText(/No items match this bucket yet/)).toBeTruthy();
    });

    // Click the Buy more tab
    fireEvent.click(screen.getByRole("tab", { name: "Buy more" }));

    await waitFor(() => {
      expect(screen.getByText("Hot Title")).toBeTruthy();
    });
    // Buy-more display shows holds + per copy
    expect(screen.getByText(/Per copy/)).toBeTruthy();
  });

  it("shows empty-state message when there are no items", async () => {
    apiState.next = Promise.resolve({
      bucket: "weed",
      limit: 10,
      count: 0,
      items: [],
    });

    render(<CollectionVelocityCard />);
    await waitFor(() => {
      expect(screen.getByText(/No items match this bucket yet/)).toBeTruthy();
    });
  });
});
