/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  Plus,
  Search,
  Edit2,
  Power,
  PowerOff,
  Loader2,
  AlertCircle,
  ExternalLink,
  Users,
  X,
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useTranslation } from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import ProgramPartnerForm from '../components/ProgramPartnerForm'
import {
  listProgramPartners,
  createProgramPartner,
  updateProgramPartner,
  deleteProgramPartner,
  type EventProgramPartner,
  type EventProgramPartnerCreate,
  type EventProgramPartnerUpdate,
} from '@/api/domains/services/program-partners-api'
import PageContainer from '@/components/layout/PageContainer'

const PER_PAGE = 20

export default function StaffProgramPartnersPage(): React.ReactElement {
  const { t } = useTranslation()
  const { token } = useAuth()
  const queryClient = useQueryClient()

  const [searchInput, setSearchInput] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [includeInactive, setIncludeInactive] = useState(false)
  const [page, setPage] = useState(1)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<EventProgramPartner | null>(null)
  const [confirmDeactivate, setConfirmDeactivate] = useState<EventProgramPartner | null>(null)

  useEffect(() => {
    const handle = setTimeout(() => {
      setDebouncedSearch(searchInput.trim())
      setPage(1)
    }, 300)
    return () => clearTimeout(handle)
  }, [searchInput])

  const queryKey = useMemo(
    () => ['program-partners', debouncedSearch, includeInactive, page],
    [debouncedSearch, includeInactive, page],
  )

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey,
    queryFn: () =>
      listProgramPartners({
        search: debouncedSearch || undefined,
        include_inactive: includeInactive || undefined,
        page,
        per_page: PER_PAGE,
      }, token ?? undefined),
  })

  const createMutation = useMutation({
    mutationFn: (payload: EventProgramPartnerCreate) =>
      createProgramPartner(token!, payload),
    onSuccess: () => {
      toast.success(t('programPartners.toast.created', 'Partner organization created'))
      queryClient.invalidateQueries({ queryKey: ['program-partners'] })
      setShowForm(false)
      setEditing(null)
    },
    onError: (e: Error) => {
      toast.error(e.message || t('programPartners.toast.createFailed', 'Could not create partner organization'))
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: EventProgramPartnerUpdate }) =>
      updateProgramPartner(token!, id, payload),
    onSuccess: () => {
      toast.success(t('programPartners.toast.updated', 'Partner organization updated'))
      queryClient.invalidateQueries({ queryKey: ['program-partners'] })
      setShowForm(false)
      setEditing(null)
    },
    onError: (e: Error) => {
      toast.error(e.message || t('programPartners.toast.updateFailed', 'Could not update partner organization'))
    },
  })

  const deactivateMutation = useMutation({
    mutationFn: (id: number) => deleteProgramPartner(token!, id, false),
    onSuccess: () => {
      toast.success(t('programPartners.toast.deactivated', 'Partner organization deactivated'))
      queryClient.invalidateQueries({ queryKey: ['program-partners'] })
      setConfirmDeactivate(null)
    },
    onError: (e: Error) => {
      toast.error(e.message || t('programPartners.toast.deactivateFailed', 'Could not deactivate partner organization'))
    },
  })

  const reactivateMutation = useMutation({
    mutationFn: (id: number) =>
      updateProgramPartner(token!, id, { is_active: true }),
    onSuccess: () => {
      toast.success(t('programPartners.toast.reactivated', 'Partner organization reactivated'))
      queryClient.invalidateQueries({ queryKey: ['program-partners'] })
    },
    onError: (e: Error) => {
      toast.error(e.message || t('programPartners.toast.reactivateFailed', 'Could not reactivate partner organization'))
    },
  })

  const handleSubmit = async (payload: EventProgramPartnerCreate | EventProgramPartnerUpdate) => {
    if (editing) {
      await updateMutation.mutateAsync({ id: editing.id, payload })
    } else {
      await createMutation.mutateAsync(payload as EventProgramPartnerCreate)
    }
  }

  const handleCloseForm = () => {
    setShowForm(false)
    setEditing(null)
  }

  const formatDateTime = (s: string) => {
    const d = new Date(s)
    return d.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  const rows = data?.data ?? []
  const pagination = data?.pagination
  const showEmptyState = !isLoading && !isError && rows.length === 0 && !debouncedSearch && !includeInactive
  const showNoResults = !isLoading && !isError && rows.length === 0 && (debouncedSearch || includeInactive)

  return (
    <AdminShell
      title={t('programPartners.pageTitle', 'Programming Partners')}
      subtitle={t('programPartners.subtitle', 'Manage partner organizations for library events.')}
    >
      <PageContainer width="wide" className="py-6">
        {/* Top bar */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 mb-6 flex flex-col md:flex-row gap-4 md:items-center">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder={t('programPartners.searchPlaceholder', 'Search by name...')}
              aria-label={t('programPartners.searchAria', 'Search partner organizations by name')}
              className="w-full pl-10 pr-4 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
            <input
              type="checkbox"
              checked={includeInactive}
              onChange={(e) => {
                setIncludeInactive(e.target.checked)
                setPage(1)
              }}
              className="h-4 w-4"
            />
            {t('programPartners.showInactive', 'Show inactive')}
          </label>
          <button
            type="button"
            onClick={() => {
              setEditing(null)
              setShowForm(true)
            }}
            className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl flex items-center gap-2 transition-colors focus:ring-2 focus:ring-lsc-rose"
          >
            <Plus className="w-5 h-5" />
            {t('programPartners.addButton', 'Add partner')}
          </button>
        </div>

        {/* States */}
        {isError ? (
          <div
            role="alert"
            className="bg-status-danger-50 dark:bg-status-danger-900/30 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-4 mb-6 flex items-start gap-3"
          >
            <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 mt-0.5" />
            <div className="flex-1">
              <p className="text-status-danger-800 dark:text-status-danger-100 font-medium">
                {t('programPartners.error.title', 'Could not load partner organizations')}
              </p>
              {error instanceof Error && (
                <p className="text-status-danger-700 dark:text-status-danger-200 text-sm mt-1">
                  {error.message}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={() => refetch()}
              className="px-3 py-1.5 bg-status-danger-600 hover:bg-status-danger-700 text-white rounded-xl text-sm"
            >
              {t('programPartners.error.retry', 'Retry')}
            </button>
          </div>
        ) : isLoading ? (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl overflow-hidden">
            <div className="p-4 space-y-3" aria-busy="true" aria-label={t('programPartners.loading', 'Loading partner organizations')}>
              {[0, 1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="h-10 bg-lsc-cream dark:bg-lsc-brown/50 rounded motion-safe:animate-pulse"
                />
              ))}
            </div>
          </div>
        ) : showEmptyState ? (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-10 text-center">
            <Users className="w-12 h-12 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-3" />
            <p className="text-lsc-dark dark:text-lsc-cream font-medium mb-2">
              {t('programPartners.empty.title', 'No partner organizations yet')}
            </p>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mb-4">
              {t('programPartners.empty.body', 'Add your first programming partner to use them on event records.')}
            </p>
            <button
              type="button"
              onClick={() => {
                setEditing(null)
                setShowForm(true)
              }}
              className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl inline-flex items-center gap-2"
            >
              <Plus className="w-5 h-5" />
              {t('programPartners.empty.cta', 'Add your first partner')}
            </button>
          </div>
        ) : showNoResults ? (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-8 text-center">
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('programPartners.noResults', 'No partner organizations match your filters.')}
            </p>
          </div>
        ) : (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full" aria-label={t('programPartners.tableAria', 'Partner organizations')}>
                <thead className="bg-lsc-cream dark:bg-lsc-brown">
                  <tr>
                    <th scope="col" className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      {t('programPartners.col.name', 'Name')}
                    </th>
                    <th scope="col" className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      {t('programPartners.col.email', 'Contact email')}
                    </th>
                    <th scope="col" className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      {t('programPartners.col.phone', 'Contact phone')}
                    </th>
                    <th scope="col" className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      {t('programPartners.col.website', 'Website')}
                    </th>
                    <th scope="col" className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      {t('programPartners.col.status', 'Status')}
                    </th>
                    <th scope="col" className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      {t('programPartners.col.updated', 'Last updated')}
                    </th>
                    <th scope="col" className="px-4 py-3 text-right text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      {t('programPartners.col.actions', 'Actions')}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                  {rows.map((partner) => (
                    <tr key={partner.id} className="hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 transition-colors">
                      <td className="px-4 py-3">
                        <p className="font-medium text-lsc-dark dark:text-lsc-cream">{partner.name}</p>
                      </td>
                      <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {partner.contact_email ? (
                          <a className="hover:underline" href={`mailto:${partner.contact_email}`}>
                            {partner.contact_email}
                          </a>
                        ) : '-'}
                      </td>
                      <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {partner.contact_phone || '-'}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {partner.website ? (
                          <a
                            href={partner.website}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-lsc-rose hover:underline inline-flex items-center gap-1"
                          >
                            {partner.website}
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        ) : '-'}
                      </td>
                      <td className="px-4 py-3">
                        {partner.is_active ? (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium text-lsc-rose dark:text-lsc-rose-light bg-lsc-cream dark:bg-lsc-dark/30">
                            {t('programPartners.badge.active', 'Active')}
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 bg-lsc-cream dark:bg-earth-800">
                            {t('programPartners.badge.inactive', 'Inactive')}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {formatDateTime(partner.updated_at)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              setEditing(partner)
                              setShowForm(true)
                            }}
                            className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/90 rounded-xl transition-colors"
                            aria-label={t('programPartners.actions.editAria', { name: partner.name })}
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          {partner.is_active ? (
                            <button
                              type="button"
                              onClick={() => setConfirmDeactivate(partner)}
                              className="p-2 text-status-danger-600 dark:text-status-danger-400 hover:bg-status-danger-100 dark:hover:bg-status-danger-900/30 rounded-xl transition-colors"
                              aria-label={t('programPartners.actions.deactivateAria', { name: partner.name })}
                            >
                              <PowerOff className="w-4 h-4" />
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={() => reactivateMutation.mutate(partner.id)}
                              disabled={reactivateMutation.isPending}
                              className="p-2 text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/90 rounded-xl transition-colors"
                              aria-label={t('programPartners.actions.reactivateAria', { name: partner.name })}
                            >
                              <Power className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {pagination && pagination.total_pages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-lsc-border dark:border-earth-700">
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('programPartners.pagination.summary', {
                    page: pagination.page,
                    total: pagination.total_pages,
                  })}
                </p>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={!pagination.has_previous || isFetching}
                    className="px-3 py-1.5 border border-lsc-border dark:border-earth-700 rounded-xl text-sm text-lsc-dark dark:text-lsc-cream disabled:opacity-50"
                  >
                    {t('programPartners.pagination.prev', 'Previous')}
                  </button>
                  <button
                    type="button"
                    onClick={() => setPage((p) => p + 1)}
                    disabled={!pagination.has_next || isFetching}
                    className="px-3 py-1.5 border border-lsc-border dark:border-earth-700 rounded-xl text-sm text-lsc-dark dark:text-lsc-cream disabled:opacity-50"
                  >
                    {t('programPartners.pagination.next', 'Next')}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </PageContainer>

      {showForm && (
        <ModalBackdrop
          onClose={handleCloseForm}
          title={
            editing
              ? t('programPartners.form.editTitle', 'Edit partner organization')
              : t('programPartners.form.createTitle', 'Add partner organization')
          }
        >
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-xl w-full" style={{ maxHeight: '90vh', overflowY: 'auto' }}>
            <div className="flex items-center justify-between p-4 border-b border-lsc-border dark:border-earth-700 sticky top-0 bg-lsc-white dark:bg-earth-800 z-10">
              <h2 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                {editing
                  ? t('programPartners.form.editTitle', 'Edit partner organization')
                  : t('programPartners.form.createTitle', 'Add partner organization')}
              </h2>
              <button
                type="button"
                onClick={handleCloseForm}
                className="p-1 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-full transition-colors"
                aria-label={t('programPartners.form.closeAria', 'Close form')}
              >
                <X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
              </button>
            </div>
            <div className="p-4">
              <ProgramPartnerForm
                mode={editing ? 'edit' : 'create'}
                initial={editing ?? undefined}
                onSubmit={handleSubmit}
                onCancel={handleCloseForm}
                isSubmitting={createMutation.isPending || updateMutation.isPending}
              />
            </div>
          </div>
        </ModalBackdrop>
      )}

      {confirmDeactivate && (
        <ModalBackdrop
          onClose={() => setConfirmDeactivate(null)}
          title={t('programPartners.deactivate.title', 'Deactivate partner organization')}
          role="alertdialog"
        >
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full">
            <div className="p-6">
              <h2 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                {t('programPartners.deactivate.title', 'Deactivate partner organization')}
              </h2>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                {t('programPartners.deactivate.body', { name: confirmDeactivate.name })}
              </p>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setConfirmDeactivate(null)}
                  disabled={deactivateMutation.isPending}
                  className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream/80 rounded-xl hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors disabled:opacity-50"
                >
                  {t('programPartners.deactivate.cancel', 'Cancel')}
                </button>
                <button
                  type="button"
                  onClick={() => deactivateMutation.mutate(confirmDeactivate.id)}
                  disabled={deactivateMutation.isPending}
                  className="flex-1 px-4 py-2 bg-status-danger-600 hover:bg-status-danger-700 disabled:bg-status-danger-400 text-white rounded-xl transition-colors flex items-center justify-center gap-2"
                >
                  {deactivateMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                      {t('programPartners.deactivate.working', 'Deactivating...')}
                    </>
                  ) : (
                    t('programPartners.deactivate.confirm', 'Deactivate')
                  )}
                </button>
              </div>
            </div>
          </div>
        </ModalBackdrop>
      )}
    </AdminShell>
  )
}
