/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
function InfoCard({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <div className="bg-earth-50 dark:bg-earth-700 rounded-lg p-3">
      <div className="flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
        <Icon className="w-3 h-3" />
        {label}
      </div>
      <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{value}</p>
    </div>
  )
}

export default InfoCard
