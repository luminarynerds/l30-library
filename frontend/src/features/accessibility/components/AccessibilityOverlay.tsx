/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Accessibility Overlay Component
 *
 * Central integration component that renders all accessibility tools
 * based on user settings. This component should be placed near the root
 * of the application to ensure overlays render correctly.
 */

import { useUnifiedAccessibility } from '../hooks/useUnifiedAccessibility';
import { BionicReadingGlobal } from './BionicReadingGlobal';
import { BlindersOverlay } from './BlindersOverlay';
import { ColorBlindFilters } from './ColorBlindFilters';
import { ReadingMask } from './ReadingMask';
import { LineFocusGuide } from './LineFocusGuide';
import { SessionTimeAwareness } from './SessionTimeAwareness';
import { VoiceControlIndicator } from './VoiceControlIndicator';

interface AccessibilityOverlayProps {
  /** Disable all overlays (useful for specific pages) */
  disabled?: boolean;
}

export function AccessibilityOverlay({ disabled = false }: AccessibilityOverlayProps) {
  const { settings } = useUnifiedAccessibility();

  if (disabled) return null;

  const showReadingMask =
    settings.readingTool === 'mask' || settings.readingTool === 'both';
  const showLineFocusGuide =
    settings.readingTool === 'guide' ||
    settings.readingTool === 'both' ||
    settings.lineFocusGuide;

  return (
    <>
      {/* SVG filters for color blind modes - always render */}
      <ColorBlindFilters />

      {/* Reading assistance tools */}
      {showReadingMask && (
        <ReadingMask
          enabled={showReadingMask}
          windowHeight={settings.readingMaskHeight}
          maskOpacity={settings.readingMaskOpacity / 100}
        />
      )}

      {showLineFocusGuide && <LineFocusGuide enabled={showLineFocusGuide} />}

      {/* Session time awareness and break reminders */}
      {(settings.breakReminders || settings.showSessionTime) && (
        <SessionTimeAwareness
          enabled={settings.breakReminders}
          breakIntervalMinutes={settings.breakIntervalMinutes}
        />
      )}

      {/* Voice control indicator */}
      {settings.voiceControlEnabled && <VoiceControlIndicator />}

      {/* Global bionic reading text processor */}
      {settings.bionicReading && <BionicReadingGlobal />}

      {/* Blinders overlay (narrow focus area) */}
      {settings.blinders && <BlindersOverlay enabled />}
    </>
  );
}

export default AccessibilityOverlay;
