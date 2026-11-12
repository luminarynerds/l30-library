/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { MessageCircle, Plus, Loader2, Trash2, Play, Square, Calendar, Pencil } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getAmaSessions,
  deleteAmaSession,
  transitionAmaSessionStatus,
  type AmaSession,
  type AmaSessionStatus,
} from '@/api/domains/content/ama-api'
import toast from 'react-hot-toast'
import { AdminShell } from '../components/shells/AdminShell'
import { CreateAmaSessionModal } from '../components/staff/CreateAmaSessionModal'
import { t } from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

const STATUS_LABELS: Record<AmaSessionStatus, string> = {
  live: 'Live',
  upcoming: 'Upcoming',
  grace_period: 'Grace Period',
  archived: 'Archived',
}

const STATUS_COLORS: Record<AmaSessionStatus, string> = {
  live: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300',
  upcoming: 'bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-300',
  grace_period: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300',
  archived: 'bg-earth-100 text-earth-600 dark:bg-earth-800 dark:text-earth-400',
}

function SessionRow({ session, onDelete, onTransition, onEdit }: {
  session: AmaSession
  onDelete: (id: number) => void
  onTransition: (id: number, status: string) => void
  onEdit: (session: AmaSession) => void
}) {
  const author = session.author
  const authorName =
    author?.pen_name ??
    author?.guest_author_name ??
    (author?.indie_author_id ? `Author #${author.indie_author_id}` : 'Unknown')

  return (
    <tr className="border-b border-earth-100 dark:border-earth-700">
      <td className="px-4 py-3">
        <div className="font-medium text-lsc-dark dark:text-lsc-cream">{session.title}</div>
        <div className="text-sm text-earth-600 dark:text-earth-400">{authorName}</div>
      </td>
      <td className="px-4 py-3">
        <span className={`text-xs font-medium px-2 py-1 rounded-full ${STATUS_COLORS[session.status]}`}>
          {STATUS_LABELS[session.status]}
        </span>
      </td>
      <td className="px-4 py-3 text-sm text-earth-600 dark:text-earth-400">
        {session.scheduled_start
          ? new Date(session.scheduled_start).toLocaleDateString()
          : '--'}
      </td>
      <td className="px-4 py-3 text-sm text-earth-600 dark:text-earth-400">
        {session.total_questions}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-1">
          {session.status === 'upcoming' && (
            <button
              onClick={() => onTransition(session.id, 'live')}
              className="p-1.5 text-status-success-600 hover:bg-status-success-50 dark:hover:bg-status-success-900/20 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-status-success-500"
              title="Go Live"
              aria-label={t('aria.staffAmas.startLiveSession')}
            >
              <Play className="w-4 h-4" />
            </button>
          )}
          {session.status === 'upcoming' && (
            <button
              onClick={() => onEdit(session)}
              className="p-1.5 text-earth-600 hover:bg-earth-50 dark:text-earth-400 dark:hover:bg-earth-800 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              title="Edit"
              aria-label="Edit session"
            >
              <Pencil className="w-4 h-4" />
            </button>
          )}
          {session.status === 'live' && (
            <button
              onClick={() => onTransition(session.id, 'grace_period')}
              className="p-1.5 text-status-warning-600 hover:bg-status-warning-50 dark:hover:bg-status-warning-900/20 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-status-warning-500"
              title="End Session"
              aria-label={t('aria.staffAmas.endLiveSession')}
            >
              <Square className="w-4 h-4" />
            </button>
          )}
          {session.status === 'upcoming' && (
            <button
              onClick={() => onDelete(session.id)}
              className="p-1.5 text-status-danger-500 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-status-danger-500"
              title="Delete"
              aria-label={t('aria.staffAmas.deleteSession')}
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </td>
    </tr>
  )
}

export default function StaffAmasPage(): React.ReactElement {
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)
  const [showCreate, setShowCreate] = useState(false)
  const [editingSession, setEditingSession] = useState<AmaSession | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['staff-ama-sessions', statusFilter],
    queryFn: () => getAmaSessions(statusFilter, 1, 50),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteAmaSession(id),
    onMutate: async (deletedId) => {
      await queryClient.cancelQueries({ queryKey: ['staff-ama-sessions', statusFilter] })
      const queryKey = ['staff-ama-sessions', statusFilter]
      const previous = queryClient.getQueryData<{ items: AmaSession[] }>(queryKey)
      if (previous) {
        queryClient.setQueryData(queryKey, {
          ...previous,
          items: previous.items.filter(s => s.id !== deletedId),
        })
      }
      return { previous, queryKey }
    },
    onSuccess: () => {
      // toast or UI cleanup can go here
    },
    onError: (_err, _id, context) => {
      if (context?.previous) {
        queryClient.setQueryData(context.queryKey, context.previous)
      }
      toast.error('Failed to delete session')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['staff-ama-sessions'] })
    },
  })

  const transitionMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      transitionAmaSessionStatus(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['staff-ama-sessions'] }),
    onError: () => {
      toast.error('Failed to update session status')
    },
  })

  const sessions = data?.items ?? []

  return (

    <AdminShell title="Ask Me Anything">    <PageContainer className="py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
            <MessageCircle className="w-6 h-6" aria-hidden="true" />
            AMA Session Management
          </h1>
          <p className="text-sm text-earth-600 dark:text-earth-400 mt-1">
            Create, manage, and moderate Author AMA sessions.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg text-sm font-medium hover:bg-lsc-rose/90 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2"
          aria-label={t('aria.staffAmas.createNewAmaSession')}
        >
          <Plus className="w-4 h-4" />
          New Session
        </button>
      </div>

      <div className="flex gap-2 mb-4 flex-wrap" role="group" aria-label={t('aria.acquisition.filterByStatus')}>
        {[
          { value: undefined, label: 'All' },
          { value: 'upcoming', label: 'Upcoming' },
          { value: 'live', label: 'Live' },
          { value: 'archived', label: 'Archived' },
        ].map((opt) => (
          <button
            key={opt.label}
            onClick={() => setStatusFilter(opt.value)}
            className={`px-3 py-1 text-xs rounded-full border transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose ${
              statusFilter === opt.value
                ? 'bg-lsc-rose text-white border-lsc-rose'
                : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 border-lsc-border dark:border-earth-700 hover:border-lsc-rose'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16" role="status" aria-label={t('aria.staffAmas.loadingSessions')}>
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
        </div>
      ) : sessions.length === 0 ? (
        <div className="text-center py-16 text-earth-600 dark:text-earth-400">
          <Calendar className="w-12 h-12 mx-auto mb-3 opacity-40" aria-hidden="true" />
          <p>No AMA sessions found.</p>
        </div>
      ) : (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
          <table className="w-full text-left">
            <thead className="bg-earth-50 dark:bg-earth-900">
              <tr>
                <th className="px-4 py-3 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">Session</th>
                <th className="px-4 py-3 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">Status</th>
                <th className="px-4 py-3 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">Date</th>
                <th className="px-4 py-3 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">Questions</th>
                <th className="px-4 py-3 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((session) => (
                <SessionRow
                  key={session.id}
                  session={session}
                  onDelete={(id) => deleteMutation.mutate(id)}
                  onTransition={(id, status) => transitionMutation.mutate({ id, status })}
                  onEdit={(s) => setEditingSession(s)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
      {(showCreate || editingSession) && (
        <CreateAmaSessionModal
          onClose={() => { setShowCreate(false); setEditingSession(null) }}
          onCreated={() => queryClient.invalidateQueries({ queryKey: ['staff-ama-sessions'] })}
          editing={editingSession}
        />
      )}
    </PageContainer>
  </AdminShell>
  )
}
