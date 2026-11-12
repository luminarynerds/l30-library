/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeAll } from "vitest";
import { render } from "@testing-library/react";
import { I18nProvider } from "@/i18n/I18nContext";
import type { HubCategory } from "@/components/navigation/NavigationHub";

// Capture the props that LibraryHubPage forwards to NavigationHub so we can
// assert (a) every visible string is translated and (b) no raw i18n key prefix
// leaks through. Mock the component itself — we don't care about render here.
const capturedProps: { current: Record<string, unknown> | null } = { current: null };
vi.mock("@/components/navigation/NavigationHub", () => ({
  __esModule: true,
  default: (props: Record<string, unknown>) => {
    capturedProps.current = props;
    return null;
  },
}));

// I18nContext needs branding defaults and a no-op token store.
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

beforeAll(async () => {
});

function isRawKeyLeak(s: unknown): boolean {
  if (typeof s !== "string") return false;
  // Heuristic: a raw key looks like one of our namespaces followed by a dot
  // and an identifier (no spaces). Real English never contains "namespace.x".
  return /\b(libraryHub|navigationHub|collectionHub|frontDeskHub|boardHub|adminSettingsHub|placeholder)\./.test(s);
}

describe("LibraryHubPage i18n structural", () => {
  it("forwards translated title, search placeholder and category titles (no raw keys)", async () => {
    const { default: LibraryHubPage } = await import("@/pages/LibraryHubPage");
    render(
      <I18nProvider>
        <LibraryHubPage />
      </I18nProvider>,
    );

    const props = capturedProps.current!;
    expect(props).toBeTruthy();

    // Top-level strings translate to English. #1409 retitled this page from
    // "Library Hub" to "Programs" (en.json libraryHub.title).
    expect(props.title).toBe("Programs");
    expect(props.searchPlaceholder).toBe("Search library...");
    expect(isRawKeyLeak(props.title)).toBe(false);
    expect(isRawKeyLeak(props.searchPlaceholder)).toBe(false);

    const categories = props.categories as HubCategory[];
    expect(categories.length).toBeGreaterThan(0);

    // Every category title + every item label/description is a real English
    // string (no raw key prefix leaked).
    for (const cat of categories) {
      expect(isRawKeyLeak(cat.title)).toBe(false);
      expect(cat.title.length).toBeGreaterThan(0);
      for (const item of cat.items) {
        expect(isRawKeyLeak(item.label)).toBe(false);
        expect(item.label.length).toBeGreaterThan(0);
        if (item.description !== undefined) {
          expect(isRawKeyLeak(item.description)).toBe(false);
          expect(item.description.length).toBeGreaterThan(0);
        }
      }
    }

    // Spot-check at least one specific translation flowed through end-to-end.
    const programs = categories.find((c) => c.id === "programs");
    expect(programs?.title).toBe("Programs");
    const events = programs?.items.find((i) => i.to === "/staff/events");
    expect(events?.label).toBe("Events");
    expect(events?.description).toBe("Browse and manage library events");
  });
});
