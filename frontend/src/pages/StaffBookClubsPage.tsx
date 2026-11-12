/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { BookOpen, Plus, Loader2, Users, Pencil, Upload, ListOrdered } from 'lucide-react'
import { StaffBookClubWaitlistModal } from '../components/staff/StaffBookClubWaitlistModal'
import { staffCapacityTone } from '@/utils/bookClubCapacity'
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'
import { t } from '@/i18n'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchApi } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'
import { AdminShell } from '../components/shells/AdminShell'
import { CreateBookClubModal } from '../components/staff/CreateBookClubModal'
import { ImportMembersModal } from '../components/book-clubs/ImportMembersModal'
import PageContainer from '@/components/layout/PageContainer'

interface BookClub {
  id: number
  name: string
  description: string | null
  status: string
  max_members: number | null
  is_public: boolean
  meeting_frequency: string | null
  members?: { id: number }[]
  meetings?: { id: number; meeting_date: string; status: string }[]
}

interface BookClubListResponse {
  total: number
  clubs: BookClub[]
}

// Keys must match BookClubStatus enum in backend/app/models/book_club.py.
export const STATUS_COLORS: Record<string, string> = {
  active: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300',
  inactive: 'bg-earth-100 text-earth-600 dark:bg-earth-800 dark:text-earth-400',
  archived: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300',
}

export const STATUS_COLOR_FALLBACK = STATUS_COLORS.inactive

function ClubRow({ club, onEdit, onImport, onWaitlist, waitlistEnabled }: { club: BookClub; onEdit: (club: BookClub) => void; onImport: (club: BookClub) => void; onWaitlist: (club: BookClub) => void; waitlistEnabled: boolean }) {
  const memberCount = club.members?.length ?? 0
  const tone = staffCapacityTone(memberCount, club.max_members)
  const toneClass =
    tone === 'full'
      ? 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300'
      : tone === 'warn'
      ? 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300'
      : 'bg-earth-100 text-earth-600 dark:bg-earth-800 dark:text-earth-400'
  const nextMeeting = club.meetings
    ?.filter(m => m.status !== 'completed' && m.status !== 'cancelled')
    .sort((a, b) => a.meeting_date.localeCompare(b.meeting_date))[0]

  return (
    <tr className="border-b border-earth-100 dark:border-earth-700">
      <td className="px-4 py-3">
        <div className="font-medium text-lsc-dark dark:text-lsc-cream">{club.name}</div>
        {club.description && (
          <div className="text-sm text-earth-600 dark:text-earth-400 line-clamp-1">{club.description}</div>
        )}
      </td>
      <td className="px-4 py-3">
        <span className={`text-xs font-medium px-2 py-1 rounded-full ${STATUS_COLORS[club.status] ?? STATUS_COLOR_FALLBACK}`}>
          {club.status}
        </span>
        {!club.is_public && (
          <span className="ml-1.5 text-xs font-medium px-2 py-1 rounded-full bg-earth-100 text-earth-600 dark:bg-earth-800 dark:text-earth-400">
            Private
          </span>
        )}
      </td>
      <td className="px-4 py-3 text-sm">
        {club.max_members != null ? (
          waitlistEnabled ? (
            <button
              type="button"
              onClick={() => onWaitlist(club)}
              aria-label={t('staffBookClubs.waitlist.openLabel', { club: club.name })}
              className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${toneClass} hover:ring-2 hover:ring-lsc-rose focus:outline-none focus:ring-2 focus:ring-lsc-rose transition-shadow`}
            >
              <ListOrdered className="w-3 h-3" aria-hidden="true" />
              {memberCount}/{club.max_members}
            </button>
          ) : (
            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${toneClass}`}>
              {memberCount}/{club.max_members}
            </span>
          )
        ) : (
          <span className="text-earth-600 dark:text-earth-400">{memberCount}</span>
        )}
      </td>
      <td className="px-4 py-3 text-sm text-earth-600 dark:text-earth-400">
        {club.meeting_frequency ?? '--'}
      </td>
      <td className="px-4 py-3 text-sm text-earth-600 dark:text-earth-400">
        {nextMeeting
          ? new Date(nextMeeting.meeting_date).toLocaleDateString()
          : '--'}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-1">
          <button
            onClick={() => onImport(club)}
            className="p-1.5 text-earth-600 hover:bg-earth-50 dark:text-earth-400 dark:hover:bg-earth-800 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            title="Import members"
            aria-label={`Import members into ${club.name}`}
          >
            <Upload className="w-4 h-4" />
          </button>
          <button
            onClick={() => onEdit(club)}
            className="p-1.5 text-earth-600 hover:bg-earth-50 dark:text-earth-400 dark:hover:bg-earth-800 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            title="Edit"
            aria-label="Edit book club"
          >
            <Pencil className="w-4 h-4" />
          </button>
        </div>
      </td>
    </tr>
  )
}

export default function StaffBookClubsPage(): React.ReactElement {
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [editingClub, setEditingClub] = useState<BookClub | null>(null)
  const [importingClub, setImportingClub] = useState<BookClub | null>(null)
  const [waitlistClub, setWaitlistClub] = useState<BookClub | null>(null)
  const { isFeatureEnabled } = useOrganizationFeatures()
  const waitlistEnabled = isFeatureEnabled('book_club_waitlist_enabled')

  const { data, isLoading } = useQuery({
    queryKey: ['staff-book-clubs'],
    queryFn: async () => {
      const token = getAccessToken()
      // Trailing slash matters: `/book-clubs` (no slash) resolves to the
      // patron router (registered first) which returns a public-only,
      // reduced shape with no status/members/meetings. The staff list lives
      // at `/book-clubs/`.
      return fetchApi<BookClubListResponse>('/book-clubs/', {
        ...(token ? { token } : {}),
      })
    },
  })

  const clubs = data?.clubs ?? []

  return (
    <AdminShell title="Book Clubs">
      <PageContainer className="py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
              <BookOpen className="w-6 h-6" aria-hidden="true" />
              Book Club Management
            </h1>
            <p className="text-sm text-earth-600 dark:text-earth-400 mt-1">
              Create and manage library book clubs.
            </p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg text-sm font-medium hover:bg-lsc-rose/90 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2"
            aria-label="Create new book club"
          >
            <Plus className="w-4 h-4" />
            New Club
          </button>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-16" role="status" aria-label="Loading book clubs">
            <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-gold" />
          </div>
        ) : clubs.length === 0 ? (
          <div className="text-center py-16 text-earth-600 dark:text-earth-400">
            <Users className="w-12 h-12 mx-auto mb-3 opacity-40" aria-hidden="true" />
            <p>No book clubs yet.</p>
          </div>
        ) : (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
            <table className="w-full text-left">
              <thead className="bg-earth-50 dark:bg-earth-900">
                <tr>
                  <th className="px-4 py-3 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">Club</th>
                  <th className="px-4 py-3 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">Status</th>
                  <th className="px-4 py-3 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">Members</th>
                  <th className="px-4 py-3 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">Frequency</th>
                  <th className="px-4 py-3 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">Next Meeting</th>
                  <th className="px-4 py-3 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody>
                {clubs.map((club) => (
                  <ClubRow key={club.id} club={club} onEdit={(c) => setEditingClub(c)} onImport={(c) => setImportingClub(c)} onWaitlist={(c) => setWaitlistClub(c)} waitlistEnabled={waitlistEnabled} />
                ))}
              </tbody>
            </table>
          </div>
        )}

        {(showCreate || editingClub) && (
          <CreateBookClubModal
            onClose={() => { setShowCreate(false); setEditingClub(null) }}
            onCreated={() => queryClient.invalidateQueries({ queryKey: ['staff-book-clubs'] })}
            editing={editingClub}
          />
        )}

        {importingClub && (
          <ImportMembersModal
            clubId={importingClub.id}
            onClose={() => setImportingClub(null)}
            onImported={() => queryClient.invalidateQueries({ queryKey: ['staff-book-clubs'] })}
          />
        )}

        {waitlistClub && (
          <StaffBookClubWaitlistModal
            clubId={waitlistClub.id}
            clubName={waitlistClub.name}
            onClose={() => setWaitlistClub(null)}
          />
        )}
      </PageContainer>
    </AdminShell>
  )
}
