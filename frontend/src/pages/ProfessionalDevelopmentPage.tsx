/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useId } from 'react'
import { useTranslation} from '../i18n/I18nContext'
import toast from 'react-hot-toast'
import { fetchApi } from '@/api/fetchApi'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

// Shapes mirror the backend wire format (snake_case, no camelCase transform in
// fetchApi). See backend/app/schemas/reading.py: TeacherTrainingModuleResponse,
// the completions/certificates dicts in school_reading/family_engagement.py.
interface TrainingModule {
  id: number
  partner_id: number
  title: string
  description?: string | null
  content_url?: string | null
  duration_minutes?: number | null
  category: string
  level: string
  is_active: boolean
  created_at?: string | null
}

interface ModuleCompletion {
  module_id: number
  module_title: string | null
  status: 'not_started' | 'in_progress' | 'completed'
  started_at?: string | null
  completed_at?: string | null
  quiz_score?: number | null
  passed_assessment: boolean
}

interface Certificate {
  id: number
  certification_name: string
  certification_level: string
  certification_number?: string | null
  issued_at?: string | null
  expires_at?: string | null
}

const CATEGORY_COLORS: { [key: string]: string } = {
  'reading-strategies': 'bg-earth-100 dark:bg-earth-800/30 text-earth-900 dark:text-lsc-rose-light/80',
  'engagement': 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-900 dark:text-status-success-200',
  'assessment': 'bg-category-100 dark:bg-category-900/30 text-category-900 dark:text-category-200',
  'technology': 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-900 dark:text-status-warning-200',
}

export default function ProfessionalDevelopmentPage() {
  const { t } = useTranslation()
  const schoolSelectId = useId()
  const [loading, setLoading] = useState(true)
  const [modules, setModules] = useState<TrainingModule[]>([])
  const [completions, setCompletions] = useState<ModuleCompletion[]>([])
  const [certificates, setCertificates] = useState<Certificate[]>([])
  const [selectedSchoolId, setSelectedSchoolId] = useState<string>('')
  const [schools, setSchools] = useState<Array<{ id: number | string; name: string }>>([])
  const [selectedModule, setSelectedModule] = useState<TrainingModule | null>(null)
  const [showModuleModal, setShowModuleModal] = useState(false)
  const [moduleCompleted, setModuleCompleted] = useState(false)
  const [view, setView] = useState<'browse' | 'progress' | 'certificates'>('browse')

  const fetchSchools = async () => {
    try {
      const data = await fetchApi('/school-partnerships/schools')
      const list = Array.isArray(data) ? data : (data?.schools ?? [])
      setSchools(list)
      if (list.length > 0) {
        setSelectedSchoolId(String(list[0].id))
      }
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('professionalDevelopment.failedToLoadSchools'))
    }
  }


  useEffect(() => {
    fetchSchools()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const fetchCertificates = async () => {
    if (!selectedSchoolId) return
    try {
      const data = await fetchApi(`/school-partnerships/training-modules/${selectedSchoolId}/certificates`)
      setCertificates(data.certificates || [])
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }


  const fetchCompletions = async () => {
    if (!selectedSchoolId) return
    try {
      const data = await fetchApi(`/school-partnerships/training-modules/${selectedSchoolId}/completions`)
      setCompletions(data.completions || [])
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }


  const fetchModules = async () => {
    if (!selectedSchoolId) return
    setLoading(true)
    try {
      const data = await fetchApi(`/school-partnerships/training-modules/${selectedSchoolId}`)
      // Backend returns a bare List[TeacherTrainingModuleResponse]; tolerate a
      // wrapped {modules:[]} shape too in case the contract is ever changed.
      setModules(Array.isArray(data) ? data : (data?.modules ?? []))
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('professionalDevelopment.failedToLoadTrainingModules'))
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    if (selectedSchoolId) {
      fetchModules()
      fetchCompletions()
      fetchCertificates()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSchoolId])

  const handleStartModule = async (module: TrainingModule) => {
    if (!selectedSchoolId) return

    try {
      await fetchApi(`/school-partnerships/training-modules/${module.id}/start`, {
        method: 'POST',
        body: JSON.stringify({ partnerId: selectedSchoolId }),
      })
      setSelectedModule(module)
      setModuleCompleted(false)
      setShowModuleModal(true)
      toast.success(t('toast.professionalDevelopment.startedTitle', { title: module.title }))
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('professionalDevelopment.failedToStartModule'))
    }
  }

  const handleMarkComplete = async () => {
    if (!selectedModule || !selectedSchoolId) return

    try {
      await fetchApi(`/school-partnerships/training-modules/${selectedModule.id}/complete`, {
        method: 'POST',
        body: JSON.stringify({
          partnerId: selectedSchoolId,
        }),
      })
      setModuleCompleted(true)
      toast.success(t('toast.professionalDevelopment.completedTitle', { title: selectedModule.title }))
      setTimeout(() => {
        setShowModuleModal(false)
        setModuleCompleted(false)
        fetchCompletions()
        fetchCertificates()
      }, 1800)
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('professionalDevelopment.failedToSubmitModule'))
    }
  }

  const getCompletionStatus = (moduleId: number) => {
    const completion = completions.find((c) => c.module_id === moduleId)
    return completion?.status || 'not_started'
  }

  const getCompletionScore = (moduleId: number) => {
    const completion = completions.find((c) => c.module_id === moduleId)
    return completion?.quiz_score ?? undefined
  }

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="font-serif text-4xl font-bold text-lsc-dark dark:text-lsc-cream mb-4">
            Professional Development
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Training modules for teachers and librarians
          </p>
        </div>

        {/* Controls */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label htmlFor={schoolSelectId} className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                Select School
              </label>
              <select
                id={schoolSelectId}
                value={selectedSchoolId}
                onChange={(e) => setSelectedSchoolId(e.target.value)}
                className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100"
              >
                <option value="">-- Choose a school --</option>
                {schools.map((school) => (
                  <option key={school.id} value={school.id}>
                    {school.name}
                  </option>
                ))}
              </select>
            </div>

            <div role="group" aria-label="Professional development view" className="flex items-end gap-4">
              <button
                type="button"
                onClick={() => setView('browse')}
                aria-pressed={view === 'browse'}
                className={`min-h-[44px] flex-1 px-4 py-2 rounded-lg font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-earth-600 focus-visible:ring-offset-2 ${
                  view === 'browse'
                    ? 'bg-earth-600 text-white'
                    : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-earth-200 dark:hover:bg-earth-600'
                }`}
              >
                Browse Modules
              </button>
              <button
                type="button"
                onClick={() => setView('progress')}
                aria-pressed={view === 'progress'}
                className={`min-h-[44px] flex-1 px-4 py-2 rounded-lg font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-earth-600 focus-visible:ring-offset-2 ${
                  view === 'progress'
                    ? 'bg-earth-600 text-white'
                    : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-earth-200 dark:hover:bg-earth-600'
                }`}
              >
                My Progress
              </button>
              <button
                type="button"
                onClick={() => setView('certificates')}
                aria-pressed={view === 'certificates'}
                className={`min-h-[44px] flex-1 px-4 py-2 rounded-lg font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-earth-600 focus-visible:ring-offset-2 ${
                  view === 'certificates'
                    ? 'bg-earth-600 text-white'
                    : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-earth-200 dark:hover:bg-earth-600'
                }`}
              >
                Certificates
              </button>
            </div>
          </div>
        </div>

        {/* Browse Modules */}
        {view === 'browse' && (
          <div className="space-y-6">
            {loading ? (
              <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
                Loading modules...
              </div>
            ) : modules.length === 0 ? (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-12 text-center">
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                  No training modules available for this school.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {modules.map((module) => {
                  const status = getCompletionStatus(module.id)
                  const score = getCompletionScore(module.id)

                  return (
                    <div
                      key={module.id}
                      className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6 hover:shadow-lg transition"
                    >
                      <div className="flex items-start justify-between mb-4">
                        <div>
                          <h3 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream mb-2">
                            {module.title}
                          </h3>
                          <div className="flex gap-2 mb-3">
                            <span
                              className={`px-3 py-1 rounded-full text-xs font-semibold ${
                                CATEGORY_COLORS[module.category] || 'bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream'
                              }`}
                            >
                              {module.category}
                            </span>
                            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream">
                              {module.level}
                            </span>
                          </div>
                        </div>
                        <div
                          className={`px-3 py-1 rounded-full text-xs font-semibold ${
                            status === 'completed'
                              ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-900 dark:text-status-success-200'
                              : status === 'in_progress'
                                ? 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-900 dark:text-status-warning-200'
                                : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream'
                          }`}
                        >
                          {status === 'completed' ? '✓ Completed' : status === 'in_progress' ? 'In Progress' : 'Not Started'}
                        </div>
                      </div>

                      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mb-4">
                        {module.description}
                      </p>

                      <div className="mb-4">
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                          Duration: {module.duration_minutes ?? '--'} minutes
                        </p>
                      </div>

                      {status === 'completed' && score !== undefined && (
                        <div className="mb-4 p-3 bg-status-success-50 dark:bg-status-success-900/20 rounded-lg">
                          <p className="text-sm font-semibold text-status-success-900 dark:text-status-success-100">
                            Score: {score}%
                          </p>
                        </div>
                      )}

                      <div className="flex gap-2">
                        <button
                          onClick={() => handleStartModule(module)}
                          disabled={status === 'completed'}
                          className={`flex-1 px-4 py-2 rounded-lg font-medium transition ${
                            status === 'completed'
                              ? 'bg-earth-200 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 cursor-not-allowed'
                              : 'bg-earth-600 text-white hover:bg-earth-700'
                          }`}
                        >
                          {status === 'completed' ? 'Completed' : 'Start Module'}
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {/* My Progress */}
        {view === 'progress' && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg overflow-hidden">
            {completions.length === 0 ? (
              <div className="p-12 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                No modules started yet. Start a module to track your progress!
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-earth-100 dark:bg-earth-700 border-b border-lsc-border dark:border-earth-700">
                    <tr>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        Module
                      </th>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        Score
                      </th>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        Completed Date
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-earth-200 dark:divide-earth-700">
                    {completions.map((completion) => (
                      <tr
                        key={completion.module_id}
                        className="hover:bg-earth-50 dark:hover:bg-earth-700 transition"
                      >
                        <td className="px-6 py-4 text-lsc-dark dark:text-lsc-cream">
                          {completion.module_title}
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={`px-3 py-1 rounded-full text-sm font-semibold ${
                              completion.status === 'completed'
                                ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-900 dark:text-status-success-200'
                                : completion.status === 'in_progress'
                                  ? 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-900 dark:text-status-warning-200'
                                  : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream'
                            }`}
                          >
                            {completion.status.charAt(0).toUpperCase() +
                              completion.status.slice(1).replace('_', ' ')}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          {completion.quiz_score != null ? (
                            <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                              {completion.quiz_score}%
                            </span>
                          ) : (
                            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">--</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
                          {completion.completed_at
                            ? new Date(completion.completed_at).toLocaleDateString()
                            : '--'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Certificates */}
        {view === 'certificates' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {certificates.length === 0 ? (
              <div className="col-span-full bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-12 text-center">
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                  No certificates earned yet. Complete training modules to earn certificates!
                </p>
              </div>
            ) : (
              certificates.map((cert) => (
                <div
                  key={cert.id}
                  className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-8 border-4 border-status-warning-400"
                >
                  <div className="text-center">
                    <h3 className="text-2xl font-serif font-bold text-status-warning-700 dark:text-status-warning-300 mb-4">Certificate of Completion</h3>
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                      This certifies successful completion of
                    </p>
                    <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream mb-4">
                      {cert.certification_name}
                    </p>
                    <p className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-6 capitalize">
                      {cert.certification_level} level
                    </p>
                    <div className="border-t-2 border-lsc-border dark:border-earth-700 pt-4">
                      {cert.issued_at && (
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                          Issued: {new Date(cert.issued_at).toLocaleDateString()}
                        </p>
                      )}
                      {cert.certification_number && (
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          Certificate No. {cert.certification_number}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Module Modal */}
        {showModuleModal && selectedModule && (
          <ModalBackdrop onClose={() => { setShowModuleModal(false); setSelectedModule(null) }} title="Training Module">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-2xl w-full p-8 my-8">
              <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
                {selectedModule.title}
              </h2>

              {!moduleCompleted ? (
                <div className="space-y-6">
                  <div>
                    <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
                      Overview
                    </h3>
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                      {selectedModule.description}
                    </p>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <span className="px-3 py-1 rounded-full text-xs font-semibold bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream capitalize">
                      {selectedModule.category}
                    </span>
                    <span className="px-3 py-1 rounded-full text-xs font-semibold bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream capitalize">
                      {selectedModule.level}
                    </span>
                    {selectedModule.duration_minutes != null && (
                      <span className="px-3 py-1 rounded-full text-xs font-semibold bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream">
                        {selectedModule.duration_minutes} min
                      </span>
                    )}
                  </div>

                  {selectedModule.content_url && (
                    <a
                      href={selectedModule.content_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block text-earth-700 dark:text-earth-300 underline"
                    >
                      Open module materials
                    </a>
                  )}

                  <div className="flex gap-4 pt-2 border-t border-lsc-border dark:border-earth-700">
                    <button
                      onClick={() => { setShowModuleModal(false); setSelectedModule(null) }}
                      className="flex-1 px-4 py-2 bg-earth-200 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-earth-300 dark:hover:bg-earth-600 transition"
                    >
                      Close
                    </button>
                    <button
                      onClick={handleMarkComplete}
                      className="flex-1 px-4 py-2 bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 transition font-semibold"
                    >
                      Mark as Complete
                    </button>
                  </div>
                </div>
              ) : (
                <div className="text-center space-y-4">
                  <div className="text-5xl font-bold text-status-success-600 dark:text-status-success-400">✓</div>
                  <h3 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                    Module Completed!
                  </h3>
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                    This module is now marked complete in My Progress.
                  </p>
                </div>
              )}
            </div>
          </ModalBackdrop>
        )}
      </div>
    </div>
  )
}