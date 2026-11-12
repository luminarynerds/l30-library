/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Focus Mode Component
 * Hides distractions to help neurodivergent learners focus
 * Includes reading ruler and auto-scroll features
 */
import { useEffect, useState, useRef, useCallback } from 'react';
import { Focus as FocusIcon, X, Minus, Play, Pause, ChevronUp, ChevronDown } from 'lucide-react';
import { useTranslation} from '@/i18n'
import { useAccessibility } from '@/features/accessibility/hooks/useAccessibility'

interface FocusModeProps {
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
  children: React.ReactNode;
}

interface ReadingRulerProps {
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
}

function ReadingRuler({ enabled, onToggle }: ReadingRulerProps) {
  const [position, setPosition] = useState(200);
  const [rulerHeight, setRulerHeight] = useState(80);

  useEffect(() => {
    if (!enabled) return;

    const handleMouseMove = (e: MouseEvent) => {
      setPosition(e.clientY);
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowUp') {
        setPosition(prev => Math.max(0, prev - 20));
      } else if (e.key === 'ArrowDown') {
        setPosition(prev => Math.min(window.innerHeight, prev + 20));
      } else if (e.key === '[') {
        setRulerHeight(prev => Math.max(40, prev - 10));
      } else if (e.key === ']') {
        setRulerHeight(prev => Math.min(200, prev + 10));
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [enabled]);

  if (!enabled) return null;

  return (
    <>
      {/* Top overlay */}
      <div
        className="fixed inset-x-0 top-0 bg-black/60 pointer-events-none transition-all z-[9998]"
        style={{ height: position - rulerHeight / 2 }}
      />
      {/* Reading window */}
      <div
        className="fixed inset-x-0 pointer-events-none transition-all z-[9998] border-y-2 border-lsc-rose/50"
        style={{ top: position - rulerHeight / 2, height: rulerHeight }}
      />
      {/* Bottom overlay */}
      <div
        className="fixed inset-x-0 bottom-0 bg-black/60 pointer-events-none transition-all z-[9998]"
        style={{ top: position + rulerHeight / 2 }}
      />
      {/* Controls */}
      <div className="fixed top-4 left-4 z-[10001] flex flex-col gap-2 bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg p-2">
        <button
          onClick={() => onToggle(false)}
          className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose rounded"
          title="Disable reading ruler"
        >
          <Minus className="w-4 h-4" />
        </button>
        <button
          onClick={() => setRulerHeight(prev => Math.min(200, prev + 10))}
          className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose rounded"
          title="Increase reading window (])"
        >
          <ChevronUp className="w-4 h-4" />
        </button>
        <button
          onClick={() => setRulerHeight(prev => Math.max(40, prev - 10))}
          className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose rounded"
          title="Decrease reading window ([)"
        >
          <ChevronDown className="w-4 h-4" />
        </button>
      </div>
    </>
  );
}

interface AutoScrollProps {
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
  containerRef: React.RefObject<HTMLElement>;
}

function AutoScroll({ enabled, onToggle, containerRef }: AutoScrollProps) {
  const { settings } = useAccessibility()
  const [speed, setSpeed] = useState(30); // pixels per second
  const [isPlaying, setIsPlaying] = useState(false);
  const animationRef = useRef<number>();
  const intervalRef = useRef<ReturnType<typeof setInterval>>();
  const lastTimeRef = useRef<number>();
  const scrollRef = useRef<(timestamp: number) => void>();

  const scroll = useCallback((timestamp: number) => {
    if (!containerRef.current) return;

    if (lastTimeRef.current === undefined) {
      lastTimeRef.current = timestamp;
    }

    const elapsed = timestamp - lastTimeRef.current;
    const scrollAmount = (speed * elapsed) / 1000;

    containerRef.current.scrollTop += scrollAmount;
    lastTimeRef.current = timestamp;

    // Stop if reached bottom
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    if (scrollTop + clientHeight >= scrollHeight) {
      setIsPlaying(false);
      return;
    }

    animationRef.current = requestAnimationFrame((t) => scrollRef.current?.(t));
  }, [speed, containerRef]);

  useEffect(() => { scrollRef.current = scroll; }, [scroll]);

  useEffect(() => {
    if (isPlaying && enabled) {
      if (settings.reduceMotion) {
        // Instant scroll jumps instead of smooth rAF animation
        intervalRef.current = setInterval(() => {
          if (!containerRef.current) return;
          containerRef.current.scrollTop += speed;
          const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
          if (scrollTop + clientHeight >= scrollHeight) {
            setIsPlaying(false);
          }
        }, 1000);
      } else {
        lastTimeRef.current = undefined;
        animationRef.current = requestAnimationFrame(scroll);
      }
    } else {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
      if (intervalRef.current) clearInterval(intervalRef.current);
    }

    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isPlaying, enabled, scroll, settings.reduceMotion, speed, containerRef]);

  if (!enabled) return null;

  return (
    <div className="fixed bottom-4 left-4 z-[10001] flex items-center gap-3 bg-lsc-white dark:bg-earth-800 rounded-full shadow-lg px-4 py-2">
      <button
        onClick={() => setIsPlaying(!isPlaying)}
        className={`p-2 rounded-full ${isPlaying ? 'bg-lsc-rose text-white' : 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream'}`}
        title={isPlaying ? 'Pause auto-scroll' : 'Start auto-scroll'}
      >
        {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
      </button>
      <div className="flex items-center gap-2">
        <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Speed</span>
        <input
          type="range"
          min="10"
          max="100"
          value={speed}
          onChange={e => setSpeed(Number(e.target.value))}
          className="w-20 h-1 bg-lsc-cream dark:bg-lsc-brown rounded-full appearance-none cursor-pointer"
          title={`${speed} px/s`}
        />
      </div>
      <button
        onClick={() => onToggle(false)}
        className="p-1 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose"
        title="Disable auto-scroll"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

export function FocusMode({ enabled, onToggle, children }: FocusModeProps) {
  const { t } = useTranslation();
  const [readingRulerEnabled, setReadingRulerEnabled] = useState(false);
  const [autoScrollEnabled, setAutoScrollEnabled] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (enabled) {
      document.body.classList.add('focus-mode-active');
      const distractions = document.querySelectorAll('.sidebar, nav, header, footer');
      distractions.forEach((el) => {
        (el as HTMLElement).style.display = 'none';
      });
    } else {
      document.body.classList.remove('focus-mode-active');
      const distractions = document.querySelectorAll('.sidebar, nav, header, footer');
      distractions.forEach((el) => {
        (el as HTMLElement).style.display = '';
      });
      // Disable features when focus mode is off
      // eslint-disable-next-line react-hooks/set-state-in-effect -- resets child feature toggles as part of focus-mode disable cleanup; lifting out needs parent key/handler
      setReadingRulerEnabled(false);
      setAutoScrollEnabled(false);
    }

    return () => {
      document.body.classList.remove('focus-mode-active');
    };
  }, [enabled]);

  if (!enabled) {
    return (
      <>
        <button
          onClick={() => onToggle(true)}
          className="fixed bottom-4 right-4 z-50 flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl shadow-lg hover:bg-lsc-rose transition-colors"
          aria-label={t('aria.training.enableFocusMode')}
        >
          <FocusIcon aria-hidden="true" className="w-4 h-4" />
          <span>Focus Mode</span>
        </button>
        {children}
      </>
    );
  }

  return (
    <div className="focus-mode-container">
      <style>{`
        .focus-mode-active {
          overflow: hidden;
        }
        .focus-mode-container {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: var(--focus-bg, var(--focus-bg));
          z-index: 9999;
          overflow-y: auto;
        }
        .dark .focus-mode-container {
          background: var(--focus-bg-dark, var(--focus-bg-dark));
        }
        .focus-mode-container .focus-exit {
          position: fixed;
          top: 1rem;
          right: 1rem;
          z-index: 10000;
        }
        .focus-toolbar {
          position: fixed;
          top: 1rem;
          left: 50%;
          transform: translateX(-50%);
          z-index: 10000;
        }
      `}</style>

      {/* Focus Mode Toolbar */}
      <div className="focus-toolbar flex items-center gap-2 bg-lsc-white dark:bg-earth-800 rounded-full shadow-lg px-4 py-2">
        <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mr-2">Focus Tools:</span>
        <button
          onClick={() => setReadingRulerEnabled(!readingRulerEnabled)}
          className={`px-3 py-1.5 rounded-full text-sm transition-colors ${
            readingRulerEnabled
              ? 'bg-lsc-rose text-white'
              : 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/80 dark:hover:bg-lsc-brown/80'
          }`}
          title={t('components.training.focusMode.readingRulerHelpsYouFocus')}
        >
          Reading Ruler
        </button>
        <button
          onClick={() => setAutoScrollEnabled(!autoScrollEnabled)}
          className={`px-3 py-1.5 rounded-full text-sm transition-colors ${
            autoScrollEnabled
              ? 'bg-lsc-rose text-white'
              : 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/80 dark:hover:bg-lsc-brown/80'
          }`}
          title={t('components.training.focusMode.autoScrollReadsAtYour')}
        >
          Auto-Scroll
        </button>
      </div>

      <button
        onClick={() => onToggle(false)}
        className="focus-exit flex items-center gap-2 px-4 py-2 bg-lsc-cream dark:bg-lsc-brown hover:bg-lsc-border dark:hover:bg-lsc-brown/90 text-lsc-dark dark:text-lsc-cream rounded-xl transition-colors"
        aria-label={t('aria.training.exitFocusMode')}
      >
        <X aria-hidden="true" className="w-4 h-4" />
        <span>Exit Focus</span>
      </button>

      <div ref={containerRef as React.RefObject<HTMLDivElement>} className="max-w-3xl mx-auto p-8 pt-20">
        {children}
      </div>

      {/* Reading Ruler Overlay */}
      <ReadingRuler enabled={readingRulerEnabled} onToggle={setReadingRulerEnabled} />

      {/* Auto-Scroll Controls */}
      <AutoScroll
        enabled={autoScrollEnabled}
        onToggle={setAutoScrollEnabled}
        containerRef={containerRef as React.RefObject<HTMLElement>}
      />
    </div>
  );
}
