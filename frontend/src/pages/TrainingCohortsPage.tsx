/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Users,
  Plus,
  Edit,
  Trash2,
  UserPlus,
  UserMinus,
  BookOpen,
  Calendar,
  Loader2,
  X,
  ChevronRight,
  GraduationCap,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  getCohorts,
  getCohort,
  createCohort,
  updateCohort,
  deleteCohort,
  addCohortMember,
  removeCohortMember,
  removeCohortTraining,
  type Cohort,
  type CohortCreateData,
  type CohortMember,
  type CohortTraining,
} from '@/api/api'
import ConfirmDialog from '@/components/ConfirmDialog'
import { useTranslation} from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import PageContainer from '@/components/layout/PageContainer'

export default function TrainingCohortsPage(): React.ReactElement {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const [statusFilter, setStatusFilter] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editingCohort, setEditingCohort] = useState<Cohort | null>(null)
  const [selectedCohort, setSelectedCohort] = useState<Cohort | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<Cohort | null>(null)
  const [showAddMemberModal, setShowAddMemberModal] = useState(false)
  const [newMemberUserId, setNewMemberUserId] = useState('')
  const [newMemberRole, setNewMemberRole] = useState<'member' | 'facilitator'>('member')

  // Form state
  const [formData, setFormData] = useState<CohortCreateData>({
    name: '',
    description: '',
    start_date: '',
    end_date: '',
  })

  // Queries
  const { data: cohortsData, isLoading } = useQuery({
    queryKey: ['cohorts', statusFilter],
    queryFn: () => getCohorts({ ...(statusFilter ? { status: statusFilter } : {}),}),
  })

  const { data: cohortDetail, isLoading: loadingDetail } = useQuery({
    queryKey: ['cohort', selectedCohort?.id],
    queryFn: () => getCohort(selectedCohort!.id),
    enabled: !!selectedCohort,
  })

  // Mutations
  const createMutation = useMutation({
    mutationFn: createCohort,
    onSuccess: () => {
      toast.success(t('toast.trainingCohorts.cohortCreated'))
      queryClient.invalidateQueries({ queryKey: ['cohorts'] })
      setShowModal(false)
      resetForm()
    },
    onError: () => toast.error(t('trainingCohorts.failedToCreateCohort')),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<CohortCreateData> }) => updateCohort(id, data),
    onSuccess: () => {
      toast.success(t('toast.trainingCohorts.cohortUpdated'))
      queryClient.invalidateQueries({ queryKey: ['cohorts'] })
      queryClient.invalidateQueries({ queryKey: ['cohort'] })
      setShowModal(false)
      setEditingCohort(null)
      resetForm()
    },
    onError: () => toast.error(t('trainingCohorts.failedToUpdateCohort')),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteCohort,
    onSuccess: () => {
      toast.success(t('toast.trainingCohorts.cohortDeleted'))
      queryClient.invalidateQueries({ queryKey: ['cohorts'] })
      setDeleteConfirm(null)
      setSelectedCohort(null)
    },
    onError: () => toast.error(t('trainingCohorts.failedToDeleteCohort')),
  })

  const addMemberMutation = useMutation({
    mutationFn: ({ cohortId, data }: { cohortId: number; data: { user_id: number; role?: string } }) =>
      addCohortMember(cohortId, data),
    onSuccess: () => {
      toast.success(t('toast.trainingCohorts.memberAdded'))
      queryClient.invalidateQueries({ queryKey: ['cohort', selectedCohort?.id] })
      setShowAddMemberModal(false)
      setNewMemberUserId('')
      setNewMemberRole('member')
    },
    onError: () => toast.error(t('trainingCohorts.failedToAddMember')),
  })

  const removeMemberMutation = useMutation({
    mutationFn: ({ cohortId, userId }: { cohortId: number; userId: number }) =>
      removeCohortMember(cohortId, userId),
    onSuccess: () => {
      toast.success(t('toast.trainingCohorts.memberRemoved'))
      queryClient.invalidateQueries({ queryKey: ['cohort', selectedCohort?.id] })
    },
    onError: () => toast.error(t('trainingCohorts.failedToRemoveMember')),
  })

  const removeTrainingMutation = useMutation({
    mutationFn: ({ cohortId, trainingId }: { cohortId: number; trainingId: number }) =>
      removeCohortTraining(cohortId, trainingId),
    onSuccess: () => {
      toast.success(t('toast.trainingCohorts.trainingRemoved'))
      queryClient.invalidateQueries({ queryKey: ['cohort', selectedCohort?.id] })
    },
    onError: () => toast.error(t('trainingCohorts.failedToRemoveTraining')),
  })

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      start_date: '',
      end_date: '',
    })
  }

  const openEditModal = (cohort: Cohort) => {
    setEditingCohort(cohort)
    setFormData({
      name: cohort.name,
      description: cohort.description || '',
      start_date: cohort.start_date.split('T')[0] ?? '',
      end_date: cohort.end_date?.split('T')[0] ?? '',
      ...(cohort.max_members ? { max_members: cohort.max_members } : {}),
    })
    setShowModal(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (editingCohort) {
      updateMutation.mutate({ id: editingCohort.id, data: formData })
    } else {
      createMutation.mutate(formData)
    }
  }

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      planned: 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300',
      active: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
      completed: 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light',
      cancelled: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
    }
    return colors[status] || colors.planned
  }

  return (

    <AdminShell title="Training Cohorts">    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900">
      <PageContainer width="wide" className="py-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-3">
              <Users className="w-8 h-8 text-lsc-rose" />
              Training Cohorts
            </h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('trainingCohorts.manageStaffTrainingGroupsAnd')}</p>
          </div>
          <button
            onClick={() => { resetForm(); setEditingCohort(null); setShowModal(true) }}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90"
          >
            <Plus className="w-4 h-4" />
            New Cohort
          </button>
        </div>

        {/* Filters */}
        <div className="mb-6">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
          >
            <option value="">All Statuses</option>
            <option value="planned">Planned</option>
            <option value="active">Active</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Cohorts List */}
          <div className="lg:col-span-1">
            {isLoading ? (
              <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
              </div>
            ) : (
              <div className="space-y-3">
                {cohortsData?.items.map((cohort) => (
                  <div
                    key={cohort.id}
                    onClick={() => setSelectedCohort(cohort)} tabIndex={0} role="button" onKeyDown={(e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); (() => setSelectedCohort(cohort))(); } }}
                    className={`bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border p-4 cursor-pointer transition-all ${
                      selectedCohort?.id === cohort.id
                        ? 'border-lsc-rose ring-2 ring-lsc-rose/20'
                        : 'border-lsc-border dark:border-earth-700 hover:border-lsc-rose/50'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{cohort.name}</h3>
                        <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium ${getStatusBadge(cohort.status)}`}>
                          {cohort.status}
                        </span>
                      </div>
                      <ChevronRight className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                    </div>
                    <div className="mt-3 flex items-center gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      <span className="flex items-center gap-1">
                        <Users className="w-4 h-4" />
                        {cohort.member_count}{cohort.max_members ? `/${cohort.max_members}` : ''}
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar className="w-4 h-4" />
                        {new Date(cohort.start_date).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                ))}

                {cohortsData?.items.length === 0 && (
                  <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
                    No cohorts found.
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Cohort Detail */}
          <div className="lg:col-span-2">
            {selectedCohort ? (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700">
                {loadingDetail ? (
                  <div className="flex items-center justify-center h-64">
                    <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
                  </div>
                ) : cohortDetail ? (
                  <>
                    <div className="p-6 border-b border-lsc-border dark:border-earth-700">
                      <div className="flex items-start justify-between">
                        <div>
                          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">{cohortDetail.name}</h2>
                          <span className={`inline-block mt-2 px-2 py-0.5 rounded-full text-xs font-medium ${getStatusBadge(cohortDetail.status)}`}>
                            {cohortDetail.status}
                          </span>
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={() => openEditModal(cohortDetail)}
                            className="p-2 text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-200 rounded-lg hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-700"
                          >
                            <Edit className="w-5 h-5" />
                          </button>
                          <button
                            onClick={() => setDeleteConfirm(cohortDetail)}
                            className="p-2 text-status-danger-500 hover:text-status-danger-700 dark:text-status-danger-300 rounded-lg hover:bg-status-danger-50 dark:bg-status-danger-900/20 dark:hover:bg-status-danger-900/20"
                          >
                            <Trash2 className="w-5 h-5" />
                          </button>
                        </div>
                      </div>
                      {cohortDetail.description && (
                        <p className="mt-3 text-lsc-dark/70 dark:text-lsc-cream/70">{cohortDetail.description}</p>
                      )}
                      <div className="mt-4 flex items-center gap-6 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-4 h-4" />
                          {new Date(cohortDetail.start_date).toLocaleDateString()}
                          {cohortDetail.end_date && ` - ${new Date(cohortDetail.end_date).toLocaleDateString()}`}
                        </span>
                      </div>
                    </div>

                    {/* Members Section */}
                    <div className="p-6 border-b border-lsc-border dark:border-earth-700">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                          <Users className="w-5 h-5 text-lsc-rose" />
                          Members ({cohortDetail.members.length})
                        </h3>
                        <button
                          onClick={() => setShowAddMemberModal(true)}
                          className="flex items-center gap-1 px-3 py-1 rounded-lg bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-200 dark:hover:bg-earth-600 text-sm"
                        >
                          <UserPlus className="w-4 h-4" />
                          Add
                        </button>
                      </div>
                      {cohortDetail.members.length > 0 ? (
                        <div className="space-y-2">
                          {cohortDetail.members.map((member: CohortMember) => (
                            <div key={member.user_id} className="flex items-center justify-between p-3 bg-earth-50 dark:bg-earth-700/50 rounded-lg">
                              <div>
                                <p className="font-medium text-lsc-dark dark:text-lsc-cream">{member.user_name}</p>
                                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{member.email}</p>
                              </div>
                              <div className="flex items-center gap-3">
                                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                                  member.role === 'facilitator'
                                    ? 'bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-400'
                                    : 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300'
                                }`}>
                                  {member.role}
                                </span>
                                <div className="w-16 bg-earth-200 dark:bg-earth-600 rounded-full h-2">
                                  <div
                                    className="bg-lsc-rose h-2 rounded-full"
                                    style={{ width: `${member.progress_percentage}%` }}
                                  />
                                </div>
                                <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{member.progress_percentage}%</span>
                                <button
                                  onClick={() => removeMemberMutation.mutate({ cohortId: cohortDetail.id, userId: member.user_id })}
                                  className="p-1 text-status-danger-500 hover:text-status-danger-700 dark:text-status-danger-300"
                                >
                                  <UserMinus className="w-4 h-4" />
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-center py-4">No members yet.</p>
                      )}
                    </div>

                    {/* Trainings Section */}
                    <div className="p-6">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                          <GraduationCap className="w-5 h-5 text-lsc-rose" />
                          Assigned Training ({cohortDetail.trainings.length})
                        </h3>
                      </div>
                      {cohortDetail.trainings.length > 0 ? (
                        <div className="space-y-2">
                          {cohortDetail.trainings.map((training: CohortTraining) => (
                            <div key={training.id} className="flex items-center justify-between p-3 bg-earth-50 dark:bg-earth-700/50 rounded-lg">
                              <div className="flex items-center gap-3">
                                <BookOpen className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                                <div>
                                  <p className="font-medium text-lsc-dark dark:text-lsc-cream">{training.training_name}</p>
                                  {training.due_date && (
                                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Due: {new Date(training.due_date).toLocaleDateString()}</p>
                                  )}
                                </div>
                              </div>
                              <div className="flex items-center gap-2">
                                {training.required && (
                                  <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400">
                                    Required
                                  </span>
                                )}
                                <button
                                  onClick={() => removeTrainingMutation.mutate({ cohortId: cohortDetail.id, trainingId: training.training_id })}
                                  className="p-1 text-status-danger-500 hover:text-status-danger-700 dark:text-status-danger-300"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-center py-4">{t('trainingCohorts.noTrainingAssignedYet')}</p>
                      )}
                    </div>
                  </>
                ) : null}
              </div>
            ) : (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-8 text-center">
                <Users className="w-12 h-12 text-earth-300 dark:text-earth-300 mx-auto mb-4" />
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('trainingCohorts.selectACohortToView')}</p>
              </div>
            )}
          </div>
        </div>

        {/* Create/Edit Modal */}
        {showModal && (
          <ModalBackdrop onClose={() => { setShowModal(false); setEditingCohort(null) }} title={editingCohort ? 'Edit Cohort' : 'New Cohort'}>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-md w-full">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                  {editingCohort ? 'Edit Cohort' : 'New Cohort'}
                </h3>
                <button onClick={() => { setShowModal(false); setEditingCohort(null) }} className="text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-200">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <form onSubmit={handleSubmit} className="p-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Cohort Name *</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Description</label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    rows={2}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Start Date *</label>
                    <input
                      type="date"
                      value={formData.start_date}
                      onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                      required
                      className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">End Date</label>
                    <input
                      type="date"
                      value={formData.end_date}
                      onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Max Members</label>
                  <input
                    type="number"
                    value={formData.max_members || ''}
                    onChange={(e) => setFormData({ ...formData, ...(e.target.value ? { max_members: parseInt(e.target.value) } : {}) })}
                    min="1"
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
              </form>
              <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => { setShowModal(false); setEditingCohort(null) }}
                  className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={createMutation.isPending || updateMutation.isPending}
                  className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50"
                >
                  {createMutation.isPending || updateMutation.isPending ? (
                    <Loader2 className="w-5 h-5 motion-safe:animate-spin" />
                  ) : editingCohort ? 'Update' : 'Create'}
                </button>
              </div>
            </div>
          </ModalBackdrop>
        )}

        {/* Add Member Modal */}
        {showAddMemberModal && selectedCohort && (
          <ModalBackdrop onClose={() => setShowAddMemberModal(false)} title="Add Member">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-sm w-full">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Add Member</h3>
              </div>
              <div className="p-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">User ID *</label>
                  <input
                    type="number"
                    value={newMemberUserId}
                    onChange={(e) => setNewMemberUserId(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Role</label>
                  <select
                    value={newMemberRole}
                    onChange={(e) => setNewMemberRole(e.target.value as 'member' | 'facilitator')}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  >
                    <option value="member">Member</option>
                    <option value="facilitator">Facilitator</option>
                  </select>
                </div>
              </div>
              <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-2">
                <button
                  onClick={() => setShowAddMemberModal(false)}
                  className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
                >
                  Cancel
                </button>
                <button
                  onClick={() => addMemberMutation.mutate({
                    cohortId: selectedCohort.id,
                    data: { user_id: parseInt(newMemberUserId), role: newMemberRole }
                  })}
                  disabled={addMemberMutation.isPending || !newMemberUserId}
                  className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50"
                >
                  {addMemberMutation.isPending ? <Loader2 className="w-5 h-5 motion-safe:animate-spin" /> : 'Add'}
                </button>
              </div>
            </div>
          </ModalBackdrop>
        )}

        {/* Delete Confirmation */}
        <ConfirmDialog
          isOpen={!!deleteConfirm}
          onClose={() => setDeleteConfirm(null)}
          onConfirm={() => { if (deleteConfirm) deleteMutation.mutate(deleteConfirm.id) }}
          title="Delete Cohort"
          message={`Are you sure you want to delete "${deleteConfirm?.name}"? This will remove all member assignments.`}
          confirmLabel="Delete"
          confirmVariant="danger"
        />
      </PageContainer>
    </div>
  </AdminShell>
  )
}
