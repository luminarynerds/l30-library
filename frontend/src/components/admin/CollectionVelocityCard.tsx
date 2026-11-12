/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Staff collection-velocity report card. Surfaces three actionable
 * buckets backed by the catalog_circulation_velocity_mv materialized
 * view (refreshed nightly):
 *
 * - Weed: cold inventory candidates for withdrawal
 * - Buy more: titles starved by active hold pressure
 * - Cold spend: recent acquisitions with zero circulation
 *
 * Lives alongside DemandSignalsCard on CirculationReportsPage.
 */
import { useEffect, useState, useCallback } from "react";
import { Loader2, AlertTriangle, TrendingUp } from "lucide-react";
import api from "@/lib/api-client";
import { useTranslation } from "@/i18n";

type Bucket = "weed" | "buy_more" | "cold_spend";

interface VelocityItem {
  catalog_item_id: number;
  title: string;
  author: string | null;
  isbn: string | null;
  checkouts_30d: number;
  checkouts_90d: number;
  checkouts_365d: number;
  days_since_last_checkout: number | null;
  holds_active: number;
  holds_per_copy: number | null;
  total_copies: number;
  last_refreshed_at: string | null;
}

interface VelocityResponse {
  bucket: Bucket;
  limit: number;
  count: number;
  items: VelocityItem[];
}

const BUCKETS: { value: Bucket; labelKey: string; labelFallback: string }[] = [
  { value: "weed", labelKey: "collection_velocity.tab.weed", labelFallback: "Weed" },
  {
    value: "buy_more",
    labelKey: "collection_velocity.tab.buy_more",
    labelFallback: "Buy more",
  },
  {
    value: "cold_spend",
    labelKey: "collection_velocity.tab.cold_spend",
    labelFallback: "Cold spend",
  },
];

export default function CollectionVelocityCard(): React.ReactElement {
  const { t } = useTranslation();
  const [bucket, setBucket] = useState<Bucket>("weed");
  const [items, setItems] = useState<VelocityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadFailedLabel = t(
    "collection_velocity.load_failed",
    "Could not load collection velocity report.",
  );

  const load = useCallback(
    (b: Bucket) => {
      let cancelled = false;
      setLoading(true);
      setError(null);
      api
        .get<VelocityResponse>(
          `/admin/reports/collection-velocity?bucket=${b}&limit=10`,
        )
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
    },
    [loadFailedLabel],
  );

  useEffect(() => {
    const cleanup = load(bucket);
    return cleanup;
  }, [bucket, load]);

  return (
    <section
      aria-labelledby="collection-velocity-heading"
      className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <h2
          id="collection-velocity-heading"
          className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2"
        >
          <TrendingUp aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
          {t("collection_velocity.heading", "Collection velocity")}
        </h2>
      </div>

      <div
        role="tablist"
        aria-label={t(
          "collection_velocity.tablist_label",
          "Collection velocity buckets",
        )}
        className="flex gap-2 mb-4 border-b border-lsc-border dark:border-earth-700"
      >
        {BUCKETS.map((b) => {
          const active = b.value === bucket;
          return (
            <button
              key={b.value}
              type="button"
              role="tab"
              aria-selected={active}
              aria-controls={`collection-velocity-panel-${b.value}`}
              id={`collection-velocity-tab-${b.value}`}
              onClick={() => setBucket(b.value)}
              className={
                "px-3 py-1.5 text-sm font-medium rounded-t border-b-2 -mb-px transition " +
                (active
                  ? "border-lsc-rose text-lsc-dark dark:text-lsc-cream"
                  : "border-transparent text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream")
              }
            >
              {t(b.labelKey, b.labelFallback)}
            </button>
          );
        })}
      </div>

      <div
        role="tabpanel"
        id={`collection-velocity-panel-${bucket}`}
        aria-labelledby={`collection-velocity-tab-${bucket}`}
      >
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
              {t("collection_velocity.loading", "Loading collection velocity...")}
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
              "collection_velocity.empty",
              "No items match this bucket yet. The report refreshes nightly.",
            )}
          </p>
        )}

        {!loading && !error && items.length > 0 && (
          <ol
            className="space-y-2"
            aria-label={t(
              "collection_velocity.list_label",
              "Top collection velocity items",
            )}
          >
            {items.map((item) => (
              <li
                key={item.catalog_item_id}
                className="flex items-center justify-between gap-3 text-sm border-b border-lsc-border/50 dark:border-earth-700/50 pb-2 last:border-0"
              >
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate">
                    {item.title}
                  </p>
                  <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 truncate">
                    {item.author || t("collection_velocity.unknown_author", "Unknown author")}
                    {item.isbn ? ` - ISBN ${item.isbn}` : ""}
                  </p>
                </div>
                <div className="shrink-0 text-right text-xs text-lsc-dark/80 dark:text-lsc-cream/80">
                  {bucket === "weed" && (
                    <>
                      <p>
                        {t("collection_velocity.copies", "Copies")}: {item.total_copies}
                      </p>
                      <p>
                        {t("collection_velocity.days_since", "Days since")}:{" "}
                        {item.days_since_last_checkout !== null
                          ? Math.round(item.days_since_last_checkout)
                          : "-"}
                      </p>
                    </>
                  )}
                  {bucket === "buy_more" && (
                    <>
                      <p>
                        {t("collection_velocity.holds", "Holds")}: {item.holds_active}
                      </p>
                      <p>
                        {t("collection_velocity.per_copy", "Per copy")}:{" "}
                        {item.holds_per_copy !== null
                          ? item.holds_per_copy.toFixed(1)
                          : "-"}
                      </p>
                    </>
                  )}
                  {bucket === "cold_spend" && (
                    <>
                      <p>
                        {t("collection_velocity.copies", "Copies")}: {item.total_copies}
                      </p>
                      <p>
                        {t("collection_velocity.checkouts_365", "365d ckouts")}:{" "}
                        {item.checkouts_365d}
                      </p>
                    </>
                  )}
                </div>
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}
