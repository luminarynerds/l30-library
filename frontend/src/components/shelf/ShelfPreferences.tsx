/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useShelfPreferences } from '@/hooks/useShelfPreferences'

export default function ShelfPreferences() {
  const { preferences, handleUpdate } = useShelfPreferences()

  const toggle = (key: 'show_reading_activity' | 'show_pace_stats') => {
    handleUpdate({ ...preferences, [key]: !preferences[key] })
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border/60 dark:border-earth-700/80 p-4 mb-6">
      <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
        Display Preferences
      </h3>
      <div className="space-y-3">
        <label className="flex items-center justify-between cursor-pointer">
          <div>
            <span className="text-sm text-lsc-dark dark:text-lsc-cream">Show my reading activity</span>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">Display streak and activity stats in the feed</p>
          </div>
          <button
            role="switch"
            aria-checked={preferences.show_reading_activity}
            onClick={() => toggle('show_reading_activity')}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              preferences.show_reading_activity
                ? 'bg-lsc-rose'
                : 'bg-earth-300 dark:bg-earth-600'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-lsc-white transition-transform ${
                preferences.show_reading_activity ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </label>

        <label className="flex items-center justify-between cursor-pointer">
          <div>
            <span className="text-sm text-lsc-dark dark:text-lsc-cream">Show pace estimates</span>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">Display avg pages/day and estimated finish date</p>
          </div>
          <button
            role="switch"
            aria-checked={preferences.show_pace_stats}
            onClick={() => toggle('show_pace_stats')}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              preferences.show_pace_stats
                ? 'bg-lsc-rose'
                : 'bg-earth-300 dark:bg-earth-600'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-lsc-white transition-transform ${
                preferences.show_pace_stats ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </label>
      </div>
    </div>
  )
}
