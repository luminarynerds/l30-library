/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect } from 'react'
import { useTranslation} from '../i18n/I18nContext'
import toast from 'react-hot-toast'
import { fetchApi } from '@/api/fetchApi'
import { AdminShell } from '../components/shells/AdminShell'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface ReadingBundle {
  id: string
  title: string
  description: string
  themeOrGradeLevel: string
  numberOfBooks: number
  readingLevels: string[]
  totalCopiesAvailable: number
  copiesTomorrow: number
  bundles: string[]
}

interface BundleDistribution {
  id: string
  bundleId: string
  bundleTitle: string
  studentName: string
  className: string
  distributedDate: string
  returnedDate?: string
  status: 'distributed' | 'returned' | 'pending'
  feedback?: string
}

export default function ReadingBundleDistributionPage() {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  const [bundles, setBundles] = useState<ReadingBundle[]>([])
  const [distributions, setDistributions] = useState<BundleDistribution[]>([])
  const [selectedSchoolId, setSelectedSchoolId] = useState<string>('')
  const [schools, setSchools] = useState<Array<{ id: string; name: string }>>([])
  const [selectedBundle, setSelectedBundle] = useState<ReadingBundle | null>(null)
  const [showDistributionModal, setShowDistributionModal] = useState(false)
  const [studentName, setStudentName] = useState('')
  const [className, setClassName] = useState('')
  const [_distributionsLoading, setDistributionsLoading] = useState(false)
  const [view, setView] = useState<'bundles' | 'distributions'>('bundles')
  const [filterTheme, setFilterTheme] = useState('')

  const fetchSchools = async () => {
    try {
      const data = await fetchApi('/school-partnerships/schools')
      const schoolList = Array.isArray(data) ? data : (data.schools || [])
      setSchools(schoolList)
      if (schoolList.length > 0) {
        setSelectedSchoolId(schoolList[0].id)
      }
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('readingBundleDistribution.failedToLoadSchools'))
    }
  }


  useEffect(() => {
    fetchSchools()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const fetchDistributions = async () => {
    if (!selectedSchoolId) return
    setDistributionsLoading(true)
    try {
      const data = await fetchApi(
        `/school-partnerships/take-home-bundles/${selectedSchoolId}/distributions`
      )
      setDistributions(data.distributions || [])
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('readingBundleDistribution.failedToLoadDistributions'))
    } finally {
      setDistributionsLoading(false)
    }
  }


  const fetchBundles = async () => {
    if (!selectedSchoolId) return
    setLoading(true)
    try {
      const data = await fetchApi(`/school-partnerships/take-home-bundles/${selectedSchoolId}`)
      setBundles(data.bundles || [])
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('readingBundleDistribution.failedToLoadReadingBundles'))
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    if (selectedSchoolId) {
      fetchBundles()
      fetchDistributions()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSchoolId])

  const handleDistributeBundle = async () => {
    if (!selectedBundle || !selectedSchoolId || !studentName || !className) {
      toast.error(t('readingBundleDistribution.pleaseFillInAllRequired'))
      return
    }

    try {
      await fetchApi(
        `/school-partnerships/take-home-bundles/${selectedBundle.id}/distribute`,
        {
          method: 'POST',
          body: JSON.stringify({
            student_name: studentName,
            class_name: className,
          }),
        }
      )
      toast.success(t('toast.readingBundleDistribution.bundleDistributedSuccessfully'))
      setShowDistributionModal(false)
      setSelectedBundle(null)
      setStudentName('')
      setClassName('')
      fetchBundles()
      fetchDistributions()
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('readingBundleDistribution.failedToDistributeBundle'))
    }
  }

  const handleReturnBundle = async (distributionId: string, feedback?: string) => {
    try {
      await fetchApi(
        `/school-partnerships/take-home-bundles/distributions/${distributionId}/return`,
        {
          method: 'POST',
          body: JSON.stringify({ feedback }),
        }
      )
      toast.success(t('toast.readingBundleDistribution.bundleReturnRecorded'))
      fetchDistributions()
      fetchBundles()
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('readingBundleDistribution.failedToRecordBundleReturn'))
    }
  }

  const themes = [...new Set(bundles.map((b) => b.themeOrGradeLevel))]
  const filteredBundles = bundles.filter((bundle) => {
    return filterTheme === '' || bundle.themeOrGradeLevel === filterTheme
  })

  return (

    <AdminShell title="Take-Home Reading Bundles">    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="font-serif text-4xl font-bold text-lsc-dark dark:text-lsc-cream mb-4">
            Take-Home Reading Bundles
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Manage reading bundle distributions to students and families
          </p>
        </div>

        {/* Controls */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                School
              </label>
              <select
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

            <div>
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                Theme/Grade
              </label>
              <select
                value={filterTheme}
                onChange={(e) => setFilterTheme(e.target.value)}
                className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100"
              >
                <option value="">-- All Themes --</option>
                {themes.map((theme) => (
                  <option key={theme} value={theme}>
                    {theme}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-end">
              <button
                onClick={() => setView('bundles')}
                className={`flex-1 px-4 py-2 rounded-lg font-medium transition ${
                  view === 'bundles'
                    ? 'bg-earth-600 text-white'
                    : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream'
                }`}
              >
                Available Bundles
              </button>
            </div>

            <div className="flex items-end">
              <button
                onClick={() => setView('distributions')}
                className={`flex-1 px-4 py-2 rounded-lg font-medium transition relative ${
                  view === 'distributions'
                    ? 'bg-earth-600 text-white'
                    : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream'
                }`}
              >
                Distributions
                {distributions.filter((d) => d.status === 'distributed').length > 0 && (
                  <span className="absolute -top-2 -right-2 bg-status-danger-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
                    {distributions.filter((d) => d.status === 'distributed').length}
                  </span>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Available Bundles */}
        {view === 'bundles' && (
          <div className="space-y-6">
            {loading ? (
              <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
                Loading bundles...
              </div>
            ) : filteredBundles.length === 0 ? (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-12 text-center">
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('readingBundleDistribution.noReadingBundlesAvailable')}</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {filteredBundles.map((bundle) => (
                  <div
                    key={bundle.id}
                    className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6 hover:shadow-lg transition"
                  >
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream mb-2">
                          {bundle.title}
                        </h3>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
                          {bundle.description}
                        </p>
                      </div>
                      <span className="px-3 py-1 rounded-full text-sm font-semibold bg-earth-100 dark:bg-earth-800 text-earth-900 dark:text-earth-200">
                        {bundle.themeOrGradeLevel}
                      </span>
                    </div>

                    <div className="space-y-2 mb-4 p-3 bg-earth-50 dark:bg-earth-700 rounded-lg">
                      <div className="flex justify-between text-sm">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Books:</span>
                        <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                          {bundle.numberOfBooks}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Available:</span>
                        <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                          {bundle.totalCopiesAvailable} copies
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Ready Tomorrow:</span>
                        <span className="font-semibold text-status-success-600 dark:text-status-success-400">
                          {bundle.copiesTomorrow} copies
                        </span>
                      </div>
                    </div>

                    <div className="mb-4">
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">Reading Levels:</p>
                      <div className="flex flex-wrap gap-2">
                        {bundle.readingLevels.map((level) => (
                          <span
                            key={level}
                            className="px-2 py-1 text-xs rounded-full bg-status-success-100 dark:bg-status-success-900 text-status-success-900 dark:text-status-success-100"
                          >
                            {level}
                          </span>
                        ))}
                      </div>
                    </div>

                    <button
                      onClick={() => {
                        setSelectedBundle(bundle)
                        setShowDistributionModal(true)
                      }}
                      disabled={bundle.totalCopiesAvailable === 0}
                      title={bundle.totalCopiesAvailable === 0 ? 'No copies available' : undefined}
                      className={`w-full px-4 py-2 rounded-lg transition font-medium ${bundle.totalCopiesAvailable === 0 ? 'bg-earth-300 dark:bg-earth-600 text-earth-600 dark:text-earth-400 cursor-not-allowed' : 'bg-earth-600 text-white hover:bg-earth-700'}`}
                    >
                      Distribute Bundle
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Distributions */}
        {view === 'distributions' && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg overflow-hidden">
            {distributions.length === 0 ? (
              <div className="p-12 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                No bundles distributed yet.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-earth-100 dark:bg-earth-700 border-b border-lsc-border dark:border-earth-700">
                    <tr>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        Bundle
                      </th>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        Student
                      </th>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        Class
                      </th>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        Distributed
                      </th>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        Status
                      </th>
                      <th className="px-6 py-3 text-right text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-earth-200 dark:divide-earth-700">
                    {distributions.map((dist) => (
                      <tr key={dist.id} className="hover:bg-earth-50 dark:hover:bg-earth-700 transition">
                        <td className="px-6 py-4 text-lsc-dark dark:text-lsc-cream font-medium">
                          {dist.bundleTitle}
                        </td>
                        <td className="px-6 py-4 text-lsc-dark dark:text-lsc-cream">{dist.studentName}</td>
                        <td className="px-6 py-4 text-lsc-dark/70 dark:text-lsc-cream/70">{dist.className}</td>
                        <td className="px-6 py-4 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
                          {new Date(dist.distributedDate).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={`px-3 py-1 rounded-full text-sm font-semibold ${
                              dist.status === 'returned'
                                ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-900 dark:text-status-success-200'
                                : dist.status === 'distributed'
                                  ? 'bg-earth-100 dark:bg-earth-800/30 text-earth-900 dark:text-lsc-rose-light/80'
                                  : 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-900 dark:text-status-warning-200'
                            }`}
                          >
                            {dist.status.charAt(0).toUpperCase() + dist.status.slice(1)}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right">
                          {dist.status === 'distributed' && (
                            <button
                              onClick={() => handleReturnBundle(dist.id)}
                              className="px-3 py-1 text-status-success-600 dark:text-status-success-400 hover:bg-status-success-50 dark:hover:bg-status-success-900/20 rounded transition text-sm"
                            >
                              Mark Returned
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Distribution Modal */}
        {showDistributionModal && selectedBundle && (
          <ModalBackdrop onClose={() => setShowDistributionModal(false)} title="Distribute Bundle">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full p-8">
              <h2 id="distribute-modal-title" className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
                Distribute Bundle
              </h2>

              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
                <span className="font-semibold">{selectedBundle.title}</span>
              </p>

              <div className="space-y-4 mb-6">
                <div>
                  <label htmlFor="distribute-student-name" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                    Student Name *
                  </label>
                  <input
                    id="distribute-student-name"
                    type="text"
                    value={studentName}
                    onChange={(e) => setStudentName(e.target.value)}
                    placeholder={t('placeholder.readingBundleDistribution.enterStudentName')}
                    className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100 placeholder-earth-500 dark:placeholder-earth-400"
                  />
                </div>

                <div>
                  <label htmlFor="distribute-class-grade" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                    Class/Grade *
                  </label>
                  <input
                    id="distribute-class-grade"
                    type="text"
                    value={className}
                    onChange={(e) => setClassName(e.target.value)}
                    placeholder={t('placeholder.readingBundleDistribution.eg3rdGradeA')}
                    className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100 placeholder-earth-500 dark:placeholder-earth-400"
                  />
                </div>
              </div>

              <div className="flex gap-4">
                <button
                  onClick={() => {
                    setShowDistributionModal(false)
                    setSelectedBundle(null)
                    setStudentName('')
                    setClassName('')
                  }}
                  className="flex-1 px-4 py-2 bg-earth-200 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-earth-300 dark:hover:bg-earth-600 transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDistributeBundle}
                  className="flex-1 px-4 py-2 bg-earth-600 text-white rounded-lg hover:bg-earth-700 transition font-medium"
                >
                  Distribute
                </button>
              </div>
            </div>
          </ModalBackdrop>
        )}
      </div>
    </div>
  </AdminShell>
  )
}