/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle, AlertCircle, Clock, GraduationCap } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import {
  getMyTeacherApplication,
  listTeacherSchools,
  submitTeacherApplication,
  TeacherApplication,
  TeacherApplicationCreate,
  TeacherSchoolOption,
} from '@/api/teacher-applications-api'

const REVIEW_NOTE =
  "A librarian will review your application and email you with the decision. " +
  "If you don't see a response within a few business days, just reply to the " +
  'confirmation email or visit the front desk.'

function StatusBlock({ application }: { application: TeacherApplication }) {
  if (application.status === 'pending') {
    return (
      <div
        role="status"
        className="rounded-lg border border-amber-200 bg-amber-50 dark:bg-amber-900/10 dark:border-amber-900/40 p-6"
      >
        <div className="flex items-start gap-3">
          <Clock className="h-6 w-6 text-amber-700 dark:text-amber-300 shrink-0 mt-1" aria-hidden />
          <div>
            <h2 className="text-lg font-semibold text-amber-900 dark:text-amber-100">
              Your teacher application is pending review
            </h2>
            <p className="mt-2 text-sm text-amber-900/90 dark:text-amber-100/90">
              {REVIEW_NOTE}
            </p>
          </div>
        </div>
      </div>
    )
  }
  if (application.status === 'approved') {
    return (
      <div
        role="status"
        className="rounded-lg border border-emerald-200 bg-emerald-50 dark:bg-emerald-900/10 dark:border-emerald-900/40 p-6"
      >
        <div className="flex items-start gap-3">
          <CheckCircle className="h-6 w-6 text-emerald-700 dark:text-emerald-300 shrink-0 mt-1" aria-hidden />
          <div>
            <h2 className="text-lg font-semibold text-emerald-900 dark:text-emerald-100">
              You are approved as a teacher
            </h2>
            <p className="mt-2 text-sm text-emerald-900/90 dark:text-emerald-100/90">
              Your account is linked to{' '}
              <strong>{application.school_name || 'your school'}</strong>.
              You now have access to teacher-only features.
            </p>
          </div>
        </div>
      </div>
    )
  }
  // denied
  return (
    <div
      role="status"
      className="rounded-lg border border-red-200 bg-red-50 dark:bg-red-900/10 dark:border-red-900/40 p-6"
    >
      <div className="flex items-start gap-3">
        <AlertCircle className="h-6 w-6 text-red-700 dark:text-red-300 shrink-0 mt-1" aria-hidden />
        <div>
          <h2 className="text-lg font-semibold text-red-900 dark:text-red-100">
            Your previous teacher application was not approved
          </h2>
          {application.denial_reason ? (
            <p className="mt-2 text-sm text-red-900/90 dark:text-red-100/90 whitespace-pre-wrap">
              {application.denial_reason}
            </p>
          ) : null}
          <p className="mt-2 text-sm text-red-900/90 dark:text-red-100/90">
            You may submit a new application below if your situation has
            changed.
          </p>
        </div>
      </div>
    </div>
  )
}

export default function TeacherApplicationPage(): React.ReactElement {
  const { token, user } = useAuth()
  const [schools, setSchools] = useState<TeacherSchoolOption[]>([])
  const [existing, setExisting] = useState<TeacherApplication | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<TeacherApplication | null>(null)

  const [form, setForm] = useState<TeacherApplicationCreate>({
    school_id: null,
    school_name_freetext: '',
    grade_level: '',
    subject: '',
    classroom_size: undefined,
    notes: '',
  })

  useEffect(() => {
    if (!token) {
      setLoading(false)
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const [schoolList, mine] = await Promise.all([
          listTeacherSchools(token),
          getMyTeacherApplication(token),
        ])
        if (cancelled) return
        setSchools(schoolList)
        setExisting(mine)
      } catch (e) {
        if (cancelled) return
        setError(e instanceof Error ? e.message : 'Failed to load page')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [token])

  const showForm =
    !loading && !success && (!existing || existing.status === 'denied')

  const onChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ): void => {
    const { name, value } = e.target
    setForm((prev) => ({
      ...prev,
      [name]:
        name === 'school_id'
          ? value
            ? Number(value)
            : null
          : name === 'classroom_size'
            ? value
              ? Number(value)
              : undefined
            : value,
    }))
  }

  const onSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault()
    if (!token) return
    setSubmitting(true)
    setError(null)
    try {
      const payload: TeacherApplicationCreate = {
        school_id: form.school_id ?? null,
        school_name_freetext: form.school_name_freetext?.trim() || null,
        grade_level: form.grade_level?.trim() || null,
        subject: form.subject?.trim() || null,
        classroom_size: form.classroom_size ?? null,
        notes: form.notes?.trim() || null,
      }
      const created = await submitTeacherApplication(token, payload)
      setSuccess(created)
      setExisting(created)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to submit')
    } finally {
      setSubmitting(false)
    }
  }

  if (!user) {
    return (
      <div className="max-w-2xl mx-auto p-8 text-center">
        <p>
          You must be{' '}
          <Link to="/login" className="text-blue-700 dark:text-blue-300 underline">
            signed in
          </Link>{' '}
          to apply for a teacher account.
        </p>
      </div>
    )
  }

  return (
    <main className="max-w-2xl mx-auto p-6 sm:p-8" id="main-content">
      <header className="mb-6">
        <div className="flex items-center gap-3">
          <GraduationCap className="h-8 w-8 text-blue-700 dark:text-blue-300" aria-hidden />
          <h1 className="text-2xl sm:text-3xl font-bold">Apply to Teach</h1>
        </div>
        <p className="mt-2 text-sm text-neutral-700 dark:text-neutral-300">
          Tell us about your classroom so a librarian can set you up with a
          teacher account.
        </p>
      </header>

      {loading ? (
        <p>Loading…</p>
      ) : (
        <>
          {existing && !success ? <StatusBlock application={existing} /> : null}
          {success ? (
            <div
              role="status"
              className="rounded-lg border border-emerald-200 bg-emerald-50 dark:bg-emerald-900/10 dark:border-emerald-900/40 p-6 mb-6"
            >
              <h2 className="text-lg font-semibold text-emerald-900 dark:text-emerald-100">
                Application submitted
              </h2>
              <p className="mt-2 text-sm text-emerald-900/90 dark:text-emerald-100/90">
                Thanks! A librarian will review your application. We just sent
                a confirmation to <strong>{user.email}</strong>.
              </p>
            </div>
          ) : null}

          {error ? (
            <div
              role="alert"
              className="rounded-lg border border-red-200 bg-red-50 dark:bg-red-900/10 dark:border-red-900/40 p-4 mb-6"
            >
              <p className="text-sm text-red-900 dark:text-red-100">{error}</p>
            </div>
          ) : null}

          {showForm ? (
            <form onSubmit={onSubmit} noValidate className="space-y-5">
              <div>
                <label
                  htmlFor="teacher-app-school"
                  className="block text-sm font-medium mb-1"
                >
                  School
                </label>
                <select
                  id="teacher-app-school"
                  name="school_id"
                  value={form.school_id ?? ''}
                  onChange={onChange}
                  className="w-full min-h-[44px] rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:outline-none"
                >
                  <option value="">— Select a school —</option>
                  {schools.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-neutral-600 dark:text-neutral-400">
                  Don&apos;t see your school? Leave this blank and enter the
                  name below.
                </p>
              </div>

              <div>
                <label
                  htmlFor="teacher-app-school-freetext"
                  className="block text-sm font-medium mb-1"
                >
                  School name (if not listed)
                </label>
                <input
                  id="teacher-app-school-freetext"
                  name="school_name_freetext"
                  type="text"
                  value={form.school_name_freetext ?? ''}
                  onChange={onChange}
                  maxLength={255}
                  className="w-full min-h-[44px] rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:outline-none"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label
                    htmlFor="teacher-app-grade"
                    className="block text-sm font-medium mb-1"
                  >
                    Grade level(s)
                  </label>
                  <input
                    id="teacher-app-grade"
                    name="grade_level"
                    type="text"
                    value={form.grade_level ?? ''}
                    onChange={onChange}
                    placeholder="e.g. K-2, 6th, HS"
                    maxLength={100}
                    className="w-full min-h-[44px] rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:outline-none"
                  />
                </div>
                <div>
                  <label
                    htmlFor="teacher-app-subject"
                    className="block text-sm font-medium mb-1"
                  >
                    Subject
                  </label>
                  <input
                    id="teacher-app-subject"
                    name="subject"
                    type="text"
                    value={form.subject ?? ''}
                    onChange={onChange}
                    placeholder="e.g. reading, math"
                    maxLength={255}
                    className="w-full min-h-[44px] rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:outline-none"
                  />
                </div>
              </div>

              <div>
                <label
                  htmlFor="teacher-app-classroom-size"
                  className="block text-sm font-medium mb-1"
                >
                  Approximate classroom size
                </label>
                <input
                  id="teacher-app-classroom-size"
                  name="classroom_size"
                  type="number"
                  min={0}
                  max={10000}
                  inputMode="numeric"
                  value={form.classroom_size ?? ''}
                  onChange={onChange}
                  className="w-full min-h-[44px] rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:outline-none"
                />
              </div>

              <div>
                <label
                  htmlFor="teacher-app-notes"
                  className="block text-sm font-medium mb-1"
                >
                  Anything else we should know?
                </label>
                <textarea
                  id="teacher-app-notes"
                  name="notes"
                  value={form.notes ?? ''}
                  onChange={onChange}
                  maxLength={4000}
                  rows={4}
                  className="w-full rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-2 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:outline-none"
                />
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="min-h-[44px] inline-flex items-center justify-center rounded-lg bg-blue-700 hover:bg-blue-800 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium px-6 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 focus-visible:outline-none"
              >
                {submitting ? 'Submitting…' : 'Submit application'}
              </button>
            </form>
          ) : null}
        </>
      )}
    </main>
  )
}
