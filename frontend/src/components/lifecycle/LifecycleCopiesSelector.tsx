/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { LifecycleTimeline } from "../../api/lifecycle-api"

interface Props {
  timelines: LifecycleTimeline[]
  selectedTimeline: LifecycleTimeline | null
  onSelect: (timeline: LifecycleTimeline) => void
}

export function LifecycleCopiesSelector({ timelines, selectedTimeline, onSelect }: Props): React.ReactElement {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
      <h3 className="font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
        {timelines.length} Copies Found
      </h3>
      <div className="flex flex-wrap gap-2">
        {timelines.map((timeline) => (
          <button
            key={timeline.item_copy_id}
            onClick={() => onSelect(timeline)}
            className={`px-3 py-1.5 rounded-xl text-sm transition-colors ${
              selectedTimeline?.item_copy_id === timeline.item_copy_id
                ? "bg-lsc-rose text-white"
                : "bg-lsc-cream dark:bg-lsc-brown/30 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/80 dark:hover:bg-lsc-brown/50"
            }`}
          >
            Copy #{timeline.item_copy_id}
            {timeline.item_copy_barcode && ` (${timeline.item_copy_barcode})`}
          </button>
        ))}
      </div>
    </div>
  )
}
