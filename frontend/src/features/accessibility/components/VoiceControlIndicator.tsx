/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Voice Control Indicator Component
 *
 * Displays the current voice control status and provides
 * controls for managing voice recognition.
 */

import { useState, useEffect } from 'react';
import FocusTrap from 'focus-trap-react';
import { Mic, MicOff, HelpCircle, X } from 'lucide-react';
import { useVoiceControl } from '../hooks/useVoiceControl';
import { useAccessibility } from '../hooks/useAccessibility';
import { t } from '@/i18n'

export function VoiceControlIndicator() {
  const { settings } = useAccessibility();
  const {
    isListening,
    isSupported,
    lastCommand,
    error,
    toggleListening,
    getCommands,
  } = useVoiceControl({
    enabled: settings.voiceControlEnabled,
    language: settings.voiceControlLanguage || undefined,
    continuous: settings.voiceControlContinuous,
  });

  const [showHelp, setShowHelp] = useState(false);

  // Handle Escape key for help modal
  useEffect(() => {
    if (!showHelp) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        setShowHelp(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showHelp]);

  // Lock body scroll when help modal is open
  useEffect(() => {
    if (showHelp) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [showHelp]);

  if (!settings.voiceControlEnabled || !isSupported) {
    return null;
  }

  const commands = getCommands();
  const groupedCommands = commands.reduce(
    (acc, cmd) => {
      if (!acc[cmd.category]) acc[cmd.category] = [];
      acc[cmd.category]!.push(cmd);
      return acc;
    },
    {} as Record<string, typeof commands>
  );

  return (
    <>
      {/* Status indicator */}
      <div
        className="voice-control-active"
        role="status"
        aria-live="polite"
        aria-label={isListening ? 'Voice control listening' : 'Voice control paused'}
      >
        {isListening && <span className="pulse" aria-hidden="true" />}
        <button
          type="button"
          onClick={toggleListening}
          className="flex items-center gap-2 hover:opacity-80 transition-opacity"
          aria-label={isListening ? 'Pause voice control' : 'Resume voice control'}
        >
          {isListening ? (
            <Mic className="w-4 h-4 text-status-success-500" aria-hidden="true" />
          ) : (
            <MicOff className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
          )}
          <span className="text-sm">
            {isListening ? 'Listening...' : 'Click to start'}
          </span>
        </button>

        <button
          onClick={() => setShowHelp(true)}
          className="p-1 hover:bg-lsc-white dark:bg-earth-800/10 rounded transition-colors"
          aria-label={t('aria.accessibility.showVoiceCommandsHelp')}
        >
          <HelpCircle className="w-4 h-4" aria-hidden="true" />
        </button>
      </div>

      {/* Last command feedback */}
      {lastCommand && (
        <div
          className="fixed bottom-16 right-4 z-[9999] bg-status-success-100 dark:bg-status-success-900/50 text-status-success-700 dark:text-status-success-300 text-sm px-3 py-2 rounded-lg shadow-md motion-safe:animate-fade-in"
          role="status"
          aria-live="polite"
        >
          Heard: "{lastCommand}"
        </div>
      )}

      {/* Error display */}
      {error && (
        <div
          className="fixed bottom-16 right-4 z-[9999] bg-status-danger-100 dark:bg-status-danger-900/50 text-status-danger-700 dark:text-status-danger-300 text-sm px-3 py-2 rounded-lg shadow-md"
          role="alert"
        >
          Voice control error: {error}
        </div>
      )}

      {/* Help modal */}
      {showHelp && (
        <FocusTrap active={showHelp} focusTrapOptions={{ escapeDeactivates: true }}>
        {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
        <div
          className="fixed inset-0 z-[10000] bg-black/50 flex items-center justify-center p-4"
          onClick={() => setShowHelp(false)}
          role="dialog"
          aria-labelledby="voice-help-title"
          aria-modal="true"
        >
          {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
          <div
            className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-lg w-full max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-4 border-b border-lsc-border dark:border-earth-700">
              <h2
                id="voice-help-title"
                className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream"
              >
                Voice Commands
              </h2>
              <button
                onClick={() => setShowHelp(false)}
                className="p-2 hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-700 rounded-lg transition-colors"
                aria-label={t('aria.accessibility.closeHelp')}
              >
                <X className="w-5 h-5" aria-hidden="true" />
              </button>
            </div>

            <div className="p-4 overflow-y-auto max-h-[60vh]">
              {Object.entries(groupedCommands).map(([category, cmds]) => (
                <div key={category} className="mb-6 last:mb-0">
                  <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider mb-2">
                    {category}
                  </h3>
                  <ul className="space-y-2">
                    {cmds.map((cmd, index) => (
                      <li
                        key={index}
                        className="flex items-start gap-3 text-sm"
                      >
                        <span className="flex-shrink-0 px-2 py-1 bg-earth-100 dark:bg-earth-700 rounded text-lsc-dark/70 dark:text-lsc-cream/70 font-mono text-xs">
                          "{cmd.phrases[0]}"
                        </span>
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                          {cmd.description}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>

            <div className="p-4 bg-earth-50 dark:bg-earth-900 border-t border-lsc-border dark:border-earth-700">
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 text-center">
                Tip: Speak clearly and wait for the "Listening..." indicator
              </p>
            </div>
          </div>
        </div>
        </FocusTrap>
      )}
    </>
  );
}

export default VoiceControlIndicator;
