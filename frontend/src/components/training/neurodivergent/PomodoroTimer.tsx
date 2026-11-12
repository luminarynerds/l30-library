/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Pomodoro Timer Component
 * Helps with focus and attention management
 */
import { useState, useEffect, useRef } from 'react';
import { Timer, Play, Pause, RotateCcw, Coffee } from 'lucide-react';
import { t } from '@/i18n'

interface PomodoroTimerProps {
  enabled: boolean;
  workMinutes?: number;
  breakMinutes?: number;
  onComplete?: () => void;
}

export function PomodoroTimer({
  enabled,
  workMinutes = 25,
  breakMinutes = 5,
  onComplete,
}: PomodoroTimerProps) {
  const [isRunning, setIsRunning] = useState(false);
  const [isBreak, setIsBreak] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(workMinutes * 60);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (isRunning && secondsLeft > 0) {
      intervalRef.current = setInterval(() => {
        setSecondsLeft((prev) => {
          if (prev <= 1) {
            setIsRunning(false);
            if (!isBreak) {
              setIsBreak(true);
              return breakMinutes * 60;
            } else {
              setIsBreak(false);
              onComplete?.();
              return workMinutes * 60;
            }
          }
          return prev - 1;
        });
      }, 1000);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [isRunning, secondsLeft, isBreak, workMinutes, breakMinutes, onComplete]);

  const formatTime = (totalSeconds: number) => {
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  };

  const reset = () => {
    setIsRunning(false);
    setIsBreak(false);
    setSecondsLeft(workMinutes * 60);
    if (intervalRef.current) clearInterval(intervalRef.current);
  };

  if (!enabled) return null;

  const progress = isBreak
    ? ((breakMinutes * 60 - secondsLeft) / (breakMinutes * 60)) * 100
    : ((workMinutes * 60 - secondsLeft) / (workMinutes * 60)) * 100;

  return (
    <div className="fixed bottom-20 sm:bottom-4 left-2 sm:left-4 z-40 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl shadow-lg p-4 min-w-[200px]">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {isBreak ? (
            <Coffee aria-hidden="true" className="w-4 h-4 text-lsc-rose" />
          ) : (
            <Timer aria-hidden="true" className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
          )}
          <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
            {isBreak ? 'Break Time' : 'Focus Time'}
          </span>
        </div>
        <button onClick={reset} className="text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream" aria-label={t('aria.training.reset')}>
          <RotateCcw aria-hidden="true" className="w-4 h-4" />
        </button>
      </div>

      <div className="text-center mb-3">
        <div className="text-3xl font-mono font-bold text-lsc-dark dark:text-lsc-cream">
          {formatTime(secondsLeft)}
        </div>
      </div>

      <div className="w-full bg-lsc-cream dark:bg-lsc-brown rounded-full h-2 mb-3">
        <div className={`h-2 rounded-full transition-all duration-1000 ${isBreak ? 'bg-lsc-rose' : 'bg-lsc-rose'}`} style={{ width: `${progress}%` }} />
      </div>

      <button
        onClick={() => setIsRunning(!isRunning)}
        className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose transition-colors"
      >
        {isRunning ? <><Pause aria-hidden="true" className="w-4 h-4" /><span>Pause</span></> : <><Play aria-hidden="true" className="w-4 h-4" /><span>Start</span></>}
      </button>

      {secondsLeft === 0 && !isBreak && (
        <div className="mt-3 p-2 bg-lsc-cream dark:bg-lsc-dark/30 border border-lsc-border dark:border-earth-700 rounded-xl text-lsc-dark dark:text-lsc-rose-light/50 text-sm text-center">
          Time for a break! Great work!
        </div>
      )}
    </div>
  );
}
