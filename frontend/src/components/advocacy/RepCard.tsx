/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Phone, Mail, Globe } from 'lucide-react'
import { getInitials, getPartyAbbrev, getPartyColor } from './helpers'
import type { RepresentativeInfo } from './types'

interface RepCardProps {
  rep: RepresentativeInfo
  isSelected: boolean
  onSelect: (rep: RepresentativeInfo) => void
}

export default function RepCard({ rep, isSelected, onSelect }: RepCardProps): React.ReactElement {
  const phone = rep.phones?.[0]
  const email = rep.emails?.[0]
  const website = rep.urls?.[0]

  return (
    <div
      className={`bg-lsc-white dark:bg-earth-800 rounded-xl border p-5 cursor-pointer transition-shadow hover:shadow-md ${
        isSelected
          ? 'border-lsc-rose dark:border-lsc-rose ring-2 ring-lsc-rose/30'
          : 'border-lsc-border dark:border-earth-700'
      }`}
      onClick={() => onSelect(rep)}
      role="button"
      tabIndex={0}
      aria-pressed={isSelected}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') onSelect(rep)
      }}
    >
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0">
          {rep.photoUrl ? (
            <img
              src={rep.photoUrl}
              alt={rep.name}
              className="w-12 h-12 rounded-full object-cover"
              onError={(e) => {
                const target = e.currentTarget
                target.style.display = 'none'
                const sibling = target.nextElementSibling as HTMLElement | null
                if (sibling) sibling.style.display = 'flex'
              }}
            />
          ) : null}
          <div
            className={`w-12 h-12 rounded-full bg-lsc-rose/10 dark:bg-lsc-rose/20 items-center justify-center text-lsc-rose dark:text-lsc-rose-light font-bold text-sm ${
              rep.photoUrl ? 'hidden' : 'flex'
            }`}
            aria-hidden="true"
          >
            {getInitials(rep.name)}
          </div>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 flex-wrap">
            <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream text-base leading-tight">
              {rep.name}
            </h3>
            {rep.party && (
              <span className={`px-2 py-0.5 text-xs font-semibold rounded-full flex-shrink-0 ${getPartyColor(rep.party)}`}>
                {getPartyAbbrev(rep.party)}
              </span>
            )}
          </div>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">{rep.office}</p>

          <div className="mt-3 flex flex-col gap-1.5">
            {phone && (
              <a
                href={`tel:${phone}`}
                className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light transition-colors"
                onClick={(e) => e.stopPropagation()}
                aria-label={`Call ${rep.name} at ${phone}`}
              >
                <Phone className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                <span>{phone}</span>
              </a>
            )}
            {email && (
              <a
                href={`mailto:${email}`}
                className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light transition-colors"
                onClick={(e) => e.stopPropagation()}
                aria-label={`Email ${rep.name}`}
              >
                <Mail className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                <span className="truncate" title={email}>{email}</span>
              </a>
            )}
            {website && (
              <a
                href={website}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose dark:hover:text-lsc-rose-light transition-colors"
                onClick={(e) => e.stopPropagation()}
                aria-label={`Visit ${rep.name}'s website`}
              >
                <Globe className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                <span className="truncate">Official website</span>
              </a>
            )}
          </div>
        </div>
      </div>

      {isSelected && (
        <p className="mt-3 text-xs text-lsc-rose dark:text-lsc-rose-light font-medium">
          Selected for letter composition
        </p>
      )}
    </div>
  )
}
