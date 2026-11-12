/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Bookmark, CheckCircle } from 'lucide-react'
import { useBookmarks, BookmarkType } from '@/hooks/useBookmarks'
import { COPY_FEEDBACK_DURATION_MS } from '@/constants/timeouts'
import { useTranslation } from '@/i18n'

interface SaveButtonProps {
  id: number
  type: BookmarkType
  title: string
  description?: string
  className?: string
  showLabel?: boolean
}

export default function SaveButton({
  id,
  type,
  title,
  description,
  className = '',
  showLabel = true,
}: SaveButtonProps) {
  const { t } = useTranslation()
  const { isBookmarked, toggleBookmark } = useBookmarks()
  const [showConfirm, setShowConfirm] = useState(false)

  const bookmarked = isBookmarked(id, type)

  const handleClick = () => {
    toggleBookmark(id, type, title, description)
    if (!bookmarked) {
      setShowConfirm(true)
      setTimeout(() => setShowConfirm(false), COPY_FEEDBACK_DURATION_MS)
    }
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <button
        onClick={handleClick}
        className={`flex items-center gap-1 px-3 py-1.5 rounded-lg transition-all ${
          bookmarked
            ? 'bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light'
            : 'bg-lsc-cream dark:bg-lsc-brown/20 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-rose/10'
        }`}
        title={bookmarked ? t('components.legal.saveButton.removeBookmark', 'Remove bookmark') : t('components.legal.saveButton.saveForLater', 'Save for later')}
        aria-label={bookmarked ? t('components.legal.saveButton.removeBookmark', 'Remove bookmark') : t('components.legal.saveButton.saveForLater', 'Save for later')}
      >
        <Bookmark
          className={`w-4 h-4 ${bookmarked ? 'fill-current' : ''}`}
          aria-hidden="true"
        />
        {showLabel && <span className="text-xs font-medium">{t('components.legal.saveButton.save', 'Save')}</span>}
      </button>

      {showConfirm && (
        <div className="flex items-center gap-1 text-xs text-status-success-600 dark:text-status-success-400 font-medium motion-safe:animate-pulse">
          <CheckCircle className="w-3 h-3" aria-hidden="true" />
          {t('components.legal.saveButton.saved', 'Saved')}
        </div>
      )}
    </div>
  )
}
