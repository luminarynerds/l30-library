/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
/**
 * Blinders Overlay Component
 *
 * Narrows the content focus area and dims/blurs peripheral content.
 * Helps users with ADHD or sensory processing issues focus on central content
 * by reducing visual distractions.
 *
 * Features:
 * - Configurable content width
 * - Optional blur or dim effect on periphery
 * - Respects reduceMotion setting
 * - Scrolls with content
 * - Toggle with keyboard shortcut (Ctrl/Cmd + B)
 *
 * @module BlindersOverlay
 */

import { useState, useEffect, useCallback } from 'react';
import { useAccessibility } from '../hooks/useAccessibility';
import { clsx } from '../../../utils/helpers';
import { t } from '@/i18n'

export interface BlindersOverlayProps {
  /** Whether blinders are enabled */
  enabled: boolean;

  /** Width of focused content area in characters (ch units) */
  contentWidth?: number;

  /** Maximum width in pixels (overrides contentWidth if smaller) */
  maxWidth?: number;

  /** Opacity of dimmed areas (0-100) */
  dimOpacity?: number;

  /** Whether to blur peripheral content */
  enableBlur?: boolean;

  /** Blur intensity in pixels */
  blurAmount?: number;

  /** Background color of blinders */
  backgroundColor?: string;
}

export function BlindersOverlay({
  enabled,
  contentWidth = 60, // 60ch is a comfortable reading width
  maxWidth = 800,
  dimOpacity = 70,
  enableBlur = false,
  blurAmount = 4,
  backgroundColor,
}: BlindersOverlayProps) {
  const { settings, updateSetting } = useAccessibility();
  const isActive = enabled;

  /**
   * Toggle blinders with keyboard shortcut (Ctrl/Cmd + B)
   */
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl/Cmd + B to toggle blinders
      if ((e.ctrlKey || e.metaKey) && e.key === 'b' && !e.shiftKey && !e.altKey) {
        e.preventDefault();
        updateSetting('blinders', !enabled);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [enabled, updateSetting]);

  /**
   * Apply blinders effect to body
   */
  useEffect(() => {
    if (!isActive) {
      // Remove blinders styling
      document.body.style.removeProperty('--blinders-content-width');
      document.body.style.removeProperty('--blinders-max-width');
      document.body.classList.remove('blinders-active');
      return;
    }

    // Apply blinders styling
    document.body.style.setProperty('--blinders-content-width', `${contentWidth}ch`);
    document.body.style.setProperty('--blinders-max-width', `${maxWidth}px`);
    document.body.classList.add('blinders-active');

    return () => {
      document.body.style.removeProperty('--blinders-content-width');
      document.body.style.removeProperty('--blinders-max-width');
      document.body.classList.remove('blinders-active');
    };
  }, [isActive, contentWidth, maxWidth]);

  if (!isActive) {
    return null;
  }

  // Calculate colors based on theme
  const bgColor = backgroundColor || (
    settings.theme === 'dark' ? 'rgba(0, 0, 0, 0.8)' : 'rgba(255, 255, 255, 0.8)'
  );

  const blindersOpacity = dimOpacity / 100;

  return (
    <>
      {/* Left blinder */}
      <div
        className={clsx(
          'fixed top-0 bottom-0 left-0 pointer-events-none z-30',
          !settings.reduceMotion && 'transition-opacity duration-300'
        )}
        style={{
          width: 'calc((100vw - min(var(--blinders-content-width, 60ch), var(--blinders-max-width, 800px))) / 2)',
          backgroundColor: bgColor,
          opacity: blindersOpacity,
          backdropFilter: enableBlur && !settings.reduceMotion ? `blur(${blurAmount}px)` : undefined,
          WebkitBackdropFilter: enableBlur && !settings.reduceMotion ? `blur(${blurAmount}px)` : undefined,
        }}
        role="presentation"
        aria-hidden="true"
      />

      {/* Right blinder */}
      <div
        className={clsx(
          'fixed top-0 bottom-0 right-0 pointer-events-none z-30',
          !settings.reduceMotion && 'transition-opacity duration-300'
        )}
        style={{
          width: 'calc((100vw - min(var(--blinders-content-width, 60ch), var(--blinders-max-width, 800px))) / 2)',
          backgroundColor: bgColor,
          opacity: blindersOpacity,
          backdropFilter: enableBlur && !settings.reduceMotion ? `blur(${blurAmount}px)` : undefined,
          WebkitBackdropFilter: enableBlur && !settings.reduceMotion ? `blur(${blurAmount}px)` : undefined,
        }}
        role="presentation"
        aria-hidden="true"
      />

      {/* Inject CSS for content width constraint */}
      <style dangerouslySetInnerHTML={{
        __html: `
          body.blinders-active main,
          body.blinders-active article,
          body.blinders-active .blinders-content {
            max-width: min(var(--blinders-content-width, 60ch), var(--blinders-max-width, 800px)) !important;
            margin-left: auto !important;
            margin-right: auto !important;
          }

          /* Ensure main content stays centered */
          body.blinders-active {
            position: relative;
          }
        `
      }} />

      {/* Screen reader announcement */}
      <div className="sr-only" role="status" aria-live="polite">
        {isActive ? 'Blinders mode enabled - content area narrowed for focus' : 'Blinders mode disabled'}
      </div>

      {/* Blinders state indicator */}
      <div
        className={clsx(
          'fixed bottom-4 left-4 z-40',
          'bg-lsc-rose/20 dark:bg-lsc-rose/30 border border-lsc-rose/40 dark:border-lsc-rose/50',
          'px-3 py-2 rounded-lg shadow-sm',
          'text-xs font-medium text-lsc-rose dark:text-lsc-rose-light',
          'pointer-events-auto',
          'flex items-center gap-2',
          !settings.reduceMotion && 'motion-safe:animate-fade-in'
        )}
        role="status"
        aria-live="polite"
      >
        <span>Blinders on</span>
        <button
          type="button"
          className="underline underline-offset-2 hover:no-underline focus-visible:outline-none"
          onClick={() => updateSetting('blinders', false)}
          aria-label={t('aria.accessibility.turnOffBlindersMode')}
        >
          Turn off
        </button>
      </div>
    </>
  );
}

export function useBlinders() {
  const { settings, updateSetting } = useAccessibility();
  const [isEnabled, setIsEnabled] = useState(settings.blinders);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- mirrors external accessibility-context changes into local state
    setIsEnabled(settings.blinders);
  }, [settings.blinders]);

  const toggle = useCallback(() => {
    const newValue = !isEnabled;
    setIsEnabled(newValue);
    updateSetting('blinders', newValue);
  }, [isEnabled, updateSetting]);

  const enable = useCallback(() => {
    setIsEnabled(true);
    updateSetting('blinders', true);
  }, [updateSetting]);

  const disable = useCallback(() => {
    setIsEnabled(false);
    updateSetting('blinders', false);
  }, [updateSetting]);

  return {
    isEnabled,
    toggle,
    enable,
    disable,
  };
}

export default BlindersOverlay;
