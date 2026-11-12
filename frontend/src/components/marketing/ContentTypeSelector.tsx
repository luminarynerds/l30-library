/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { CONTENT_TYPE_OPTIONS, type ContentType } from '@/api/marketing-hub-api'
import { chipSelected, chipUnselected } from './useAIGeneration'

interface ContentTypeSelectorProps {
  contentType: ContentType
  setContentType: (ct: ContentType) => void
  description?: string
}

export default function ContentTypeSelector({ contentType, setContentType, description }: ContentTypeSelectorProps) {
  return (
    <div>
      <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
        Content Type
      </label>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
        {CONTENT_TYPE_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => setContentType(option.value)}
            className={`px-3 py-2 rounded-xl text-sm font-medium motion-safe:transition-colors text-center focus:outline-none focus:ring-2 focus:ring-lsc-rose ${
              contentType === option.value ? chipSelected : chipUnselected
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>
      {description && (
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
          {description}
        </p>
      )}
    </div>
  )
}
