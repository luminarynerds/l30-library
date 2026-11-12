/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as Sentry from '@/lib/sentry-lazy'
import toast from 'react-hot-toast'
import { Modal } from '@/components/ui/Modal'
import { useTranslation } from '@/i18n'
import {
  createConnectionGroup,
  type ConnectionGroupCreatePayload,
  type ConnectionGroupType,
  type MeetingFrequency,
} from '@/api/parent-onboarding-api'
import { listBranches } from '@/api/branch-api'
import { Field, ModalFooter, REDACTED_CTX, Section, inputCls } from './shared'

const GROUP_TYPES: ConnectionGroupType[] = [
  'first_time_parents', 'teen_parents', 'single_parents', 'postpartum_support', 'general',
]
const FREQUENCIES: MeetingFrequency[] = ['weekly', 'biweekly', 'monthly']
const DAYS_OF_WEEK = [
  'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
] as const

interface CreateProps {
  isOpen: boolean
  onClose: () => void
}

export function CreateGroupModal({ isOpen, onClose }: CreateProps) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  // Branch list. Bare loader — branches change rarely, so we don't bother
  // with optimistic cache invalidation; admin reload is fine.
  const branchesQuery = useQuery({
    queryKey: ['branches', 'admin-create-group'],
    queryFn: () => listBranches({ active_only: true }),
    enabled: isOpen,
  })

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [groupType, setGroupType] = useState<ConnectionGroupType>('general')
  const [branchId, setBranchId] = useState<number | ''>('')
  const [frequency, setFrequency] = useState<MeetingFrequency>('weekly')
  const [dayOfWeek, setDayOfWeek] = useState<string>('monday')
  const [meetingTime, setMeetingTime] = useState<string>('')
  const [location, setLocation] = useState<string>('')
  const [maxMembers, setMaxMembers] = useState<number>(12)
  const [cohortStart, setCohortStart] = useState<string>('')
  const [cohortEnd, setCohortEnd] = useState<string>('')

  useEffect(() => {
    if (!isOpen) {
      setName('')
      setDescription('')
      setGroupType('general')
      setBranchId('')
      setFrequency('weekly')
      setDayOfWeek('monday')
      setMeetingTime('')
      setLocation('')
      setMaxMembers(12)
      setCohortStart('')
      setCohortEnd('')
    }
  }, [isOpen])

  const mutation = useMutation({
    mutationFn: (payload: ConnectionGroupCreatePayload) => createConnectionGroup(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connection-groups'] })
      toast.success(t('parentOnboarding.connectionGroups.admin.create.success'))
      onClose()
    },
    onError: (err) => {
      Sentry.captureException(err, REDACTED_CTX)
      toast.error(t('parentOnboarding.connectionGroups.admin.create.errorGeneric'))
    },
  })

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || branchId === '') return
    const payload: ConnectionGroupCreatePayload = {
      name: name.trim(),
      description: description.trim() || undefined,
      group_type: groupType,
      branch_id: Number(branchId),
      meeting_frequency: frequency,
      meeting_day_of_week: dayOfWeek || null,
      meeting_time: meetingTime || null,
      location: location || null,
      max_members: maxMembers,
      cohort_start_date: cohortStart || null,
      cohort_end_date: cohortEnd || null,
    }
    mutation.mutate(payload)
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t('parentOnboarding.connectionGroups.admin.create.title')}
      size="2xl"
    >
      <form onSubmit={submit} className="space-y-6" data-testid="cg-create-form">
        <Section title={t('parentOnboarding.connectionGroups.admin.create.sectionBasics')}>
          <Field label={t('parentOnboarding.connectionGroups.admin.create.fieldName')} required>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={200}
              className={inputCls}
            />
          </Field>
          <Field label={t('parentOnboarding.connectionGroups.admin.create.fieldDescription')}>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={2000}
              rows={3}
              className={inputCls}
            />
          </Field>
          <Field label={t('parentOnboarding.connectionGroups.admin.create.fieldGroupType')}>
            <select
              value={groupType}
              onChange={(e) => setGroupType(e.target.value as ConnectionGroupType)}
              className={inputCls}
            >
              {GROUP_TYPES.map((gt) => (
                <option key={gt} value={gt}>
                  {t(`parentOnboarding.connectionGroups.types.${gt}`)}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('parentOnboarding.connectionGroups.admin.create.fieldBranch')} required>
            <select
              required
              value={branchId === '' ? '' : String(branchId)}
              onChange={(e) => setBranchId(e.target.value === '' ? '' : Number(e.target.value))}
              className={inputCls}
              data-testid="cg-create-branch"
            >
              <option value="">--</option>
              {(branchesQuery.data ?? []).map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
          </Field>
        </Section>

        <Section title={t('parentOnboarding.connectionGroups.admin.create.sectionSchedule')}>
          <Field label={t('parentOnboarding.connectionGroups.admin.create.fieldMeetingFrequency')}>
            <div role="radiogroup" className="flex gap-3 flex-wrap">
              {FREQUENCIES.map((f) => (
                <label key={f} className="inline-flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name="meeting-frequency"
                    value={f}
                    checked={frequency === f}
                    onChange={() => setFrequency(f)}
                  />
                  {t(`parentOnboarding.connectionGroups.admin.meetingFrequency.${f}`)}
                </label>
              ))}
            </div>
          </Field>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label={t('parentOnboarding.connectionGroups.admin.create.fieldDayOfWeek')}>
              <select
                value={dayOfWeek}
                onChange={(e) => setDayOfWeek(e.target.value)}
                className={inputCls}
              >
                {DAYS_OF_WEEK.map((d) => (
                  <option key={d} value={d}>
                    {t(`parentOnboarding.connectionGroups.admin.dayOfWeek.${d}`)}
                  </option>
                ))}
              </select>
            </Field>
            <Field label={t('parentOnboarding.connectionGroups.admin.create.fieldMeetingTime')}>
              <input
                type="time"
                value={meetingTime}
                onChange={(e) => setMeetingTime(e.target.value)}
                className={inputCls}
              />
            </Field>
          </div>
          <Field label={t('parentOnboarding.connectionGroups.admin.create.fieldLocation')}>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              maxLength={300}
              className={inputCls}
            />
          </Field>
        </Section>

        <Section title={t('parentOnboarding.connectionGroups.admin.create.sectionCohort')}>
          <Field label={t('parentOnboarding.connectionGroups.admin.create.fieldMaxMembers')}>
            <input
              type="number"
              value={maxMembers}
              onChange={(e) => setMaxMembers(Math.max(2, Math.min(30, Number(e.target.value))))}
              min={2}
              max={30}
              className={inputCls}
            />
          </Field>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 -mt-2">
            {t('parentOnboarding.connectionGroups.admin.create.fieldCohortHint')}
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label={t('parentOnboarding.connectionGroups.admin.create.fieldCohortStart')}>
              <input
                type="date"
                value={cohortStart}
                onChange={(e) => setCohortStart(e.target.value)}
                className={inputCls}
              />
            </Field>
            <Field label={t('parentOnboarding.connectionGroups.admin.create.fieldCohortEnd')}>
              <input
                type="date"
                value={cohortEnd}
                onChange={(e) => setCohortEnd(e.target.value)}
                className={inputCls}
              />
            </Field>
          </div>
        </Section>

        <ModalFooter
          onCancel={onClose}
          cancelLabel={t('parentOnboarding.connectionGroups.admin.create.cancel')}
          submitLabel={t('parentOnboarding.connectionGroups.admin.create.submit')}
          submitting={mutation.isPending}
          submitDisabled={!name.trim() || branchId === ''}
        />
      </form>
    </Modal>
  )
}
