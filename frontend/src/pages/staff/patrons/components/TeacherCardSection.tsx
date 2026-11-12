/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from "react"
import { GraduationCap, Loader2 } from "lucide-react"
import toast from "react-hot-toast"
import { useAuth } from "../../../../contexts/AuthContext"
import {
  listSchoolPartnersForTeacherCard,
  setTeacherCard,
  type TeacherCardSchoolOption,
} from "../../../../api/staff-api"
import type { PatronDetail } from "../types"

interface TeacherCardSectionProps {
  patron: PatronDetail
  onPatronUpdated?: ((patron: PatronDetail) => void) | undefined
}

export function TeacherCardSection({ patron, onPatronUpdated }: TeacherCardSectionProps) {
  const { token } = useAuth()
  const [schools, setSchools] = useState<TeacherCardSchoolOption[]>([])
  const [isLoadingSchools, setIsLoadingSchools] = useState(false)
  const [schoolsError, setSchoolsError] = useState<string | null>(null)
  const [selectedSchoolId, setSelectedSchoolId] = useState<number | ''>(
    typeof patron.school_id === 'number' ? patron.school_id : '',
  )
  const [isSaving, setIsSaving] = useState(false)
  const [showPicker, setShowPicker] = useState(false)

  useEffect(() => {
    setSelectedSchoolId(typeof patron.school_id === 'number' ? patron.school_id : '')
  }, [patron.school_id])

  useEffect(() => {
    if (!token || !showPicker) return
    if (schools.length > 0 || isLoadingSchools) return
    setIsLoadingSchools(true)
    listSchoolPartnersForTeacherCard(token)
      .then((rows) => setSchools(rows))
      .catch((err: Error) => setSchoolsError(err.message || 'Failed to load schools'))
      .finally(() => setIsLoadingSchools(false))
  }, [token, showPicker, schools.length, isLoadingSchools])

  const isTeacher = patron.role === 'teacher'
  const currentSchool = schools.find((s) => s.id === patron.school_id)
  const currentSchoolName = currentSchool?.name

  const applyChange = async (schoolId: number | null) => {
    if (!token) return
    setIsSaving(true)
    try {
      const updated = await setTeacherCard(token, patron.id, schoolId)
      toast.success(schoolId === null ? 'Teacher card revoked' : 'Teacher card updated')
      if (onPatronUpdated) {
        onPatronUpdated({
          ...patron,
          role: updated.role,
          school_id: updated.school_id ?? null,
        })
      }
      setShowPicker(false)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to update teacher card')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="bg-lsc-cream dark:bg-lsc-brown/50 rounded-xl p-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
          <GraduationCap className="w-5 h-5 text-lsc-rose" />
          Teacher Card
        </h3>
        {isTeacher && (
          <span className="text-xs px-2 py-1 rounded-full bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-200">
            Active
          </span>
        )}
      </div>

      {isTeacher ? (
        <div className="space-y-2">
          <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
            Linked to school:{' '}
            <span className="font-medium">
              {currentSchoolName || (typeof patron.school_id === 'number' ? `Partner #${patron.school_id}` : 'unknown')}
            </span>
          </p>
          <div className="flex flex-wrap gap-2 pt-2">
            <button
              type="button"
              onClick={() => setShowPicker((v) => !v)}
              disabled={isSaving}
              className="px-3 py-1.5 text-xs font-medium text-lsc-rose border border-lsc-rose/30 rounded-lg hover:bg-lsc-rose/5 disabled:opacity-50"
            >
              {showPicker ? 'Cancel' : 'Change school'}
            </button>
            <button
              type="button"
              onClick={() => applyChange(null)}
              disabled={isSaving}
              className="px-3 py-1.5 text-xs font-medium text-status-danger-700 border border-status-danger-300 rounded-lg hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 disabled:opacity-50"
            >
              {isSaving ? <Loader2 className="w-3 h-3 inline motion-safe:animate-spin mr-1" /> : null}
              Revoke teacher card
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            This patron does not have a teacher card. Issue one to link them to a school partner and grant elevated lending limits.
          </p>
          <button
            type="button"
            onClick={() => setShowPicker((v) => !v)}
            disabled={isSaving}
            className="px-3 py-1.5 text-xs font-medium text-lsc-rose border border-lsc-rose/30 rounded-lg hover:bg-lsc-rose/5 disabled:opacity-50"
          >
            {showPicker ? 'Cancel' : 'Issue teacher card'}
          </button>
        </div>
      )}

      {showPicker && (
        <div className="mt-4 p-3 bg-lsc-white/50 dark:bg-earth-800/50 rounded-lg space-y-2">
          <label htmlFor={`teacher-card-school-${patron.id}`} className="block text-xs font-medium text-lsc-dark/80 dark:text-lsc-cream/80">
            School
          </label>
          <select
            id={`teacher-card-school-${patron.id}`}
            value={selectedSchoolId === '' ? '' : String(selectedSchoolId)}
            onChange={(e) => setSelectedSchoolId(e.target.value ? Number(e.target.value) : '')}
            disabled={isLoadingSchools || isSaving}
            className="w-full px-3 py-1.5 text-sm border border-sage/30 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
          >
            <option value="">{isLoadingSchools ? 'Loading schools...' : 'Select a school'}</option>
            {schools.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
          {schoolsError && (
            <p role="alert" className="text-xs text-status-danger-600 dark:text-status-danger-400">
              {schoolsError}
            </p>
          )}
          <button
            type="button"
            onClick={() => typeof selectedSchoolId === 'number' && applyChange(selectedSchoolId)}
            disabled={isSaving || typeof selectedSchoolId !== 'number'}
            className="px-3 py-1.5 text-xs font-medium text-white bg-lsc-rose rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50"
          >
            {isSaving ? <Loader2 className="w-3 h-3 inline motion-safe:animate-spin mr-1" /> : null}
            {isTeacher ? 'Update school' : 'Issue teacher card'}
          </button>
        </div>
      )}
    </div>
  )
}
