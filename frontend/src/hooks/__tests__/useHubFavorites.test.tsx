/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";

// --- Mocks ---
const apiCalls: Array<{
  path: string;
  method: string;
  body?: string;
  params?: Record<string, unknown>;
}> = [];

// Two layers: the spy is the inner mock used to set up per-test resolutions;
// the outer wrapper records every call into `apiCalls` regardless of which
// resolution path runs.
const apiSpy = vi.fn();
// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function apiClientImpl(path: string, options: Record<string, unknown> = {}): Promise<any> {
  apiCalls.push({
    path,
    method: (options.method as string) ?? "GET",
    body: options.body as string | undefined,
    params: options.params as Record<string, unknown> | undefined,
  });
  return apiSpy(path, options);
}

vi.mock("@/lib/api-client", () => ({
  apiClient: (path: string, options?: Record<string, unknown>) => apiClientImpl(path, options),
}));

const mockAuth = { isAuthenticated: true };
vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => mockAuth,
}));

// Import after mocks so the hook uses them.
import { useHubFavorites } from "../useHubFavorites";

beforeEach(() => {
  apiCalls.length = 0;
  apiSpy.mockReset();
  apiSpy.mockResolvedValue([]);
  mockAuth.isAuthenticated = true;
});

describe("useHubFavorites", () => {
  it("fetches favorites for the given hub slug on mount", async () => {
    apiSpy.mockResolvedValueOnce([
      { id: "1", hub_slug: "report-hub", item_path: "/staff/reports", created_at: "" },
      { id: "2", hub_slug: "report-hub", item_path: "/staff/fines", created_at: "" },
    ]);

    const { result } = renderHook(() => useHubFavorites("report-hub"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(apiCalls[0]).toMatchObject({
      path: "/hub-favorites",
      method: "GET",
      params: { hub_slug: "report-hub" },
    });
    expect(result.current.favorites.has("/staff/reports")).toBe(true);
    expect(result.current.favorites.has("/staff/fines")).toBe(true);
    expect(result.current.isFavorite("/staff/reports")).toBe(true);
    expect(result.current.isFavorite("/missing")).toBe(false);
  });

  it("does not fetch when unauthenticated and toggle is a no-op", async () => {
    mockAuth.isAuthenticated = false;
    const { result } = renderHook(() => useHubFavorites("report-hub"));

    // No GET issued for unauthenticated users.
    expect(apiCalls.length).toBe(0);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.favorites.size).toBe(0);

    await act(async () => {
      await result.current.toggle("/staff/reports");
    });

    expect(apiCalls.length).toBe(0);
    expect(result.current.favorites.size).toBe(0);
  });

  it("toggle adds optimistically and POSTs the favorite", async () => {
    apiSpy.mockResolvedValueOnce([]); // initial GET
    apiSpy.mockResolvedValueOnce({
      id: "1",
      hub_slug: "report-hub",
      item_path: "/staff/reports",
      created_at: "",
    });

    const { result } = renderHook(() => useHubFavorites("report-hub"));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.toggle("/staff/reports");
    });

    // Final state: favorited.
    expect(result.current.favorites.has("/staff/reports")).toBe(true);

    // POST was made with the correct body.
    const post = apiCalls.find((c) => c.method === "POST");
    expect(post).toBeDefined();
    expect(post!.path).toBe("/hub-favorites");
    expect(JSON.parse(post!.body as string)).toEqual({
      hub_slug: "report-hub",
      item_path: "/staff/reports",
    });
  });

  it("toggle removes optimistically and DELETEs the favorite", async () => {
    apiSpy.mockResolvedValueOnce([
      { id: "1", hub_slug: "report-hub", item_path: "/staff/reports", created_at: "" },
    ]);
    apiSpy.mockResolvedValueOnce(null); // DELETE

    const { result } = renderHook(() => useHubFavorites("report-hub"));
    await waitFor(() => expect(result.current.favorites.has("/staff/reports")).toBe(true));

    await act(async () => {
      await result.current.toggle("/staff/reports");
    });

    expect(result.current.favorites.has("/staff/reports")).toBe(false);

    const del = apiCalls.find((c) => c.method === "DELETE");
    expect(del).toBeDefined();
    expect(JSON.parse(del!.body as string)).toEqual({
      hub_slug: "report-hub",
      item_path: "/staff/reports",
    });
  });

  it("rolls back optimistic add when the POST rejects", async () => {
    apiSpy.mockResolvedValueOnce([]); // initial GET
    apiSpy.mockRejectedValueOnce(new Error("boom")); // POST fails

    const { result } = renderHook(() => useHubFavorites("report-hub"));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.toggle("/staff/reports");
    });

    // Rolled back to NOT favorite.
    expect(result.current.favorites.has("/staff/reports")).toBe(false);
  });

  it("rolls back optimistic remove when the DELETE rejects", async () => {
    apiSpy.mockResolvedValueOnce([
      { id: "1", hub_slug: "report-hub", item_path: "/staff/reports", created_at: "" },
    ]);
    apiSpy.mockRejectedValueOnce(new Error("boom")); // DELETE fails

    const { result } = renderHook(() => useHubFavorites("report-hub"));
    await waitFor(() => expect(result.current.favorites.has("/staff/reports")).toBe(true));

    await act(async () => {
      await result.current.toggle("/staff/reports");
    });

    // Rolled back to STILL favorite.
    expect(result.current.favorites.has("/staff/reports")).toBe(true);
  });

  it("dedups concurrent toggles for the same itemPath", async () => {
    apiSpy.mockResolvedValueOnce([]); // initial GET
    // We only set up ONE POST mock. A second POST call (if dedup is broken)
    // would resolve via the default fn impl.
    let postResolve: ((v: unknown) => void) | null = null;
    const pendingPost = new Promise((res) => {
      postResolve = res;
    });
    apiSpy.mockReturnValueOnce(pendingPost);

    const { result } = renderHook(() => useHubFavorites("report-hub"));
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    let firstToggle!: Promise<void>;
    let secondToggle!: Promise<void>;
    await act(async () => {
      firstToggle = result.current.toggle("/staff/reports");
      // Second toggle while the first is still in-flight: should be deduped.
      secondToggle = result.current.toggle("/staff/reports");
    });

    // Resolve the pending POST so the awaits unwind.
    await act(async () => {
      postResolve!({
        id: "1",
        hub_slug: "report-hub",
        item_path: "/staff/reports",
        created_at: "",
      });
      await firstToggle;
      await secondToggle;
    });

    // Only ONE POST should have happened (the duplicate was deduped).
    const posts = apiCalls.filter((c) => c.method === "POST");
    expect(posts.length).toBe(1);
    expect(result.current.favorites.has("/staff/reports")).toBe(true);
  });
});
