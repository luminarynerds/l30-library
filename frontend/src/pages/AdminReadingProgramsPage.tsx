/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { BookOpen, Plus, Edit2, Trash2, Loader2, Users, TrendingUp, AlertCircle, X, List } from 'lucide-react'
import {
  getReadingPrograms,
  createReadingProgram,
  updateReadingProgram,
  deleteReadingProgram,
  type ReadingProgram,
  type ReadingProgramCreateData,
} from '@/api/api'
import { AdminShell } from '../components/shells'
import { useAuth } from '@/contexts/AuthContext'
import { useRequireRole } from '@/hooks/useRequireRole'
import AdminProgramForm from '@/components/AdminProgramForm'
import toast from 'react-hot-toast'
import { useTranslation} from '@/i18n'
import { parseDate } from '@/utils/format-utils'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import AdminProgramBooklistManager from '@/components/programs/AdminProgramBooklistManager'
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'
import PageContainer from '@/components/layout/PageContainer'

export default function AdminReadingProgramsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { token } = useAuth()
  const { isAuthorized } = useRequireRole('adminOrStaff')
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editingProgram, setEditingProgram] = useState<ReadingProgram | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)
  const [booklistManagerProgram, setBooklistManagerProgram] = useState<ReadingProgram | null>(null)
  const { isFeatureEnabled } = useOrganizationFeatures()
  const booklistEnabled = isFeatureEnabled('reading_programs_booklist_enabled')

// Auth check moved below hooks (React rules of hooks)

  // Fetch programs
  const { data: programs = [], isLoading, error } = useQuery({
    queryKey: ['admin-reading-programs'],
    queryFn: () =>
      getReadingPrograms({ active_only: false }).then((progs) =>
        // Sort by is_active first, then by start_date
        progs.sort((a, b) => {
          if (a.is_active !== b.is_active) return b.is_active ? -1 : 1
          return new Date(b.start_date).getTime() - new Date(a.start_date).getTime()
        })
      ),
    enabled: !!token,
  })

  // Create mutation
  const createMutation = useMutation({
    mutationFn: async (data: ReadingProgramCreateData) => createReadingProgram(token!, data),
    onSuccess: () => {
      toast.success(t('admin.adminReadingPrograms.toast.created'))
      queryClient.invalidateQueries({ queryKey: ['admin-reading-programs'] })
      setShowForm(false)
    },
    onError: (error: Error) => {
      toast.error(error.message)
    },
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: async ({ id, data }: { id: number; data: ReadingProgramCreateData }) =>
      updateReadingProgram(token!, id, data),
    onSuccess: () => {
      toast.success(t('admin.adminReadingPrograms.toast.updated'))
      queryClient.invalidateQueries({ queryKey: ['admin-reading-programs'] })
      setEditingProgram(null)
      setShowForm(false)
    },
    onError: (error: Error) => {
      toast.error(error.message)
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (id: number) => deleteReadingProgram(token!, id),
    onMutate: async (deletedId) => {
      await queryClient.cancelQueries({ queryKey: ['admin-reading-programs'] })
      const queryKey = ['admin-reading-programs']
      const previous = queryClient.getQueryData<ReadingProgram[]>(queryKey)
      if (previous) {
        queryClient.setQueryData(queryKey, previous.filter(prog => prog.id !== deletedId))
      }
      return { previous, queryKey }
    },
    onSuccess: () => {
      toast.success(t('admin.adminReadingPrograms.toast.deleted'))
      setDeleteConfirm(null)
    },
    onError: (_err, _id, context) => {
      if (context?.previous) {
        queryClient.setQueryData(context.queryKey, context.previous)
      }
      toast.error(t('admin.adminReadingPrograms.toast.deleteFailed'))
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-reading-programs'] })
    },
  })

  const handleCreateProgram = async (data: ReadingProgramCreateData) => {
    await createMutation.mutateAsync(data)
  }

  const handleUpdateProgram = async (data: ReadingProgramCreateData) => {
    if (!editingProgram) return
    await updateMutation.mutateAsync({ id: editingProgram.id, data })
  }

  const handleDeleteProgram = (id: number) => {
    deleteMutation.mutate(id)
  }

  const activePrograms = programs.filter((p) => p.is_active)
  const inactivePrograms = programs.filter((p) => !p.is_active)

  // Check authorization
  if (!isAuthorized) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-lsc-dark dark:via-earth-800 dark:to-lsc-dark py-20">
        <PageContainer className="text-center">
          <AlertCircle className="w-16 h-16 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-4" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Staff-Only Area</h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">{t('admin.adminReadingPrograms.staffOrAdminAccessRequired')}</p>
        </PageContainer>
      </div>
    )
  }
  if (!showForm && !editingProgram) {
    return (
      <AdminShell
        title="Manage Reading Programs"
        subtitle={t('admin.adminReadingPrograms.createEditAndManageLibrary')}
        icon={<BookOpen className="w-7 h-7 text-lsc-rose" />}
        actions={
          <button
            onClick={() => {
              setEditingProgram(null)
              setShowForm(true)
            }}
            className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl flex items-center gap-2 transition-colors font-medium"
          >
            <Plus className="w-5 h-5" />
            Create Program
          </button>
        }
      >
        {/* Loading state */}
        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : error ? (
          <div className="p-4 bg-status-danger-50 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-400 rounded-xl flex gap-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <p>{t('admin.adminReadingPrograms.failedToLoadProgramsPlease')}</p>
          </div>
        ) : programs.length === 0 ? (
          <div className="text-center py-12">
            <BookOpen className="w-16 h-16 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-4" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">No programs found</p>
            <button
              onClick={() => setShowForm(true)}
              className="text-lsc-rose hover:text-lsc-rose/80 font-medium"
            >
              Create the first program →
            </button>
          </div>
        ) : (
          <>
            {/* Active programs */}
            {activePrograms.length > 0 && (
              <div>
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                  <div className="w-2 h-2 bg-lsc-rose rounded-full" />
                  Active Programs ({activePrograms.length})
                </h2>
                <ProgramsTable
                  programs={activePrograms}
                  onEdit={(program) => {
                    setEditingProgram(program)
                    setDeleteConfirm(null)
                    setShowForm(true)
                  }}
                  onDelete={setDeleteConfirm}
                  onManageBooklist={booklistEnabled ? setBooklistManagerProgram : undefined}
                />
              </div>
            )}

            {/* Inactive programs */}
            {inactivePrograms.length > 0 && (
              <div>
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                  <div className="w-2 h-2 bg-lsc-dark/30 dark:bg-lsc-cream/30 rounded-full" />
                  Inactive Programs ({inactivePrograms.length})
                </h2>
                <ProgramsTable
                  programs={inactivePrograms}
                  onEdit={(program) => {
                    setEditingProgram(program)
                    setShowForm(true)
                    setDeleteConfirm(null)
                  }}
                  onDelete={setDeleteConfirm}
                  onManageBooklist={booklistEnabled ? setBooklistManagerProgram : undefined}
                />
              </div>
            )}
          </>
        )}

        {booklistManagerProgram && (
          <AdminProgramBooklistManager
            programId={booklistManagerProgram.id}
            programName={booklistManagerProgram.name}
            onClose={() => setBooklistManagerProgram(null)}
          />
        )}

        {/* Delete confirmation */}
        {deleteConfirm && (
          <ModalBackdrop onClose={() => setDeleteConfirm(null)} title="Delete Program?" role="alertdialog">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full p-6">
              <h2 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">Delete Program?</h2>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                This action cannot be undone. All associated data will be permanently deleted.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setDeleteConfirm(null)}
                  disabled={deleteMutation.isPending}
                  className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream/80 rounded-xl hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleDeleteProgram(deleteConfirm)}
                  disabled={deleteMutation.isPending}
                  className="flex-1 px-4 py-2 bg-status-danger-600 hover:bg-status-danger-700 disabled:bg-status-danger-400 text-white rounded-xl transition-colors flex items-center justify-center gap-2"
                >
                  {deleteMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                      Deleting...
                    </>
                  ) : (
                    'Delete'
                  )}
                </button>
              </div>
            </div>
          </ModalBackdrop>
        )}
      </AdminShell>
    )
  }

  return (
    <AdminShell
      title={editingProgram ? 'Edit Program' : 'Create Program'}
      icon={<BookOpen className="w-7 h-7 text-lsc-rose" />}
      actions={
        <button
          onClick={() => {
            setShowForm(false)
            setEditingProgram(null)
          }}
          className="p-2 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-full transition-colors"
          aria-label={t('aria.authModals.close')}
        >
          <X className="w-5 h-5 text-lsc-dark dark:text-lsc-cream" />
        </button>
      }
    >
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
        <AdminProgramForm
          {...(editingProgram && { program: editingProgram })}
          onSubmit={editingProgram ? handleUpdateProgram : handleCreateProgram}
          onCancel={() => {
            setShowForm(false)
            setEditingProgram(null)
          }}
          isLoading={createMutation.isPending || updateMutation.isPending}
        />
      </div>
    </AdminShell>
  )
}

function ProgramsTable({
  programs,
  onEdit,
  onDelete,
  onManageBooklist,
}: {
  programs: ReadingProgram[]
  onEdit: (program: ReadingProgram) => void
  onDelete: (id: number) => void
  onManageBooklist?: (program: ReadingProgram) => void
}): React.ReactElement {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl overflow-hidden border border-lsc-border dark:border-earth-700">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-lsc-cream dark:bg-lsc-brown">
            <tr>
              <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">Name</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">Dates</th>
              <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">Goal</th>
              <th className="px-6 py-3 text-center text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                <Users className="w-4 h-4 inline" aria-hidden="true" /> Registered
              </th>
              <th className="px-6 py-3 text-center text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                <TrendingUp className="w-4 h-4 inline" aria-hidden="true" /> Activity
              </th>
              <th className="px-6 py-3 text-right text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
            {programs.map((program) => (
              <tr key={program.id} className="hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 transition-colors">
                <td className="px-6 py-4">
                  <div>
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream">{program.name}</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{program.age_group || 'All ages'}</p>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {parseDate(program.start_date)?.toLocaleDateString() ?? '-'} –{' '}
                  {parseDate(program.end_date)?.toLocaleDateString() ?? '-'}
                </td>
                <td className="px-6 py-4 text-sm text-lsc-dark dark:text-lsc-cream">
                  {program.reading_goal_value ? (
                    <>
                      {program.reading_goal_value} {program.reading_goal_type}
                    </>
                  ) : (
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">-</span>
                  )}
                </td>
                <td className="px-6 py-4 text-center text-sm text-lsc-dark dark:text-lsc-cream font-medium">
                  {program.registration_count}
                </td>
                <td className="px-6 py-4 text-center text-sm text-lsc-dark dark:text-lsc-cream">
                  {program.total_minutes_read + program.total_books_read > 0 ? (
                    <span className="text-lsc-rose dark:text-lsc-rose-light font-medium">
                      {program.total_minutes_read} min, {program.total_books_read} books
                    </span>
                  ) : (
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">-</span>
                  )}
                </td>
                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    {onManageBooklist && (
                      <button
                        onClick={() => onManageBooklist(program)}
                        className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 rounded-lg transition-colors"
                        aria-label={`Manage booklist for ${program.name}`}
                      >
                        <List className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={() => onEdit(program)}
                      className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 rounded-lg transition-colors"
                      aria-label={`Edit ${program.name}`}
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => onDelete(program.id)}
                      className="p-2 text-status-danger-600 dark:text-status-danger-400 hover:bg-status-danger-100 dark:hover:bg-status-danger-900/30 rounded-lg transition-colors"
                      aria-label={`Delete ${program.name}`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
