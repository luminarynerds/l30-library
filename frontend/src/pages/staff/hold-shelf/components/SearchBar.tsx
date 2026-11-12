/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Search, X } from "lucide-react"

interface SearchBarProps {
  value: string
  onChange: (value: string) => void
}

export function SearchBar({ value, onChange }: SearchBarProps) {
  return (
    <div className="mb-6 relative">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-lsc-dark/40 dark:text-lsc-cream/40" />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search by patron name or item title..."
        aria-label="Search hold shelf by patron name or item title"
        className="w-full pl-10 pr-10 py-2.5 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream placeholder:text-lsc-dark/40 dark:placeholder:text-lsc-cream/40 focus:ring-2 focus:ring-lsc-rose focus:outline-none"
      />
      {value && (
        <button
          onClick={() => onChange("")}
          aria-label="Clear search"
          className="absolute right-3 top-1/2 -translate-y-1/2 text-lsc-dark/40 dark:text-lsc-cream/40 hover:text-lsc-dark dark:hover:text-lsc-cream"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  )
}
