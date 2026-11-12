/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Reading Mask Component
 *
 * Creates a movable reading window that dims everything except
 * a horizontal strip, helping users focus on one line at a time.
 * Particularly helpful for users with ADHD, dyslexia, or visual processing difficulties.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useUnifiedAccessibility } from '../hooks/useUnifiedAccessibility';
import { X, Move, ChevronUp, ChevronDown } from 'lucide-react';
import { t } from '@/i18n'

interface ReadingMaskProps {
  /** Whether the mask is enabled */
  enabled?: boolean;
  /** Callback when mask is closed */
  onClose?: () => void;
  /** Height of the visible reading window in pixels */
  windowHeight?: number;
  /** Opacity of the masked areas (0-1) */
  maskOpacity?: number;
}

export function ReadingMask({
  enabled: enabledProp,
  onClose,
  windowHeight: windowHeightProp = 80,
  maskOpacity = 0.75,
}: ReadingMaskProps) {
  const { settings } = useUnifiedAccessibility();
  const enabled = enabledProp ?? settings.readingGuide;

  const [position, setPosition] = useState(50); // Percentage from top
  const [windowHeight, setWindowHeight] = useState(windowHeightProp);
  const [isDragging, setIsDragging] = useState(false);
  const maskRef = useRef<HTMLDivElement>(null);

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!enabled) return;

      const step = e.shiftKey ? 10 : 2; // Larger steps with shift

      switch (e.key) {
        case 'ArrowUp':
        case 'k':
          e.preventDefault();
          setPosition((prev) => Math.max(0, prev - step));
          break;
        case 'ArrowDown':
        case 'j':
          e.preventDefault();
          setPosition((prev) => Math.min(100, prev + step));
          break;
        case 'PageUp':
          e.preventDefault();
          setPosition((prev) => Math.max(0, prev - 20));
          break;
        case 'PageDown':
          e.preventDefault();
          setPosition((prev) => Math.min(100, prev + 20));
          break;
        case 'Home':
          e.preventDefault();
          setPosition(10);
          break;
        case 'End':
          e.preventDefault();
          setPosition(90);
          break;
        case '+':
        case '=':
          e.preventDefault();
          setWindowHeight((prev) => Math.min(200, prev + 10));
          break;
        case '-':
        case '_':
          e.preventDefault();
          setWindowHeight((prev) => Math.max(40, prev - 10));
          break;
        case 'Escape':
          e.preventDefault();
          onClose?.();
          break;
      }
    },
    [enabled, onClose]
  );

  // Mouse/touch drag handling
  const handleMouseMove = useCallback(
    (e: MouseEvent | TouchEvent) => {
      if (!isDragging) return;

      const clientY = 'touches' in e ? e.touches[0]!.clientY : e.clientY;
      const percentage = (clientY / window.innerHeight) * 100;
      setPosition(Math.max(5, Math.min(95, percentage)));
    },
    [isDragging]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Scroll wheel to move mask
  const handleWheel = useCallback(
    (e: WheelEvent) => {
      if (!enabled) return;
      // Only handle if mask is focused or user is hovering over mask controls
      if (
        document.activeElement === maskRef.current ||
        maskRef.current?.contains(document.activeElement)
      ) {
        e.preventDefault();
        const step = e.deltaY > 0 ? 3 : -3;
        setPosition((prev) => Math.max(5, Math.min(95, prev + step)));
      }
    },
    [enabled]
  );

  useEffect(() => {
    if (!enabled) return;

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    window.addEventListener('touchmove', handleMouseMove);
    window.addEventListener('touchend', handleMouseUp);
    window.addEventListener('wheel', handleWheel, { passive: false });

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('touchmove', handleMouseMove);
      window.removeEventListener('touchend', handleMouseUp);
      window.removeEventListener('wheel', handleWheel);
    };
  }, [enabled, handleKeyDown, handleMouseMove, handleMouseUp, handleWheel]);

  if (!enabled) return null;

  const topMaskHeight = `calc(${position}% - ${windowHeight / 2}px)`;
  const bottomMaskTop = `calc(${position}% + ${windowHeight / 2}px)`;

  return (
    <div
      ref={maskRef}
      className="reading-mask-container"
      role="application"
      aria-label={t('aria.accessibility.readingMaskUseArrowKeys')}
      tabIndex={0}
    >
      {/* Top mask */}
      <div
        className="fixed inset-x-0 top-0 pointer-events-none z-[9997]"
        style={{
          height: topMaskHeight,
          background: `rgba(0, 0, 0, ${maskOpacity})`,
        }}
        aria-hidden="true"
      />

      {/* Bottom mask */}
      <div
        className="fixed inset-x-0 bottom-0 pointer-events-none z-[9997]"
        style={{
          top: bottomMaskTop,
          background: `rgba(0, 0, 0, ${maskOpacity})`,
        }}
        aria-hidden="true"
      />

      {/* Reading window border/indicator */}
      <div
        className="fixed left-0 right-0 pointer-events-none z-[9998] border-y-2 border-status-warning-400/50"
        style={{
          top: `calc(${position}% - ${windowHeight / 2}px)`,
          height: windowHeight,
        }}
        aria-hidden="true"
      />

      {/* Control panel */}
      <div
        className="fixed right-4 z-[9999] flex flex-col items-center gap-1 bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg p-2"
        style={{ top: `calc(${position}% - 60px)` }}
      >
        {/* Move up button */}
        <button
          onClick={() => setPosition((prev) => Math.max(5, prev - 5))}
          className="p-1.5 hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-700 rounded transition-colors"
          aria-label={t('aria.accessibility.moveReadingWindowUp')}
        >
          <ChevronUp className="w-4 h-4" aria-hidden="true" />
        </button>

        {/* Drag handle */}
        <button
          onMouseDown={() => setIsDragging(true)}
          onTouchStart={() => setIsDragging(true)}
          className="p-1.5 hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-700 rounded cursor-move transition-colors"
          aria-label={t('aria.accessibility.dragToMoveReadingWindow')}
        >
          <Move className="w-4 h-4" aria-hidden="true" />
        </button>

        {/* Move down button */}
        <button
          onClick={() => setPosition((prev) => Math.min(95, prev + 5))}
          className="p-1.5 hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-700 rounded transition-colors"
          aria-label={t('aria.accessibility.moveReadingWindowDown')}
        >
          <ChevronDown className="w-4 h-4" aria-hidden="true" />
        </button>

        {/* Close button */}
        <button
          onClick={onClose}
          className="p-1.5 hover:bg-status-danger-100 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/30 text-status-danger-600 dark:text-status-danger-400 rounded transition-colors mt-1"
          aria-label={t('aria.accessibility.closeReadingMask')}
        >
          <X className="w-4 h-4" aria-hidden="true" />
        </button>
      </div>

      {/* Keyboard hints */}
      <div
        className="fixed bottom-4 left-1/2 -translate-x-1/2 z-[9999] bg-black/80 text-white text-xs px-3 py-2 rounded-full"
        aria-hidden="true"
      >
        <kbd className="px-1 bg-lsc-white dark:bg-earth-800/20 rounded">↑↓</kbd> Move{' '}
        <kbd className="px-1 bg-lsc-white dark:bg-earth-800/20 rounded">+/-</kbd> Resize{' '}
        <kbd className="px-1 bg-lsc-white dark:bg-earth-800/20 rounded">Esc</kbd> Close
      </div>
    </div>
  );
}

export default ReadingMask;
