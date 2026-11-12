/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useMemo, useEffect, useRef, useCallback, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { Search, ChevronRight, ChevronDown, Star } from "lucide-react";
import { AdminShell } from "../shells";
import { useOrganizationFeatures, type OrganizationFeatures } from "../../contexts/OrganizationFeaturesContext";
import { useTranslation } from "@/i18n";
// --- Wave 3B: inline header stat chips ---
import HubStatChips from "./HubStatChips";
// --- end Wave 3B ---
import { useHubFavorites } from "../../hooks/useHubFavorites";

// --- Jump-list thresholds (auto-applies when EITHER is met) ---
const JUMP_LIST_MIN_CATEGORIES = 6;
const JUMP_LIST_MIN_ITEMS = 30;

// --- URL persistence helpers ---
const EXPANSION_URL_PARAM = "open";

function readExpansionFromUrl(validIds: Set<string>): Set<string> | null {
  if (typeof window === "undefined") return null;
  const params = new URLSearchParams(window.location.search);
  if (!params.has(EXPANSION_URL_PARAM)) return null;
  const raw = params.get(EXPANSION_URL_PARAM) ?? "";
  const ids = raw
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0 && validIds.has(s));
  return new Set(ids);
}

function writeExpansionToUrl(expanded: Set<string>): void {
  if (typeof window === "undefined") return;
  const params = new URLSearchParams(window.location.search);
  if (expanded.size === 0) {
    params.delete(EXPANSION_URL_PARAM);
  } else {
    params.set(EXPANSION_URL_PARAM, Array.from(expanded).join(","));
  }
  const query = params.toString();
  const next = `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`;
  window.history.replaceState(window.history.state, "", next);
}

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export interface HubItem {
  to: string;
  label: string;
  description?: string;
  icon?: React.ComponentType<{ className?: string }>;
  badge?: string;
  /** Hide item when this organization feature flag is false. */
  featureFlag?: keyof OrganizationFeatures;
  /** Reserved for future role-based filtering (no current consumer). */
  roleAllowList?: string[];
  /** Extra search-only tokens; never displayed. */
  keywords?: string[];
}

export interface HubCategory {
  id: string;
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  items: HubItem[];
  defaultOpen?: boolean;
}

export interface NavigationHubProps {
  title: string;
  /** Optional subtitle; if omitted, auto-computed from counts + itemNoun. */
  subtitle?: string;
  /** Icon shown in the AdminShell page header. */
  icon?: ReactNode;
  categories: HubCategory[];
  /** Renders the built-in search input when provided. Omit to disable search entirely. */
  searchPlaceholder?: string;
  /** Action element rendered to the right of the page title (AdminShell `actions`). */
  headerAction?: ReactNode;
  /** Grid column count at xl breakpoint. Default 2. */
  columns?: 2 | 3;
  /** Optional content rendered above the grid (e.g. a custom search widget). */
  beforeGrid?: ReactNode;
  /** Future hook for badges/favorites. Return null to fall back to default item row. */
  itemSlot?: (item: HubItem) => ReactNode;
  /** Noun used in count strings (e.g. "tool"/"tools", "setting"/"settings"). Default "item"/"items". */
  itemNoun?: { singular: string; plural: string };
  /**
   * When set, render a star toggle next to each item that calls into the
   * server-side hub-favorites API for the given `hubSlug`. When the user has
   * starred items, render a "Favorites" section above the category grid
   * (toggleable via `showFavoritesSection`, defaults to true). Patron-role
   * pages that aren't authenticated render the stars as inert (toggle no-ops).
   */
  favorites?: {
    hubSlug: string;
    showFavoritesSection?: boolean;
  };
  /**
   * When true, persist which categories are expanded to the URL (`?open=a,b`)
   * via history.replaceState. Initial state hydrates from the URL if present.
   * Default false.
   */
  persistExpansion?: boolean;
  /**
   * When true, suppress the jump-to-category anchor list even if thresholds are met.
   * Default false (auto-renders when categories>=6 OR totalItems>=30).
   */
  hideJumpList?: boolean;
  // --- Wave 3B: inline header stat chips (see HubStatChips) ---
  /** When true, renders <HubStatChips hubSlug={hubSlug} /> in the header area. */
  showStatChips?: boolean;
  /** Stable hub identifier passed to GET /api/v1/hub-stats/{hubSlug}. Required when showStatChips. */
  hubSlug?: string;
  // --- end Wave 3B ---
  /**
   * Fired after the user clicks an item link. Use for fire-and-forget visit
   * logging or analytics; do not block navigation.
   */
  onItemClick?: (item: HubItem) => void;
}

function pluralize(count: number, noun: { singular: string; plural: string }): string {
  return count === 1 ? noun.singular : noun.plural;
}

export default function NavigationHub({
  title,
  subtitle,
  icon,
  categories,
  searchPlaceholder,
  headerAction,
  columns = 2,
  beforeGrid,
  itemSlot,
  itemNoun,
  persistExpansion = false,
  hideJumpList = false,
  // --- Wave 3B: inline header stat chips ---
  showStatChips = false,
  hubSlug,
  // --- end Wave 3B ---
  favorites,
  onItemClick,
}: NavigationHubProps) {
  const { t } = useTranslation();
  // Always call useHubFavorites so the hook order is stable across renders.
  // When no `favorites` prop is set we pass an empty slug; the hook treats
  // unauthenticated/empty as "no favorites".
  const favoritesHubSlug = favorites?.hubSlug ?? "";
  const {
    favorites: favoriteSet,
    toggle: toggleFavorite,
    isFavorite,
  } = useHubFavorites(favoritesHubSlug);
  const favoritesEnabled = Boolean(favorites && favorites.hubSlug);
  const showFavoritesSection =
    favoritesEnabled && (favorites?.showFavoritesSection ?? true);
  // Default item noun translates here, not at module scope, so it follows the
  // active language. Callers may still pass an explicit `itemNoun`.
  const resolvedItemNoun = itemNoun ?? {
    singular: t("navigationHub.defaultItemSingular"),
    plural: t("navigationHub.defaultItemPlural"),
  };

  const [searchQuery, setSearchQuery] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(() => {
    if (persistExpansion) {
      const validIds = new Set(categories.map((c) => c.id));
      const fromUrl = readExpansionFromUrl(validIds);
      if (fromUrl) return fromUrl;
    }
    return new Set(categories.filter((c) => c.defaultOpen).map((c) => c.id));
  });
  const { isFeatureEnabled } = useOrganizationFeatures();

  // --- Refs for jump-to-category scroll targets ---
  const categoryRefs = useRef<Map<string, HTMLElement>>(new Map());
  const setCategoryRef = useCallback((id: string, node: HTMLElement | null) => {
    if (node) categoryRefs.current.set(id, node);
    else categoryRefs.current.delete(id);
  }, []);

  const searchEnabled = typeof searchPlaceholder === "string";
  const isSearching = searchEnabled && searchQuery.trim().length > 0;

  // Filter by feature flags first.
  const enabledCategories = useMemo<HubCategory[]>(() => {
    return categories
      .map((cat) => ({
        ...cat,
        items: cat.items.filter((item) => !item.featureFlag || isFeatureEnabled(item.featureFlag)),
      }))
      .filter((cat) => cat.items.length > 0);
  }, [categories, isFeatureEnabled]);

  const matchesQuery = useCallback(
    (item: HubItem, categoryTitle: string, query: string): boolean => {
      return (
        item.label.toLowerCase().includes(query) ||
        (item.description?.toLowerCase().includes(query) ?? false) ||
        categoryTitle.toLowerCase().includes(query) ||
        (item.keywords?.some((kw) => kw.toLowerCase().includes(query)) ?? false)
      );
    },
    [],
  );

  const filteredCategories = useMemo<HubCategory[]>(() => {
    if (!isSearching) return enabledCategories;
    const query = searchQuery.toLowerCase();
    return enabledCategories
      .map((category) => ({
        ...category,
        items: category.items.filter((item) => matchesQuery(item, category.title, query)),
      }))
      .filter((category) => category.items.length > 0);
  }, [searchQuery, isSearching, enabledCategories, matchesQuery]);

  // Favorite items, flattened across enabled categories so search filtering
  // mirrors the main grid.
  const favoriteItems = useMemo<HubItem[]>(() => {
    if (!showFavoritesSection || favoriteSet.size === 0) return [];
    const query = searchQuery.toLowerCase();
    const all: HubItem[] = [];
    for (const cat of enabledCategories) {
      for (const item of cat.items) {
        if (!favoriteSet.has(item.to)) continue;
        if (isSearching && !matchesQuery(item, cat.title, query)) continue;
        all.push(item);
      }
    }
    return all;
  }, [showFavoritesSection, favoriteSet, enabledCategories, isSearching, searchQuery, matchesQuery]);

  const totalItems = enabledCategories.reduce((sum, c) => sum + c.items.length, 0);
  const filteredItems = filteredCategories.reduce((sum, c) => sum + c.items.length, 0);

  const computedSubtitle =
    subtitle ??
    t("navigationHub.subtitle", {
      count: totalItems,
      itemNoun: pluralize(totalItems, resolvedItemNoun),
      categories: enabledCategories.length,
    });

  const toggleCategory = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // --- Persist `expanded` -> URL whenever the user toggles (not during search,
  // which never mutates `expanded`). ---
  useEffect(() => {
    if (!persistExpansion) return;
    writeExpansionToUrl(expanded);
  }, [expanded, persistExpansion]);

  // --- Jump-list visibility + handler ---
  const showJumpList =
    !hideJumpList &&
    !isSearching &&
    (enabledCategories.length >= JUMP_LIST_MIN_CATEGORIES || totalItems >= JUMP_LIST_MIN_ITEMS);

  const jumpToCategory = (id: string) => {
    setExpanded((prev) => {
      if (prev.has(id)) return prev;
      const next = new Set(prev);
      next.add(id);
      return next;
    });
    const node = categoryRefs.current.get(id);
    if (node) {
      const behavior: ScrollBehavior = prefersReducedMotion() ? "auto" : "smooth";
      node.scrollIntoView({ behavior, block: "start" });
    }
  };

  const gridClass =
    columns === 3
      ? "grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"
      : "grid grid-cols-1 md:grid-cols-2 gap-4";

  // Render a default item row with optional star button when favorites are
  // enabled. Pages can still pass an `itemSlot` to fully replace this row.
  const renderDefaultRow = (item: HubItem): ReactNode => {
    const ItemIcon = item.icon;
    const fav = favoritesEnabled && isFavorite(item.to);
    return (
      <Link
        to={item.to}
        onClick={() => onItemClick?.(item)}
        className="flex items-center justify-between px-5 py-3 hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 transition-colors group"
      >
        <div className="flex items-center gap-3 min-w-0">
          {ItemIcon && (
            <ItemIcon className="w-4 h-4 text-lsc-dark/40 dark:text-lsc-cream/40 flex-shrink-0" />
          )}
          <div className="min-w-0">
            <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose transition-colors">
              {item.label}
              {item.badge && (
                <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-lsc-rose/10 text-lsc-rose">
                  {item.badge}
                </span>
              )}
            </p>
            {item.description && (
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50 truncate">
                {item.description}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0 ml-2">
          {favoritesEnabled && (
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                void toggleFavorite(item.to);
              }}
              aria-label={
                fav
                  ? t("navigationHub.removeFavoriteAria", { label: item.label })
                  : t("navigationHub.addFavoriteAria", { label: item.label })
              }
              aria-pressed={fav}
              className="p-1 rounded hover:bg-lsc-cream dark:hover:bg-earth-600 transition-colors"
            >
              <Star
                className={`w-4 h-4 transition-colors ${fav ? "fill-status-warning-400 text-status-warning-400" : "text-lsc-dark/20 dark:text-lsc-cream/20 group-hover:text-lsc-dark/40 dark:group-hover:text-lsc-cream/40"}`}
              />
            </button>
          )}
          <ChevronRight className="w-4 h-4 text-lsc-dark/30 dark:text-lsc-cream/60 group-hover:text-lsc-rose transition-colors" />
        </div>
      </Link>
    );
  };

  const renderFavoritesSection = (): ReactNode => {
    if (!showFavoritesSection || favoriteItems.length === 0) return null;
    return (
      <div
        data-testid="hub-favorites-section"
        className="mb-4 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl overflow-hidden"
      >
        <div className="px-5 py-4 flex items-center gap-3">
          <div className="bg-status-warning-100 dark:bg-status-warning-900/30 p-2 rounded-lg flex-shrink-0">
            <Star className="w-5 h-5 fill-status-warning-400 text-status-warning-400" />
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
              {t("navigationHub.favoritesSectionTitle")}
            </h2>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">
              {favoriteItems.length === 1
                ? t("navigationHub.favoritesSavedOne", {
                    itemNoun: resolvedItemNoun.singular,
                  })
                : t("navigationHub.favoritesSavedOther", {
                    count: favoriteItems.length,
                    itemNoun: resolvedItemNoun.plural,
                  })}
            </p>
          </div>
        </div>
        <ul className="border-t border-lsc-border dark:border-earth-700 divide-y divide-lsc-border/50 dark:divide-earth-700/50">
          {favoriteItems.map((item) => {
            const slot = itemSlot?.(item);
            return <li key={`fav-${item.to}`}>{slot ?? renderDefaultRow(item)}</li>;
          })}
        </ul>
      </div>
    );
  };

  return (
    <AdminShell title={title} subtitle={computedSubtitle} icon={icon} actions={headerAction}>
      {/* --- Wave 3B: inline header stat chips --- */}
      {showStatChips && hubSlug && <HubStatChips hubSlug={hubSlug} className="mb-4" />}
      {/* --- end Wave 3B --- */}
      {searchEnabled && (
        <div className="mb-6 relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60" />
          <input
            type="text"
            placeholder={searchPlaceholder}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream placeholder:text-lsc-dark/70 dark:placeholder:text-lsc-cream/40 focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
          />
          {isSearching && (
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-lsc-dark/70 dark:text-lsc-cream/50">
              {filteredItems === 1
                ? t("navigationHub.resultCountOne")
                : t("navigationHub.resultCountOther", { count: filteredItems })}
            </span>
          )}
        </div>
      )}

      {beforeGrid}

      {/* --- Jump-to-category anchor list (logic-only; minimal text content) --- */}
      {showJumpList && (
        <nav
          aria-label={t("navigationHub.jumpListAriaLabel")}
          data-testid="hub-jump-list"
          className="mb-4 flex flex-wrap gap-2"
        >
          {enabledCategories.map((category) => (
            <button
              key={`jump-${category.id}`}
              type="button"
              onClick={() => jumpToCategory(category.id)}
              aria-label={t("navigationHub.jumpToCategoryAria", {
                title: category.title,
                count: category.items.length,
                itemNoun: pluralize(category.items.length, resolvedItemNoun),
              })}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-lsc-cream/60 dark:bg-earth-700 border border-lsc-border dark:border-earth-600 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-rose/10 hover:border-lsc-rose/40 hover:text-lsc-rose dark:hover:bg-lsc-rose/20 transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
            >
              <span>{category.title}</span>
              <span className="text-lsc-dark/60 dark:text-lsc-cream/60">{category.items.length}</span>
            </button>
          ))}
        </nav>
      )}

      <div>
        {searchEnabled && filteredCategories.length === 0 ? (
          <div className="text-center py-12">
            <Search className="w-12 h-12 mx-auto text-lsc-dark/20 dark:text-lsc-cream/20" />
            <p className="mt-4 text-lsc-dark/70 dark:text-lsc-cream/60">
              {t("navigationHub.noMatchesFor", {
                itemNoun: resolvedItemNoun.plural,
                query: searchQuery,
              })}
            </p>
            <button
              onClick={() => setSearchQuery("")}
              className="mt-2 text-lsc-rose hover:underline text-sm"
            >
              {t("navigationHub.clearSearch")}
            </button>
          </div>
        ) : (
          <>
            {renderFavoritesSection()}
            <div className={gridClass}>
            {filteredCategories.map((category) => {
              const CategoryIcon = category.icon;
              const isOpen = isSearching || expanded.has(category.id);
              return (
                <div
                  key={category.id}
                  ref={(node) => setCategoryRef(category.id, node)}
                  className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl overflow-hidden"
                >
                  <button
                    type="button"
                    onClick={() => toggleCategory(category.id)}
                    className="w-full px-5 py-4 flex items-center gap-3 hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30 transition-colors text-left"
                    aria-expanded={isOpen}
                  >
                    <div className="bg-lsc-rose/10 dark:bg-lsc-rose/20 p-2 rounded-lg flex-shrink-0">
                      <CategoryIcon className="w-5 h-5 text-lsc-rose" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                        {category.title}
                      </h2>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">
                        {category.items.length} {pluralize(category.items.length, resolvedItemNoun)}
                      </p>
                    </div>
                    {isOpen ? (
                      <ChevronDown className="w-4 h-4 text-lsc-dark/40 dark:text-lsc-cream/40 flex-shrink-0" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-lsc-dark/40 dark:text-lsc-cream/40 flex-shrink-0" />
                    )}
                  </button>
                  {isOpen && (
                    <ul className="border-t border-lsc-border dark:border-earth-700 divide-y divide-lsc-border/50 dark:divide-earth-700/50">
                      {category.items.map((item) => {
                        const slot = itemSlot?.(item);
                        return (
                          <li key={item.to}>{slot ?? renderDefaultRow(item)}</li>
                        );
                      })}
                    </ul>
                  )}
                </div>
              );
            })}
            </div>
          </>
        )}
      </div>
    </AdminShell>
  );
}
