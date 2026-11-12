/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

import { useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import * as Sentry from '@/lib/sentry-lazy'
import toast from 'react-hot-toast'
import { Modal } from '@/components/ui/Modal'
import { useTranslation } from '@/i18n'
import {
  updateConnectionGroup,
  type ConnectionGroupType,
  type ConnectionGroupUpdatePayload,
  type MeetingFrequency,
  type ParentConnectionGroup,
} from '@/api/parent-onboarding-api'
import { Field, ModalFooter, REDACTED_CTX, Section, inputCls } from './shared'

const GROUP_TYPES: ConnectionGroupType[] = [
  'first_time_parents', 'teen_parents', 'single_parents', 'postpartum_support', 'general',
]
const FREQUENCIES: MeetingFrequency[] = ['weekly', 'biweekly', 'monthly']
const DAYS_OF_WEEK = [
  'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
] as const

interface EditProps {
  group: ParentConnectionGroup
  activeMemberCount?: number
  isOpen: boolean
  onClose: () => void
}

export function EditGroupModal({ group, activeMemberCount, isOpen, onClose }: EditProps) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  // Prefill from group. Re-runs on every open so re-opening for a different
  // group reflects that group's current values.
  const [name, setName] = useState(group.name)
  const [description, setDescription] = useState(group.description ?? '')
  const [groupType, setGroupType] = useState<ConnectionGroupType>(group.group_type)
  const [frequency, setFrequency] = useState<MeetingFrequency>(
    group.meeting_frequency ?? 'weekly',
  )
  const [dayOfWeek, setDayOfWeek] = useState<string>(group.meeting_day_of_week ?? 'monday')
  const [meetingTime, setMeetingTime] = useState<string>(group.meeting_time ?? '')
  const [location, setLocation] = useState<string>(group.location ?? group.meeting_location ?? '')
  const [maxMembers, setMaxMembers] = useState<number>(group.max_members)
  const [cohortStart, setCohortStart] = useState<string>(group.cohort_start_date ?? '')
  const [cohortEnd, setCohortEnd] = useState<string>(group.cohort_end_date ?? '')
  const [capacityError, setCapacityError] = useState<{ excess: number } | null>(null)

  useEffect(() => {
    if (isOpen) {
      setName(group.name)
      setDescription(group.description ?? '')
      setGroupType(group.group_type)
      setFrequency(group.meeting_frequency ?? 'weekly')
      setDayOfWeek(group.meeting_day_of_week ?? 'monday')
      setMeetingTime(group.meeting_time ?? '')
      setLocation(group.location ?? group.meeting_location ?? '')
      setMaxMembers(group.max_members)
      setCohortStart(group.cohort_start_date ?? '')
      setCohortEnd(group.cohort_end_date ?? '')
      setCapacityError(null)
    }
  }, [isOpen, group])

  const mutation = useMutation({
    mutationFn: (payload: ConnectionGroupUpdatePayload) =>
      updateConnectionGroup(group.id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connection-groups'] })
      toast.success(t('parentOnboarding.connectionGroups.admin.edit.success'))
      onClose()
    },
    onError: (err: unknown) => {
      // Inspect the 422 capacity-conflict body so we can render an inline
      // error instead of a toast. The shape is documented in
      // CapacityConflictDetail server-side.
      const detail =
        err &&
        typeof err === 'object' &&
        'data' in err &&
        typeof (err as { data?: unknown }).data === 'object'
          ? (err as { data?: { detail?: unknown } }).data?.detail
          : undefined
      const conflict =
        detail &&
        typeof detail === 'object' &&
        (detail as { error?: string }).error === 'capacity_below_active_members'
          ? (detail as { excess?: number; current_active_count?: number })
          : null
      if (conflict) {
        setCapacityError({ excess: Number(conflict.excess ?? 0) })
        return
      }
      Sentry.captureException(err, REDACTED_CTX)
      toast.error(t('parentOnboarding.connectionGroups.admin.edit.errorGeneric'))
    },
  })

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    setCapacityError(null)
    const payload: ConnectionGroupUpdatePayload = {
      name: name.trim(),
      description: description.trim() || undefined,
      group_type: groupType,
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

  const capacityHelperId = 'cg-edit-capacity-helper'

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t('parentOnboarding.connectionGroups.admin.edit.title', { groupName: group.name })}
      size="2xl"
    >
      <form onSubmit={submit} className="space-y-6" data-testid="cg-edit-form">
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
        </Section>

        <Section title={t('parentOnboarding.connectionGroups.admin.create.sectionSchedule')}>
          <Field label={t('parentOnboarding.connectionGroups.admin.create.fieldMeetingFrequency')}>
            <div role="radiogroup" className="flex gap-3 flex-wrap">
              {FREQUENCIES.map((f) => (
                <label key={f} className="inline-flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name="meeting-frequency-edit"
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
              aria-describedby={capacityHelperId}
            />
            {typeof activeMemberCount === 'number' && (
              <p
                id={capacityHelperId}
                className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1"
                data-testid="cg-edit-capacity-current"
              >
                {t('parentOnboarding.connectionGroups.admin.edit.capacityCurrent', {
                  count: String(activeMemberCount),
                })}
              </p>
            )}
            {capacityError && (
              <p
                role="alert"
                aria-live="polite"
                className="text-xs text-status-danger-600 dark:text-status-danger-400 mt-1"
                data-testid="cg-edit-capacity-error"
              >
                {t('parentOnboarding.connectionGroups.admin.edit.errorCapacityTooLow', {
                  excess: String(capacityError.excess),
                })}
              </p>
            )}
          </Field>
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
          cancelLabel={t('parentOnboarding.connectionGroups.admin.edit.cancel')}
          submitLabel={t('parentOnboarding.connectionGroups.admin.edit.submit')}
          submitting={mutation.isPending}
        />
      </form>
    </Modal>
  )
}
