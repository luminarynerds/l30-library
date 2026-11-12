/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X, Check, Loader2 } from 'lucide-react'
import type { AuthorCreate } from '../../api/releases-api'
import { useTranslation } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface CreateAuthorModalProps {
  authorForm: AuthorCreate
  isSubmitting: boolean
  onClose: () => void
  onSubmit: () => void
  onFormChange: (form: AuthorCreate) => void
}

export function CreateAuthorModal({
  authorForm,
  isSubmitting,
  onClose,
  onSubmit,
  onFormChange,
}: CreateAuthorModalProps): React.ReactElement {
  const { t } = useTranslation()

  return (
    <ModalBackdrop onClose={onClose} title="Add New Author">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-md">
        <div className="flex items-center justify-between p-4 border-b border-lsc-border dark:border-earth-700">
          <h2 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            Add New Author
          </h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-full"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            onSubmit()
          }}
          className="p-6 space-y-4"
        >
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Name *
            </label>
            <input
              type="text"
              value={authorForm.name}
              onChange={(e) => onFormChange({ ...authorForm, name: e.target.value })}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Google Books ID
            </label>
            <input
              type="text"
              value={authorForm.google_id || ''}
              onChange={(e) => onFormChange({ ...authorForm, google_id: e.target.value })}
              placeholder={t('releasesManagement.optionalForExternalDataSync')}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Image URL
            </label>
            <input
              type="url"
              value={authorForm.image_url || ''}
              onChange={(e) => onFormChange({ ...authorForm, image_url: e.target.value })}
              placeholder={t('placeholder.admin.https1')}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Website
            </label>
            <input
              type="url"
              value={authorForm.website || ''}
              onChange={(e) => onFormChange({ ...authorForm, website: e.target.value })}
              placeholder={t('placeholder.admin.https1')}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Bio
            </label>
            <textarea
              value={authorForm.bio || ''}
              onChange={(e) => onFormChange({ ...authorForm, bio: e.target.value })}
              rows={3}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            />
          </div>
          <div className="flex justify-end gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-xl disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl flex items-center gap-2 disabled:opacity-50"
            >
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
              ) : (
                <Check className="w-4 h-4" />
              )}
              {isSubmitting ? 'Creating...' : 'Create Author'}
            </button>
          </div>
        </form>
      </div>
    </ModalBackdrop>
  )
}
