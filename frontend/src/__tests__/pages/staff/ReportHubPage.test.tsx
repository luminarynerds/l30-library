/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { I18nProvider } from "@/i18n/I18nContext";
import type { HubCategory } from "@/components/navigation/NavigationHub";

// --- Mocks ---
const apiCalls: Array<{ path: string; method: string; body?: string }> = [];
const apiSpy = vi.fn();
// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function apiClientImpl(path: string, options: Record<string, unknown> = {}): Promise<any> {
  apiCalls.push({
    path,
    method: (options.method as string) ?? "GET",
    body: options.body as string | undefined,
  });
  return apiSpy(path, options);
}

vi.mock("@/lib/api-client", () => ({
  apiClient: (path: string, options?: Record<string, unknown>) => apiClientImpl(path, options),
}));

const mockAuth: {
  isAuthenticated: boolean;
  user: { role: string; is_board_member?: boolean };
} = { isAuthenticated: true, user: { role: "admin" } };
vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => mockAuth,
}));

// Capture props passed to NavigationHub.
const capturedProps: { current: Record<string, unknown> | null } = { current: null };
vi.mock("@/components/navigation/NavigationHub", () => ({
  __esModule: true,
  default: (props: Record<string, unknown>) => {
    capturedProps.current = props;
    return null;
  },
}));

// ReportScheduleModal is heavyweight; stub it.
vi.mock("../../../components/reports/ReportScheduleModal", () => ({
  __esModule: true,
  default: () => null,
}));

// I18n / Branding noise.
vi.mock("@/contexts/BrandingContext", () => ({
  useBrandingContext: () => ({
    branding: {
      library_name: "Library",
      library_short_name: "Library",
      contact_email: "",
      privacy_email: "",
      giving_email: "",
      phone: "",
      address_line1: "",
      address_line2: "",
      card_prefix: "",
    },
    loading: false,
    setupComplete: true,
    hasAdmin: true,
    refetch: vi.fn(),
  }),
}));
vi.mock("@/utils/tokenStore", () => ({ getAccessToken: () => null }));

// The global setup.ts replaces window.localStorage with naked vi.fn()s.
// Restore a real in-memory store for these tests so the migration code can
// actually read/write the legacy key.
const localStorageStore = new Map<string, string>();
beforeAll(async () => {
  Object.defineProperty(window, "localStorage", {
    configurable: true,
    value: {
      getItem: (k: string) => (localStorageStore.has(k) ? localStorageStore.get(k)! : null),
      setItem: (k: string, v: string) => {
        localStorageStore.set(k, String(v));
      },
      removeItem: (k: string) => {
        localStorageStore.delete(k);
      },
      clear: () => {
        localStorageStore.clear();
      },
      key: (i: number) => Array.from(localStorageStore.keys())[i] ?? null,
      get length() {
        return localStorageStore.size;
      },
    },
  });
});

beforeEach(() => {
  apiCalls.length = 0;
  localStorageStore.clear();
  apiSpy.mockReset();
  apiSpy.mockImplementation((_path: string, options: Record<string, unknown> = {}) => {
    if ((options.method as string) === "POST") {
      return Promise.resolve({
        id: "fake-id",
        hub_slug: "report-hub",
        item_path: JSON.parse((options.body as string) ?? "{}").item_path,
        created_at: "2026-05-18T00:00:00Z",
      });
    }
    return Promise.resolve([]);
  });
  capturedProps.current = null;
  mockAuth.isAuthenticated = true;
  mockAuth.user = { role: "admin" };
  try {
    window.localStorage.removeItem("l30-report-hub-favorites");
  } catch {
    // ignore
  }
});

async function renderPage() {
  const { default: ReportHubPage } = await import("@/pages/staff/ReportHubPage");
  return render(
    <I18nProvider>
      <MemoryRouter>
        <ReportHubPage />
      </MemoryRouter>
    </I18nProvider>,
  );
}

describe("ReportHubPage", () => {
  it("renders all 8 categories with translated titles", async () => {
    await renderPage();
    const props = capturedProps.current!;
    expect(props).toBeTruthy();
    expect(props.title).toBe("Report Hub");
    expect(props.searchPlaceholder).toBe("Search reports...");

    const categories = props.categories as HubCategory[];
    expect(categories.length).toBe(8);
    const titles = categories.map((c) => c.title);
    expect(titles).toEqual([
      "Circulation",
      "Financial",
      "Patrons",
      "Collection",
      "Operations",
      "Compliance & State Reporting",
      "Board Reporting",
      "Strategic & Performance",
    ]);
  });

  it("hides admin-only report cards from roles that can't open them", async () => {
    // 'legal' can open the hub (a staff-area role) but holds none of the
    // admin/director/staff roles the restricted destinations require.
    mockAuth.user = { role: "legal" };
    await renderPage();
    const categories = capturedProps.current!.categories as HubCategory[];
    const titles = categories.map((c) => c.title);
    // Categories whose every item is admin/staff-gated drop out entirely.
    expect(titles).not.toContain("Compliance & State Reporting");
    expect(titles).not.toContain("Board Reporting");
    // No restricted destination leaks through any surviving category.
    const paths = categories.flatMap((c) => c.items.map((i) => i.to.split("#")[0]));
    expect(paths).not.toContain("/staff/admin/compliance");
    expect(paths).not.toContain("/staff/admin/financial");
    expect(paths).not.toContain("/staff/admin/treasurer");
    // Unrestricted cards still show.
    expect(paths).toContain("/staff/reports");
  });

  it("forwards favorites prop with the report-hub slug", async () => {
    await renderPage();
    const props = capturedProps.current!;
    expect(props.favorites).toEqual({ hubSlug: "report-hub" });
  });

  it("forwards a headerAction button labelled 'Schedule report'", async () => {
    await renderPage();
    const props = capturedProps.current!;
    expect(props.headerAction).toBeDefined();
    // Render the action node and look for the label.
    render(<>{props.headerAction as React.ReactNode}</>);
    expect(screen.getByRole("button", { name: /Schedule report/i })).toBeInTheDocument();
  });

  it("each category has at least one item and reports total ~34", async () => {
    await renderPage();
    const categories = capturedProps.current!.categories as HubCategory[];
    const total = categories.reduce((s, c) => s + c.items.length, 0);
    expect(total).toBeGreaterThanOrEqual(34);
    for (const cat of categories) {
      expect(cat.items.length).toBeGreaterThan(0);
    }
  });

  it("does NOT POST migrations when localStorage is empty", async () => {
    await renderPage();
    // Wait a microtask for the effect.
    await waitFor(() => {
      // Only no POSTs should be observed.
      const posts = apiCalls.filter((c) => c.method === "POST");
      expect(posts.length).toBe(0);
    });
  });

  it("migrates localStorage favorites to the server and clears the key", async () => {
    window.localStorage.setItem(
      "l30-report-hub-favorites",
      JSON.stringify(["/staff/reports", "/staff/fines"]),
    );

    await renderPage();

    await waitFor(() => {
      const posts = apiCalls.filter((c) => c.method === "POST");
      expect(posts.length).toBe(2);
    });

    const bodies = apiCalls
      .filter((c) => c.method === "POST")
      .map((c) => JSON.parse(c.body as string));
    expect(bodies).toEqual(
      expect.arrayContaining([
        { hub_slug: "report-hub", item_path: "/staff/reports" },
        { hub_slug: "report-hub", item_path: "/staff/fines" },
      ]),
    );

    // Wait until cleared (after all POSTs resolve).
    await waitFor(() => {
      expect(window.localStorage.getItem("l30-report-hub-favorites")).toBeNull();
    });
  });

  it("does NOT migrate when unauthenticated", async () => {
    mockAuth.isAuthenticated = false;
    window.localStorage.setItem(
      "l30-report-hub-favorites",
      JSON.stringify(["/staff/reports"]),
    );

    await renderPage();
    // The migration effect should be skipped.
    await waitFor(() => {
      const posts = apiCalls.filter((c) => c.method === "POST");
      expect(posts.length).toBe(0);
    });
    // localStorage is preserved so the migration can run after sign-in.
    expect(window.localStorage.getItem("l30-report-hub-favorites")).not.toBeNull();
  });

  it("preserves localStorage when a migration POST fails", async () => {
    window.localStorage.setItem(
      "l30-report-hub-favorites",
      JSON.stringify(["/staff/reports"]),
    );
    apiSpy.mockRejectedValueOnce(new Error("server down"));

    await renderPage();
    await waitFor(() => {
      const posts = apiCalls.filter((c) => c.method === "POST");
      expect(posts.length).toBe(1);
    });

    // Failure means the key stays so the next mount retries.
    expect(window.localStorage.getItem("l30-report-hub-favorites")).not.toBeNull();
  });

  it("drops a corrupt localStorage blob without POSTing", async () => {
    window.localStorage.setItem("l30-report-hub-favorites", "not-json");

    await renderPage();
    await waitFor(() => {
      // Corrupt input gets removed; no POSTs.
      expect(window.localStorage.getItem("l30-report-hub-favorites")).toBeNull();
    });
    expect(apiCalls.filter((c) => c.method === "POST").length).toBe(0);
  });
});
