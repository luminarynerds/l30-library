/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
/**
 * Voice Control Hook
 *
 * Provides voice-based navigation and control for the application.
 * Uses the Web Speech API for speech recognition.
 * Helpful for users with motor impairments or those who prefer hands-free interaction.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useTranslation } from '../../../i18n/I18nContext';

// Type definitions for Web Speech API
interface SpeechRecognitionEvent extends Event {
  readonly resultIndex: number;
  readonly results: SpeechRecognitionResultList;
}

interface SpeechRecognitionErrorEvent extends Event {
  readonly error: string;
  readonly message: string;
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;

  onstart: ((this: SpeechRecognition, ev: Event) => void) | null;
  onend: ((this: SpeechRecognition, ev: Event) => void) | null;
  onerror: ((this: SpeechRecognition, ev: SpeechRecognitionErrorEvent) => void) | null;
  onresult: ((this: SpeechRecognition, ev: SpeechRecognitionEvent) => void) | null;

  start(): void;
  stop(): void;
  abort(): void;
}

interface VoiceCommand {
  /** Command phrases that trigger this action (lowercase) */
  phrases: string[];
  /** Action to execute when command is recognized */
  action: () => void;
  /** Description for help menu */
  description: string;
  /** Category for grouping in help */
  category: 'navigation' | 'actions' | 'accessibility' | 'custom';
}

interface UseVoiceControlOptions {
  /** Enable voice control */
  enabled?: boolean;
  /** Language for speech recognition */
  language?: string;
  /** Continuous listening mode */
  continuous?: boolean;
  /** Custom commands to add */
  customCommands?: VoiceCommand[];
  /** Callback when a command is recognized */
  onCommand?: (command: string) => void;
  /** Callback when speech recognition errors */
  onError?: (error: Error) => void;
}

interface VoiceControlState {
  isListening: boolean;
  isSupported: boolean;
  lastCommand: string | null;
  error: string | null;
}

// Constructor type for SpeechRecognition
type SpeechRecognitionConstructor = new () => SpeechRecognition;

// Get browser's SpeechRecognition constructor
const getBrowserSpeechRecognition = (): SpeechRecognitionConstructor | null => {
  if (typeof window === 'undefined') return null;

  const win = window as unknown as Window & {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  };

  return win.SpeechRecognition || win.webkitSpeechRecognition || null;
};

// Check for browser support
const SpeechRecognitionCtor = getBrowserSpeechRecognition();

/**
 * Default navigation commands
 */
const DEFAULT_COMMANDS: VoiceCommand[] = [
  // Navigation
  {
    phrases: ['go home', 'home page', 'go to home'],
    action: () => (window.location.href = '/'),
    description: 'Navigate to home page',
    category: 'navigation',
  },
  {
    phrases: ['go back', 'back', 'previous page'],
    action: () => window.history.back(),
    description: 'Go to previous page',
    category: 'navigation',
  },
  {
    phrases: ['go forward', 'forward', 'next page'],
    action: () => window.history.forward(),
    description: 'Go to next page',
    category: 'navigation',
  },
  {
    phrases: ['scroll down', 'page down', 'down'],
    action: () => window.scrollBy({ top: 300, behavior: 'smooth' }),
    description: 'Scroll down',
    category: 'navigation',
  },
  {
    phrases: ['scroll up', 'page up', 'up'],
    action: () => window.scrollBy({ top: -300, behavior: 'smooth' }),
    description: 'Scroll up',
    category: 'navigation',
  },
  {
    phrases: ['scroll to top', 'top of page', 'go to top'],
    action: () => window.scrollTo({ top: 0, behavior: 'smooth' }),
    description: 'Scroll to top of page',
    category: 'navigation',
  },
  {
    phrases: ['scroll to bottom', 'bottom of page', 'go to bottom'],
    action: () => window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }),
    description: 'Scroll to bottom of page',
    category: 'navigation',
  },

  // Actions
  {
    phrases: ['click', 'select', 'press'],
    action: () => {
      const focused = document.activeElement as HTMLElement;
      if (focused && focused !== document.body) {
        focused.click();
      }
    },
    description: 'Click focused element',
    category: 'actions',
  },
  {
    phrases: ['next', 'next element', 'tab'],
    action: () => {
      const focusables = document.querySelectorAll<HTMLElement>(
        'a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      const current = document.activeElement;
      const currentIndex = Array.from(focusables).indexOf(current as HTMLElement);
      const next = focusables[currentIndex + 1] || focusables[0];
      next?.focus();
    },
    description: 'Focus next element',
    category: 'actions',
  },
  {
    phrases: ['previous', 'previous element', 'shift tab'],
    action: () => {
      const focusables = document.querySelectorAll<HTMLElement>(
        'a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      const current = document.activeElement;
      const currentIndex = Array.from(focusables).indexOf(current as HTMLElement);
      const prev = focusables[currentIndex - 1] || focusables[focusables.length - 1];
      prev?.focus();
    },
    description: 'Focus previous element',
    category: 'actions',
  },
  {
    phrases: ['search', 'find', 'search for'],
    action: () => {
      const searchInput = document.querySelector<HTMLInputElement>(
        'input[type="search"], input[name="search"], input[placeholder*="search" i], #search'
      );
      searchInput?.focus();
    },
    description: 'Focus search input',
    category: 'actions',
  },
  {
    phrases: ['close', 'close modal', 'close dialog', 'dismiss'],
    action: () => {
      const closeButton = document.querySelector<HTMLButtonElement>(
        '[aria-label*="close" i], [aria-label*="dismiss" i], .modal button.close, dialog button[aria-label]'
      );
      closeButton?.click();
    },
    description: 'Close modal or dialog',
    category: 'actions',
  },

  // Accessibility
  {
    phrases: ['read page', 'read content', 'read aloud'],
    action: () => {
      const main = document.querySelector('main') || document.body;
      const text = main.textContent || '';
      const utterance = new SpeechSynthesisUtterance(text.slice(0, 5000)); // Limit length
      speechSynthesis.speak(utterance);
    },
    description: 'Read page content aloud',
    category: 'accessibility',
  },
  {
    phrases: ['stop reading', 'stop', 'quiet', 'silence'],
    action: () => speechSynthesis.cancel(),
    description: 'Stop text-to-speech',
    category: 'accessibility',
  },
  {
    phrases: ['increase font', 'bigger text', 'larger text'],
    action: () => {
      document.documentElement.style.fontSize =
        parseFloat(getComputedStyle(document.documentElement).fontSize) * 1.1 + 'px';
    },
    description: 'Increase font size',
    category: 'accessibility',
  },
  {
    phrases: ['decrease font', 'smaller text'],
    action: () => {
      document.documentElement.style.fontSize =
        parseFloat(getComputedStyle(document.documentElement).fontSize) * 0.9 + 'px';
    },
    description: 'Decrease font size',
    category: 'accessibility',
  },
  {
    phrases: ['reset font', 'normal text size'],
    action: () => {
      document.documentElement.style.fontSize = '';
    },
    description: 'Reset font size',
    category: 'accessibility',
  },
];

export function useVoiceControl(options: UseVoiceControlOptions = {}) {
  const { language: uiLanguage } = useTranslation();
  const {
    enabled = false,
    language = uiLanguage || 'en-US',
    continuous = true,
    customCommands = [],
    onCommand,
    onError,
  } = options;

  const [state, setState] = useState<VoiceControlState>({
    isListening: false,
    isSupported: !!SpeechRecognitionCtor,
    lastCommand: null,
    error: null,
  });

  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const commandsRef = useRef<VoiceCommand[]>([...DEFAULT_COMMANDS, ...customCommands]);

  // Update commands when custom commands change
  useEffect(() => {
    commandsRef.current = [...DEFAULT_COMMANDS, ...customCommands];
  }, [customCommands]);

  /**
   * Process recognized speech and execute matching command
   */
  const processCommand = useCallback(
    (transcript: string) => {
      const normalizedTranscript = transcript.toLowerCase().trim();
      setState((prev) => ({ ...prev, lastCommand: normalizedTranscript }));

      // Find matching command
      for (const command of commandsRef.current) {
        const match = command.phrases.some(
          (phrase) =>
            normalizedTranscript.includes(phrase) ||
            phrase.includes(normalizedTranscript)
        );

        if (match) {
          try {
            command.action();
            onCommand?.(normalizedTranscript);

            // Provide audio feedback
            const utterance = new SpeechSynthesisUtterance('Done');
            utterance.volume = 0.3;
            utterance.rate = 1.5;
            speechSynthesis.speak(utterance);

            return true;
          } catch (_err) {
            Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)));
          }
        }
      }

      return false;
    },
    [onCommand]
  );

  /**
   * Start listening for voice commands
   */
  const startListening = useCallback(() => {
    if (!SpeechRecognitionCtor || !enabled) return;

    try {
      const recognition = new SpeechRecognitionCtor();
      recognition.continuous = continuous;
      recognition.interimResults = false;
      recognition.lang = language;

      recognition.onstart = () => {
        setState((prev) => ({ ...prev, isListening: true, error: null }));
      };

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        const last = event.results.length - 1;
        const result = event.results[last];
        if (result && result[0]) {
          const transcript = result[0].transcript;
          processCommand(transcript);
        }
      };

      recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        const error = new Error(`Speech recognition error: ${event.error}`);
        setState((prev) => ({ ...prev, error: event.error }));
        onError?.(error);

        // Permission denied or not allowed — stop permanently so onend doesn't restart
        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          recognitionRef.current = null;
          setState((prev) => ({ ...prev, isListening: false, isSupported: false }));
          return;
        }

        // Restart on recoverable errors
        if (event.error === 'no-speech' || event.error === 'aborted') {
          setTimeout(() => {
            if (enabled && recognitionRef.current) {
              try {
                recognitionRef.current.start();
              } catch {
                // Already started
              }
            }
          }, 1000);
        }
      };

      recognition.onend = () => {
        setState((prev) => ({ ...prev, isListening: false }));
        // Restart if continuous mode and still enabled
        if (continuous && enabled) {
          setTimeout(() => {
            if (recognitionRef.current) {
              try {
                recognitionRef.current.start();
              } catch {
                // Already started
              }
            }
          }, 100);
        }
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (_err) {
      const error = _err instanceof Error ? _err : new Error('Failed to start speech recognition');
      setState((prev) => ({ ...prev, error: error.message }));
      onError?.(error);
    }
  }, [enabled, continuous, language, processCommand, onError]);

  /**
   * Stop listening for voice commands
   */
  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    setState((prev) => ({ ...prev, isListening: false }));
  }, []);

  /**
   * Toggle listening state
   */
  const toggleListening = useCallback(() => {
    if (state.isListening) {
      stopListening();
    } else {
      startListening();
    }
  }, [state.isListening, startListening, stopListening]);

  /**
   * Add a custom command dynamically
   */
  const addCommand = useCallback((command: VoiceCommand) => {
    commandsRef.current = [...commandsRef.current, command];
  }, []);

  /**
   * Remove a custom command
   */
  const removeCommand = useCallback((phrases: string[]) => {
    commandsRef.current = commandsRef.current.filter(
      (cmd) => !phrases.some((p) => cmd.phrases.includes(p))
    );
  }, []);

  /**
   * Get all available commands (for help display)
   */
  const getCommands = useCallback(() => {
    return commandsRef.current;
  }, []);

  // Stop when disabled; don't auto-start — mic permission requires a user gesture
  useEffect(() => {
    if (!enabled && state.isListening) {
      stopListening();
    }

    return () => {
      stopListening();
    };
  }, [enabled]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    ...state,
    startListening,
    stopListening,
    toggleListening,
    addCommand,
    removeCommand,
    getCommands,
  };
}

export type { VoiceCommand, UseVoiceControlOptions, VoiceControlState };
export default useVoiceControl;
