/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import {
  Share2,
  Edit2,
  Loader2,
  Check,
  Search,
  Settings,
  RefreshCw,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  updateConsortiumSettings,
  type ConsortiumDetail,
  type ConsortiumSettings,
} from '../../../api/consortium-api'
import { t } from '@/i18n'

// eslint-disable-next-line complexity
function SharedResourcesTab({
  token,
  selectedConsortium,
}: {
  token: string | null
  selectedConsortium: ConsortiumDetail | null
}) {
  const [settings, setSettings] = useState<ConsortiumSettings | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formData, setFormData] = useState<Partial<ConsortiumSettings>>({})

  useEffect(() => {
    if (selectedConsortium?.settings) {
      setSettings(selectedConsortium.settings)
      setFormData(selectedConsortium.settings)
    }
  }, [selectedConsortium])

  const handleSave = async () => {
    if (!token || !selectedConsortium) return
    setIsSubmitting(true)
    try {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars -- id/consortium_id/updated_at intentionally omitted from payload
      const { id: _id, consortium_id: _cid, updated_at: _ua, ...payload } = formData as ConsortiumSettings
      const updated = await updateConsortiumSettings(token, selectedConsortium.id, payload)
      setSettings(updated)
      setIsEditing(false)
      toast.success(t('toast.settingsUpdated'))
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.adminSiteSettings.failedToUpdateSettings'))
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!selectedConsortium) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-12 text-center">
        <Share2 className="w-16 h-16 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-lsc-dark dark:text-lsc-cream mb-2">
          Select a consortium
        </h3>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          Go to the Consortiums tab and select a consortium to manage shared resources.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            Shared Resources & Settings
          </h2>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            Configure reciprocal borrowing, ILL, and resource sharing for {selectedConsortium.name}
          </p>
        </div>
        {!isEditing && (
          <button
            onClick={() => setIsEditing(true)}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium transition-colors"
          >
            <Edit2 className="w-4 h-4" />
            Edit Settings
          </button>
        )}
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Catalog Sharing */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-earth-100 dark:bg-earth-800/30 rounded-lg">
              <Search className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
              Catalog Sharing
            </h3>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Shared Catalog
              </span>
              {isEditing ? (
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.enable_shared_catalog ?? settings?.enable_shared_catalog ?? false}
                    onChange={(e) =>
                      setFormData({ ...formData, enable_shared_catalog: e.target.checked })
                    }
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-earth-200 peer-focus:ring-2 peer-focus:ring-lsc-rose rounded-full peer dark:bg-earth-700 peer-checked:bg-lsc-rose"></div>
                </label>
              ) : (
                <span
                  className={`text-sm font-medium ${settings?.enable_shared_catalog ? 'text-status-success-600' : 'text-lsc-dark/70 dark:text-lsc-cream/70'}`}
                >
                  {settings?.enable_shared_catalog ? 'Enabled' : 'Disabled'}
                </span>
              )}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Search All Members
              </span>
              {isEditing ? (
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={
                      formData.catalog_search_all_members ??
                      settings?.catalog_search_all_members ??
                      false
                    }
                    onChange={(e) =>
                      setFormData({ ...formData, catalog_search_all_members: e.target.checked })
                    }
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-earth-200 peer-focus:ring-2 peer-focus:ring-lsc-rose rounded-full peer dark:bg-earth-700 peer-checked:bg-lsc-rose"></div>
                </label>
              ) : (
                <span
                  className={`text-sm font-medium ${settings?.catalog_search_all_members ? 'text-status-success-600' : 'text-lsc-dark/70 dark:text-lsc-cream/70'}`}
                >
                  {settings?.catalog_search_all_members ? 'Enabled' : 'Disabled'}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Reciprocal Borrowing */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-status-success-100 dark:bg-status-success-900/30 rounded-lg">
              <Share2 className="w-5 h-5 text-status-success-600 dark:text-status-success-400" />
            </div>
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
              Reciprocal Borrowing
            </h3>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Enable Reciprocal Borrowing
              </span>
              {isEditing ? (
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={
                      formData.enable_reciprocal_borrowing ??
                      settings?.enable_reciprocal_borrowing ??
                      false
                    }
                    onChange={(e) =>
                      setFormData({ ...formData, enable_reciprocal_borrowing: e.target.checked })
                    }
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-earth-200 peer-focus:ring-2 peer-focus:ring-lsc-rose rounded-full peer dark:bg-earth-700 peer-checked:bg-lsc-rose"></div>
                </label>
              ) : (
                <span
                  className={`text-sm font-medium ${settings?.enable_reciprocal_borrowing ? 'text-status-success-600' : 'text-lsc-dark/70 dark:text-lsc-cream/70'}`}
                >
                  {settings?.enable_reciprocal_borrowing ? 'Enabled' : 'Disabled'}
                </span>
              )}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Checkout Limit
              </span>
              {isEditing ? (
                <input
                  type="number"
                  value={formData.reciprocal_checkout_limit ?? settings?.reciprocal_checkout_limit ?? 5}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      reciprocal_checkout_limit: parseInt(e.target.value),
                    })
                  }
                  className="w-20 px-2 py-1 rounded border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream text-right"
                  min={0}
                />
              ) : (
                <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  {settings?.reciprocal_checkout_limit ?? 5}
                </span>
              )}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Hold Limit</span>
              {isEditing ? (
                <input
                  type="number"
                  value={formData.reciprocal_hold_limit ?? settings?.reciprocal_hold_limit ?? 3}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      reciprocal_hold_limit: parseInt(e.target.value),
                    })
                  }
                  className="w-20 px-2 py-1 rounded border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream text-right"
                  min={0}
                />
              ) : (
                <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  {settings?.reciprocal_hold_limit ?? 3}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* ILL Settings */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-category-100 dark:bg-category-900/30 rounded-lg">
              <RefreshCw className="w-5 h-5 text-category-600 dark:text-category-400" />
            </div>
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
              Interlibrary Loan (ILL)
            </h3>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Enable ILL</span>
              {isEditing ? (
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.enable_ill ?? settings?.enable_ill ?? false}
                    onChange={(e) => setFormData({ ...formData, enable_ill: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-earth-200 peer-focus:ring-2 peer-focus:ring-lsc-rose rounded-full peer dark:bg-earth-700 peer-checked:bg-lsc-rose"></div>
                </label>
              ) : (
                <span
                  className={`text-sm font-medium ${settings?.enable_ill ? 'text-status-success-600' : 'text-lsc-dark/70 dark:text-lsc-cream/70'}`}
                >
                  {settings?.enable_ill ? 'Enabled' : 'Disabled'}
                </span>
              )}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Request Limit</span>
              {isEditing ? (
                <input
                  type="number"
                  value={formData.ill_request_limit ?? settings?.ill_request_limit ?? 10}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      ill_request_limit: parseInt(e.target.value),
                    })
                  }
                  className="w-20 px-2 py-1 rounded border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream text-right"
                  min={0}
                />
              ) : (
                <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  {settings?.ill_request_limit ?? 10}
                </span>
              )}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Loan Period (days)
              </span>
              {isEditing ? (
                <input
                  type="number"
                  value={formData.ill_loan_period_days ?? settings?.ill_loan_period_days ?? 21}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      ill_loan_period_days: parseInt(e.target.value),
                    })
                  }
                  className="w-20 px-2 py-1 rounded border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream text-right"
                  min={1}
                />
              ) : (
                <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  {settings?.ill_loan_period_days ?? 21}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Transit Settings */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-status-warning-100 dark:bg-status-warning-900/30 rounded-lg">
              <Settings className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400" />
            </div>
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Transit Settings</h3>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Consortium Transit
              </span>
              {isEditing ? (
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={
                      formData.enable_consortium_transit ??
                      settings?.enable_consortium_transit ??
                      false
                    }
                    onChange={(e) =>
                      setFormData({ ...formData, enable_consortium_transit: e.target.checked })
                    }
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-earth-200 peer-focus:ring-2 peer-focus:ring-lsc-rose rounded-full peer dark:bg-earth-700 peer-checked:bg-lsc-rose"></div>
                </label>
              ) : (
                <span
                  className={`text-sm font-medium ${settings?.enable_consortium_transit ? 'text-status-success-600' : 'text-lsc-dark/70 dark:text-lsc-cream/70'}`}
                >
                  {settings?.enable_consortium_transit ? 'Enabled' : 'Disabled'}
                </span>
              )}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Transit Time (days)
              </span>
              {isEditing ? (
                <input
                  type="number"
                  value={
                    formData.default_transit_time_days ?? settings?.default_transit_time_days ?? 3
                  }
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      default_transit_time_days: parseInt(e.target.value),
                    })
                  }
                  className="w-20 px-2 py-1 rounded border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream text-right"
                  min={1}
                />
              ) : (
                <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  {settings?.default_transit_time_days ?? 3}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {isEditing && (
        <div className="flex justify-end gap-3">
          <button
            onClick={() => {
              setIsEditing(false)
              setFormData(settings || {})
            }}
            disabled={isSubmitting}
            className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-xl font-medium disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isSubmitting}
            className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium flex items-center gap-2 disabled:opacity-50"
          >
            {isSubmitting ? (
              <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
            ) : (
              <Check className="w-4 h-4" />
            )}
            Save Changes
          </button>
        </div>
      )}
    </div>
  )
}

export default SharedResourcesTab
