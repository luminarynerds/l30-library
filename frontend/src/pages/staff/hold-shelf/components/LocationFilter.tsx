/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { PullListResponse } from "../types"

interface LocationFilterProps {
  pullList: PullListResponse
  selectedLocation: string | null
  onLocationSelect: (location: string | null) => void
}

export function LocationFilter({ pullList, selectedLocation, onLocationSelect }: LocationFilterProps) {
  if (pullList.locations.length <= 1) return null

  return (
    <div className="mb-6 flex gap-2 flex-wrap">
      <button
        onClick={() => onLocationSelect(null)}
        aria-pressed={selectedLocation === null}
        className={`px-4 py-2 rounded-lg font-medium transition-colors ${
          selectedLocation === null
            ? "bg-lsc-rose text-white"
            : "bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 border border-lsc-border dark:border-earth-700 hover:bg-earth-50 dark:hover:bg-earth-800"
        }`}
      >
        All Locations
      </button>
      {pullList.locations.map((loc) => (
        <button
          key={loc.location}
          onClick={() => onLocationSelect(loc.location)}
          aria-pressed={selectedLocation === loc.location}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            selectedLocation === loc.location
              ? "bg-lsc-rose text-white"
              : "bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 border border-lsc-border dark:border-earth-700 hover:bg-earth-50 dark:hover:bg-earth-800"
          }`}
        >
          {loc.location} ({loc.item_count})
        </button>
      ))}
    </div>
  )
}
