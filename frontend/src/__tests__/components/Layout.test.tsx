/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, within } from "../utils/test-utils"
// import userEvent from "@testing-library/user-event"
import Layout from "../../components/Layout"

// Mock the API module to prevent real API calls
vi.mock("../../api/api", () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: null }),
    put: vi.fn().mockResolvedValue({ data: null }),
  },
  getMe: vi.fn().mockResolvedValue(null),
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  updateMe: vi.fn(),
  refreshAccessToken: vi.fn(),
}))

// Mock the auth context to use the test provider
vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({
    isAuthenticated: false,
    user: null,
    token: null,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
    updateProfile: vi.fn(),
    refreshUser: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}))

// Mock the preferences context
vi.mock("../../contexts/PreferencesContext", () => ({
  usePreferences: () => ({
    preferences: { content_density: "comfortable" },
    loading: false,
    updatePreferences: vi.fn(),
    refreshPreferences: vi.fn(),
  }),
  PreferencesProvider: ({ children }: { children: React.ReactNode }) => children,
}))

// Mock i18n
vi.mock("../../i18n/I18nContext", () => ({
  useTranslation: () => ({
    language: "en",
    setLanguage: vi.fn(),
    isRTL: false,
    t: (key: string) => {
      const translations: Record<string, string> = {
        "navigation.skipToNavigation": "Skip to navigation",
        "navigation.skipToMobileMenu": "Skip to mobile menu",
        "a11y.skipLinks": "Skip links",
        "navigation.skipToMainContent": "Skip to main content",
        "a11y.skipToContent": "Skip to main content",
        "footer.skipToFooter": "Skip to footer",
        "navigation.mainNavigation": "Main navigation",
        "navigation.mobileNavigation": "Mobile navigation",
        "navigation.home": "Home",
        "navigation.catalog": "Catalog",
        "navigation.search": "Search",
        "navigation.browse": "Browse",
        "navigation.events": "Events",
        "navigation.explore": "Explore",
        "navigation.services": "Services",
        "navigation.visit": "Visit",
        "navigation.getHelp": "Get Help",
        "navigation.hoursAndLocations": "Hours & Locations",
        "navigation.searchForBooks": "Search for Books",
        "navigation.rooms": "Rooms",
        "navigation.programsAndEvents": "Programs & Events",
        "navigation.help": "Help",
        "navigation.account": "Account",
        "navigation.myAccount": "My Account",
        "navigation.publicReadingLists": "Reading Lists",
        "navigation.digitalResources": "Digital Resources",
        "navigation.databases": "Databases",
        "navigation.freeEbooks": "Free E-books",
        "navigation.localAuthors": "Local Authors",
        "navigation.readingPrograms": "Reading Programs",
        "navigation.learn": "Learn",
        "navigation.aiTools": "AI Tools",
        "navigation.askALibrarian": "Ask a Librarian",
        "navigation.techSupport": "Tech Support",
        "navigation.legalHelp": "Legal Help",
        "header.libraryName": "L30 Library",
        "header.libraryFullName": "L30 Library",
        "header.librarySubtitle": "Community Library",
        "header.switchToLightMode": "Switch to light mode",
        "header.switchToDarkMode": "Switch to dark mode",
        "catalog.searchButton": "Search",
        "common.search": "Search",
        "common.more": "More",
        "common.close": "Close",
        "auth.signInToAccount": "Sign in to your account",
        "navigation.login": "Sign in",
        "navigation.register": "Get a Library Card",
        "home.quickLinks.libraryCard.title": "Get Library Card",
      }
      return translations[key] || key
    },
    i18n: { language: "en", changeLanguage: vi.fn() },
  }),
  useLanguage: () => ({
    language: "en",
    setLanguage: vi.fn(),
    isRTL: false,
  }),
  I18nProvider: ({ children }: { children: React.ReactNode }) => children,
}))

// Mock theme toggle hook
vi.mock("../../hooks/useThemeToggle", () => ({
  useThemeToggle: () => ({
    isDark: false,
    toggleTheme: vi.fn(),
  }),
}))

// Mock sticky header hook
vi.mock("../../hooks/useStickyHeader", () => ({
  useStickyHeader: () => ({
    isSticky: false,
    isVisible: true,
    isAtTop: true,
  }),
}))

// Mock child components that aren't relevant to Layout structure tests
vi.mock("../../components/HeaderSearch", () => ({
  default: () => <div data-testid="header-search">Search</div>,
}))

vi.mock("../../components/NotificationsDropdown", () => ({
  default: () => <div data-testid="notifications">Notifications</div>,
}))

vi.mock("../../components/LibraryStatusBanner", () => ({
  default: () => null,
}))

vi.mock("../../components/NavigationProgress", () => ({
  default: () => null,
}))

vi.mock("../../components/PanicAlertSystem", () => ({
  PanicAlertSystem: () => null,
}))

vi.mock("../../components/Footer", () => ({
  default: () => (
    <footer id="footer" role="contentinfo">
      <div>(555) 123-4567</div>
      <div>howdy@l30.org</div>
      <a href="/catalog">Catalog</a>
      <div>2026 L30 Library</div>
    </footer>
  ),
}))

vi.mock("../../components/AuthModals", () => ({
  default: () => null,
}))

vi.mock("../../components/LanguageSwitcher", () => ({
  default: () => <div>Language</div>,
}))

vi.mock("../../components/Breadcrumbs", () => ({
  default: () => null,
}))

beforeEach(() => {
  vi.clearAllMocks()
})

// Helper to render Layout with all necessary providers
const renderLayout = (initialRoute = "/") => {
  return render(<Layout />, {
    routerProps: {
      initialEntries: [initialRoute],
    },
  })
}

describe("Layout Component", () => {
  describe("Navigation Links", () => {
    it("should render Catalog link and dropdown buttons in desktop nav", () => {
      renderLayout()

      const desktopNav = screen.getByRole("navigation", { name: /main navigation/i })

      // Catalog is a direct link
      expect(within(desktopNav).getByRole("link", { name: /catalog/i })).toBeInTheDocument()

      // Dropdown buttons for consolidated categories (Services / Explore).
      // Visit was folded into Services as "In the building" in PR B.
      expect(within(desktopNav).getByRole("button", { name: /services/i })).toBeInTheDocument()
      expect(within(desktopNav).getByRole("button", { name: /explore/i })).toBeInTheDocument()
    })

    it("should render Catalog link pointing to /catalog", () => {
      renderLayout()

      const desktopNav = screen.getByRole("navigation", { name: /main navigation/i })
      const catalogLink = within(desktopNav).getByRole("link", { name: /catalog/i })
      expect(catalogLink).toHaveAttribute("href", "/catalog")
    })

    it("should render Events as a direct link in desktop nav", () => {
      renderLayout()

      const desktopNav = screen.getByRole("navigation", { name: /main navigation/i })
      const eventsLink = within(desktopNav).getByRole("link", { name: /events/i })
      expect(eventsLink).toHaveAttribute("href", "/events")
    })
  })

  describe("Header", () => {
    it("should render header with navigation", () => {
      renderLayout()

      const header = screen.getByRole("banner")
      expect(header).toBeInTheDocument()
    })
  })

  describe("Footer", () => {
    it("should render footer with contact information", () => {
      renderLayout()

      const footer = screen.getByRole("contentinfo")
      expect(within(footer).getByText(/123-4567/i)).toBeInTheDocument()
      expect(within(footer).getByText(/howdy@l30.org/i)).toBeInTheDocument()
    })

    it("should render footer explore links section", () => {
      renderLayout()

      const footer = screen.getByRole("contentinfo")
      expect(within(footer).getByRole("link", { name: /^catalog$/i })).toBeInTheDocument()
    })

    it("should render copyright notice", () => {
      renderLayout()

      const footer = screen.getByRole("contentinfo")
      expect(within(footer).getByText(/2026 L30 Library/i)).toBeInTheDocument()
    })
  })

  describe("Accessibility", () => {
    it("should have skip to main content link", () => {
      renderLayout()

      const skipLink = screen.getByRole("link", { name: /skip to main content/i })
      expect(skipLink).toBeInTheDocument()
      expect(skipLink).toHaveAttribute("href", "#main-content")
    })

    it("should have skip to mobile menu link on mobile (default jsdom width)", () => {
      // matchMedia is stubbed in src/__tests__/setup.ts to return matches=false,
      // so the Layout treats the viewport as < lg and points the skip-to-nav
      // link at the mobile bottom nav landmark.
      renderLayout()

      const skipNavLink = screen.getByRole("link", { name: /skip to mobile menu/i })
      expect(skipNavLink).toBeInTheDocument()
      expect(skipNavLink).toHaveAttribute("href", "#mobile-bottom-nav")
    })

    it("should have main navigation with aria-label", () => {
      renderLayout()

      const mainNav = screen.getByRole("navigation", { name: /main navigation/i })
      expect(mainNav).toBeInTheDocument()
    })

    it("should have mobile navigation with aria-label", () => {
      renderLayout()

      const mobileNav = screen.getByRole("navigation", { name: /mobile navigation/i })
      expect(mobileNav).toBeInTheDocument()
    })

    it("should have main content area with id for skip link target", () => {
      renderLayout()

      const main = screen.getByRole("main")
      expect(main).toHaveAttribute("id", "main-content")
    })

    it("should have navigation element with id for skip-to-nav target", () => {
      renderLayout()

      const nav = screen.getByRole("navigation", { name: /main navigation/i })
      expect(nav).toHaveAttribute("id", "main-navigation")
    })
  })

  describe("Active Link State", () => {
    it("should highlight Explore dropdown when on digital page", () => {
      renderLayout("/digital")

      const desktopNav = screen.getByRole("navigation", { name: /main navigation/i })
      const exploreButton = within(desktopNav).getByRole("button", { name: /explore/i })

      // Explore button should have active styling — NavDropdown uses
      // `bg-lsc-rose/10 ... border-b-2 border-lsc-rose` for active state.
      expect(exploreButton.className).toMatch(/border-lsc-rose|bg-lsc-rose/)
    })

    it("should mark Catalog link as current when on catalog page", () => {
      renderLayout("/catalog")

      const desktopNav = screen.getByRole("navigation", { name: /main navigation/i })
      const catalogLink = within(desktopNav).getByRole("link", { name: /catalog/i })
      expect(catalogLink).toHaveAttribute("aria-current", "page")
    })
  })

  describe("Responsive Design", () => {
    it("should render both desktop and mobile navigation", () => {
      renderLayout()

      const desktopNav = screen.getByRole("navigation", { name: /main navigation/i })
      expect(desktopNav).toBeInTheDocument()

      const mobileNav = screen.getByRole("navigation", { name: /mobile navigation/i })
      expect(mobileNav).toBeInTheDocument()
    })

    it("should render core links in mobile bottom navigation", () => {
      renderLayout()

      const mobileNav = screen.getByRole("navigation", { name: /mobile navigation/i })

      // Current bottom nav items: Search (→/catalog), Events, Browse (→/discover),
      // Hours & Locations, Account. See bottomNavItems in components/Layout.tsx.
      expect(within(mobileNav).getByRole("link", { name: /search/i })).toBeInTheDocument()
      expect(within(mobileNav).getByRole("link", { name: /events/i })).toBeInTheDocument()
      expect(within(mobileNav).getByRole("link", { name: /browse/i })).toBeInTheDocument()
      expect(within(mobileNav).getByRole("link", { name: /account/i })).toBeInTheDocument()
    })
  })
})
