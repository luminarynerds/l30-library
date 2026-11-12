/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Users } from 'lucide-react'
import RepCard from './RepCard'
import { getLevelLabel } from './helpers'
import type { RepresentativeInfo } from './types'

interface RepLevelSectionProps {
  level: 'federal' | 'state' | 'local'
  reps: RepresentativeInfo[]
  selectedRep: RepresentativeInfo | null
  onSelectRep: (rep: RepresentativeInfo) => void
}

export default function RepLevelSection({
  level,
  reps,
  selectedRep,
  onSelectRep,
}: RepLevelSectionProps): React.ReactElement {
  if (reps.length === 0) return <></>
  return (
    <div className="mb-8">
      <div className="flex items-center gap-2 mb-4">
        <Users className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
        <h3 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream">
          {getLevelLabel(level)}
        </h3>
        <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">({reps.length})</span>
      </div>
      <div className="grid sm:grid-cols-2 gap-4">
        {reps.map((rep) => (
          <RepCard
            key={`${rep.name}-${rep.office}`}
            rep={rep}
            isSelected={selectedRep?.name === rep.name && selectedRep?.office === rep.office}
            onSelect={onSelectRep}
          />
        ))}
      </div>
    </div>
  )
}
