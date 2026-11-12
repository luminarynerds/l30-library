/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Modal for reading a book preview/sample.
 */
import { useQuery } from '@tanstack/react-query'
import { BookOpen, Loader2, X } from 'lucide-react'
import FocusTrap from 'focus-trap-react'
import { useEffect } from 'react'
import { getEbookPreview } from '@/api/indie-catalog-api'
import DOMPurify from 'dompurify'

interface BookPreviewModalProps {
  ebookId: number
  onClose: () => void
}

export default function BookPreviewModal({ ebookId, onClose }: BookPreviewModalProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['ebook-preview', ebookId],
    queryFn: () => getEbookPreview(ebookId),
  })

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  // Lock body scroll
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  return (
    // eslint-disable-next-line jsx-a11y/click-events-have-key-events
    <div
      className="fixed inset-0 bg-black/60 z-50 flex items-start justify-center p-4 overflow-y-auto"
      onClick={onClose}
    >
      <FocusTrap active focusTrapOptions={{ escapeDeactivates: true }}>
        {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="preview-modal-title"
          className="bg-lsc-white dark:bg-earth-900 rounded-xl shadow-lg w-full max-w-2xl my-8 flex flex-col max-h-[85vh]"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-lsc-border dark:border-earth-700 flex-shrink-0">
            <div className="flex items-center gap-2 min-w-0">
              <BookOpen className="w-5 h-5 text-lsc-rose flex-shrink-0" />
              <div className="min-w-0">
                <h2 id="preview-modal-title" className="font-serif font-bold text-lsc-dark dark:text-lsc-cream truncate">
                  {data?.title ?? 'Book Preview'}
                </h2>
                {data?.author_name && (
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 truncate">
                    by {data.author_name}
                  </p>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/60"
              aria-label="Close preview"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {isLoading && (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
              </div>
            )}
            {error && (
              <div className="text-center py-12">
                <p className="text-lsc-dark/70 dark:text-lsc-cream/60">
                  Preview not available for this book.
                </p>
              </div>
            )}
            {data && (
              <div
                className="prose dark:prose-invert prose-sm max-w-none text-lsc-dark/90 dark:text-lsc-cream/90 leading-relaxed"
                dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(data.preview_html) }}
              />
            )}
          </div>

          {/* Footer */}
          {data && (
            <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex-shrink-0">
              <p className="text-xs text-center text-lsc-dark/70 dark:text-lsc-cream/60">
                {data.preview_pct > 0
                  ? `This is approximately ${data.preview_pct}% of the book. Borrow to read the full version.`
                  : 'This is the book description. Borrow to read the full book.'}
              </p>
            </div>
          )}
        </div>
      </FocusTrap>
    </div>
  )
}
