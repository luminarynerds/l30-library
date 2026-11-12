/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Plus, RefreshCw, Settings } from 'lucide-react'
import { StatusBadge } from '@/components/admin'
import type { ProxyConfig } from './types'

interface ProxyConfigTabProps {
  configs: unknown[] | undefined
  isLoading: boolean
  isAdmin: boolean
}

export function ProxyConfigTab({ configs, isLoading, isAdmin }: ProxyConfigTabProps): React.ReactElement {
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

  const proxyConfigs = configs as ProxyConfig[]

  return (
    <div className="space-y-4">
      {isAdmin && (
        <div className="flex justify-end">
          <button
            type="button"
            className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium rounded-lg flex items-center gap-2"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            Add Proxy Configuration
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {proxyConfigs?.map((config) => (
          <div
            key={config.id}
            className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-category-100 dark:bg-category-900 rounded-lg">
                  <Settings
                    className="h-5 w-5 text-category-600 dark:text-category-400"
                    aria-hidden="true"
                  />
                </div>
                <div>
                  <h3 className="font-medium text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                    {config.name}
                    {config.is_default && (
                      <StatusBadge label="Default" tone="info" size="sm" />
                    )}
                  </h3>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 capitalize">
                    {config.proxy_type.replace('_', ' ')}
                  </p>
                </div>
              </div>
              <StatusBadge
                label={config.is_active ? 'Active' : 'Inactive'}
                tone={config.is_active ? 'success' : 'muted'}
                size="sm"
              />
            </div>

            {config.ezproxy_base_url && (
              <div className="bg-earth-50 dark:bg-earth-700 rounded p-3 font-mono text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {config.ezproxy_base_url}
              </div>
            )}

            {isAdmin && (
              <div className="mt-4 flex gap-2">
                <button
                  type="button"
                  className="text-sm text-lsc-rose dark:text-lsc-rose-light hover:text-lsc-rose dark:text-lsc-rose-light"
                >
                  Edit
                </button>
                <button
                  type="button"
                  className="text-sm text-status-danger-600 hover:text-status-danger-700 dark:text-status-danger-300"
                >
                  Delete
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {(!proxyConfigs || proxyConfigs.length === 0) && (
        <div className="text-center py-12">
          <Settings
            className="h-12 w-12 text-earth-300 dark:text-earth-300 mx-auto mb-4"
            aria-hidden="true"
          />
          <h3 className="text-lg font-medium text-lsc-dark dark:text-lsc-cream">
            No Proxy Configuration
          </h3>
          <p className="mt-2 text-lsc-dark/70 dark:text-lsc-cream/70">
            Configure EZproxy or OpenAthens to enable remote database access.
          </p>
        </div>
      )}
    </div>
  )
}
