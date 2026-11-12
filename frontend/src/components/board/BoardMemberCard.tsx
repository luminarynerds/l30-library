/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { Mail, Clock } from 'lucide-react'
import { getCurrentLocale } from '@/i18n'

interface BoardMemberCardProps {
  id: number
  full_name: string
  position: string
  term_start_date: string
  term_end_date?: string | null
  bio?: string | null
  photo_url?: string | null
  public_email?: string | null
  office_hours?: string | null
  committees?: Array<{ id: number; name: string }> | undefined
}

const positionLabels: Record<string, string> = {
  president: 'President',
  vice_president: 'Vice President',
  secretary: 'Secretary',
  treasurer: 'Treasurer',
  member: 'Trustee',
}

const positionBadgeColors: Record<string, string> = {
  president: 'bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-300',
  vice_president: 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light',
  secretary: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300',
  treasurer: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300',
  member: 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300',
}

function getInitials(fullName: string): string {
  return fullName
    .split(' ')
    .map((part) => part.charAt(0).toUpperCase())
    .slice(0, 2)
    .join('')
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString(getCurrentLocale(), {
    year: 'numeric',
    month: 'short',
  })
}

export default function BoardMemberCard({
  full_name,
  position,
  term_start_date,
  term_end_date,
  bio,
  photo_url,
  public_email,
  office_hours,
  committees,
}: BoardMemberCardProps): React.ReactElement {
  const [imgError, setImgError] = useState(false)

  const positionLabel = positionLabels[position] || position
  const badgeColor =
    positionBadgeColors[position] ||
    'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300'
  const initials = getInitials(full_name)
  const showPhoto = photo_url && !imgError

  const termLabel = term_end_date
    ? `${formatDate(term_start_date)} - ${formatDate(term_end_date)}`
    : `Since ${formatDate(term_start_date)}`

  const bioExcerpt =
    bio && bio.length > 120 ? bio.slice(0, 117).trimEnd() + '...' : bio

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-md overflow-hidden flex flex-col h-full border border-lsc-border dark:border-earth-700 hover:shadow-lg transition-shadow">
      {/* Photo / Avatar */}
      <div className="flex justify-center pt-6 pb-4 px-6">
        {showPhoto ? (
          <img
            src={photo_url}
            alt={`Photo of ${full_name}`}
            className="w-24 h-24 rounded-full object-cover ring-2 ring-lsc-cream dark:ring-earth-700"
            onError={() => setImgError(true)}
          />
        ) : (
          <div
            className="w-24 h-24 rounded-full bg-lsc-rose/20 dark:bg-lsc-rose/30 flex items-center justify-center ring-2 ring-lsc-cream dark:ring-earth-700"
            aria-hidden="true"
          >
            <span className="text-2xl font-bold text-lsc-rose">{initials}</span>
          </div>
        )}
      </div>

      {/* Member info */}
      <div className="px-6 pb-6 flex flex-col flex-1">
        <div className="text-center mb-3">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream leading-snug">
            {full_name}
          </h3>
          <span
            className={`inline-block mt-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${badgeColor}`}
          >
            {positionLabel}
          </span>
        </div>

        <div className="flex-1 space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {bioExcerpt && (
            <p className="text-lsc-dark/80 dark:text-lsc-cream/80 leading-relaxed">
              {bioExcerpt}
            </p>
          )}

          <p className="flex items-start gap-1.5">
            <Clock className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
            <span>{termLabel}</span>
          </p>

          {public_email && (
            <p className="flex items-start gap-1.5">
              <Mail className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
              <a
                href={`mailto:${public_email}`}
                className="text-lsc-rose hover:underline break-all"
              >
                {public_email}
              </a>
            </p>
          )}

          {office_hours && (
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              <span className="font-medium">Office hours:</span> {office_hours}
            </p>
          )}

          {committees && committees.length > 0 && (
            <div className="flex flex-wrap gap-1 pt-1">
              {committees.map((c) => (
                <Link
                  key={c.id}
                  to={`/board/committees/${c.id}`}
                  className="text-xs bg-lsc-cream dark:bg-earth-700 text-lsc-dark/80 dark:text-lsc-cream/80 px-2 py-0.5 rounded hover:bg-lsc-rose/20 dark:hover:bg-lsc-rose/30 transition-colors"
                >
                  {c.name}
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
