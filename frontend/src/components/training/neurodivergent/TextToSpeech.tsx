/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Text-to-Speech Component
 * Reads lesson content aloud for accessibility
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import toast from 'react-hot-toast';
import { Volume2, VolumeX, Play, Pause, RotateCcw } from 'lucide-react';
import { useTranslation} from '@/i18n'

interface TextToSpeechProps {
  text: string;
  enabled: boolean;
  onToggle?: (enabled: boolean) => void;
}

export function TextToSpeech({ text, enabled, onToggle }: TextToSpeechProps) {
  const { t } = useTranslation()
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  const stop = useCallback(() => {
    window.speechSynthesis.cancel();
    setIsPlaying(false);
    setIsPaused(false);
    utteranceRef.current = null;
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- cleanup external speech synth on disable
    if (!enabled) stop();
  }, [enabled, stop]);

  const speak = () => {
    if (!('speechSynthesis' in window)) {
      toast.error(t('components.training.textToSpeech.textToSpeechIsNot'));
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.9;
    utterance.pitch = 1;
    utterance.volume = 1;
    utterance.onstart = () => { setIsPlaying(true); setIsPaused(false); };
    utterance.onend = () => { setIsPlaying(false); setIsPaused(false); };
    utterance.onerror = () => { setIsPlaying(false); setIsPaused(false); };
    utteranceRef.current = utterance;
    window.speechSynthesis.speak(utterance);
  };

  const pause = () => {
    if (window.speechSynthesis.speaking && !window.speechSynthesis.paused) {
      window.speechSynthesis.pause();
      setIsPaused(true);
    }
  };

  const resume = () => {
    if (window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
      setIsPaused(false);
    }
  };

  if (!enabled) {
    return (
      <button
        onClick={() => onToggle?.(true)}
        className="flex items-center gap-2 px-3 py-2 text-sm bg-lsc-cream dark:bg-lsc-brown hover:bg-lsc-cream/90 dark:hover:bg-lsc-brown/90 text-lsc-dark dark:text-lsc-cream rounded-xl transition-colors"
        aria-label={t('aria.training.enableTexttospeech')}
      >
        <VolumeX aria-hidden="true" className="w-4 h-4" />
        <span>Enable Read-Aloud</span>
      </button>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={isPlaying ? (isPaused ? resume : pause) : speak}
        className="flex items-center gap-2 px-3 py-2 text-sm bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose transition-colors"
        aria-label={isPlaying ? (isPaused ? 'Resume' : 'Pause') : 'Play'}
      >
        {isPlaying ? (
          isPaused ? (
            <><Play aria-hidden="true" className="w-4 h-4" /><span>Resume</span></>
          ) : (
            <><Pause aria-hidden="true" className="w-4 h-4" /><span>Pause</span></>
          )
        ) : (
          <><Volume2 className="w-4 h-4" /><span>Read Aloud</span></>
        )}
      </button>

      {isPlaying && (
        <button onClick={stop} className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream rounded-xl transition-colors" aria-label={t('aria.training.stop')}>
          <RotateCcw aria-hidden="true" className="w-4 h-4" />
        </button>
      )}

      <button
        onClick={() => { stop(); onToggle?.(false); }}
        className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream rounded-xl transition-colors"
        aria-label={t('aria.training.disableTexttospeech')}
      >
        <VolumeX aria-hidden="true" className="w-4 h-4" />
      </button>
    </div>
  );
}
