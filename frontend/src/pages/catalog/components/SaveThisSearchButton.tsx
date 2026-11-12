/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useId, useState } from 'react'
import toast from 'react-hot-toast'
import { Bookmark } from 'lucide-react'
import { useTranslation } from '@/i18n/I18nContext'
import { useAuth } from '@/contexts/AuthContext'
import { useUnifiedAccessibility } from '@/features/accessibility/hooks/useUnifiedAccessibility'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import { useSavedSearches } from '../hooks/useSavedSearches'

export interface SaveThisSearchSnapshot {
  /** Patron's current search query string (may be empty). */
  query: string
  /** Filter shape stored in filters_json — opaque to the backend on save. */
  filters: Record<string, unknown>
  /** Optional sort/view hints for replay completeness. */
  sortBy?: string | null
  viewMode?: string | null
}

interface SaveThisSearchButtonProps {
  snapshot: SaveThisSearchSnapshot
  /** Hide the button entirely when there's nothing meaningful to save. */
  hasActiveContext: boolean
}

export default function SaveThisSearchButton({
  snapshot,
  hasActiveContext,
}: SaveThisSearchButtonProps): React.ReactElement | null {
  const { t } = useTranslation()
  const { user, isAuthenticated } = useAuth()
  const { announceToScreenReader } = useUnifiedAccessibility()
  const { create } = useSavedSearches({ enabled: isAuthenticated })
  const [isOpen, setIsOpen] = useState(false)
  const [name, setName] = useState('')
  const [notifyInApp, setNotifyInApp] = useState(true)
  const [notifyEmail, setNotifyEmail] = useState(false)
  const nameInputId = useId()
  const emailHelperId = useId()

  if (!isAuthenticated || !hasActiveContext) return null

  const hasEmail = !!(user?.email && user.email.trim())

  const reset = () => {
    setName('')
    setNotifyInApp(true)
    setNotifyEmail(false)
  }

  const handleOpen = () => {
    reset()
    setIsOpen(true)
  }

  const handleClose = () => {
    setIsOpen(false)
    reset()
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) return
    // notify_on_new mirrors whichever channel(s) the patron opted into. If
    // neither is checked, we don't enable alerts — saving a search without
    // alerts is a valid use case (run it on demand).
    const notifyOnNew = notifyInApp || notifyEmail
    try {
      await create.mutateAsync({
        name: trimmed,
        query: snapshot.query || null,
        filters_json: snapshot.filters,
        sort_by: snapshot.sortBy ?? null,
        view_mode: snapshot.viewMode ?? null,
        notify_on_new: notifyOnNew,
        notify_in_app: notifyInApp,
        notify_email: notifyEmail && hasEmail,
      })
      toast.success(t('catalog.savedSearches.dialog.saved', 'Saved.'))
      announceToScreenReader('Search saved.')
      handleClose()
    } catch {
      toast.error(t('catalog.savedSearches.dialog.saveError', 'Could not save this search. Please try again.'))
    }
  }

  const dialogTitle = t('catalog.savedSearches.dialog.title', 'Save this search')

  return (
    <>
      <button
        type="button"
        onClick={handleOpen}
        className="inline-flex items-center gap-1 rounded-lg border border-lsc-rose px-2 py-1 text-sm font-medium text-lsc-rose hover:bg-lsc-rose hover:text-white focus:outline-none focus:ring-2 focus:ring-lsc-rose"
        data-testid="save-this-search-button"
      >
        <Bookmark className="h-3.5 w-3.5" aria-hidden />
        {t('catalog.savedSearches.saveButton', 'Save this search')}
      </button>

      {isOpen && (
        <ModalBackdrop onClose={handleClose} title={dialogTitle}>
          <form
            onSubmit={handleSubmit}
            className="w-full max-w-md rounded-lg bg-lsc-white dark:bg-earth-800 p-6 shadow-lg"
            data-testid="save-this-search-dialog"
          >
            <h2 className="mb-4 text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              {dialogTitle}
            </h2>

            <label htmlFor={nameInputId} className="mb-1 block text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              {t('catalog.savedSearches.dialog.nameLabel', 'Name')}
              <span aria-hidden className="ml-0.5 text-lsc-rose">*</span>
            </label>
            <input
              id={nameInputId}
              type="text"
              required
              minLength={1}
              maxLength={120}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t('catalog.savedSearches.dialog.namePlaceholder', 'e.g. New sci-fi 2024+')}
              autoFocus
              className="w-full rounded border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-900 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            />

            <fieldset className="mt-4 space-y-2">
              <legend className="sr-only">Notification preferences</legend>
              <label className="flex items-start gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
                <input
                  type="checkbox"
                  checked={notifyInApp}
                  onChange={(e) => setNotifyInApp(e.target.checked)}
                  className="mt-0.5 h-4 w-4 rounded border-lsc-border dark:border-earth-600 text-lsc-rose focus:ring-lsc-rose"
                />
                <span>
                  {t('catalog.savedSearches.dialog.notifyInApp', 'Notify me in the app when new items match')}
                </span>
              </label>
              <label
                className={
                  'flex items-start gap-2 text-sm ' +
                  (hasEmail ? 'text-lsc-dark dark:text-lsc-cream' : 'text-lsc-dark/40 dark:text-lsc-cream/40')
                }
                title={hasEmail ? undefined : t('catalog.savedSearches.dialog.noEmailOnFile', 'Add an email address to your account to enable email alerts.')}
              >
                <input
                  type="checkbox"
                  checked={notifyEmail && hasEmail}
                  disabled={!hasEmail}
                  onChange={(e) => setNotifyEmail(e.target.checked)}
                  aria-describedby={!hasEmail ? emailHelperId : undefined}
                  className="mt-0.5 h-4 w-4 rounded border-lsc-border dark:border-earth-600 text-lsc-rose focus:ring-lsc-rose disabled:opacity-50"
                />
                <span>
                  {t('catalog.savedSearches.dialog.notifyEmail', 'Email me when new items match')}
                </span>
              </label>
              {!hasEmail && (
                <p id={emailHelperId} className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
                  {t('catalog.savedSearches.dialog.noEmailOnFile', 'Add an email address to your account to enable email alerts.')}
                </p>
              )}
            </fieldset>

            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={handleClose}
                className="rounded px-3 py-1.5 text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              >
                {t('catalog.savedSearches.dialog.cancel', 'Cancel')}
              </button>
              <button
                type="submit"
                disabled={create.isPending || !name.trim()}
                className="rounded bg-lsc-rose px-3 py-1.5 text-sm font-semibold text-white hover:bg-lsc-rose/90 focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-60"
              >
                {t('catalog.savedSearches.dialog.save', 'Save')}
              </button>
            </div>
          </form>
        </ModalBackdrop>
      )}
    </>
  )
}
