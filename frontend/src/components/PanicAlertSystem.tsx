/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { DiscretePanicButton } from './DiscretePanicButton'
import { usePanicAlertShortcut } from '@/hooks/usePanicAlertShortcut'
import { clean } from '@/lib/utils'

interface PanicAlertSystemProps {
  enableKeyboardShortcut?: boolean
  showButton?: boolean
  buttonPosition?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right'
  buttonRequireDoubleTap?: boolean
  buttonRequireHold?: boolean
  holdDurationMs?: number
  onAlertTriggered?: () => void
}

// Separate component for keyboard shortcut so a crash doesn't take down the button
const PanicKeyboardShortcut: React.FC<{
  enabled: boolean
  onTriggered?: () => void
}> = ({ enabled, onTriggered }) => {
  usePanicAlertShortcut(clean({
    enabled,
    onTriggered,
    requireHold: true,
    holdDurationMs: 500,
  }))
  return null
}

export const PanicAlertSystem: React.FC<PanicAlertSystemProps> = ({
  enableKeyboardShortcut = true,
  showButton = true,
  buttonPosition = 'bottom-right',
  buttonRequireDoubleTap = true,
  buttonRequireHold = false,
  holdDurationMs = 500,
  onAlertTriggered,
}) => {
  return (
    <>
      <PanicKeyboardShortcut
        enabled={enableKeyboardShortcut}
        {...(onAlertTriggered !== undefined ? { onTriggered: onAlertTriggered } : {})}
      />
      <DiscretePanicButton
        visible={showButton}
        position={buttonPosition}
        requireDoubleTap={buttonRequireDoubleTap}
        requireHold={buttonRequireHold}
        holdDurationMs={holdDurationMs}
        {...(onAlertTriggered !== undefined ? { onTriggered: onAlertTriggered } : {})}
      />
    </>
  )
}
