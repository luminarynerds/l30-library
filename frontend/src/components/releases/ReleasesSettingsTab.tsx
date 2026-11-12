/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { RefreshCw, Bell, Loader2 } from 'lucide-react'

interface ReleasesSettingsTabProps {
  isAdmin: boolean
  isRefreshingAll: boolean
  onRefreshAll: () => void
}

export function ReleasesSettingsTab({
  isAdmin,
  isRefreshingAll,
  onRefreshAll,
}: ReleasesSettingsTabProps): React.ReactElement {
  return (
    <div className="max-w-2xl">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
          Bulk Operations
        </h2>
        <div className="space-y-6">
          <div className="p-4 bg-lsc-cream dark:bg-lsc-brown rounded-xl">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-lsc-white dark:bg-earth-800 rounded-lg">
                <RefreshCw className="w-6 h-6 text-lsc-rose" />
              </div>
              <div className="flex-1">
                <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">
                  Refresh All Authors
                </h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  Fetch the latest book information from external sources for all tracked authors. This
                  operation runs in the background and may take several minutes.
                </p>
                {isAdmin ? (
                  <button
                    onClick={onRefreshAll}
                    disabled={isRefreshingAll}
                    className="mt-4 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl flex items-center gap-2 disabled:opacity-50"
                  >
                    {isRefreshingAll ? (
                      <>
                        <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                        Starting...
                      </>
                    ) : (
                      <>
                        <RefreshCw className="w-4 h-4" />
                        Refresh All Authors
                      </>
                    )}
                  </button>
                ) : (
                  <p className="mt-4 text-sm text-status-warning-600 dark:text-status-warning-400">
                    Admin access required for this operation.
                  </p>
                )}
              </div>
            </div>
          </div>

          <div className="p-4 bg-lsc-cream dark:bg-lsc-brown rounded-xl">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-lsc-white dark:bg-earth-800 rounded-lg">
                <Bell className="w-6 h-6 text-lsc-rose" />
              </div>
              <div className="flex-1">
                <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">
                  Notification Settings
                </h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  Configure how patrons receive notifications about new releases from authors they follow.
                </p>
                <p className="mt-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  Coming soon...
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
