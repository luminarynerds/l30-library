/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from "react"
import { X, Bell, Shield, UserCheck, Loader2, Save } from "lucide-react"
import toast from "react-hot-toast"
import { useTranslation } from '@/i18n'
import { fetchApi } from "../../../../api/fetchApi"
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface PatronAccountSettingsModalProps {
  isOpen: boolean
  onClose: () => void
  patronId: number
  patronName?: string
}

interface PatronSettings {
  notifications: {
    holds_ready: boolean
    items_due: boolean
    events: boolean
  }
  privacy: {
    retain_reading_history: boolean
  }
  account_status: "active" | "suspended" | "expired"
}

const DEFAULT_SETTINGS: PatronSettings = {
  notifications: {
    holds_ready: true,
    items_due: true,
    events: false,
  },
  privacy: {
    retain_reading_history: true,
  },
  account_status: "active",
}

export function PatronAccountSettingsModal({ isOpen, onClose, patronId, patronName }: PatronAccountSettingsModalProps) {
  const { t } = useTranslation()
  const [settings, setSettings] = useState<PatronSettings>(DEFAULT_SETTINGS)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isDirty, setIsDirty] = useState(false)

  const loadSettings = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await fetchApi(`/staff/patrons/${patronId}/settings`)
      setSettings(data)
    } catch (err: unknown) {
      // 404 means the endpoint doesn't exist yet -- use defaults silently
      const status = (err as { status?: number })?.status
      if (status !== 404) {
        toast.error(
          err instanceof Error
            ? err.message
            : t('patronAccountSettings.failedToLoad')
        )
      }
    } finally {
      setIsLoading(false)
    }
  }, [patronId, t])

  useEffect(() => {
    if (isOpen) {
      setIsDirty(false)
      loadSettings()
    }
  }, [isOpen, loadSettings])

  const updateNotification = (key: keyof PatronSettings["notifications"], value: boolean) => {
    setSettings(prev => ({
      ...prev,
      notifications: { ...prev.notifications, [key]: value },
    }))
    setIsDirty(true)
  }

  const updatePrivacy = (key: keyof PatronSettings["privacy"], value: boolean) => {
    setSettings(prev => ({
      ...prev,
      privacy: { ...prev.privacy, [key]: value },
    }))
    setIsDirty(true)
  }

  const handleSave = async () => {
    setIsSaving(true)
    try {
      await fetchApi(`/staff/patrons/${patronId}/settings`, {
        method: "PUT",
        body: JSON.stringify({
          notifications: settings.notifications,
          privacy: settings.privacy,
        }),
      })
      toast.success(t('patronAccountSettings.saved'))
      setIsDirty(false)
      onClose()
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status
      if (status === 404) {
        toast.error(t('patronAccountSettings.endpointNotReady'))
      } else {
        toast.error(
          err instanceof Error
            ? err.message
            : t('patronAccountSettings.failedToSave')
        )
      }
    } finally {
      setIsSaving(false)
    }
  }

  if (!isOpen) return null

  const statusColors: Record<string, string> = {
    active: "bg-lsc-green/10 text-forest-800 dark:bg-lsc-green/20 dark:text-status-success-300",
    suspended: "bg-lsc-rose/10 text-lsc-rose dark:bg-lsc-rose/20",
    expired: "bg-status-danger-100 text-status-danger-600 dark:bg-status-danger-900/30 dark:text-status-danger-400",
  }

  return (
    <ModalBackdrop onClose={onClose} title="Dialog">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            {patronName
              ? t('patronAccountSettings.titleWithName', { name: patronName })
              : t('patronAccountSettings.title')}
          </h2>
          <button
            onClick={onClose}
            aria-label={t('aria.authModals.close')}
            className="text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : (
          <div className="space-y-6">
            {/* Account Status (read-only) */}
            <section>
              <div className="flex items-center gap-2 mb-3">
                <UserCheck className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60" />
                <h3 className="text-sm font-semibold uppercase tracking-wide text-lsc-dark/70 dark:text-lsc-cream/60">
                  {t('patronAccountSettings.accountStatus')}
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${statusColors[settings.account_status] || statusColors.active}`}>
                  {t(`patronAccountSettings.status.${settings.account_status}`)}
                </span>
                <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('patronAccountSettings.statusReadOnly')}
                </span>
              </div>
            </section>

            {/* Notification Preferences */}
            <section>
              <div className="flex items-center gap-2 mb-3">
                <Bell className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60" />
                <h3 className="text-sm font-semibold uppercase tracking-wide text-lsc-dark/70 dark:text-lsc-cream/60">
                  {t('patronAccountSettings.notifications')}
                </h3>
              </div>
              <div className="space-y-3">
                <ToggleRow
                  label={t('patronAccountSettings.holdsReady')}
                  description={t('patronAccountSettings.holdsReadyDesc')}
                  checked={settings.notifications.holds_ready}
                  onChange={v => updateNotification("holds_ready", v)}
                />
                <ToggleRow
                  label={t('patronAccountSettings.itemsDue')}
                  description={t('patronAccountSettings.itemsDueDesc')}
                  checked={settings.notifications.items_due}
                  onChange={v => updateNotification("items_due", v)}
                />
                <ToggleRow
                  label={t('patronAccountSettings.events')}
                  description={t('patronAccountSettings.eventsDesc')}
                  checked={settings.notifications.events}
                  onChange={v => updateNotification("events", v)}
                />
              </div>
            </section>

            {/* Privacy Controls */}
            <section>
              <div className="flex items-center gap-2 mb-3">
                <Shield className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60" />
                <h3 className="text-sm font-semibold uppercase tracking-wide text-lsc-dark/70 dark:text-lsc-cream/60">
                  {t('patronAccountSettings.privacy')}
                </h3>
              </div>
              <div className="space-y-3">
                <ToggleRow
                  label={t('patronAccountSettings.retainHistory')}
                  description={t('patronAccountSettings.retainHistoryDesc')}
                  checked={settings.privacy.retain_reading_history}
                  onChange={v => updatePrivacy("retain_reading_history", v)}
                />
              </div>
            </section>
          </div>
        )}

        {/* Footer */}
        <div className="flex justify-end gap-2 pt-4 mt-6 border-t border-lsc-border dark:border-earth-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream/50 dark:hover:bg-earth-700 rounded-lg transition-colors"
          >
            {t('patronAccountSettings.cancel')}
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving || isLoading || !isDirty}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-forest-800 rounded-lg hover:bg-forest-900 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSaving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Save className="w-4 h-4" />}
            {t('patronAccountSettings.save')}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}

/* -- Toggle Row sub-component ------------------------------------------------ */

interface ToggleRowProps {
  label: string
  description: string
  checked: boolean
  onChange: (value: boolean) => void
}

function ToggleRow({ label, description, checked, onChange }: ToggleRowProps) {
  return (
    <label className="flex items-start gap-3 cursor-pointer group">
      <div className="pt-0.5">
        <button
          type="button"
          role="switch"
          aria-checked={checked}
          onClick={() => onChange(!checked)}
          className={`relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 dark:focus-visible:ring-offset-earth-800 ${
            checked ? "bg-lsc-green" : "bg-lsc-dark/20 dark:bg-lsc-cream/20"
          }`}
        >
          <span
            className={`pointer-events-none inline-block h-4 w-4 rounded-full bg-lsc-white dark:bg-earth-100 shadow-sm ring-0 transition-transform ${
              checked ? "translate-x-4" : "translate-x-0"
            }`}
          />
        </button>
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
          {label}
        </div>
        <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50 mt-0.5">
          {description}
        </div>
      </div>
    </label>
  )
}
