/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Building2, Edit, Plus, RefreshCw } from 'lucide-react'
import type { DatabaseVendor } from '../../api/databases-api'

interface VendorsTabProps {
  vendors: DatabaseVendor[] | undefined
  isLoading: boolean
  isAdmin: boolean
}

export function VendorsTab({ vendors, isLoading, isAdmin }: VendorsTabProps): React.ReactElement {
  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <RefreshCw
          className="h-8 w-8 text-lsc-rose dark:text-lsc-rose-light motion-safe:animate-spin"
          aria-hidden="true"
        />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {isAdmin && (
        <div className="flex justify-end">
          <button
            type="button"
            className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium rounded-lg flex items-center gap-2"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            Add Vendor
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {vendors?.map((vendor) =>
          vendor ? (
            <div
              key={vendor.id}
              className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-earth-100 dark:bg-earth-800 rounded-lg">
                    <Building2
                      className="h-5 w-5 text-lsc-rose dark:text-lsc-rose-light"
                      aria-hidden="true"
                    />
                  </div>
                  <div>
                    <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">{vendor.name}</h3>
                    {vendor.short_name && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {vendor.short_name}
                      </p>
                    )}
                  </div>
                </div>
                {isAdmin && (
                  <button
                    type="button"
                    className="p-1 text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-300"
                    aria-label="Edit vendor"
                  >
                    <Edit className="h-4 w-4" aria-hidden="true" />
                  </button>
                )}
              </div>
              {vendor.support_email && (
                <p className="mt-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {vendor.support_email}
                </p>
              )}
            </div>
          ) : null,
        )}
      </div>

      {(!vendors || vendors.length === 0) && (
        <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
          No vendors configured.
        </div>
      )}
    </div>
  )
}
