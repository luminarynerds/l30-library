/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { TONE_PRESETS, chipSelected, chipUnselected } from './useAIGeneration'

interface ToneSelectorProps {
  tone: string
  setTone: (tone: string) => void
}

export default function ToneSelector({ tone, setTone }: ToneSelectorProps) {
  return (
    <div>
      <span id="tone-label" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
        Tone
      </span>
      <div role="radiogroup" aria-label="Tone" aria-labelledby="tone-label" className="flex flex-wrap gap-2">
        {TONE_PRESETS.map((preset) => {
          const isSelected = tone === preset.value
          return (
            <button
              key={preset.value || 'default'}
              type="button"
              role="radio"
              aria-checked={isSelected}
              onClick={() => setTone(preset.value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium motion-safe:transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose ${
                isSelected ? chipSelected : chipUnselected
              }`}
            >
              {preset.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}
