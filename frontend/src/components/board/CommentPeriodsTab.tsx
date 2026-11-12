/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { Calendar, Plus, Play, Square, Trash2 } from 'lucide-react'
import ConfirmDialog from '@/components/ConfirmDialog'
import { useTranslation } from '@/i18n'
import type { CommentPeriod, CommentPeriodCreate } from '../../api/board-public-comments-api'

interface CommentPeriodsTabProps {
  commentPeriods: CommentPeriod[]
  showPeriodForm: boolean
  setShowPeriodForm: (v: boolean) => void
  editingPeriod: CommentPeriod | null
  setEditingPeriod: (v: CommentPeriod | null) => void
  periodForm: CommentPeriodCreate
  setPeriodForm: (v: CommentPeriodCreate) => void
  submitting: boolean
  confirmOpen: boolean
  setConfirmOpen: (v: boolean) => void
  setPendingDeletePeriodId: (v: number | null) => void
  onCreatePeriod: (e: React.FormEvent) => void
  onStartPeriod: (id: number) => void
  onEndPeriod: (id: number) => void
  onDeletePeriod: (id: number) => void
  onDeletePeriodConfirm: () => void
}

const DEFAULT_PERIOD_FORM: CommentPeriodCreate = {
  title: '',
  description: '',
  opens_at: '',
  closes_at: '',
  is_active: true,
  allow_written: true,
  allow_in_person: true,
  allow_virtual: true,
  max_comment_length: 2000,
  speaker_time_limit_seconds: 180,
}

export function CommentPeriodsTab({
  commentPeriods,
  showPeriodForm,
  setShowPeriodForm,
  editingPeriod,
  setEditingPeriod,
  periodForm,
  setPeriodForm,
  submitting,
  confirmOpen,
  setConfirmOpen,
  setPendingDeletePeriodId,
  onCreatePeriod,
  onStartPeriod,
  onEndPeriod,
  onDeletePeriod,
  onDeletePeriodConfirm,
}: CommentPeriodsTabProps) {
  const { t } = useTranslation()

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button
          onClick={() => {
            setEditingPeriod(null)
            setPeriodForm(DEFAULT_PERIOD_FORM)
            setShowPeriodForm(true)
          }}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90"
        >
          <Plus className="w-4 h-4" />
          Add Comment Period
        </button>
      </div>

      {showPeriodForm && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            {editingPeriod ? 'Edit Comment Period' : 'Create Comment Period'}
          </h3>
          <form onSubmit={onCreatePeriod} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium mb-1 dark:text-earth-200">Title *</label>
                <input
                  type="text"
                  value={periodForm.title}
                  onChange={(e) => setPeriodForm({ ...periodForm, title: e.target.value })}
                  required
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900"
                  placeholder={t('placeholder.boardPublicCommentsAdmin.egPremeetingPublicComment')}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1 dark:text-earth-200">Description</label>
                <input
                  type="text"
                  value={periodForm.description || ''}
                  onChange={(e) => setPeriodForm({ ...periodForm, description: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900"
                  placeholder={t('placeholder.boardPublicCommentsAdmin.optionalDescription')}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1 dark:text-earth-200">Opens At *</label>
                <input
                  type="datetime-local"
                  value={periodForm.opens_at}
                  onChange={(e) => setPeriodForm({ ...periodForm, opens_at: e.target.value })}
                  required
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1 dark:text-earth-200">Closes At *</label>
                <input
                  type="datetime-local"
                  value={periodForm.closes_at}
                  onChange={(e) => setPeriodForm({ ...periodForm, closes_at: e.target.value })}
                  required
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1 dark:text-earth-200">Max Comments</label>
                <input
                  type="number"
                  value={periodForm.max_comments || ''}
                  onChange={(e) => {
                    // eslint-disable-next-line @typescript-eslint/no-unused-vars
                    const { max_comments: _max_comments, ...rest } = periodForm
                    setPeriodForm(e.target.value ? { ...rest, max_comments: parseInt(e.target.value) } : rest)
                  }}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900"
                  placeholder={t('placeholder.boardPublicCommentsAdmin.noLimit')}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1 dark:text-earth-200">Max Comment Length</label>
                <input
                  type="number"
                  value={periodForm.max_comment_length || ''}
                  onChange={(e) => {
                    // eslint-disable-next-line @typescript-eslint/no-unused-vars
                    const { max_comment_length: _max_comment_length, ...rest } = periodForm
                    setPeriodForm(e.target.value ? { ...rest, max_comment_length: parseInt(e.target.value) } : rest)
                  }}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900"
                  placeholder={t('placeholder.boardPublicCommentsAdmin.2000')}
                />
              </div>
            </div>
            <div className="flex flex-wrap gap-4">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={periodForm.is_active}
                  onChange={(e) => setPeriodForm({ ...periodForm, is_active: e.target.checked })}
                  className="rounded"
                />
                <span className="text-sm">Active</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={periodForm.allow_written}
                  onChange={(e) => setPeriodForm({ ...periodForm, allow_written: e.target.checked })}
                  className="rounded"
                />
                <span className="text-sm">Allow Written</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={periodForm.allow_in_person}
                  onChange={(e) => setPeriodForm({ ...periodForm, allow_in_person: e.target.checked })}
                  className="rounded"
                />
                <span className="text-sm">Allow In-Person</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={periodForm.allow_virtual}
                  onChange={(e) => setPeriodForm({ ...periodForm, allow_virtual: e.target.checked })}
                  className="rounded"
                />
                <span className="text-sm">Allow Virtual</span>
              </label>
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={submitting}
                className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50"
              >
                {submitting ? 'Saving...' : (editingPeriod ? 'Update' : 'Create')}
              </button>
              <button
                type="button"
                onClick={() => setShowPeriodForm(false)}
                className="px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-earth-700 dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {commentPeriods.length === 0 ? (
        <div className="p-8 text-center bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
          <Calendar className="w-12 h-12 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('boardPublicCommentsAdmin.noCommentPeriodsConfigured')}</p>
        </div>
      ) : (
        commentPeriods.map((period) => {
          const now = new Date()
          const opens = new Date(period.opens_at)
          const closes = new Date(period.closes_at)
          const isOpen = period.is_active && now >= opens && now <= closes
          const isPast = now > closes
          const hasStarted = !!period.actual_start_time
          const hasEnded = !!period.actual_end_time

          return (
            <div
              key={period.id}
              className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6"
            >
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2 flex-wrap">
                    <h3 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream">
                      {period.title}
                    </h3>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                      isOpen ? 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300' :
                      isPast ? 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300' :
                      'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300'
                    }`}>
                      {isOpen ? 'Open' : isPast ? 'Closed' : 'Upcoming'}
                    </span>
                    {hasStarted && !hasEnded && (
                      <span className="px-3 py-1 rounded-full text-xs font-medium bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light">
                        In Progress
                      </span>
                    )}
                  </div>

                  {period.description && (
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mb-3">
                      {period.description}
                    </p>
                  )}

                  <div className="flex flex-wrap gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    <div className="flex items-center gap-2">
                      <Calendar className="w-4 h-4" />
                      {opens.toLocaleString()} - {closes.toLocaleString()}
                    </div>
                    {period.max_comment_length && (
                      <div>Max {period.max_comment_length} chars</div>
                    )}
                    {period.max_comments && (
                      <div>Max {period.max_comments} comments</div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {isOpen && !hasStarted && (
                    <button
                      onClick={() => onStartPeriod(period.id)}
                      className="flex items-center gap-1 px-3 py-1 text-sm bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300 hover:bg-status-success-200 dark:hover:bg-status-success-900/50 rounded-lg"
                    >
                      <Play className="w-4 h-4" />
                      Start
                    </button>
                  )}
                  {hasStarted && !hasEnded && (
                    <button
                      onClick={() => onEndPeriod(period.id)}
                      className="flex items-center gap-1 px-3 py-1 text-sm bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-300 hover:bg-status-danger-200 dark:hover:bg-status-danger-900/50 rounded-lg"
                    >
                      <Square className="w-4 h-4" />
                      End
                    </button>
                  )}
                  <button
                    onClick={() => {
                      setEditingPeriod(period)
                      setPeriodForm({
                        title: period.title,
                        description: period.description || '',
                        opens_at: period.opens_at.slice(0, 16),
                        closes_at: period.closes_at.slice(0, 16),
                        is_active: period.is_active,
                        allow_written: period.allow_written,
                        allow_in_person: period.allow_in_person,
                        allow_virtual: period.allow_virtual,
                        ...(period.max_comments && { max_comments: period.max_comments }),
                        ...(period.max_comment_length && { max_comment_length: period.max_comment_length }),
                        ...(period.speaker_time_limit_seconds && { speaker_time_limit_seconds: period.speaker_time_limit_seconds }),
                      })
                      setShowPeriodForm(true)
                    }}
                    className="flex items-center gap-1 px-3 py-1 text-sm bg-lsc-cream dark:bg-earth-700 rounded-lg dark:text-lsc-cream hover:bg-lsc-cream/80 dark:hover:bg-earth-600"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => onDeletePeriod(period.id)}
                    className="flex items-center gap-1 px-3 py-1 text-sm bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-300 hover:bg-status-danger-200 dark:hover:bg-status-danger-900/50 rounded-lg"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          )
        })
      )}

      <ConfirmDialog
        isOpen={confirmOpen}
        title="Delete comment period?"
        message="Are you sure you want to delete this comment period? This cannot be undone."
        confirmText="Delete"
        confirmVariant="danger"
        onConfirm={onDeletePeriodConfirm}
        onCancel={() => { setConfirmOpen(false); setPendingDeletePeriodId(null) }}
      />
    </div>
  )
}
