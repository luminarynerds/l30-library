/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * EventPreferencesModal - Let users set their favorite event categories and audiences
 * Stores preferences in localStorage for personalized event recommendations
 */
import { useCallback, useId } from 'react'
import { X, Sparkles, Check } from 'lucide-react'
import FocusTrap from 'focus-trap-react'
import type { EventPreferences } from '@/hooks/useEventPersonalization'
import { t } from '@/i18n'

interface EventPreferencesModalProps {
  isOpen: boolean
  onClose: () => void
  preferences: EventPreferences
  onToggleCategory: (category: string) => void
  onToggleAudience: (audience: string) => void
  onClearPreferences: () => void
  availableCategories?: string[]
  availableAudiences?: string[]
}

// Note: Categories and audiences are now fetched dynamically from the backend
// and passed as props to this component

function PreferenceChip({
  label,
  description,
  isSelected,
  onToggle,
}: {
  label: string
  description: string
  isSelected: boolean
  onToggle: () => void
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all focus:outline-none focus:ring-2 focus:ring-lsc-rose ${
        isSelected
          ? 'bg-lsc-rose text-white shadow-md'
          : 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-border dark:hover:bg-earth-600'
      }`}
      aria-pressed={isSelected}
      title={description}
    >
      {isSelected && <Check aria-hidden="true" className="w-4 h-4" />}
      {label}
    </button>
  )
}

export default function EventPreferencesModal({
  isOpen,
  onClose,
  preferences,
  onToggleCategory,
  onToggleAudience,
  onClearPreferences,
  availableCategories = [],
  availableAudiences = [],
}: EventPreferencesModalProps): React.ReactElement | null {
  const titleId = useId()

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose()
    }
  }, [onClose])

  const handleBackdropClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }, [onClose])

  const hasPreferences = preferences.categories.length > 0 || preferences.audiences.length > 0

  if (!isOpen) return null

  return (
    <FocusTrap focusTrapOptions={{ allowOutsideClick: true }}>
      <div
        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
        role="presentation"
        onClick={handleBackdropClick}
        onKeyDown={handleKeyDown}
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-lg w-full max-h-[90vh] overflow-y-auto"
        >
          {/* Header */}
          <div className="sticky top-0 bg-lsc-white dark:bg-earth-800 flex items-center justify-between p-4 border-b border-lsc-border dark:border-earth-700 z-10">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-lsc-rose/20 rounded-xl">
                <Sparkles aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
              </div>
              <div>
                <h2
                  id={titleId}
                  className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream"
                >
                  Event Preferences
                </h2>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  Tell us what you're interested in
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              aria-label={t('aria.events.closePreferences')}
            >
              <X aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            </button>
          </div>

          {/* Content */}
          <div className="p-4 space-y-6">
            {/* Categories Section */}
            <div>
              <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
                Event Categories
              </h3>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
                Select the types of events you're most interested in:
              </p>
              <div className="flex flex-wrap gap-2">
                {availableCategories.map((category) => (
                  <PreferenceChip
                    key={category}
                    label={category}
                    description={category}
                    isSelected={preferences.categories.includes(category)}
                    onToggle={() => onToggleCategory(category)}
                  />
                ))}
              </div>
            </div>

            {/* Audiences Section */}
            <div>
              <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
                Age Groups & Audiences
              </h3>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
                Who will be attending? Select all that apply:
              </p>
              <div className="flex flex-wrap gap-2">
                {availableAudiences.map((audience) => (
                  <PreferenceChip
                    key={audience}
                    label={audience}
                    description={audience}
                    isSelected={preferences.audiences.includes(audience)}
                    onToggle={() => onToggleAudience(audience)}
                  />
                ))}
              </div>
            </div>

            {/* Summary */}
            {hasPreferences && (
              <div className="p-4 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-xl">
                <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                  Your Preferences
                </h3>
                <div className="space-y-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {preferences.categories.length > 0 && (
                    <p>
                      <span className="font-medium">Categories:</span>{' '}
                      {preferences.categories.join(', ')}
                    </p>
                  )}
                  {preferences.audiences.length > 0 && (
                    <p>
                      <span className="font-medium">Audiences:</span>{' '}
                      {preferences.audiences.join(', ')}
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Info text */}
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              Your preferences are saved locally on this device and help us show you relevant events in the "For You" section.
            </p>
          </div>

          {/* Footer */}
          <div className="sticky bottom-0 bg-lsc-white dark:bg-earth-800 flex items-center justify-between p-4 border-t border-lsc-border dark:border-earth-700">
            {hasPreferences ? (
              <button
                onClick={onClearPreferences}
                className="text-sm text-status-danger-600 dark:text-status-danger-400 hover:text-status-danger-700 dark:hover:text-status-danger-300 font-medium"
              >
                Clear all preferences
              </button>
            ) : (
              <span />
            )}
            <button
              onClick={onClose}
              className="px-6 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2"
            >
              Done
            </button>
          </div>
        </div>
      </div>
    </FocusTrap>
  )
}
