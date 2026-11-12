/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Megaphone,
  Plus,
  Edit,
  Trash2,
  Eye,
  Archive,
  Filter,
  ChevronDown,
  Loader2,
  X,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  getAnnouncements,
  createAnnouncement,
  updateAnnouncement,
  deleteAnnouncement,
  toggleAnnouncement,
  type Announcement,
  type AnnouncementCreateData,
} from '@/api/announcements-api'
import { useAuth } from '@/contexts/AuthContext'
import ConfirmDialog from '@/components/ConfirmDialog'
import { useTranslation} from '@/i18n'
import { clean } from '@/lib/utils'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import PageContainer from '@/components/layout/PageContainer'

const PRIORITY_KEYS = {
  normal: 'announcements.priorityNormal',
  important: 'announcements.priorityImportant',
  urgent: 'announcements.priorityUrgent',
} as const

export default function AnnouncementsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const location = useLocation()
  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin'

  const [page, setPage] = useState(1)
  const [priorityFilter, setPriorityFilter] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [editingAnnouncement, setEditingAnnouncement] = useState<Announcement | null>(null)
  const [selectedAnnouncement, setSelectedAnnouncement] = useState<Announcement | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<Announcement | null>(null)

  // Form state
  const [formData, setFormData] = useState<AnnouncementCreateData>({
    title: '',
    content: '',
    priority: 'normal',
    ends_at: '',
  })

  // Queries
  const { data: announcementsData, isLoading } = useQuery({
    queryKey: ['announcements', page, priorityFilter, isAdmin],
    queryFn: () => getAnnouncements(clean({
      ...(priorityFilter ? { priority: priorityFilter } : {}),
      active_only: !isAdmin,
      page,
      per_page: 10,
    })),
  })

  // Scroll to a specific announcement when arrived via hash anchor
  // (e.g. /announcements#announcement-42 from site search results).
  // Wait until data is loaded so the target element actually exists.
  useEffect(() => {
    if (isLoading || !announcementsData?.items?.length) return
    const hash = location.hash
    if (!hash || !hash.startsWith('#announcement-')) return
    const targetId = hash.slice(1)
    const el = document.getElementById(targetId)
    if (!el) return
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    el.focus({ preventScroll: true })
  }, [isLoading, announcementsData, location.hash])

  // Mutations
  const createMutation = useMutation({
    mutationFn: createAnnouncement,
    onSuccess: () => {
      toast.success(t('toast.announcements.announcementCreated'))
      queryClient.invalidateQueries({ queryKey: ['announcements'] })
      setShowModal(false)
      resetForm()
    },
    onError: () => toast.error(t('announcements.failedToCreateAnnouncement')),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<AnnouncementCreateData> }) => updateAnnouncement(id, data),
    onSuccess: () => {
      toast.success(t('toast.announcements.announcementUpdated'))
      queryClient.invalidateQueries({ queryKey: ['announcements'] })
      setShowModal(false)
      setEditingAnnouncement(null)
      resetForm()
    },
    onError: () => toast.error(t('announcements.failedToUpdateAnnouncement')),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteAnnouncement,
    onMutate: async (deletedId) => {
      await queryClient.cancelQueries({ queryKey: ['announcements'] })
      const queryKey = ['announcements', page, priorityFilter, isAdmin]
      const previous = queryClient.getQueryData<{ items: Announcement[]; total: number; page: number }>(queryKey)
      if (previous) {
        queryClient.setQueryData(queryKey, {
          ...previous,
          items: previous.items.filter(a => a.id !== deletedId),
          total: previous.total - 1,
        })
      }
      return { previous, queryKey }
    },
    onSuccess: () => {
      toast.success(t('toast.announcements.announcementDeleted'))
      setDeleteConfirm(null)
    },
    onError: (_err, _id, context) => {
      if (context?.previous) {
        queryClient.setQueryData(context.queryKey, context.previous)
      }
      toast.error(t('announcements.failedToDeleteAnnouncement'))
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['announcements'] })
    },
  })

  const toggleMutation = useMutation({
    mutationFn: toggleAnnouncement,
    onSuccess: (data) => {
      toast.success(data?.active ? t('announcements.announcementActivated') : t('announcements.announcementDeactivated'))
      queryClient.invalidateQueries({ queryKey: ['announcements'] })
    },
    onError: () => toast.error(t('announcements.failedToUpdateAnnouncement')),
  })

  const resetForm = () => {
    setFormData({
      title: '',
      content: '',
      priority: 'normal',
      ends_at: '',
    })
  }

  const openEditModal = (announcement: Announcement) => {
    setEditingAnnouncement(announcement)
    setFormData({
      title: announcement.title,
      content: announcement.content,
      priority: announcement.priority,
      ends_at: announcement.ends_at?.split('T')[0] || '',
    })
    setShowModal(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (editingAnnouncement) {
      updateMutation.mutate({ id: editingAnnouncement.id, data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const getPriorityBadge = (priority: string) => {
    const colors: Record<string, string> = {
      normal: 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light',
      important: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
      urgent: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
    }
    return colors[priority] || colors.normal
  }

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900">
      <PageContainer className="py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-3">
              <Megaphone className="w-8 h-8 text-lsc-rose" />
              {t('announcements.title')}
            </h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('announcements.libraryNewsAndUpdates')}</p>
          </div>
          {isAdmin && (
            <button
              onClick={() => { resetForm(); setEditingAnnouncement(null); setShowModal(true) }}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90"
            >
              <Plus className="w-4 h-4" />
              {t('announcements.newAnnouncement')}
            </button>
          )}
        </div>

        {/* Filters */}
        <div className="mb-6">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-900 dark:hover:text-earth-100"
          >
            <Filter className="w-4 h-4" />
            {t('announcements.filterByPriority')}
            <ChevronDown className={`w-4 h-4 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
          </button>
          {showFilters && (
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                onClick={() => setPriorityFilter('')}
                className={`px-3 py-1 rounded-full text-sm ${
                  !priorityFilter ? 'bg-lsc-rose text-white' : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70'
                }`}
              >
                {t('common.all')}
              </button>
              {(['normal', 'important', 'urgent'] as const).map((value) => (
                <button
                  key={value}
                  onClick={() => setPriorityFilter(value)}
                  className={`px-3 py-1 rounded-full text-sm ${
                    priorityFilter === value
                      ? 'bg-lsc-rose text-white'
                      : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70'
                  }`}
                >
                  {t(PRIORITY_KEYS[value])}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Announcements List */}
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : (
          <div className="space-y-4">
            {announcementsData?.items.map((announcement) => (
              <div
                key={announcement.id}
                id={`announcement-${announcement.id}`}
                tabIndex={-1}
                className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-6 scroll-mt-20 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getPriorityBadge(announcement.priority)}`}>
                        {t(PRIORITY_KEYS[announcement.priority as keyof typeof PRIORITY_KEYS] || PRIORITY_KEYS.normal)}
                      </span>
                      {isAdmin && (
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          announcement.active
                            ? 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400'
                            : 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300'
                        }`}>
                          {announcement.active ? t('announcements.active') : t('announcements.inactive')}
                        </span>
                      )}
                    </div>
                    {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
                    <h2
                      className="font-serif text-xl font-semibold text-lsc-dark dark:text-lsc-cream cursor-pointer hover:text-lsc-rose"
                      onClick={() => setSelectedAnnouncement(announcement)}
                    >
                      {announcement.title}
                    </h2>
                    <div className="mt-3 flex items-center gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      <span>{new Date(announcement.created_at).toLocaleDateString()}</span>
                      {announcement.ends_at && (
                        <span>{t('announcements.expires')}: {new Date(announcement.ends_at).toLocaleDateString()}</span>
                      )}
                    </div>
                  </div>
                  {isAdmin && (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => toggleMutation.mutate(announcement.id)}
                        className={`p-2 rounded-lg ${
                          announcement.active
                            ? 'text-status-warning-600 hover:bg-status-warning-50 dark:hover:bg-status-warning-900/20'
                            : 'text-status-success-600 hover:bg-status-success-50 dark:hover:bg-status-success-900/20'
                        }`}
                        title={announcement.active ? t('announcements.deactivate') : t('announcements.activate')}
                      >
                        {announcement.active ? (
                          <Archive className="w-4 h-4" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                      </button>
                      <button
                        onClick={() => openEditModal(announcement)}
                        className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-700 rounded-lg"
                        title={t('common.edit')}
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setDeleteConfirm(announcement)}
                        className="p-2 text-status-danger-500 hover:bg-status-danger-50 dark:bg-status-danger-900/20 dark:hover:bg-status-danger-900/20 rounded-lg"
                        title={t('common.delete')}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {announcementsData?.items.length === 0 && (
              <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
                <Megaphone className="w-12 h-12 text-earth-300 dark:text-earth-300 mx-auto mb-4" />
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('announcements.noAnnouncementsFound')}</p>
              </div>
            )}
          </div>
        )}

        {/* Pagination */}
        {announcementsData && announcementsData.total > 10 && (
          <div className="mt-6 flex items-center justify-between">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('announcements.pageOf', { current: page, total: Math.ceil(announcementsData.total / 10) })}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(page - 1)}
                disabled={page === 1}
                className="px-3 py-1 rounded bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 disabled:opacity-50"
              >
                {t('common.previous')}
              </button>
              <button
                onClick={() => setPage(page + 1)}
                disabled={page * 10 >= announcementsData.total}
                className="px-3 py-1 rounded bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 disabled:opacity-50"
              >
                {t('common.next')}
              </button>
            </div>
          </div>
        )}

        {/* Create/Edit Modal */}
        {showModal && (
          <ModalBackdrop onClose={() => { setShowModal(false); setEditingAnnouncement(null) }} title="Dialog">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-hidden">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                  {editingAnnouncement ? t('announcements.editAnnouncement') : t('announcements.newAnnouncement')}
                </h3>
                <button onClick={() => { setShowModal(false); setEditingAnnouncement(null) }} className="text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-200">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <form onSubmit={handleSubmit} className="p-4 space-y-4 overflow-y-auto max-h-[70vh]">
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('announcements.titleField')} *</label>
                  <input
                    type="text"
                    value={formData.title}
                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                    required
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('announcements.contentField')} *</label>
                  <textarea
                    value={formData.content}
                    onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                    required
                    rows={6}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('announcements.priority')}</label>
                  <select
                    value={formData.priority}
                    onChange={(e) => setFormData({ ...formData, priority: e.target.value as 'normal' | 'important' | 'urgent' })}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  >
                    {(['normal', 'important', 'urgent'] as const).map((value) => (
                      <option key={value} value={value}>{t(PRIORITY_KEYS[value])}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{t('announcements.expirationDate')}</label>
                  <input
                    type="date"
                    value={formData.ends_at}
                    onChange={(e) => setFormData({ ...formData, ends_at: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
              </form>
              <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => { setShowModal(false); setEditingAnnouncement(null) }}
                  className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
                >
                  {t('common.cancel')}
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={createMutation.isPending || updateMutation.isPending}
                  className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50"
                >
                  {createMutation.isPending || updateMutation.isPending ? (
                    <Loader2 className="w-5 h-5 motion-safe:animate-spin" />
                  ) : editingAnnouncement ? t('announcements.update') : t('announcements.create')}
                </button>
              </div>
            </div>
          </ModalBackdrop>
        )}

        {/* View Detail Modal */}
        {selectedAnnouncement && (
          <ModalBackdrop onClose={() => setSelectedAnnouncement(null)} title="Dialog">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-hidden">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getPriorityBadge(selectedAnnouncement.priority)}`}>
                  {t(PRIORITY_KEYS[selectedAnnouncement.priority as keyof typeof PRIORITY_KEYS] || PRIORITY_KEYS.normal)}
                </span>
                <button onClick={() => setSelectedAnnouncement(null)} className="text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-200">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="p-6 overflow-y-auto max-h-[70vh]">
                <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">{selectedAnnouncement.title}</h2>
                <div className="prose dark:prose-invert max-w-none">
                  <p className="whitespace-pre-wrap text-lsc-dark/70 dark:text-lsc-cream/70">{selectedAnnouncement.content}</p>
                </div>
                <div className="mt-6 pt-4 border-t border-lsc-border dark:border-earth-700 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  <p>{t('announcements.posted')}: {new Date(selectedAnnouncement.created_at).toLocaleString()}</p>
                  {selectedAnnouncement.ends_at && (
                    <p>{t('announcements.expires')}: {new Date(selectedAnnouncement.ends_at).toLocaleDateString()}</p>
                  )}
                </div>
              </div>
            </div>
          </ModalBackdrop>
        )}

        {/* Delete Confirmation */}
        <ConfirmDialog
          isOpen={!!deleteConfirm}
          onClose={() => setDeleteConfirm(null)}
          onConfirm={() => { if (deleteConfirm) deleteMutation.mutate(deleteConfirm.id) }}
          title={t('announcements.deleteAnnouncement')}
          message={t('announcements.deleteConfirmMessage', { title: deleteConfirm?.title })}
          confirmLabel={t('common.delete')}
          confirmVariant="danger"
        />
      </PageContainer>
    </div>
  )
}
