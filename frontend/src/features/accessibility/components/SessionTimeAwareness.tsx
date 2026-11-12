/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Session Time Awareness Component
 *
 * Tracks session duration and provides gentle reminders for breaks.
 * Helps users with ADHD manage hyperfocus and promotes healthy screen habits.
 * Implements break reminders without creating anxiety or pressure.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useUnifiedAccessibility } from '../hooks/useUnifiedAccessibility';
import { Clock, Coffee, X, Pause, Play } from 'lucide-react';
import { t } from '@/i18n'
import FocusTrap from 'focus-trap-react'

interface SessionTimeAwarenessProps {
  /** Override break reminder setting */
  enabled?: boolean;
  /** Custom break interval in minutes (overrides settings) */
  breakIntervalMinutes?: number;
  /** Callback when user takes a break */
  onBreakStarted?: () => void;
  /** Callback when user returns from break */
  onBreakEnded?: () => void;
}

interface SessionState {
  startTime: number;
  totalActiveTime: number;
  isOnBreak: boolean;
  breakStartTime: number | null;
  lastBreakTime: number;
  remindersDismissed: number;
}

const GENTLE_MESSAGES = [
  "You've been focused for a while. Maybe stretch a bit?",
  "Great progress! Your eyes might appreciate a short rest.",
  "Time for a micro-break? Even 30 seconds helps.",
  "You're doing well! Consider looking away from the screen briefly.",
  "A quick break can help you stay sharp.",
  "Remember to blink and relax your shoulders.",
  "You've earned a moment to breathe deeply.",
];

const BREAK_ACTIVITIES = [
  "Look at something 20 feet away for 20 seconds",
  "Stand up and stretch your arms",
  "Take 5 deep breaths",
  "Roll your shoulders back",
  "Close your eyes for a moment",
  "Get a glass of water",
  "Walk to a window and look outside",
];

export function SessionTimeAwareness({
  enabled: enabledProp,
  breakIntervalMinutes: intervalProp,
  onBreakStarted,
  onBreakEnded,
}: SessionTimeAwarenessProps) {
  const { settings } = useUnifiedAccessibility();
  const remindersEnabled = enabledProp ?? settings.breakReminders;
  const showTimer = settings.showSessionTime;
  const visible = remindersEnabled || showTimer;
  const breakInterval = (intervalProp ?? settings.breakIntervalMinutes ?? 25) * 60 * 1000;

  const [session, setSession] = useState<SessionState>(() => {
    const t = Date.now()
    return {
      startTime: t,
      totalActiveTime: 0,
      isOnBreak: false,
      breakStartTime: null,
      lastBreakTime: t,
      remindersDismissed: 0,
    }
  });

  const [showReminder, setShowReminder] = useState(false);
  const [currentMessage, setCurrentMessage] = useState('');
  const [suggestedActivity, setSuggestedActivity] = useState('');
  const [showSessionInfo, setShowSessionInfo] = useState(false);
  const [now, setNow] = useState(() => Date.now());

  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const activeTimeRef = useRef<NodeJS.Timeout | null>(null);

  // Format time display
  const formatTime = useCallback((ms: number): string => {
    const minutes = Math.floor(ms / 60000);
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;

    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
  }, []);

  // Get random message and activity
  const getRandomContent = useCallback(() => {
    const messageIndex = Math.floor(Math.random() * GENTLE_MESSAGES.length);
    const activityIndex = Math.floor(Math.random() * BREAK_ACTIVITIES.length);
    setCurrentMessage(GENTLE_MESSAGES[messageIndex] ?? '');
    setSuggestedActivity(BREAK_ACTIVITIES[activityIndex] ?? '');
  }, []);

  // Check if break reminder should show
  const checkBreakTime = useCallback(() => {
    if (!remindersEnabled || session.isOnBreak) return;

    const timeSinceLastBreak = Date.now() - session.lastBreakTime;
    if (timeSinceLastBreak >= breakInterval) {
      getRandomContent();
      setShowReminder(true);
    }
  }, [remindersEnabled, session.isOnBreak, session.lastBreakTime, breakInterval, getRandomContent]);

  // Track active time
  useEffect(() => {
    if (!visible || session.isOnBreak) return;

    activeTimeRef.current = setInterval(() => {
      setNow(Date.now());
      setSession((prev) => ({
        ...prev,
        totalActiveTime: prev.totalActiveTime + 1000,
      }));
    }, 1000);

    return () => {
      if (activeTimeRef.current) {
        clearInterval(activeTimeRef.current);
      }
    };
  }, [visible, session.isOnBreak]);

  // Set up break check interval
  useEffect(() => {
    if (!remindersEnabled) return;

    // Check every minute
    timerRef.current = setInterval(checkBreakTime, 60000);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial break time check on mount
    checkBreakTime();

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [remindersEnabled, checkBreakTime]);

  // Handle starting a break
  const startBreak = useCallback(() => {
    setSession((prev) => ({
      ...prev,
      isOnBreak: true,
      breakStartTime: Date.now(),
    }));
    setShowReminder(false);
    onBreakStarted?.();
  }, [onBreakStarted]);

  // Handle ending a break
  const endBreak = useCallback(() => {
    setSession((prev) => ({
      ...prev,
      isOnBreak: false,
      breakStartTime: null,
      lastBreakTime: Date.now(),
      remindersDismissed: 0,
    }));
    onBreakEnded?.();
  }, [onBreakEnded]);

  // Dismiss reminder (snooze)
  const dismissReminder = useCallback(() => {
    setShowReminder(false);
    setSession((prev) => ({
      ...prev,
      remindersDismissed: prev.remindersDismissed + 1,
      // Add 5 minutes to last break time as a snooze
      lastBreakTime: Date.now(),
    }));
  }, []);

  if (!visible) return null;

  return (
    <>
      {/* Session info toggle button */}
      <button
        onClick={() => setShowSessionInfo(!showSessionInfo)}
        className="fixed bottom-4 left-4 z-[9990] p-2 bg-lsc-white dark:bg-earth-800 rounded-full shadow-lg hover:shadow-lg transition-shadow focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
        aria-label={`Session time: ${formatTime(session.totalActiveTime)}. Click for details.`}
        aria-expanded={showSessionInfo}
      >
        <Clock
          className={`w-5 h-5 ${session.isOnBreak ? 'text-status-success-500' : 'text-status-warning-500'}`}
          aria-hidden="true"
        />
      </button>

      {/* Session info panel */}
      {showSessionInfo && (
        <div
          className="fixed bottom-16 left-4 z-[9990] bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg p-4 w-64"
          role="status"
          aria-live="polite"
        >
          <div className="flex justify-between items-start mb-3">
            <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">Session Info</h3>
            <button
              onClick={() => setShowSessionInfo(false)}
              className="text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-300"
              aria-label={t('aria.accessibility.closeSessionInfo')}
            >
              <X className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>

          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Active time:</span>
              <span className="font-medium">{formatTime(session.totalActiveTime)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Since last break:</span>
              <span className="font-medium">
                {formatTime(now - session.lastBreakTime)}
              </span>
            </div>
            {remindersEnabled && (
              <div className="flex justify-between">
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Break interval:</span>
                <span className="font-medium">{breakInterval / 60000}m</span>
              </div>
            )}
          </div>

          {!session.isOnBreak ? (
            <button
              onClick={startBreak}
              className="mt-3 w-full flex items-center justify-center gap-2 px-3 py-2 bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 rounded-lg hover:bg-status-success-200 dark:hover:bg-status-success-900/50 transition-colors"
            >
              <Pause className="w-4 h-4" aria-hidden="true" />
              Take a break now
            </button>
          ) : (
            <button
              onClick={endBreak}
              className="mt-3 w-full flex items-center justify-center gap-2 px-3 py-2 bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300 rounded-lg hover:bg-status-warning-200 dark:hover:bg-status-warning-900/50 transition-colors"
            >
              <Play className="w-4 h-4" aria-hidden="true" />
              Resume session
            </button>
          )}
        </div>
      )}

      {/* Break reminder notification */}
      {showReminder && !session.isOnBreak && (
        <div
          className="session-time-warning"
          role="alertdialog"
          aria-labelledby="break-reminder-title"
          aria-describedby="break-reminder-desc"
        >
          <Coffee className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
          <div className="flex-1">
            <p id="break-reminder-title" className="font-medium">
              {currentMessage}
            </p>
            <p id="break-reminder-desc" className="text-xs opacity-80 mt-0.5">
              Try: {suggestedActivity}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={startBreak}
              className="px-3 py-1 bg-status-success-600 text-white rounded-full text-sm hover:bg-status-success-700 transition-colors"
            >
              Break
            </button>
            <button
              onClick={dismissReminder}
              className="px-3 py-1 bg-lsc-white dark:bg-earth-800/20 rounded-full text-sm hover:bg-lsc-white/30 transition-colors"
              aria-label={t('aria.accessibility.remindMeLater')}
            >
              Later
            </button>
          </div>
        </div>
      )}

      {/* Break mode overlay */}
      {session.isOnBreak && (
        <FocusTrap active={true} focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: true, fallbackFocus: () => document.body }}>
        <div
          className="fixed inset-0 z-[9995] bg-gradient-to-b from-green-50 to-green-100 dark:from-green-900/30 dark:to-green-950/50 flex items-center justify-center"
          role="dialog"
          aria-label={t('aria.accessibility.breakTime')}
        >
          <div className="text-center max-w-md p-8">
            <div className="w-20 h-20 mx-auto mb-6 bg-status-success-100 dark:bg-status-success-900/50 rounded-full flex items-center justify-center">
              <Coffee className="w-10 h-10 text-status-success-600 dark:text-status-success-400" aria-hidden="true" />
            </div>
            <h2 className="font-serif text-2xl font-semibold text-status-success-800 dark:text-status-success-200 mb-2">
              Enjoying your break
            </h2>
            <p className="text-status-success-600 dark:text-status-success-400 mb-2">{suggestedActivity}</p>
            <p className="text-sm text-status-success-500 dark:text-status-success-500 mb-6">
              Break started {formatTime(now - (session.breakStartTime || now))} ago
            </p>
            <button
              onClick={endBreak}
              className="px-6 py-3 bg-status-success-600 text-white rounded-full text-lg font-medium hover:bg-status-success-700 transition-colors shadow-lg"
            >
              Ready to continue
            </button>
          </div>
        </div>
        </FocusTrap>
      )}
    </>
  );
}

export default SessionTimeAwareness;
