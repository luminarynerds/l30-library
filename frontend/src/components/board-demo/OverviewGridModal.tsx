/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import FocusTrap from 'focus-trap-react'
import { Grid3X3 } from 'lucide-react'
import { SCENES } from './board-demo-data'

export function OverviewGridModal({ onSelect, currentScene }: { onSelect: (i: number) => void; currentScene: number }) {
  return (
    // eslint-disable-next-line jsx-a11y/click-events-have-key-events
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4" onClick={() => onSelect(currentScene)}>
      <FocusTrap active={true} focusTrapOptions={{ escapeDeactivates: true }}>
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
      <div role="dialog" aria-modal="true" aria-labelledby="scene-overview-title" className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 max-w-3xl w-full max-h-[80vh] overflow-y-auto shadow-lg" onClick={(e) => e.stopPropagation()}>
        <h2 id="scene-overview-title" className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Grid3X3 className="w-5 h-5 text-lsc-rose" />
          Scene Overview
        </h2>
        <div className="grid grid-cols-3 gap-3">
          {SCENES.map((s, i) => (
            <button
              key={s.id}
              onClick={() => onSelect(i)}
              className={`rounded-xl p-4 text-left transition-all hover:scale-[1.03] hover:shadow-md border-2 ${
                i === currentScene
                  ? 'border-lsc-rose bg-status-warning-50 dark:bg-status-warning-900/20'
                  : 'border-lsc-border dark:border-earth-700 bg-earth-50 dark:bg-earth-800/50'
              }`}
            >
              <div className={`bg-gradient-to-r ${s.bgGradient} rounded-lg p-3 mb-2 flex items-center gap-2`}>
                <s.icon className={`w-5 h-5 ${s.color}`} />
                <span className="font-semibold text-sm text-lsc-dark dark:text-lsc-cream">{s.title}</span>
              </div>
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-2" title={s.subtitle}>{s.subtitle}</p>
              <span className="text-[10px] text-earth-600 mt-1 block">{s.durationMinutes} min</span>
            </button>
          ))}
        </div>
      </div>
      </FocusTrap>
    </div>
  )
}
