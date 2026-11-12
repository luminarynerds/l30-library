/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import BoardMemberCard from './BoardMemberCard'

interface BoardMember {
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

interface BoardMemberGalleryProps {
  members: BoardMember[]
}

// Order in which positions appear in the gallery
const positionOrder: Record<string, number> = {
  president: 1,
  vice_president: 2,
  secretary: 3,
  treasurer: 4,
  member: 5,
}

const positionGroupLabels: Record<string, string> = {
  president: 'President',
  vice_president: 'Vice President',
  secretary: 'Secretary',
  treasurer: 'Treasurer',
  member: 'Trustees',
}

function groupAndSortMembers(members: BoardMember[]): Array<{ label: string; items: BoardMember[] }> {
  // Group by position
  const groups = new Map<string, BoardMember[]>()

  for (const member of members) {
    const pos = member.position || 'member'
    if (!groups.has(pos)) {
      groups.set(pos, [])
    }
    groups.get(pos)!.push(member)
  }

  // Sort the groups by position order, unknown positions go last
  const sortedKeys = Array.from(groups.keys()).sort(
    (a, b) => (positionOrder[a] ?? 99) - (positionOrder[b] ?? 99)
  )

  return sortedKeys.map((pos) => ({
    label: positionGroupLabels[pos] || pos,
    items: groups.get(pos)!,
  }))
}

export default function BoardMemberGallery({ members }: BoardMemberGalleryProps): React.ReactElement {
  const groups = groupAndSortMembers(members)

  if (groups.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          Board member information will be available soon.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-10">
      {groups.map(({ label, items }) => (
        <section key={label} aria-labelledby={`group-${label.replace(/\+/g, '-').toLowerCase()}`}>
          {/* Only show group heading when there are multiple groups */}
          {groups.length > 1 && (
            <h2
              id={`group-${label.replace(/\+/g, '-').toLowerCase()}`}
              className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 pb-2 border-b border-lsc-border dark:border-earth-700"
            >
              {label}
            </h2>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {items.map((member) => (
              <BoardMemberCard key={member.id} {...member} />
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
