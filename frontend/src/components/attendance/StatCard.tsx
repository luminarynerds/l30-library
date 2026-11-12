/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="text-center">
      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{label}</p>
      <p className="text-xl font-bold text-lsc-dark dark:text-lsc-cream">{value}</p>
    </div>
  )
}
