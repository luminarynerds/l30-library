/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Unified Neurodivergent UX Hook
 *
 * Combines accessibility and neurodivergent settings into a single, easy-to-use hook
 * that provides all the settings and computed helpers needed for neurodivergent-friendly UX.
 *
 * @example
 * ```tsx
 * const {
 *   focusMode,
 *   quietMode,
 *   shouldConfirm,
 *   shouldShowUndo,
 *   shouldHideFOMO
 * } = useNeurodivergentUX()
 *
 * if (quietMode) {
 *   // Hide animations and urgency indicators
 * }
 * ```
 */

import { useMemo } from 'react'
import { useUnifiedAccessibility } from '@/features/accessibility/hooks/useUnifiedAccessibility'

export interface NeurodivergentUXHelpers {
  // Direct settings from AccessibilityContext
  focusMode: boolean
  quietMode: boolean
  simplifiedView: boolean
  reduceMotion: boolean
  mutedColors: boolean
  showImages: boolean
  preferPagination: boolean
  noFOMO: boolean
  blinders: boolean
  breakReminders: boolean
  undoEnabled: boolean
  bionicReading: boolean

  // Direct settings from NeurodivergentSettings
  taskBreakdown: boolean
  decisionHelp: boolean
  simplifiedChoices: boolean
  confirmActions: boolean
  previewChanges: boolean
  hideDeadlines: boolean
  gentleReminders: boolean
  sessionResume: boolean
  anonymousBrowsing: boolean
  calmAvailability: boolean

  // Computed helpers
  shouldConfirm: (action: 'destructive' | 'important' | 'normal') => boolean
  shouldShowUndo: boolean
  shouldHideFOMO: boolean
  shouldSimplifyChoices: boolean
  shouldBreakdownTasks: boolean
  shouldPreviewChanges: boolean
  shouldUseGentleLanguage: boolean
  shouldHideDeadlines: boolean
  shouldShowProgress: boolean
  shouldEnableKeyboardShortcuts: boolean
  shouldAutoSave: boolean
  shouldLockLayout: boolean
  shouldUseExactSearch: boolean

  // Layout helpers
  getContentWidth: () => 'narrow' | 'normal' | 'wide'
  getHeaderMode: () => 'full' | 'minimal' | 'hidden'
  getSidebarMode: () => 'full' | 'icons' | 'hidden'

  // Visual helpers
  getAnimationClass: () => string
  getTransitionClass: () => string
  getColorClass: (base: string) => string

  // Interaction helpers
  getButtonClass: (variant: 'primary' | 'secondary' | 'danger') => string
  getCardClass: (elevated?: boolean) => string
  getInputClass: () => string

  // Content helpers
  shouldShowImages: (context: 'decorative' | 'functional') => boolean
  shouldShowAnimation: (purpose: 'decorative' | 'functional' | 'feedback') => boolean
  shouldShowBadge: (type: 'new' | 'urgent' | 'info') => boolean

  // Accessibility announcement helper
  announceToScreenReader: (message: string) => void
}

export function useNeurodivergentUX(): NeurodivergentUXHelpers {
  const { settings, announceToScreenReader } = useUnifiedAccessibility()

  // Memoize computed helpers
  const helpers = useMemo(() => {
    // Extract key settings from unified accessibility settings
    const focusMode = settings.focusMode || false
    const quietMode = settings.quietMode || false
    const simplifiedView = settings.plainLanguage || settings.simplifiedView || false
    const reduceMotion = settings.reduceMotion || false
    const mutedColors = settings.mutedColors || false
    const showImages = settings.showImages ?? true
    const preferPagination = settings.preferPagination || false
    const noFOMO = settings.noFOMO || false
    const blinders = settings.blinders || false
    const breakReminders = settings.breakReminders || false
    const undoEnabled = settings.undoEnabled || false
    const bionicReading = settings.bionicReading || false

    // Neurodivergent settings (mapped from flat structure)
    const taskBreakdown = false // Not in AccessibilitySettings, default to false
    const decisionHelp = false // Not in AccessibilitySettings, default to false
    const simplifiedChoices = settings.simplifiedView || false
    const confirmActions = settings.explicitConfirmations || false
    const previewChanges = false // Not in AccessibilitySettings, default to false
    const hideDeadlines = settings.removeTimePressure || false
    const gentleReminders = settings.whisperMode || false
    const sessionResume = settings.persistSession || false
    const anonymousBrowsing = settings.anonymousMode || false
    const calmAvailability = settings.whisperMode || false

    return {
      // Direct settings
      focusMode,
      quietMode,
      simplifiedView,
      reduceMotion,
      mutedColors,
      showImages,
      preferPagination,
      noFOMO,
      blinders,
      breakReminders,
      undoEnabled,
      bionicReading,
      taskBreakdown,
      decisionHelp,
      simplifiedChoices,
      confirmActions,
      previewChanges,
      hideDeadlines,
      gentleReminders,
      sessionResume,
      anonymousBrowsing,
      calmAvailability,

      // Computed helpers
      shouldConfirm: (action: 'destructive' | 'important' | 'normal') => {
        if (action === 'destructive') return true // Always confirm destructive actions
        if (action === 'important' && confirmActions) return true
        return false
      },

      shouldShowUndo: undoEnabled,
      shouldHideFOMO: noFOMO || quietMode,
      shouldSimplifyChoices: simplifiedChoices || simplifiedView,
      shouldBreakdownTasks: taskBreakdown,
      shouldPreviewChanges: previewChanges || confirmActions,
      shouldUseGentleLanguage: gentleReminders || quietMode,
      shouldHideDeadlines: hideDeadlines || quietMode,
      shouldShowProgress: false, // Not in AccessibilitySettings
      shouldEnableKeyboardShortcuts: true, // Not in AccessibilitySettings, default to true
      shouldAutoSave: false, // Not in AccessibilitySettings, default to false
      shouldLockLayout: false, // Not in AccessibilitySettings, default to false
      shouldUseExactSearch: false, // Not in AccessibilitySettings, default to false

      // Layout helpers
      getContentWidth: () => {
        if (blinders) return 'narrow'
        if (focusMode) return 'normal'
        return 'wide'
      },

      getHeaderMode: () => {
        if (focusMode) return 'minimal'
        if (simplifiedView) return 'minimal'
        return 'full'
      },

      getSidebarMode: () => {
        if (focusMode) return 'hidden'
        if (simplifiedView) return 'icons'
        return 'full'
      },

      // Visual helpers
      getAnimationClass: () => {
        if (reduceMotion) return 'transition-none'
        return 'transition-all duration-300'
      },

      getTransitionClass: () => {
        if (reduceMotion) return ''
        return 'transition-colors duration-200'
      },

      getColorClass: (base: string) => {
        if (mutedColors) {
          // Apply muted variants
          return base.replace('bg-', 'bg-').replace('-500', '-400').replace('-600', '-500')
        }
        return base
      },

      // Interaction helpers
      getButtonClass: (variant: 'primary' | 'secondary' | 'danger') => {
        const base = 'px-4 py-2 rounded-xl font-medium focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2'
        const motion = reduceMotion ? '' : 'transition-all duration-200 hover:shadow-lg active:scale-95'

        const variants = {
          primary: 'bg-lsc-rose text-white hover:bg-lsc-rose/90',
          secondary: 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream hover:bg-lsc-border dark:hover:bg-lsc-brown/80',
          danger: 'bg-status-danger-600 text-white hover:bg-status-danger-700'
        }

        return `${base} ${variants[variant]} ${motion}`
      },

      getCardClass: (elevated = false) => {
        const base = 'bg-lsc-white dark:bg-earth-800 rounded-xl'
        const shadow = elevated ? 'shadow-md' : 'shadow-sm'
        const motion = reduceMotion ? '' : 'hover:shadow-lg transition-shadow duration-200'
        const border = simplifiedView ? 'border-2 border-lsc-border dark:border-earth-700' : ''

        return `${base} ${shadow} ${motion} ${border}`
      },

      getInputClass: () => {
        const base = 'px-4 py-2 rounded-xl border bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream'
        const focus = 'focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:border-transparent'
        const border = simplifiedView ? 'border-2 border-lsc-border dark:border-earth-700' : 'border border-lsc-border dark:border-earth-700'

        return `${base} ${focus} ${border}`
      },

      // Content helpers
      shouldShowImages: (context: 'decorative' | 'functional') => {
        if (!showImages) return false
        if (context === 'decorative' && (simplifiedView || focusMode)) return false
        return true
      },

      shouldShowAnimation: (purpose: 'decorative' | 'functional' | 'feedback') => {
        if (reduceMotion && purpose === 'decorative') return false
        if (quietMode && purpose === 'decorative') return false
        return true
      },

      shouldShowBadge: (type: 'new' | 'urgent' | 'info') => {
        if (quietMode && type === 'urgent') return false
        if (noFOMO && type === 'urgent') return false
        if (simplifiedView && type === 'new') return false
        return true
      },

      // Accessibility announcement helper
      announceToScreenReader
    }
  }, [settings, announceToScreenReader])

  return helpers
}
