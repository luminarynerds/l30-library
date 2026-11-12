/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Line Focus Guide Component
 *
 * A horizontal highlight bar that follows the mouse cursor or can be
 * controlled via keyboard, helping users track their reading position.
 * Useful for users with dyslexia, ADHD, or visual tracking difficulties.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useUnifiedAccessibility } from '../hooks/useUnifiedAccessibility';

interface LineFocusGuideProps {
  /** Whether the guide is enabled (overrides settings) */
  enabled?: boolean;
  /** Height of the guide in em units */
  height?: number;
  /** Whether to follow mouse cursor */
  followMouse?: boolean;
  /** Color of the guide highlight */
  color?: string;
}

export function LineFocusGuide({
  enabled: enabledProp,
  height = 2.5,
  followMouse = true,
  color,
}: LineFocusGuideProps) {
  const { settings } = useUnifiedAccessibility();
  const enabled = enabledProp ?? settings.lineFocusGuide;

  const [position, setPosition] = useState(200);
  const [isKeyboardMode, setIsKeyboardMode] = useState(false);
  const guideRef = useRef<HTMLDivElement>(null);
  const lastMouseY = useRef(200);

  // Handle mouse movement
  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!enabled || !followMouse || isKeyboardMode) return;
      lastMouseY.current = e.clientY;
      setPosition(e.clientY);
    },
    [enabled, followMouse, isKeyboardMode]
  );

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!enabled) return;

      // Only activate keyboard mode if user presses navigation keys
      const isNavKey = ['ArrowUp', 'ArrowDown', 'j', 'k', 'PageUp', 'PageDown'].includes(e.key);

      if (isNavKey) {
        setIsKeyboardMode(true);
        const step = e.shiftKey ? 50 : 20;

        switch (e.key) {
          case 'ArrowUp':
          case 'k':
            e.preventDefault();
            setPosition((prev) => Math.max(height * 8, prev - step));
            break;
          case 'ArrowDown':
          case 'j':
            e.preventDefault();
            setPosition((prev) => Math.min(window.innerHeight - height * 8, prev + step));
            break;
          case 'PageUp':
            e.preventDefault();
            setPosition((prev) => Math.max(height * 8, prev - 100));
            break;
          case 'PageDown':
            e.preventDefault();
            setPosition((prev) => Math.min(window.innerHeight - height * 8, prev + 100));
            break;
        }
      }

      // Return to mouse mode on any mouse movement
      if (e.key === 'Escape') {
        setIsKeyboardMode(false);
        setPosition(lastMouseY.current);
      }
    },
    [enabled, height]
  );

  // Re-enable mouse tracking on mouse move after keyboard use
  const handleMouseMoveAfterKeyboard = useCallback(
    (e: MouseEvent) => {
      if (isKeyboardMode) {
        // Small threshold to prevent accidental switches
        const delta = Math.abs(e.clientY - position);
        if (delta > 20) {
          setIsKeyboardMode(false);
          lastMouseY.current = e.clientY;
          setPosition(e.clientY);
        }
      }
    },
    [isKeyboardMode, position]
  );

  // Handle scroll to keep guide relative to viewport
  const handleScroll = useCallback(() => {
    if (!enabled || !isKeyboardMode) return;
    // In keyboard mode, guide stays fixed in viewport
  }, [enabled, isKeyboardMode]);

  useEffect(() => {
    if (!enabled) return;

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mousemove', handleMouseMoveAfterKeyboard);
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('scroll', handleScroll);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mousemove', handleMouseMoveAfterKeyboard);
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('scroll', handleScroll);
    };
  }, [enabled, handleMouseMove, handleMouseMoveAfterKeyboard, handleKeyDown, handleScroll]);

  if (!enabled) return null;

  const guideHeight = `${height}em`;
  const guideColor = color || 'rgba(255, 200, 0, 0.15)';
  const borderColor = color
    ? color.replace(/[\d.]+\)$/, '0.4)')
    : 'rgba(255, 180, 0, 0.3)';

  return (
    <>
      {/* Main guide bar */}
      <div
        ref={guideRef}
        className="line-focus-guide-element"
        style={{
          position: 'fixed',
          left: 0,
          right: 0,
          height: guideHeight,
          top: `calc(${position}px - ${height / 2}em)`,
          background: `linear-gradient(
            to bottom,
            transparent 0%,
            ${guideColor} 20%,
            ${guideColor} 80%,
            transparent 100%
          )`,
          borderTop: `1px solid ${borderColor}`,
          borderBottom: `1px solid ${borderColor}`,
          pointerEvents: 'none',
          zIndex: 9998,
          transition: isKeyboardMode ? 'top 0.15s ease-out' : 'none',
        }}
        aria-hidden="true"
      />

      {/* Mode indicator */}
      {isKeyboardMode && (
        <div
          className="fixed top-2 left-1/2 -translate-x-1/2 z-[9999] bg-black/70 text-white text-xs px-3 py-1.5 rounded-full flex items-center gap-2"
          aria-live="polite"
        >
          <span className="w-2 h-2 bg-status-warning-400 rounded-full motion-safe:animate-pulse motion-reduce:animate-none" aria-hidden="true" />
          Keyboard mode
          <span className="text-white/60">
            (<kbd className="px-1">↑↓</kbd> move, <kbd className="px-1">Esc</kbd> exit)
          </span>
        </div>
      )}
    </>
  );
}

export default LineFocusGuide;
