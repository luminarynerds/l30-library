/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeAll } from "vitest";
import { render } from "@testing-library/react";
import { I18nProvider } from "@/i18n/I18nContext";
import { OrganizationFeaturesProvider } from "@/contexts/OrganizationFeaturesContext";
import type { HubCategory } from "@/components/navigation/NavigationHub";

const capturedProps: { current: Record<string, unknown> | null } = { current: null };
vi.mock("@/components/navigation/NavigationHub", () => ({
  __esModule: true,
  default: (props: Record<string, unknown>) => {
    capturedProps.current = props;
    return null;
  },
}));

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
  return /\b(libraryHub|navigationHub|collectionHub|frontDeskHub|boardHub|adminSettingsHub|placeholder)\./.test(s);
}

describe("AdminSettingsHubPage i18n structural", () => {
  it("forwards translated title, search placeholder, itemNoun and category titles (no raw keys)", async () => {
    const { default: AdminSettingsHubPage } = await import("@/pages/AdminSettingsHubPage");
    render(
      <I18nProvider>
        <OrganizationFeaturesProvider>
          <AdminSettingsHubPage />
        </OrganizationFeaturesProvider>
      </I18nProvider>,
    );

    const props = capturedProps.current!;
    expect(props).toBeTruthy();

    expect(props.title).toBe("Settings Hub");
    expect(props.searchPlaceholder).toBe("Search settings...");
    expect(props.itemNoun).toEqual({ singular: "setting", plural: "settings" });

    for (const v of [props.title, props.searchPlaceholder] as unknown[]) {
      expect(isRawKeyLeak(v)).toBe(false);
    }

    const categories = props.categories as HubCategory[];
    expect(categories.length).toBeGreaterThan(0);

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

    // Spot-check specific known translations.
    const techAi = categories.find((c) => c.id === "technology-ai");
    expect(techAi?.title).toBe("Technology & AI");
    const aiSettings = techAi?.items.find((i) => i.to === "/staff/admin/ai");
    expect(aiSettings?.label).toBe("AI Settings");
  });
});
