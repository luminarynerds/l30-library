/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// Small select-style chip used for status + difficulty filters.
export function FilterChip<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <label className="inline-flex items-center gap-2 text-sm">
      <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
        className="
          px-3 py-2 rounded-lg
          bg-lsc-cream/50 dark:bg-earth-900
          border border-lsc-border dark:border-earth-700
          text-sm text-lsc-dark dark:text-lsc-cream
          focus:outline-none focus:ring-2 focus:ring-lsc-rose
        "
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </label>
  );
}
