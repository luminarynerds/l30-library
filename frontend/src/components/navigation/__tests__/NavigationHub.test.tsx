/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeAll, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { Book, Folder, Star } from "lucide-react";
import NavigationHub, { type HubCategory } from "../NavigationHub";
import { I18nProvider } from "@/i18n/I18nContext";

// Mock AdminShell to avoid pulling StaffLayout into the test render graph.
vi.mock("../../shells", () => ({
  AdminShell: ({
    children,
    title,
    subtitle,
    actions,
  }: {
    children: React.ReactNode;
    title: string;
    subtitle?: string;
    actions?: React.ReactNode;
  }) => (
    <div>
      <h1>{title}</h1>
      {subtitle && <p data-testid="subtitle">{subtitle}</p>}
      {actions && <div data-testid="header-action">{actions}</div>}
      {children}
    </div>
  ),
}));

// Mock OrganizationFeatures so tests can control flag state.
const mockIsFeatureEnabled = vi.fn();
vi.mock("../../../contexts/OrganizationFeaturesContext", async () => {
  const actual = await vi.importActual<typeof import("../../../contexts/OrganizationFeaturesContext")>(
    "../../../contexts/OrganizationFeaturesContext",
  );
  return {
    ...actual,
    useOrganizationFeatures: () => ({
      features: null,
      loading: false,
      fetchFeatures: vi.fn(),
      isFeatureEnabled: mockIsFeatureEnabled,
    }),
  };
});

// Mock BrandingContext so I18nProvider's branding-defaults lookup doesn't
// require mounting BrandingProvider + its async fetch.
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

// Mock token store so I18nProvider's API call short-circuits.
vi.mock("@/utils/tokenStore", () => ({
  getAccessToken: () => null,
}));

// Mock the favorites hook so tests can control its return value without
// hitting the api-client / AuthContext stack. Default = empty favorites,
// toggle is a spy.
const mockFavoritesState: {
  favorites: Set<string>;
  toggle: ReturnType<typeof vi.fn>;
  isLoading: boolean;
} = {
  favorites: new Set<string>(),
  toggle: vi.fn(),
  isLoading: false,
};
vi.mock("../../../hooks/useHubFavorites", () => ({
  useHubFavorites: () => ({
    favorites: mockFavoritesState.favorites,
    isLoading: mockFavoritesState.isLoading,
    toggle: mockFavoritesState.toggle,
    isFavorite: (p: string) => mockFavoritesState.favorites.has(p),
  }),
}));

function wrap(ui: React.ReactElement) {
  return render(
    <I18nProvider>
      <MemoryRouter>{ui}</MemoryRouter>
    </I18nProvider>,
  );
}

const baseCategories: HubCategory[] = [
  {
    id: "alpha",
    title: "Alpha",
    icon: Folder,
    items: [
      { to: "/alpha/one", label: "Alpha One", description: "First alpha item", icon: Book },
      { to: "/alpha/two", label: "Alpha Two", description: "Second alpha item", icon: Book },
    ],
  },
  {
    id: "beta",
    title: "Beta",
    icon: Folder,
    items: [
      { to: "/beta/one", label: "Beta One", description: "First beta item", icon: Star },
    ],
  },
];

// vitest setup.ts doesn't preload i18n. NavigationHub now uses useTranslation
// for default item-noun, search placeholder result count, jump-list aria-labels
// and the empty-state copy, so English must be loaded before any render.
beforeAll(async () => {
});

beforeEach(() => {
  mockIsFeatureEnabled.mockReset();
  mockIsFeatureEnabled.mockReturnValue(true);
  mockFavoritesState.favorites = new Set<string>();
  mockFavoritesState.isLoading = false;
  mockFavoritesState.toggle = vi.fn();
});

describe("NavigationHub", () => {
  describe("Rendering & default state", () => {
    it("renders categories with default-closed state (items not visible)", () => {
      wrap(<NavigationHub title="Test Hub" categories={baseCategories} />);

      // Category headers visible
      expect(screen.getByRole("heading", { name: "Alpha" })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Beta" })).toBeInTheDocument();

      // aria-expanded is false on each header button
      const alphaButton = screen.getByRole("button", { name: /Alpha/i });
      expect(alphaButton).toHaveAttribute("aria-expanded", "false");

      // Items NOT in the DOM (collapsed)
      expect(screen.queryByText("Alpha One")).not.toBeInTheDocument();
      expect(screen.queryByText("Beta One")).not.toBeInTheDocument();
    });

    it("auto-computes subtitle from total items and category count", () => {
      wrap(<NavigationHub title="Test Hub" categories={baseCategories} />);
      expect(screen.getByTestId("subtitle").textContent).toBe("3 items across 2 categories");
    });

    it("uses custom itemNoun in subtitle and per-card counts", () => {
      wrap(
        <NavigationHub
          title="Test Hub"
          categories={baseCategories}
          itemNoun={{ singular: "tool", plural: "tools" }}
        />,
      );
      expect(screen.getByTestId("subtitle").textContent).toBe("3 tools across 2 categories");
      // Per-card "N tools" line
      expect(screen.getByText("2 tools")).toBeInTheDocument();
      expect(screen.getByText("1 tool")).toBeInTheDocument();
    });

    it("respects an explicit subtitle override", () => {
      wrap(<NavigationHub title="Test Hub" subtitle="custom subtitle" categories={baseCategories} />);
      expect(screen.getByTestId("subtitle").textContent).toBe("custom subtitle");
    });

    it("renders a defaultOpen category as expanded on first render", () => {
      const cats: HubCategory[] = [
        { ...baseCategories[0]!, defaultOpen: true },
        baseCategories[1]!,
      ];
      wrap(<NavigationHub title="Test Hub" categories={cats} />);
      expect(screen.getByText("Alpha One")).toBeInTheDocument();
      expect(screen.queryByText("Beta One")).not.toBeInTheDocument();
    });
  });

  describe("Accordion behavior", () => {
    it("flips aria-expanded when toggle button is clicked", async () => {
      const user = userEvent.setup();
      wrap(<NavigationHub title="Test Hub" categories={baseCategories} />);

      const alphaButton = screen.getByRole("button", { name: /Alpha/i });
      expect(alphaButton).toHaveAttribute("aria-expanded", "false");

      await user.click(alphaButton);
      expect(alphaButton).toHaveAttribute("aria-expanded", "true");
      expect(screen.getByText("Alpha One")).toBeInTheDocument();

      await user.click(alphaButton);
      expect(alphaButton).toHaveAttribute("aria-expanded", "false");
      expect(screen.queryByText("Alpha One")).not.toBeInTheDocument();
    });
  });

  describe("Search", () => {
    it("does not render the search input when searchPlaceholder is omitted", () => {
      wrap(<NavigationHub title="Test Hub" categories={baseCategories} />);
      expect(screen.queryByPlaceholderText(/search/i)).not.toBeInTheDocument();
    });

    it("renders the search input when searchPlaceholder is provided", () => {
      wrap(
        <NavigationHub title="Test Hub" categories={baseCategories} searchPlaceholder="Search test..." />,
      );
      expect(screen.getByPlaceholderText("Search test...")).toBeInTheDocument();
    });

    it("auto-expands matching categories and hides non-matches during search", async () => {
      const user = userEvent.setup();
      wrap(
        <NavigationHub title="Test Hub" categories={baseCategories} searchPlaceholder="Search..." />,
      );

      const input = screen.getByPlaceholderText("Search...");
      await user.type(input, "Alpha");

      // Alpha header still there and auto-expanded
      const alphaButton = screen.getByRole("button", { name: /Alpha/i });
      expect(alphaButton).toHaveAttribute("aria-expanded", "true");
      // Alpha items now visible
      expect(screen.getByText("Alpha One")).toBeInTheDocument();
      expect(screen.getByText("Alpha Two")).toBeInTheDocument();
      // Beta category is filtered out entirely
      expect(screen.queryByRole("heading", { name: "Beta" })).not.toBeInTheDocument();
    });

    it("shows an empty state when search has no matches", async () => {
      const user = userEvent.setup();
      wrap(
        <NavigationHub title="Test Hub" categories={baseCategories} searchPlaceholder="Search..." />,
      );

      const input = screen.getByPlaceholderText("Search...");
      await user.type(input, "zzzzz-nothing");

      expect(screen.getByText(/No items match/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Clear search/i })).toBeInTheDocument();
    });

    it("renders result count when searching", async () => {
      const user = userEvent.setup();
      wrap(
        <NavigationHub title="Test Hub" categories={baseCategories} searchPlaceholder="Search..." />,
      );
      const input = screen.getByPlaceholderText("Search...");
      await user.type(input, "Alpha");
      expect(screen.getByText(/2 results?/)).toBeInTheDocument();
    });
  });

  describe("Feature-flag gating", () => {
    it("hides items whose featureFlag is disabled", async () => {
      const user = userEvent.setup();
      mockIsFeatureEnabled.mockImplementation((flag: string) => flag !== "events_enabled");

      const cats: HubCategory[] = [
        {
          id: "mixed",
          title: "Mixed",
          icon: Folder,
          items: [
            { to: "/a", label: "Always Visible", icon: Book },
            { to: "/b", label: "Flag Hidden", icon: Book, featureFlag: "events_enabled" },
          ],
        },
      ];
      wrap(<NavigationHub title="Test Hub" categories={cats} />);

      // Open the category
      await user.click(screen.getByRole("button", { name: /Mixed/i }));

      expect(screen.getByText("Always Visible")).toBeInTheDocument();
      expect(screen.queryByText("Flag Hidden")).not.toBeInTheDocument();
    });

    it("hides an entirely-flag-gated category", () => {
      mockIsFeatureEnabled.mockReturnValue(false);

      const cats: HubCategory[] = [
        {
          id: "all-gated",
          title: "All Gated",
          icon: Folder,
          items: [{ to: "/x", label: "Gated", icon: Book, featureFlag: "events_enabled" }],
        },
        {
          id: "open",
          title: "Open",
          icon: Folder,
          items: [{ to: "/y", label: "Always", icon: Book }],
        },
      ];
      wrap(<NavigationHub title="Test Hub" categories={cats} />);

      expect(screen.queryByRole("heading", { name: "All Gated" })).not.toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Open" })).toBeInTheDocument();
    });
  });

  describe("Column prop", () => {
    it("renders a 2-column grid by default", () => {
      const { container } = wrap(<NavigationHub title="Test Hub" categories={baseCategories} />);
      const grid = container.querySelector(".grid");
      expect(grid).toHaveClass("grid-cols-1", "md:grid-cols-2");
      expect(grid).not.toHaveClass("xl:grid-cols-3");
    });

    it("renders a 3-column grid when columns={3}", () => {
      const { container } = wrap(
        <NavigationHub title="Test Hub" categories={baseCategories} columns={3} />,
      );
      const grid = container.querySelector(".grid");
      expect(grid).toHaveClass("grid-cols-1", "md:grid-cols-2", "xl:grid-cols-3");
    });
  });

  describe("Forward-hook props", () => {
    it("renders headerAction in the shell header slot", () => {
      wrap(
        <NavigationHub
          title="Test Hub"
          categories={baseCategories}
          headerAction={<button>Action</button>}
        />,
      );
      const slot = screen.getByTestId("header-action");
      expect(slot).toContainElement(screen.getByRole("button", { name: "Action" }));
    });

    it("renders beforeGrid above the grid", () => {
      wrap(
        <NavigationHub
          title="Test Hub"
          categories={baseCategories}
          beforeGrid={<div data-testid="custom-widget">Custom Widget</div>}
        />,
      );
      expect(screen.getByTestId("custom-widget")).toBeInTheDocument();
    });

    it("renders item badge when provided", async () => {
      const user = userEvent.setup();
      const cats: HubCategory[] = [
        {
          id: "cat",
          title: "Cat",
          icon: Folder,
          items: [{ to: "/x", label: "Badged Item", icon: Book, badge: "NEW" }],
        },
      ];
      wrap(<NavigationHub title="Test Hub" categories={cats} />);
      await user.click(screen.getByRole("button", { name: /Cat/i }));
      expect(screen.getByText("NEW")).toBeInTheDocument();
    });

    it("uses itemSlot to render a custom item when it returns a node", async () => {
      const user = userEvent.setup();
      const cats: HubCategory[] = [
        {
          id: "cat",
          title: "Cat",
          icon: Folder,
          items: [{ to: "/x", label: "Original", icon: Book }],
        },
      ];
      wrap(
        <NavigationHub
          title="Test Hub"
          categories={cats}
          itemSlot={(item) => <span data-testid="slot">slot-{item.label}</span>}
        />,
      );
      await user.click(screen.getByRole("button", { name: /Cat/i }));
      expect(screen.getByTestId("slot").textContent).toBe("slot-Original");
      // Default row not rendered when slot returns a node
      expect(screen.queryByRole("link", { name: /Original/i })).not.toBeInTheDocument();
    });
  });

  describe("Item rendering", () => {
    it("renders items without icons gracefully (AdminSettingsHub case)", async () => {
      const user = userEvent.setup();
      const cats: HubCategory[] = [
        {
          id: "cat",
          title: "Cat",
          icon: Folder,
          items: [{ to: "/x", label: "Iconless", description: "no icon here" }],
        },
      ];
      wrap(<NavigationHub title="Test Hub" categories={cats} />);
      await user.click(screen.getByRole("button", { name: /Cat/i }));

      const link = screen.getByRole("link", { name: /Iconless/i });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute("href", "/x");
    });
  });

  describe("persistExpansion (URL hash sync)", () => {
    const originalReplaceState = window.history.replaceState;
    let replaceStateSpy: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      // Reset URL to a clean path for each test.
      window.history.replaceState({}, "", "/test-hub");
      replaceStateSpy = vi.fn(originalReplaceState.bind(window.history));
      window.history.replaceState = replaceStateSpy as unknown as typeof window.history.replaceState;
    });

    afterEach(() => {
      window.history.replaceState = originalReplaceState;
      window.history.replaceState({}, "", "/");
    });

    it("does not sync to URL when persistExpansion is false (default)", async () => {
      const user = userEvent.setup();
      wrap(<NavigationHub title="Test Hub" categories={baseCategories} />);

      await user.click(screen.getByRole("button", { name: /Alpha/i }));

      // No ?open= param written
      expect(window.location.search).toBe("");
    });

    it("hydrates expanded state from ?open= on mount", () => {
      window.history.replaceState({}, "", "/test-hub?open=beta");

      wrap(
        <NavigationHub title="Test Hub" categories={baseCategories} persistExpansion />,
      );

      // Beta is open: its items are visible
      expect(screen.getByText("Beta One")).toBeInTheDocument();
      // Alpha is still closed
      expect(screen.queryByText("Alpha One")).not.toBeInTheDocument();
    });

    it("hydrates multiple categories from comma-separated ?open=", () => {
      window.history.replaceState({}, "", "/test-hub?open=alpha,beta");

      wrap(
        <NavigationHub title="Test Hub" categories={baseCategories} persistExpansion />,
      );

      expect(screen.getByText("Alpha One")).toBeInTheDocument();
      expect(screen.getByText("Beta One")).toBeInTheDocument();
    });

    it("URL hydration overrides defaultOpen", () => {
      window.history.replaceState({}, "", "/test-hub?open=beta");
      const cats: HubCategory[] = [
        { ...baseCategories[0]!, defaultOpen: true },
        baseCategories[1]!,
      ];

      wrap(<NavigationHub title="Test Hub" categories={cats} persistExpansion />);

      // defaultOpen alpha is overridden -> closed; beta from URL -> open
      expect(screen.queryByText("Alpha One")).not.toBeInTheDocument();
      expect(screen.getByText("Beta One")).toBeInTheDocument();
    });

    it("ignores unknown category ids in ?open=", () => {
      window.history.replaceState({}, "", "/test-hub?open=alpha,bogus");

      wrap(
        <NavigationHub title="Test Hub" categories={baseCategories} persistExpansion />,
      );

      expect(screen.getByText("Alpha One")).toBeInTheDocument();
      expect(screen.queryByText("Beta One")).not.toBeInTheDocument();
    });

    it("falls back to defaultOpen when ?open= is missing", () => {
      const cats: HubCategory[] = [
        { ...baseCategories[0]!, defaultOpen: true },
        baseCategories[1]!,
      ];

      wrap(<NavigationHub title="Test Hub" categories={cats} persistExpansion />);

      expect(screen.getByText("Alpha One")).toBeInTheDocument();
    });

    it("writes ?open= via replaceState when user toggles a category", async () => {
      const user = userEvent.setup();
      wrap(
        <NavigationHub title="Test Hub" categories={baseCategories} persistExpansion />,
      );

      await user.click(screen.getByRole("button", { name: /Alpha/i }));

      const params = new URLSearchParams(window.location.search);
      expect(params.get("open")).toBe("alpha");

      // replaceState was used (not pushState)
      expect(replaceStateSpy).toHaveBeenCalled();
    });

    it("removes ?open= when user collapses the last expanded category", async () => {
      const user = userEvent.setup();
      window.history.replaceState({}, "", "/test-hub?open=alpha");

      wrap(
        <NavigationHub title="Test Hub" categories={baseCategories} persistExpansion />,
      );

      // Sanity: hydrated open
      expect(screen.getByText("Alpha One")).toBeInTheDocument();

      // User collapses
      await user.click(screen.getByRole("button", { name: /Alpha/i }));

      expect(new URLSearchParams(window.location.search).has("open")).toBe(false);
    });

    it("preserves unrelated query params when writing ?open=", async () => {
      const user = userEvent.setup();
      window.history.replaceState({}, "", "/test-hub?ref=email");

      wrap(
        <NavigationHub title="Test Hub" categories={baseCategories} persistExpansion />,
      );

      await user.click(screen.getByRole("button", { name: /Alpha/i }));

      const params = new URLSearchParams(window.location.search);
      expect(params.get("ref")).toBe("email");
      expect(params.get("open")).toBe("alpha");
    });

    it("search-triggered expansion does NOT pollute ?open=", async () => {
      const user = userEvent.setup();
      wrap(
        <NavigationHub
          title="Test Hub"
          categories={baseCategories}
          searchPlaceholder="Search..."
          persistExpansion
        />,
      );

      const input = screen.getByPlaceholderText("Search...");
      await user.type(input, "Alpha");

      // Alpha is visually expanded by search...
      expect(screen.getByText("Alpha One")).toBeInTheDocument();
      // ...but ?open= is NOT set
      expect(new URLSearchParams(window.location.search).has("open")).toBe(false);
    });
  });

  describe("Jump-to-category list", () => {
    function makeCats(n: number, itemsPer = 1): HubCategory[] {
      return Array.from({ length: n }, (_, i) => ({
        id: `cat-${i}`,
        title: `Cat ${i}`,
        icon: Folder,
        items: Array.from({ length: itemsPer }, (_, j) => ({
          to: `/c${i}/${j}`,
          label: `Item ${i}-${j}`,
          icon: Book,
        })),
      }));
    }

    beforeEach(() => {
      // Ensure scrollIntoView exists on Element prototype (jsdom omits it).
      Element.prototype.scrollIntoView = vi.fn();
    });

    it("does NOT render when below both thresholds", () => {
      wrap(<NavigationHub title="Test Hub" categories={baseCategories} />);
      expect(screen.queryByTestId("hub-jump-list")).not.toBeInTheDocument();
    });

    it("renders when categories >= 6", () => {
      wrap(<NavigationHub title="Test Hub" categories={makeCats(6, 1)} />);
      expect(screen.getByTestId("hub-jump-list")).toBeInTheDocument();
    });

    it("renders when totalItems >= 30 (categories < 6)", () => {
      // 3 categories x 10 items = 30 items
      wrap(<NavigationHub title="Test Hub" categories={makeCats(3, 10)} />);
      expect(screen.getByTestId("hub-jump-list")).toBeInTheDocument();
    });

    it("does NOT render when hideJumpList=true even if thresholds met", () => {
      wrap(<NavigationHub title="Test Hub" categories={makeCats(8, 1)} hideJumpList />);
      expect(screen.queryByTestId("hub-jump-list")).not.toBeInTheDocument();
    });

    it("is hidden during active search", async () => {
      const user = userEvent.setup();
      wrap(
        <NavigationHub
          title="Test Hub"
          categories={makeCats(6, 1)}
          searchPlaceholder="Search..."
        />,
      );
      expect(screen.getByTestId("hub-jump-list")).toBeInTheDocument();
      await user.type(screen.getByPlaceholderText("Search..."), "Cat 0");
      expect(screen.queryByTestId("hub-jump-list")).not.toBeInTheDocument();
    });

    it("each anchor has descriptive aria-label with title and item count", () => {
      wrap(<NavigationHub title="Test Hub" categories={makeCats(6, 3)} />);
      const anchor = screen.getByRole("button", { name: /Jump to Cat 0 \(3 items\)/i });
      expect(anchor).toBeInTheDocument();
    });

    it("clicking an anchor expands the target category AND calls scrollIntoView", async () => {
      const user = userEvent.setup();
      const scrollSpy = vi.fn();
      Element.prototype.scrollIntoView = scrollSpy;

      wrap(<NavigationHub title="Test Hub" categories={makeCats(6, 1)} />);

      // Item 3-0 not visible (cat-3 starts collapsed)
      expect(screen.queryByText("Item 3-0")).not.toBeInTheDocument();

      await user.click(screen.getByRole("button", { name: /Jump to Cat 3/i }));

      // Category expanded
      expect(screen.getByText("Item 3-0")).toBeInTheDocument();
      // scrollIntoView called
      expect(scrollSpy).toHaveBeenCalled();
    });

    it("uses smooth scroll by default", async () => {
      const user = userEvent.setup();
      const scrollSpy = vi.fn();
      Element.prototype.scrollIntoView = scrollSpy;

      wrap(<NavigationHub title="Test Hub" categories={makeCats(6, 1)} />);
      await user.click(screen.getByRole("button", { name: /Jump to Cat 1/i }));

      expect(scrollSpy).toHaveBeenCalledWith(expect.objectContaining({ behavior: "smooth" }));
    });

    it("uses non-smooth scroll when prefers-reduced-motion is set", async () => {
      const user = userEvent.setup();
      const scrollSpy = vi.fn();
      Element.prototype.scrollIntoView = scrollSpy;

      // Override the matchMedia mock for this test only.
      const originalMatchMedia = window.matchMedia;
      window.matchMedia = vi.fn().mockImplementation((q: string) => ({
        matches: q.includes("prefers-reduced-motion: reduce"),
        media: q,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })) as unknown as typeof window.matchMedia;

      try {
        wrap(<NavigationHub title="Test Hub" categories={makeCats(6, 1)} />);
        await user.click(screen.getByRole("button", { name: /Jump to Cat 1/i }));

        expect(scrollSpy).toHaveBeenCalledWith(expect.objectContaining({ behavior: "auto" }));
      } finally {
        window.matchMedia = originalMatchMedia;
      }
    });
  });

  // -----------------------------------------------------------------
  // i18n coverage: assert NavigationHub-internal strings come from t()
  // and not raw keys leaking to the UI. Three deliberate cases per the
  // i18n sweep deliverable.
  // -----------------------------------------------------------------
  describe("i18n", () => {
    it("renders the translated search placeholder when provided (no raw key leak)", () => {
      wrap(
        <NavigationHub
          title="Test Hub"
          categories={baseCategories}
          searchPlaceholder="Search test..."
        />,
      );
      // The page passes a translated literal; here we just sanity-check that
      // the placeholder reaches the DOM unchanged and no raw key prefix leaks
      // through (e.g. "navigationHub.").
      const input = screen.getByPlaceholderText("Search test...") as HTMLInputElement;
      expect(input.placeholder).toBe("Search test...");
      expect(input.placeholder).not.toMatch(/^navigationHub\./);
    });

    it("renders the translated empty-state copy (not the raw key)", async () => {
      const user = userEvent.setup();
      wrap(
        <NavigationHub
          title="Test Hub"
          categories={baseCategories}
          searchPlaceholder="Search..."
        />,
      );
      await user.type(screen.getByPlaceholderText("Search..."), "zzzzz-nothing");

      // English copy of navigationHub.noMatchesFor
      const emptyMsg = screen.getByText(/No items match/);
      expect(emptyMsg).toBeInTheDocument();
      // Curly quotes from translation, not raw key
      expect(emptyMsg.textContent ?? "").toContain("“");
      expect(emptyMsg.textContent ?? "").not.toMatch(/navigationHub\./);

      // Translated "Clear search" button (not raw key)
      const clearBtn = screen.getByRole("button", { name: /Clear search/i });
      expect(clearBtn.textContent ?? "").not.toMatch(/navigationHub\./);
    });

    it("renders translated category titles passed in by callers as-is (no raw-key leak)", () => {
      // Simulates a page that called t('libraryHub.categories.programs') and
      // got back "Programs". NavigationHub must not transform or wrap that.
      const cats: HubCategory[] = [
        {
          id: "programs",
          title: "Programs",
          icon: Folder,
          items: [{ to: "/p/1", label: "Events", icon: Book }],
        },
      ];
      wrap(<NavigationHub title="Library Hub" categories={cats} />);

      const heading = screen.getByRole("heading", { name: "Programs" });
      expect(heading).toBeInTheDocument();
      // Defensive: no namespace prefix leaked anywhere
      expect(heading.textContent ?? "").not.toMatch(/libraryHub\./);
      expect(heading.textContent ?? "").not.toMatch(/navigationHub\./);
    });
  });

  // -----------------------------------------------------------------
  // Server-side favorites (Wave 2A)
  // -----------------------------------------------------------------
  describe("favorites", () => {
    it("does NOT render the favorites section when favorites prop is omitted", async () => {
      const user = userEvent.setup();
      wrap(<NavigationHub title="Test Hub" categories={baseCategories} />);
      expect(screen.queryByTestId("hub-favorites-section")).not.toBeInTheDocument();

      // Star button also not rendered next to items.
      await user.click(screen.getByRole("button", { name: /Alpha/i }));
      expect(
        screen.queryByRole("button", { name: /Add Alpha One to favorites/i }),
      ).not.toBeInTheDocument();
    });

    it("renders a star button on each item when favorites prop is set", async () => {
      const user = userEvent.setup();
      wrap(
        <NavigationHub
          title="Test Hub"
          categories={baseCategories}
          favorites={{ hubSlug: "test-hub" }}
        />,
      );
      await user.click(screen.getByRole("button", { name: /Alpha/i }));

      expect(
        screen.getByRole("button", { name: /Add Alpha One to favorites/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Add Alpha Two to favorites/i }),
      ).toBeInTheDocument();
    });

    it("renders favorites section ABOVE the category grid when hook returns favorites", () => {
      mockFavoritesState.favorites = new Set(["/alpha/one"]);

      wrap(
        <NavigationHub
          title="Test Hub"
          categories={baseCategories}
          favorites={{ hubSlug: "test-hub" }}
        />,
      );

      const section = screen.getByTestId("hub-favorites-section");
      expect(section).toBeInTheDocument();
      // Section contains the favorited item.
      expect(section.textContent).toContain("Alpha One");
      // The favorited item should also appear in the section even though its
      // home category is collapsed.
      expect(screen.getAllByText("Alpha One").length).toBeGreaterThanOrEqual(1);
    });

    it("favorites section is hidden when no favorites exist", () => {
      mockFavoritesState.favorites = new Set();
      wrap(
        <NavigationHub
          title="Test Hub"
          categories={baseCategories}
          favorites={{ hubSlug: "test-hub" }}
        />,
      );
      expect(screen.queryByTestId("hub-favorites-section")).not.toBeInTheDocument();
    });

    it("favorites section can be opted out via showFavoritesSection=false", () => {
      mockFavoritesState.favorites = new Set(["/alpha/one"]);
      wrap(
        <NavigationHub
          title="Test Hub"
          categories={baseCategories}
          favorites={{ hubSlug: "test-hub", showFavoritesSection: false }}
        />,
      );
      expect(screen.queryByTestId("hub-favorites-section")).not.toBeInTheDocument();
    });

    it("clicking the star calls toggle(itemPath)", async () => {
      const user = userEvent.setup();
      wrap(
        <NavigationHub
          title="Test Hub"
          categories={baseCategories}
          favorites={{ hubSlug: "test-hub" }}
        />,
      );
      await user.click(screen.getByRole("button", { name: /Alpha/i }));
      await user.click(
        screen.getByRole("button", { name: /Add Alpha One to favorites/i }),
      );

      expect(mockFavoritesState.toggle).toHaveBeenCalledTimes(1);
      expect(mockFavoritesState.toggle).toHaveBeenCalledWith("/alpha/one");
    });

    it("star uses 'Remove ...' aria-label when item is already favorited", async () => {
      mockFavoritesState.favorites = new Set(["/alpha/one"]);
      const user = userEvent.setup();
      wrap(
        <NavigationHub
          title="Test Hub"
          categories={baseCategories}
          favorites={{ hubSlug: "test-hub" }}
        />,
      );
      // Open Alpha category (item is also surfaced in the favorites section).
      // Match the accordion header (it sets aria-expanded), not the star button.
      await user.click(
        screen
          .getAllByRole("button", { name: /Alpha/ })
          .find((b) => b.hasAttribute("aria-expanded"))!,
      );

      // At least one "Remove..." button exists (favorites section + main grid).
      expect(
        screen.getAllByRole("button", { name: /Remove Alpha One from favorites/i }).length,
      ).toBeGreaterThanOrEqual(1);
    });

    it("favorites section filters with active search", async () => {
      mockFavoritesState.favorites = new Set(["/alpha/one", "/beta/one"]);
      const user = userEvent.setup();
      wrap(
        <NavigationHub
          title="Test Hub"
          categories={baseCategories}
          searchPlaceholder="Search..."
          favorites={{ hubSlug: "test-hub" }}
        />,
      );

      // Before search: both favorites visible in the favorites section.
      const sectionBefore = screen.getByTestId("hub-favorites-section");
      expect(sectionBefore.textContent).toContain("Alpha One");
      expect(sectionBefore.textContent).toContain("Beta One");

      // Type a query that only matches the alpha item.
      await user.type(screen.getByPlaceholderText("Search..."), "Alpha One");

      const sectionAfter = screen.getByTestId("hub-favorites-section");
      expect(sectionAfter.textContent).toContain("Alpha One");
      expect(sectionAfter.textContent).not.toContain("Beta One");
    });

    it("search also matches against item.keywords", async () => {
      const user = userEvent.setup();
      const cats: HubCategory[] = [
        {
          id: "cat",
          title: "Cat",
          icon: Folder,
          items: [
            { to: "/a", label: "Weeding", icon: Book, keywords: ["deselect"] },
            { to: "/b", label: "Unrelated", icon: Book },
          ],
        },
      ];
      wrap(
        <NavigationHub title="Test Hub" categories={cats} searchPlaceholder="Search..." />,
      );
      // Search using a keyword that isn't in label/description.
      await user.type(screen.getByPlaceholderText("Search..."), "deselect");
      expect(screen.getByText("Weeding")).toBeInTheDocument();
      expect(screen.queryByText("Unrelated")).not.toBeInTheDocument();
    });
  });

  describe("onItemClick", () => {
    it("calls onItemClick with the item when an item link is clicked", async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();
      const cats: HubCategory[] = [
        {
          id: "alpha",
          title: "Alpha",
          icon: Folder,
          items: [
            { to: "/alpha/one", label: "Alpha One", icon: Book },
            { to: "/alpha/two", label: "Alpha Two", icon: Book },
          ],
          defaultOpen: true,
        },
      ];
      wrap(<NavigationHub title="Hub" categories={cats} onItemClick={handleClick} />);

      const link = screen.getByRole("link", { name: /Alpha One/i });
      await user.click(link);

      expect(handleClick).toHaveBeenCalledTimes(1);
      const arg = handleClick.mock.calls[0]?.[0];
      expect(arg).toMatchObject({ to: "/alpha/one", label: "Alpha One" });
    });

    it("is optional -- clicking an item without onItemClick does not throw", async () => {
      const user = userEvent.setup();
      const cats: HubCategory[] = [
        {
          id: "alpha",
          title: "Alpha",
          icon: Folder,
          items: [{ to: "/alpha/one", label: "Alpha One", icon: Book }],
          defaultOpen: true,
        },
      ];
      wrap(<NavigationHub title="Hub" categories={cats} />);

      const link = screen.getByRole("link", { name: /Alpha One/i });
      await user.click(link);
      // No exception -- click handled gracefully.
      expect(link).toBeInTheDocument();
    });
  });
});
