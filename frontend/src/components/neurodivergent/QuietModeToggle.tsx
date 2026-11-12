/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * QuietModeToggle Component
 *
 * A quick toggle for quiet mode on pages with urgency/FOMO content.
 * Allows users to temporarily enable quiet mode without going to settings.
 *
 * @example
 * ```tsx
 * <QuietModeToggle />
 * ```
 */

import { VolumeX, Volume2 } from 'lucide-react'
import { useUnifiedAccessibility } from '@/features/accessibility/hooks/useUnifiedAccessibility'
import { useNeurodivergentUX } from '@/hooks/useNeurodivergentUX'
import { clsx } from '@/utils/helpers'

interface QuietModeToggleProps {
  className?: string
  showLabel?: boolean
}

export function QuietModeToggle({
  className,
  showLabel = true
}: QuietModeToggleProps): React.ReactElement {
  const { settings, updateSetting } = useUnifiedAccessibility()
  const quietMode = settings.quietMode || false
  const { getTransitionClass, announceToScreenReader } = useNeurodivergentUX()

  const handleToggle = () => {
    const newValue = !quietMode
    updateSetting('quietMode', newValue)
    announceToScreenReader(
      newValue
        ? 'Quiet mode enabled. Reduced urgency and animations.'
        : 'Quiet mode disabled. Normal view restored.'
    )
  }

  return (
    <button
      onClick={handleToggle}
      className={clsx(
        'flex items-center gap-2 px-3 py-2 rounded-xl border-2',
        quietMode
          ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 border-status-success-300 dark:border-status-success-700'
          : 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream border-lsc-border dark:border-earth-700',
        getTransitionClass(),
        'hover:shadow-md focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2',
        className
      )}
      aria-label={quietMode ? 'Disable quiet mode' : 'Enable quiet mode'}
      aria-pressed={quietMode}
      title={quietMode ? 'Quiet mode is on' : 'Enable quiet mode to reduce urgency and animations'}
    >
      {quietMode ? (
        <VolumeX className="w-4 h-4" aria-hidden="true" />
      ) : (
        <Volume2 className="w-4 h-4" aria-hidden="true" />
      )}
      {showLabel && (
        <span className="text-sm font-medium">
          {quietMode ? 'Quiet Mode On' : 'Quiet Mode'}
        </span>
      )}
    </button>
  )
}
