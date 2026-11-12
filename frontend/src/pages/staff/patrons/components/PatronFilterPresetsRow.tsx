/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import { Bookmark, Plus, X } from "lucide-react"
import { useTranslation } from "@/i18n"
import type { FilterPreset, PatronAdvancedFilters } from "@/api/staff-api/patrons"
import type { StatusFilter } from "../types"
import {
  BUILTIN_PRESETS,
  type PresetFilters,
} from "../hooks/usePatronFilterPresets"

interface PatronFilterPresetsRowProps {
  userPresets: FilterPreset[]
  activePresetId: string | null
  currentFilters: PatronAdvancedFilters
  currentStatusFilter: StatusFilter
  onApply: (id: string, filters: PresetFilters) => void
  onClearActive: () => void
  onSavePreset: (name: string, filters: PresetFilters) => void
  onDeleteUserPreset: (id: string) => void
}

export function PatronFilterPresetsRow({
  userPresets,
  activePresetId,
  currentFilters,
  currentStatusFilter,
  onApply,
  onClearActive,
  onSavePreset,
  onDeleteUserPreset,
}: PatronFilterPresetsRowProps): React.ReactElement {
  const { t } = useTranslation()
  const [isNaming, setIsNaming] = useState(false)
  const [draftName, setDraftName] = useState("")

  const hasActiveFilters =
    Object.keys(currentFilters).length > 0 ||
    (currentStatusFilter && currentStatusFilter !== "all")

  const handleChipClick = (id: string, filters: PresetFilters) => {
    if (activePresetId === id) {
      onClearActive()
    } else {
      onApply(id, filters)
    }
  }

  const handleSaveSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    const name = draftName.trim()
    if (!name) return
    const filters: PresetFilters = {
      ...currentFilters,
      ...(currentStatusFilter && currentStatusFilter !== "all"
        ? { statusFilter: currentStatusFilter }
        : {}),
    }
    onSavePreset(name, filters)
    setDraftName("")
    setIsNaming(false)
  }

  const chipBase =
    "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors border"
  const chipInactive =
    "bg-lsc-white dark:bg-earth-800 border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/50 dark:hover:bg-earth-700"
  const chipActive =
    "bg-lsc-rose border-lsc-rose text-white hover:bg-lsc-rose/90"

  return (
    <div
      className="flex flex-wrap items-center gap-2"
      role="region"
      aria-label={t("staffPatrons.presets.region")}
    >
      <span className="inline-flex items-center gap-1.5 text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 pr-1">
        <Bookmark className="w-3.5 h-3.5" aria-hidden="true" />
        {t("staffPatrons.presets.label")}
      </span>

      {BUILTIN_PRESETS.map((preset) => {
        const isActive = activePresetId === preset.id
        return (
          <button
            key={preset.id}
            type="button"
            onClick={() => handleChipClick(preset.id, preset.build())}
            aria-pressed={isActive}
            className={`${chipBase} ${isActive ? chipActive : chipInactive}`}
          >
            {t(preset.nameKey)}
          </button>
        )
      })}

      {userPresets.map((preset) => {
        const isActive = activePresetId === preset.id
        return (
          <span
            key={preset.id}
            className={`${chipBase} ${isActive ? chipActive : chipInactive} pr-1.5`}
          >
            <button
              type="button"
              onClick={() => handleChipClick(preset.id, preset.filters)}
              aria-pressed={isActive}
              className="bg-transparent border-0 p-0 m-0 font-medium text-inherit"
            >
              {preset.name}
            </button>
            <button
              type="button"
              onClick={() => onDeleteUserPreset(preset.id)}
              aria-label={t("staffPatrons.presets.deleteAria", { name: preset.name })}
              className="ml-0.5 -mr-0.5 p-0.5 rounded-full hover:bg-black/10 dark:hover:bg-white/10"
            >
              <X className="w-3 h-3" aria-hidden="true" />
            </button>
          </span>
        )
      })}

      {isNaming ? (
        <form onSubmit={handleSaveSubmit} className="inline-flex items-center gap-1">
          <input
            autoFocus
            type="text"
            value={draftName}
            onChange={(e) => setDraftName(e.target.value)}
            onBlur={() => {
              if (!draftName.trim()) setIsNaming(false)
            }}
            placeholder={t("staffPatrons.presets.namePlaceholder")}
            aria-label={t("staffPatrons.presets.nameAria")}
            className="px-2 py-1 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream text-xs focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          />
          <button
            type="button"
            onClick={() => handleSaveSubmit()}
            disabled={!draftName.trim()}
            className={`${chipBase} ${chipInactive} disabled:opacity-50`}
          >
            {t("staffPatrons.presets.confirmSave")}
          </button>
          <button
            type="button"
            onClick={() => {
              setDraftName("")
              setIsNaming(false)
            }}
            aria-label={t("staffPatrons.presets.cancelSaveAria")}
            className={`${chipBase} ${chipInactive}`}
          >
            <X className="w-3 h-3" aria-hidden="true" />
          </button>
        </form>
      ) : (
        <button
          type="button"
          onClick={() => setIsNaming(true)}
          disabled={!hasActiveFilters}
          title={
            hasActiveFilters
              ? t("staffPatrons.presets.saveCurrent")
              : t("staffPatrons.presets.saveCurrentDisabled")
          }
          className={`${chipBase} ${chipInactive} disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          <Plus className="w-3 h-3" aria-hidden="true" />
          {t("staffPatrons.presets.saveCurrent")}
        </button>
      )}
    </div>
  )
}
