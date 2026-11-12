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

interface ReadingChallenge {
  id: string
  title: string
  description: string
  startDate: string
  endDate: string
  goalMinutes: number
  goalBooks: number
  targetAgeGroup: string
  theme: string
  prizes?: string
  participantCount: number
  schoolId: string
}

interface ChallengeRegistration {
  id: string
  challengeId: string
  challengeTitle: string
  familyName: string
  studentAge: number
  registrationDate: string
  minutesRead: number
  booksRead: number
  goalMinutes: number
  goalBooks: number
  progressPercentage: number
  status: 'active' | 'completed' | 'abandoned'
}

export default function FamilyReadingChallengesPage() {
  const { t } = useTranslation()
  const schoolSelectId = useId()
  const familyNameId = useId()
  const studentAgeId = useId()
  const [loading, setLoading] = useState(false)
  const [challenges, setChallenges] = useState<ReadingChallenge[]>([])
  const [registrations, setRegistrations] = useState<ChallengeRegistration[]>([])
  const [selectedSchoolId, setSelectedSchoolId] = useState<string>('')
  const [schools, setSchools] = useState<Array<{ id: string; name: string }>>([])
  const [selectedChallenge, setSelectedChallenge] = useState<ReadingChallenge | null>(null)
  const [showRegistrationModal, setShowRegistrationModal] = useState(false)
  const [registering, setRegistering] = useState(false)
  const [familyName, setFamilyName] = useState('')
  const [studentAge, setStudentAge] = useState('')
  const [view, setView] = useState<'challenges' | 'myProgress'>('challenges')

  const fetchSchools = async () => {
    try {
      const data = await fetchApi('/school-partnerships/schools')
      const list = Array.isArray(data) ? data : (data?.schools ?? [])
      setSchools(list)
      if (list.length > 0) {
        setSelectedSchoolId(list[0].id)
      }
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('familyReadingChallenges.failedToLoadSchools'))
    }
  }


  useEffect(() => {
    fetchSchools()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const fetchRegistrations = async () => {
    if (!selectedSchoolId) return
    try {
      const data = await fetchApi(
        `/school-partnerships/family-challenges/${selectedSchoolId}/registrations`
      )
      setRegistrations(data.registrations || [])
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }


  const fetchChallenges = async () => {
    if (!selectedSchoolId) return
    setLoading(true)
    try {
      const data = await fetchApi(`/school-partnerships/family-challenges/${selectedSchoolId}`)
      setChallenges(data.challenges || [])
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('familyReadingChallenges.failedToLoadChallenges'))
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    if (selectedSchoolId) {
      fetchChallenges()
      fetchRegistrations()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSchoolId])

  const handleRegisterChallenge = async () => {
    if (!selectedChallenge || !selectedSchoolId || !familyName || !studentAge) {
      toast.error(t('familyReadingChallenges.pleaseFillInAllRequired'))
      return
    }

    setRegistering(true)
    try {
      await fetchApi(`/school-partnerships/family-challenges/${selectedChallenge.id}/register`, {
        method: 'POST',
        body: JSON.stringify({
          schoolId: selectedSchoolId,
          familyName,
          studentAge: parseInt(studentAge),
        }),
      })
      toast.success(t('toast.familyReadingChallenges.challengeRegisteredSuccessfully'))
      setShowRegistrationModal(false)
      setSelectedChallenge(null)
      setFamilyName('')
      setStudentAge('')
      fetchChallenges()
      fetchRegistrations()
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('familyReadingChallenges.failedToRegisterForChallenge'))
    } finally {
      setRegistering(false)
    }
  }

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="font-serif text-4xl font-bold text-lsc-dark dark:text-lsc-cream mb-4">
            Family Reading Challenges
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Engage families in fun reading challenges
          </p>
        </div>

        {/* Controls */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor={schoolSelectId} className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                School
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

            <div role="group" aria-label="Challenges view" className="flex gap-2 items-end">
              <button
                type="button"
                onClick={() => setView('challenges')}
                aria-pressed={view === 'challenges'}
                className={`min-h-[44px] flex-1 px-4 py-2 rounded-lg font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-earth-600 focus-visible:ring-offset-2 ${
                  view === 'challenges'
                    ? 'bg-earth-600 text-white'
                    : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream'
                }`}
              >
                Available Challenges
              </button>
              <button
                type="button"
                onClick={() => setView('myProgress')}
                aria-pressed={view === 'myProgress'}
                className={`min-h-[44px] flex-1 px-4 py-2 rounded-lg font-medium transition relative focus:outline-none focus-visible:ring-2 focus-visible:ring-earth-600 focus-visible:ring-offset-2 ${
                  view === 'myProgress'
                    ? 'bg-earth-600 text-white'
                    : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream'
                }`}
              >
                My Challenges
                {registrations.length > 0 && (
                  <span aria-label={`${registrations.length} registered`} className="absolute -top-2 -right-2 bg-status-danger-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
                    {registrations.length}
                  </span>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Available Challenges */}
        {view === 'challenges' && (
          <div className="space-y-6">
            {loading ? (
              <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
                Loading challenges...
              </div>
            ) : challenges.length === 0 ? (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-12 text-center">
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No challenges available.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {challenges.map((challenge) => {
                  const isActive = new Date(challenge.startDate) <= new Date() && new Date() <= new Date(challenge.endDate)
                  return (
                    <div
                      key={challenge.id}
                      className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6 hover:shadow-lg transition"
                    >
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <h3 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream mb-2">
                            {challenge.title}
                          </h3>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            {challenge.description}
                          </p>
                        </div>
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap ${
                            isActive
                              ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-900 dark:text-status-success-200'
                              : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream'
                          }`}
                        >
                          {isActive ? 'Active' : 'Upcoming'}
                        </span>
                      </div>

                      <div className="space-y-2 mb-4 p-3 bg-earth-50 dark:bg-earth-700 rounded-lg">
                        <div className="flex justify-between text-sm">
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Age Group:</span>
                          <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                            {challenge.targetAgeGroup}
                          </span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Goal:</span>
                          <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                            {challenge.goalMinutes} min / {challenge.goalBooks} books
                          </span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Participants:</span>
                          <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                            {challenge.participantCount}
                          </span>
                        </div>
                        {challenge.prizes && (
                          <div className="flex justify-between text-sm">
                            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Prizes:</span>
                            <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                              ✓
                            </span>
                          </div>
                        )}
                      </div>

                      <button
                        onClick={() => {
                          setSelectedChallenge(challenge)
                          setShowRegistrationModal(true)
                        }}
                        disabled={!isActive}
                        className="w-full px-4 py-2 bg-earth-600 text-white rounded-lg hover:bg-earth-700 disabled:bg-earth-400 transition font-medium"
                      >
                        {isActive ? 'Join Challenge' : 'Challenge Not Active'}
                      </button>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {/* My Progress */}
        {view === 'myProgress' && (
          <div className="space-y-6">
            {registrations.length === 0 ? (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-12 text-center">
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                  No challenges joined yet. Join a challenge to track your progress!
                </p>
              </div>
            ) : (
              registrations.map((reg) => (
                <div key={reg.id} className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6">
                  <div className="mb-6">
                    <h3 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
                      {reg.challengeTitle}
                    </h3>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      Family: {reg.familyName} | Student Age: {reg.studentAge}
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                    {/* Reading Minutes Progress */}
                    <div>
                      <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
                        Reading Minutes
                      </h4>
                      <div className="mb-3">
                        <div className="flex justify-between text-sm mb-2">
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                            {reg.minutesRead} / {reg.goalMinutes} minutes
                          </span>
                          <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                            {reg.goalMinutes > 0 ? Math.round((reg.minutesRead / reg.goalMinutes) * 100) : 0}%
                          </span>
                        </div>
                        <div className="w-full bg-earth-200 dark:bg-earth-700 rounded-full h-4 overflow-hidden">
                          <div
                            className="bg-lsc-rose h-full transition-all duration-500"
                            style={{
                              width: `${reg.goalMinutes > 0 ? Math.min((reg.minutesRead / reg.goalMinutes) * 100, 100) : 0}%`,
                            }}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Books Read Progress */}
                    <div>
                      <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
                        Books Read
                      </h4>
                      <div className="mb-3">
                        <div className="flex justify-between text-sm mb-2">
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/70">
                            {reg.booksRead} / {reg.goalBooks} books
                          </span>
                          <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                            {reg.goalBooks > 0 ? Math.round((reg.booksRead / reg.goalBooks) * 100) : 0}%
                          </span>
                        </div>
                        <div className="w-full bg-earth-200 dark:bg-earth-700 rounded-full h-4 overflow-hidden">
                          <div
                            className="bg-status-success-600 h-full transition-all duration-500"
                            style={{
                              width: `${reg.goalBooks > 0 ? Math.min((reg.booksRead / reg.goalBooks) * 100, 100) : 0}%`,
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-between items-center p-3 bg-earth-50 dark:bg-earth-700 rounded-lg mb-6">
                    <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Overall Progress:</span>
                    <span
                      className={`px-3 py-1 rounded-full text-sm font-semibold ${
                        reg.progressPercentage >= 100
                          ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-900 dark:text-status-success-200'
                          : reg.progressPercentage >= 75
                            ? 'bg-earth-100 dark:bg-earth-800/30 text-earth-900 dark:text-lsc-rose-light/80'
                            : 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-900 dark:text-status-warning-200'
                      }`}
                    >
                      {reg.progressPercentage.toFixed(0)}%
                    </span>
                  </div>

                  <span
                    className={`inline-block px-3 py-1 rounded-full text-sm font-semibold ${
                      reg.status === 'completed'
                        ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-900 dark:text-status-success-200'
                        : reg.status === 'active'
                          ? 'bg-earth-100 dark:bg-earth-800/30 text-earth-900 dark:text-lsc-rose-light/80'
                          : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream'
                    }`}
                  >
                    {reg.status.charAt(0).toUpperCase() + reg.status.slice(1)}
                  </span>
                </div>
              ))
            )}
          </div>
        )}

        {/* Registration Modal */}
        {showRegistrationModal && selectedChallenge && (
          <ModalBackdrop onClose={() => { setShowRegistrationModal(false); setSelectedChallenge(null) }} title="Join Challenge">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full p-8">
              <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
                Join Challenge
              </h2>

              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
                <span className="font-semibold">{selectedChallenge.title}</span>
              </p>

              <div className="space-y-4 mb-6">
                <div>
                  <label htmlFor={familyNameId} className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                    Family Name *
                  </label>
                  <input
                    id={familyNameId}
                    type="text"
                    required
                    value={familyName}
                    onChange={(e) => setFamilyName(e.target.value)}
                    placeholder={t('placeholder.familyReadingChallenges.enterFamilyName')}
                    className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100 placeholder-earth-500 dark:placeholder-earth-400"
                  />
                </div>

                <div>
                  <label htmlFor={studentAgeId} className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                    Student Age *
                  </label>
                  <input
                    id={studentAgeId}
                    type="number"
                    required
                    min="3"
                    max="18"
                    value={studentAge}
                    onChange={(e) => setStudentAge(e.target.value)}
                    placeholder={t('placeholder.familyReadingChallenges.age')}
                    className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100 placeholder-earth-500 dark:placeholder-earth-400"
                  />
                </div>
              </div>

              <div className="flex gap-4">
                <button
                  onClick={() => {
                    setShowRegistrationModal(false)
                    setSelectedChallenge(null)
                    setFamilyName('')
                    setStudentAge('')
                  }}
                  className="flex-1 px-4 py-2 bg-earth-200 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-earth-300 dark:hover:bg-earth-600 transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleRegisterChallenge}
                  disabled={registering}
                  className="flex-1 px-4 py-2 bg-earth-600 text-white rounded-lg hover:bg-earth-700 disabled:bg-earth-400 transition font-medium"
                >
                  {registering ? 'Joining...' : 'Join'}
                </button>
              </div>
            </div>
          </ModalBackdrop>
        )}
      </div>
    </div>
  )
}