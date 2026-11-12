/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Format Picker - Let learners choose how they want to consume content
 * "Pick whatever works for your brain today"
 */
import { Video, Headphones, FileText, Image, MessageSquare, Sparkles } from 'lucide-react';
import clsx from 'clsx';

export type ContentFormat = 'default' | 'video' | 'audio' | 'visual' | 'text_only' | 'summary' | 'interactive';

interface FormatOption {
  type: ContentFormat;
  available: boolean;
}

interface FormatPickerProps {
  formats: FormatOption[];
  activeFormat: ContentFormat;
  onSelect: (format: ContentFormat) => void;
  preferredFormat?: ContentFormat;
  compact?: boolean;
}

const FORMAT_CONFIG: Record<ContentFormat, {
  icon: typeof FileText;
  label: string;
  description: string;
}> = {
  default: {
    icon: FileText,
    label: 'Read',
    description: 'Written guide',
  },
  video: {
    icon: Video,
    label: 'Watch',
    description: 'Video walkthrough',
  },
  audio: {
    icon: Headphones,
    label: 'Listen',
    description: 'Audio version',
  },
  visual: {
    icon: Image,
    label: 'Visual',
    description: 'Slides & diagrams',
  },
  text_only: {
    icon: FileText,
    label: 'Text Only',
    description: 'No images',
  },
  summary: {
    icon: MessageSquare,
    label: 'Quick',
    description: 'Key points only',
  },
  interactive: {
    icon: Sparkles,
    label: 'Try It',
    description: 'Hands-on',
  },
};

export function FormatPicker({ 
  formats, 
  activeFormat, 
  onSelect, 
  preferredFormat,
  compact = false 
}: FormatPickerProps) {
  // Always include default, filter to available
  const availableFormats = [
    { type: 'default' as ContentFormat, available: true },
    ...formats.filter(f => f.type !== 'default'),
  ].filter(f => f.available);

  // Don't show if only one format
  if (availableFormats.length <= 1) return null;

  if (compact) {
    return (
      <div className="flex flex-wrap gap-2">
        {availableFormats.map(({ type }) => {
          const config = FORMAT_CONFIG[type];
          const Icon = config.icon;
          const isActive = activeFormat === type;

          return (
            <button
              key={type}
              onClick={() => onSelect(type)}
              className={clsx(
                'flex items-center gap-2 px-3 py-1.5 rounded-xl text-sm font-medium transition-colors',
                isActive
                  ? 'bg-lsc-cream dark:bg-lsc-dark/30 text-lsc-rose dark:text-lsc-rose-light border-2 border-earth-500'
                  : 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70 border-2 border-transparent hover:border-lsc-border dark:hover:border-earth-500'
              )}
            >
              <Icon aria-hidden="true" className="w-4 h-4" />
              {config.label}
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 shadow-sm border border-lsc-border dark:border-earth-700">
      <p className="text-lsc-dark dark:text-earth-300 mb-4 font-medium">
        How do you want to learn this?
      </p>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
        {availableFormats.map(({ type }) => {
          const config = FORMAT_CONFIG[type];
          const isActive = activeFormat === type;
          const isPreferred = preferredFormat === type && !isActive;
          const Icon = config.icon;

          return (
            <button
              key={type}
              onClick={() => onSelect(type)}
              className={clsx(
                'relative flex flex-col items-center gap-2 p-4 rounded-xl transition-all',
                isActive
                  ? 'bg-lsc-cream dark:bg-lsc-dark/30 border-2 border-earth-500 dark:border-earth-400'
                  : 'bg-lsc-cream dark:bg-lsc-brown/50 border-2 border-transparent hover:border-lsc-border dark:hover:border-earth-600 hover:bg-lsc-cream dark:hover:bg-lsc-brown'
              )}
            >
              {isPreferred && (
                <span className="absolute -top-2 -right-2 text-xs bg-lsc-cream dark:bg-lsc-dark text-lsc-rose dark:text-lsc-cream/70 px-2 py-0.5 rounded-full">
                  your fave
                </span>
              )}

              <Icon className={clsx(
                'w-6 h-6',
                isActive ? 'text-lsc-rose dark:text-lsc-rose-light' : 'text-lsc-dark/70 dark:text-lsc-cream/70'
              )} />

              <span className={clsx(
                'font-medium text-sm',
                isActive ? 'text-lsc-rose dark:text-lsc-rose-light' : 'text-lsc-dark dark:text-lsc-cream'
              )}>
                {config.label}
              </span>

              <span className={clsx(
                'text-xs text-center',
                isActive ? 'text-lsc-rose dark:text-lsc-rose-light' : 'text-lsc-dark/70 dark:text-lsc-cream/70'
              )}>
                {config.description}
              </span>
            </button>
          );
        })}
      </div>

      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-4 text-center">
        Pick whatever works for your brain today. You can switch anytime.
      </p>
    </div>
  );
}
