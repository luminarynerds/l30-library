/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Staff demand-signals report card. Shows the top-N items the
 * library's collection is missing, ranked by recency-weighted demand
 * across failed-search/ILL/peak-hold/agent-unfound capture surfaces.
 *
 * PR7 ships only the failed-search ingest hook -- this card surfaces
 * whatever rows the backend has, regardless of signal_type. Future
 * PRs add hooks for the other three signal types without further
 * changes here.
 */
import { useEffect, useState } from "react";
import { Loader2, AlertTriangle, BookOpen } from "lucide-react";
import api from "@/lib/api-client";
import { useTranslation } from "@/i18n";

interface DemandSignalItem {
  key: string;
  normalized_isbn: string | null;
  normalized_title: string | null;
  signal_type: string;
  count: number;
  weighted_count: number;
  most_recent: string | null;
}

interface DemandSignalsResponse {
  days: number;
  limit: number;
  signal_type: string | null;
  items: DemandSignalItem[];
}

export default function DemandSignalsCard(): React.ReactElement {
  const { t } = useTranslation();
  const [items, setItems] = useState<DemandSignalItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    // The error label is held as a static fallback so we do not need
    // ``t`` in the dependency array (re-running this effect on every
    // render would refetch on each parent re-render).
    const loadFailedLabel = t(
      "demand_signals.load_failed",
      "Could not load demand signals.",
    );
    setLoading(true);
    setError(null);
    api
      .get<DemandSignalsResponse>("/admin/demand-signals?days=30&limit=10")
      .then((res) => {
        if (cancelled) return;
        setItems(res.items ?? []);
      })
      .catch(() => {
        if (cancelled) return;
        setError(loadFailedLabel);
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // Effect runs once on mount; t() is captured at first render. The
    // staff report doesn't switch language without a page nav.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section
      aria-labelledby="demand-signals-heading"
      className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <h2
          id="demand-signals-heading"
          className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2"
        >
          <BookOpen aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
          {t(
            "demand_signals.heading",
            "Collection gap signals (last 30 days)",
          )}
        </h2>
      </div>

      {loading && (
        <div
          className="flex items-center justify-center h-24"
          role="status"
          aria-live="polite"
        >
          <Loader2
            aria-hidden="true"
            className="w-6 h-6 motion-safe:animate-spin text-lsc-dark/40 dark:text-lsc-cream/40"
          />
          <span className="sr-only">
            {t("demand_signals.loading", "Loading demand signals...")}
          </span>
        </div>
      )}

      {!loading && error && (
        <div
          role="alert"
          className="flex items-center gap-2 text-sm text-status-danger-700 dark:text-status-danger-300"
        >
          <AlertTriangle aria-hidden="true" className="w-4 h-4" />
          <span>{error}</span>
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {t(
            "demand_signals.empty",
            "No demand signals captured yet. Failed patron searches will appear here.",
          )}
        </p>
      )}

      {!loading && !error && items.length > 0 && (
        <ol className="space-y-2" aria-label={t("demand_signals.list_label", "Top demand signals")}>
          {items.map((item, idx) => (
            <li
              key={`${item.signal_type}:${item.key}:${idx}`}
              className="flex items-center justify-between gap-3 text-sm border-b border-lsc-border/50 dark:border-earth-700/50 pb-2 last:border-0"
            >
              <div className="flex-1 min-w-0">
                <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate">
                  {item.normalized_title || item.normalized_isbn || item.key}
                </p>
                <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
                  {item.signal_type}
                  {item.normalized_isbn ? ` - ISBN ${item.normalized_isbn}` : ""}
                </p>
              </div>
              <div className="shrink-0 text-right">
                <p
                  className="text-base font-semibold text-lsc-dark dark:text-lsc-cream"
                  aria-label={t(
                    "demand_signals.count_label",
                    "request count",
                  )}
                >
                  {item.count}
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
