/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Globe } from "lucide-react";
import type { ReportStats } from "./BoardReportTypes";

export function WebsiteTrafficCard({ data }: { data: ReportStats }) {
  const site = data.website;
  if (!site) {
    return (
      <div className="bg-lsc-white dark:bg-earth-900 rounded-lg border border-lsc-border dark:border-earth-700 p-6">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Globe className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          Website Traffic
        </h3>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          Website analytics unavailable for this period.
        </p>
      </div>
    );
  }

  const tiles = [
    { label: "Pageviews", value: site.pageviews },
    { label: "Visitors", value: site.visitors },
    { label: "Visits", value: site.visits },
    { label: "Bounces", value: site.bounces },
  ];

  const topPages = (site.top_pages || []).slice(0, 5);
  const topReferrers = (site.top_referrers || []).slice(0, 5);

  return (
    <div className="bg-lsc-white dark:bg-earth-900 rounded-lg border border-lsc-border dark:border-earth-700 p-6">
      <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
        <Globe className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
        Website Traffic
      </h3>

      <div className="grid grid-cols-2 gap-3 mb-4">
        {tiles.map((t) => (
          <div
            key={t.label}
            className="bg-earth-50 dark:bg-earth-800 rounded-lg p-3"
          >
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t.label}</p>
            <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">
              {(t.value ?? 0).toLocaleString()}
            </p>
          </div>
        ))}
      </div>

      {topPages.length > 0 && (
        <div className="mb-4">
          <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
            Top Pages
          </p>
          <div className="space-y-1">
            {topPages.map((p, idx) => (
              <div
                key={`${p.path}-${idx}`}
                className="flex items-center justify-between text-sm"
              >
                <span className="truncate text-lsc-dark/70 dark:text-lsc-cream/70 max-w-[70%]">
                  {p.path || "(unknown)"}
                </span>
                <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                  {p.views.toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {topReferrers.length > 0 && (
        <div>
          <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
            Top Referrers
          </p>
          <div className="space-y-1">
            {topReferrers.map((r, idx) => (
              <div
                key={`${r.referrer}-${idx}`}
                className="flex items-center justify-between text-sm"
              >
                <span className="truncate text-lsc-dark/70 dark:text-lsc-cream/70 max-w-[70%]">
                  {r.referrer || "(direct)"}
                </span>
                <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                  {r.views.toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
