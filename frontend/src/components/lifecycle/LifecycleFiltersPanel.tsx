/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { LIFECYCLE_STAGES, type LifecycleStage } from "../../api/lifecycle-api"
import { useTranslation } from "@/i18n"

interface Props {
  stageFilter: LifecycleStage | "all"
  onStageFilterChange: (value: LifecycleStage | "all") => void
}

export function LifecycleFiltersPanel({ stageFilter, onStageFilterChange }: Props): React.ReactElement {
  const { t } = useTranslation()
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 shadow-sm">
      <div className="flex flex-wrap gap-4 items-center">
        <div>
          <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
            Filter by Stage
          </label>
          <select
            value={stageFilter}
            onChange={(e) => onStageFilterChange(e.target.value as LifecycleStage | "all")}
            aria-label={t('staffLifecycleManagement.filterByLifecycleStage')}
            className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          >
            <option value="all">All Stages</option>
            {Object.entries(LIFECYCLE_STAGES).map(([key, stage]) => (
              <option key={key} value={key}>
                {stage.label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex gap-2 ml-auto">
          <button
            onClick={() => onStageFilterChange("all")}
            className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 rounded-xl transition-colors"
          >
            Clear Filters
          </button>
        </div>
      </div>
    </div>
  )
}
