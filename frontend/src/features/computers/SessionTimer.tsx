/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/** React component for displaying session timer with warnings. */

import { useEffect, useState } from "react";
import { Clock, AlertTriangle, Zap } from "lucide-react";
import { t } from "@/i18n";

const WARNING_THRESHOLD_MS = 5 * 60 * 1000;

export interface SessionTimerSession {
  session_start_time: string;
  session_end_time: string;
}

interface SessionTimerProps {
  session: SessionTimerSession;
  onExtensionRequest?: () => void;
  onLogoff?: () => void;
}

export function SessionTimer({
  session,
  onExtensionRequest,
  onLogoff,
}: SessionTimerProps) {
  const [timeRemaining, setTimeRemaining] = useState<number>(0);
  const [isWarning, setIsWarning] = useState(false);
  const [isExpired, setIsExpired] = useState(false);

  useEffect(() => {
    const updateTimer = () => {
      const now = new Date().getTime();
      const endTime = new Date(session.session_end_time).getTime();
      const remaining = Math.max(0, endTime - now);

      setTimeRemaining(remaining);
      setIsWarning(remaining > 0 && remaining < WARNING_THRESHOLD_MS);
      setIsExpired(remaining === 0);
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);

    return () => clearInterval(interval);
  }, [session.session_end_time]);

  const formatTime = (ms: number): string => {
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, "0")}`;
  };

  const getProgressPercentage = (): number => {
    const totalTime = new Date(session.session_end_time).getTime() -
      new Date(session.session_start_time).getTime();
    if (!totalTime || totalTime <= 0) return 0;
    const elapsed = totalTime - timeRemaining;
    return (elapsed / totalTime) * 100;
  };

  const bgColor = isExpired
    ? "bg-status-danger-50 dark:bg-status-danger-900/20"
    : isWarning
      ? "bg-status-warning-50 dark:bg-status-warning-900/20"
      : "bg-earth-50 dark:bg-earth-800/20";
  const borderColor = isExpired
    ? "border-status-danger-200 dark:border-status-danger-800"
    : isWarning
      ? "border-status-warning-200 dark:border-status-warning-800"
      : "border-lsc-border dark:border-earth-700";
  const textColor = isExpired
    ? "text-status-danger-700 dark:text-status-danger-300"
    : isWarning
      ? "text-status-warning-700 dark:text-status-warning-300"
      : "text-lsc-rose dark:text-lsc-rose-light";

  return (
    <div className={`${bgColor} border ${borderColor} rounded-lg p-6`}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <Clock aria-hidden="true" className={`w-5 h-5 ${textColor}`} />
        <h3 className={`font-semibold ${textColor}`}>{t("computers.timer.sessionTime")}</h3>
      </div>

      {/* Warning Message */}
      {isWarning && !isExpired && (
        <div role="alert" className="flex items-center gap-2 mb-3 p-3 bg-status-warning-100 dark:bg-status-warning-900/30 rounded border border-status-warning-300 dark:border-status-warning-700">
          <AlertTriangle aria-hidden="true" className="w-4 h-4 text-status-warning-700 dark:text-status-warning-300" />
          <span className="text-sm text-status-warning-700 dark:text-status-warning-300">
            {t("computers.timer.minutesRemaining", { minutes: Math.ceil(timeRemaining / 60000) })}
          </span>
        </div>
      )}

      {isExpired && (
        <div role="alert" className="flex items-center gap-2 mb-3 p-3 bg-status-danger-100 dark:bg-status-danger-900/30 rounded border border-status-danger-300 dark:border-status-danger-700">
          <AlertTriangle aria-hidden="true" className="w-4 h-4 text-status-danger-700 dark:text-status-danger-300" />
          <span className="text-sm text-status-danger-700 dark:text-status-danger-300">
            {t("computers.timer.expired")}
          </span>
        </div>
      )}

      {/* Time Display */}
      <div className="text-center mb-4">
        <div className={`text-4xl font-mono font-bold ${textColor}`}>
          {formatTime(timeRemaining)}
        </div>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t("computers.timer.timeRemaining")}</p>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-earth-200 dark:bg-earth-600 rounded-full h-2 mb-4 overflow-hidden">
        <div
          className={`h-full ${isExpired ? "bg-status-danger-500" : isWarning ? "bg-status-warning-500" : "bg-earth-500"} rounded-full transition-all`}
          style={{ width: `${Math.min(100, getProgressPercentage())}%` }}
        />
      </div>

      {/* Session Details */}
      <div className="grid grid-cols-2 gap-2 text-sm mb-4">
        <div>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t("computers.timer.started")}</p>
          <p className="text-lsc-dark dark:text-lsc-cream">
            {new Date(session.session_start_time).toLocaleTimeString()}
          </p>
        </div>
        <div>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t("computers.timer.ends")}</p>
          <p className="text-lsc-dark dark:text-lsc-cream">
            {new Date(session.session_end_time).toLocaleTimeString()}
          </p>
        </div>
      </div>

      {/* Action Buttons */}
      {!isExpired && (
        <div className="flex gap-2">
          {onExtensionRequest && (
            <button
              onClick={onExtensionRequest}
              className="flex-1 flex items-center justify-center gap-2 bg-status-success-600 hover:bg-status-success-700 text-white font-medium py-2 rounded-lg transition-colors"
            >
              <Zap aria-hidden="true" className="w-4 h-4" />
              {t("computers.timer.extendSession")}
            </button>
          )}
          {onLogoff && (
            <button
              onClick={onLogoff}
              className="flex-1 bg-earth-600 hover:bg-earth-700 text-white font-medium py-2 rounded-lg transition-colors"
            >
              {t("computers.timer.logOff")}
            </button>
          )}
        </div>
      )}

      {isExpired && onLogoff && (
        <button
          onClick={onLogoff}
          className="w-full bg-status-danger-600 hover:bg-status-danger-700 text-white font-medium py-2 rounded-lg transition-colors"
        >
          {t("computers.timer.logOffNow")}
        </button>
      )}
    </div>
  );
}
