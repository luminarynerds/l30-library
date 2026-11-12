/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useRef, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  Search, BookOpen, Package, Leaf, ChevronRight, X,
} from "lucide-react";
import { apiClient } from "@/lib/api-client";
import LoadingSpinner from "@/components/LoadingSpinner";
import { StatusBadge, type StatusVariant } from "@/components/ui/StatusBadge";

// --- Types ---

type SearchMode = "keywords" | "isbn" | "barcode";

interface CatalogResult {
  id: string;
  title: string;
  author: string;
  isbn?: string;
  status?: string;
  item_type?: string;
}

interface LifecycleResult {
  copy_id: number;
  barcode: string;
  condition: string;
  catalog_item_id: number;
  title: string;
  author: string;
  isbn: string;
  call_number: string;
}

interface WeedingResult {
  id: number;
  item_copy_id: number;
  item_title: string | null;
  item_barcode: string | null;
  item_condition: string | null;
  status: string;
  reason: string;
  crew_score: number | null;
}

interface SearchResults {
  catalog: CatalogResult[];
  catalogTotal: number;
  copies: LifecycleResult[];
  weeding: WeedingResult[];
  weedingTotal: number;
}

const MAX_PER_CATEGORY = 5;

const MODE_LABELS: Record<SearchMode, string> = {
  keywords: "Keywords",
  isbn: "ISBN",
  barcode: "Barcode",
};

const MODE_PLACEHOLDERS: Record<SearchMode, string> = {
  keywords: "Search catalog, copies, and weeding...",
  isbn: "Enter ISBN...",
  barcode: "Enter barcode...",
};

function statusVariant(status: string | undefined): StatusVariant {
  if (!status) return "neutral";
  const s = status.toLowerCase();
  if (s === "available" || s === "active" || s === "new" || s === "good") return "success";
  if (s === "pending" || s === "fair" || s === "flagged") return "warning";
  if (s === "withdrawn" || s === "damaged" || s === "disposed" || s === "poor") return "danger";
  return "info";
}

export default function UnifiedCollectionSearch() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<SearchMode>("keywords");
  const [results, setResults] = useState<SearchResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const runSearch = useCallback(async (q: string, _searchMode: SearchMode) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);

    try {
      const [catalogSettled, lifecycleSettled, weedingSettled] = await Promise.allSettled([
        apiClient<{ items: CatalogResult[]; total: number }>(
          "/staff/catalog/items",
          { params: { q, per_page: MAX_PER_CATEGORY }, signal: controller.signal },
        ),
        apiClient<LifecycleResult[]>(
          "/lifecycle/search",
          { params: { q }, signal: controller.signal },
        ),
        apiClient<{ items: WeedingResult[]; total: number }>(
          "/weeding/candidates",
          { params: { per_page: 100 }, signal: controller.signal },
        ),
      ]);

      if (controller.signal.aborted) return;

      const catalog = catalogSettled.status === "fulfilled" ? catalogSettled.value.items : [];
      const catalogTotal = catalogSettled.status === "fulfilled" ? catalogSettled.value.total : 0;

      const allCopies = lifecycleSettled.status === "fulfilled" ? lifecycleSettled.value : [];
      const copies = allCopies.slice(0, MAX_PER_CATEGORY);

      // Client-side filter weeding since endpoint has no text search
      const allWeeding = weedingSettled.status === "fulfilled" ? weedingSettled.value.items : [];
      const weedingTotal = weedingSettled.status === "fulfilled" ? weedingSettled.value.total : 0;
      const lower = q.toLowerCase();
      const weeding = allWeeding
        .filter((w) =>
          w.item_title?.toLowerCase().includes(lower) ||
          w.item_barcode?.toLowerCase().includes(lower)
        )
        .slice(0, MAX_PER_CATEGORY);

      setResults({ catalog, catalogTotal, copies, weeding, weedingTotal });
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setError("Search failed. Please try again.");
      setResults(null);
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);

    const trimmed = query.trim();
    if (!trimmed) {
      setResults(null);
      setLoading(false);
      setError(null);
      abortRef.current?.abort();
      return;
    }

    debounceRef.current = setTimeout(() => {
      runSearch(trimmed, mode);
    }, 300);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, mode, runSearch]);

  useEffect(() => {
    return () => { abortRef.current?.abort(); };
  }, []);

  const hasResults = results && (results.catalog.length > 0 || results.copies.length > 0 || results.weeding.length > 0);
  const noResults = results && !hasResults;

  return (
    <div className="mb-6">
      {/* Search mode tabs */}
      <div className="flex gap-1 mb-2">
        {(Object.keys(MODE_LABELS) as SearchMode[]).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
            className={`px-3 py-1 text-xs rounded-lg font-medium transition-colors ${
              mode === m
                ? "bg-lsc-rose text-white"
                : "bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/60 hover:bg-lsc-rose/10"
            }`}
          >
            {MODE_LABELS[m]}
          </button>
        ))}
      </div>

      {/* Search input */}
      <div className="relative max-w-xl">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60" />
        <input
          type="text"
          placeholder={MODE_PLACEHOLDERS[mode]}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full pl-10 pr-10 py-2.5 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream placeholder:text-lsc-dark/70 dark:placeholder:text-lsc-cream/40 focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
        />
        {query && (
          <button
            type="button"
            onClick={() => setQuery("")}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-lsc-dark/40 dark:text-lsc-cream/40 hover:text-lsc-dark dark:hover:text-lsc-cream"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div className="mt-4 flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
          <LoadingSpinner size="sm" />
          <span>Searching collection...</span>
        </div>
      )}

      {/* Error */}
      {error && (
        <p className="mt-3 text-sm text-status-danger-600 dark:text-status-danger-400">{error}</p>
      )}

      {/* No results */}
      {noResults && !loading && (
        <div className="mt-4 text-center py-8">
          <Search className="w-10 h-10 mx-auto text-lsc-dark/20 dark:text-lsc-cream/20" />
          <p className="mt-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
            No results for &ldquo;{query.trim()}&rdquo;
          </p>
        </div>
      )}

      {/* Results */}
      {hasResults && !loading && (
        <div className="mt-4 space-y-4">
          <ResultSection
            title="Catalog Items"
            icon={BookOpen}
            viewAllPath={`/staff/cataloging?q=${encodeURIComponent(query.trim())}`}
            viewAllLabel="View all in Cataloging"
            total={results.catalogTotal}
            count={results.catalog.length}
          >
            {results.catalog.map((item) => (
              <ResultRow
                key={item.id}
                title={item.title}
                subtitle={item.author}
                identifier={item.isbn ? `ISBN ${item.isbn}` : undefined}
                status={item.status}
                linkTo={`/staff/cataloging/${item.id}`}
              />
            ))}
          </ResultSection>

          <ResultSection
            title="Item Copies"
            icon={Package}
            viewAllPath={`/staff/lifecycle?q=${encodeURIComponent(query.trim())}`}
            viewAllLabel="View all in Lifecycle"
            total={results.copies.length}
            count={results.copies.length}
          >
            {results.copies.map((copy) => (
              <ResultRow
                key={copy.copy_id}
                title={copy.title}
                subtitle={copy.barcode ? `Barcode: ${copy.barcode}` : copy.author}
                identifier={copy.call_number || undefined}
                status={copy.condition}
                linkTo={`/staff/lifecycle/copy/${copy.copy_id}`}
              />
            ))}
          </ResultSection>

          <ResultSection
            title="Weeding Candidates"
            icon={Leaf}
            viewAllPath="/staff/weeding"
            viewAllLabel="View all in Weeding"
            total={results.weedingTotal}
            count={results.weeding.length}
          >
            {results.weeding.map((w) => (
              <ResultRow
                key={w.id}
                title={w.item_title || "Unknown item"}
                subtitle={w.item_barcode ? `Barcode: ${w.item_barcode}` : w.reason}
                identifier={w.crew_score != null ? `CREW ${w.crew_score}` : undefined}
                status={w.status}
                linkTo={`/staff/weeding/${w.id}`}
              />
            ))}
          </ResultSection>
        </div>
      )}
    </div>
  );
}

// --- Sub-components ---

function ResultSection({
  title,
  icon: Icon,
  viewAllPath,
  viewAllLabel,
  total,
  count,
  children,
}: {
  title: string;
  icon: React.ElementType;
  viewAllPath: string;
  viewAllLabel: string;
  total: number;
  count: number;
  children: React.ReactNode;
}) {
  if (count === 0) return null;
  return (
    <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl overflow-hidden">
      <div className="px-4 py-3 flex items-center justify-between border-b border-lsc-border dark:border-earth-700">
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-lsc-rose" />
          <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">{title}</h3>
          <span className="text-xs text-lsc-dark/50 dark:text-lsc-cream/40">
            {total > count ? `${count} of ${total}` : count}
          </span>
        </div>
        {total > count && (
          <Link
            to={viewAllPath}
            className="text-xs text-lsc-rose hover:underline flex items-center gap-1"
          >
            {viewAllLabel}
            <ChevronRight className="w-3 h-3" />
          </Link>
        )}
      </div>
      <ul className="divide-y divide-lsc-border/50 dark:divide-earth-700/50">
        {children}
      </ul>
    </div>
  );
}

function ResultRow({
  title,
  subtitle,
  identifier,
  status,
  linkTo,
}: {
  title: string;
  subtitle?: string;
  identifier?: string;
  status?: string;
  linkTo: string;
}) {
  return (
    <li>
      <Link
        to={linkTo}
        className="flex items-center justify-between px-4 py-2.5 hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 transition-colors group"
      >
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose transition-colors truncate">
            {title}
          </p>
          <div className="flex items-center gap-2 mt-0.5">
            {subtitle && (
              <span className="text-xs text-lsc-dark/60 dark:text-lsc-cream/50 truncate">
                {subtitle}
              </span>
            )}
            {identifier && (
              <span className="text-xs text-lsc-dark/40 dark:text-lsc-cream/35 font-mono">
                {identifier}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 ml-3 flex-shrink-0">
          {status && (
            <StatusBadge variant={statusVariant(status)} size="sm">
              {status}
            </StatusBadge>
          )}
          <ChevronRight className="w-4 h-4 text-lsc-dark/30 dark:text-lsc-cream/30 group-hover:text-lsc-rose transition-colors" />
        </div>
      </Link>
    </li>
  );
}
