/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useId } from 'react'
import { useTranslation} from '../i18n/I18nContext'
import toast from 'react-hot-toast'
import { Button } from '@/components/ui/Button'
import { fetchApi } from '@/api/fetchApi'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

// Shapes mirror _serialize_visit (snake_case) in
// backend/app/api/v1/school_reading/family_engagement.py. The page previously
// read camelCase + fields the serializer never emits (startTime/endTime/
// activities/notes do not exist).
interface LibraryVisit {
  id: number
  school_name: string | null
  scheduled_date: string | null
  number_of_students: number | null
  grade_level: string | null
  teacher_name: string | null
  status: string
}

interface VisitRequest {
  id: number
  school_name?: string | null
  request_date: string
  number_of_students: number | null
  grade_level: string | null
  teacher_name: string | null
  purpose: string | null
  status: string
}

export default function LibraryVisitSchedulingPage() {
  const { t } = useTranslation()
  const schoolSelectId = useId()
  const requestedDateId = useId()
  const teacherNameId = useId()
  const gradeLevelId = useId()
  const numberOfStudentsId = useId()
  const purposeId = useId()
  const [loading, setLoading] = useState(true)
  const [visits, setVisits] = useState<LibraryVisit[]>([])
  const [requests, setRequests] = useState<VisitRequest[]>([])
  const [selectedSchoolId, setSelectedSchoolId] = useState<string>('')
  const [schools, setSchools] = useState<Array<{ id: string; name: string }>>([])
  const [showRequestModal, setShowRequestModal] = useState(false)
  const [requestedDate, setRequestedDate] = useState('')
  const [numberOfStudents, setNumberOfStudents] = useState('')
  const [gradeLevel, setGradeLevel] = useState('')
  const [teacherName, setTeacherName] = useState('')
  const [purpose, setPurpose] = useState('')
  const [view, setView] = useState<'scheduled' | 'requests'>('scheduled')

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
      toast.error(t('libraryVisitScheduling.failedToLoadSchools'))
    }
  }


  useEffect(() => {
    fetchSchools()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const fetchRequests = async () => {
    if (!selectedSchoolId) return
    try {
      const data = await fetchApi(`/school-partnerships/library-visits/requests/${selectedSchoolId}`)
      setRequests(data.requests || [])
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }


  const fetchVisits = async () => {
    if (!selectedSchoolId) return
    setLoading(true)
    try {
      const data = await fetchApi(`/school-partnerships/library-visits/${selectedSchoolId}`)
      setVisits(data.visits || [])
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('libraryVisitScheduling.failedToLoadLibraryVisits'))
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    if (selectedSchoolId) {
      fetchVisits()
      fetchRequests()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSchoolId])

  const handleSubmitRequest = async () => {
    if (!selectedSchoolId || !requestedDate || !numberOfStudents || !gradeLevel || !teacherName || !purpose) {
      toast.error(t('libraryVisitScheduling.pleaseFillInAllRequired'))
      return
    }

    try {
      await fetchApi('/school-partnerships/library-visits/request', {
        method: 'POST',
        body: JSON.stringify({
          schoolId: selectedSchoolId,
          requestedDate,
          numberOfStudents: parseInt(numberOfStudents),
          gradeLevel,
          teacherName,
          purpose,
        }),
      })
      toast.success(t('libraryVisitScheduling.visitRequestSubmittedSuccessfully'))
      setShowRequestModal(false)
      setRequestedDate('')
      setNumberOfStudents('')
      setGradeLevel('')
      setTeacherName('')
      setPurpose('')
      fetchRequests()
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('libraryVisitScheduling.failedToSubmitVisitRequest'))
    }
  }

  const handleCancelRequest = async (requestId: number) => {
    try {
      await fetchApi(`/school-partnerships/library-visits/requests/${requestId}`, {
        method: 'DELETE',
      })
      toast.success(t('toast.interlibraryLoan.requestCancelled'))
      fetchRequests()
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('libraryVisitScheduling.failedToCancelRequest'))
    }
  }

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="font-serif text-4xl font-bold text-lsc-dark dark:text-lsc-cream mb-4">
            Library Visit Scheduling
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Schedule and track school visits to the library
          </p>
        </div>

        {/* Controls */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6 mb-8">
          <div className="flex flex-col md:flex-row gap-4 items-end">
            <div className="flex-1">
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

            <div role="group" aria-label="Library visits view" className="flex gap-2 w-full md:w-auto">
              <Button variant="primary"
                aria-pressed={view === 'scheduled'}
                onClick={() => setView('scheduled')}
              >
                Scheduled Visits
              </Button>
              <Button variant="danger"
                aria-pressed={view === 'requests'}
                onClick={() => setView('requests')}
              >
                My Requests
                {requests.filter((r) => r.status === 'pending').length > 0 && (
                  <span aria-label={`${requests.filter((r) => r.status === 'pending').length} pending requests`}>
                    {requests.filter((r) => r.status === 'pending').length}
                  </span>
                )}
              </Button>
              <Button variant="primary"
                onClick={() => setShowRequestModal(true)}
              >
                Request Visit
              </Button>
            </div>
          </div>
        </div>

        {/* Scheduled Visits */}
        {view === 'scheduled' && (
          <div className="space-y-6">
            {loading ? (
              <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
                Loading visits...
              </div>
            ) : visits.length === 0 ? (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-12 text-center">
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                  No scheduled visits yet. Request a visit to get started!
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {visits.map((visit) => (
                  <div key={visit.id} className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6">
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h3 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream mb-1">
                          {visit.school_name}
                        </h3>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          {visit.grade_level} Class
                        </p>
                      </div>
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap ${
                          visit.status === 'scheduled'
                            ? 'bg-earth-100 dark:bg-earth-800/30 text-earth-900 dark:text-lsc-rose-light/80'
                            : visit.status === 'completed'
                              ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-900 dark:text-status-success-200'
                              : 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-900 dark:text-status-danger-200'
                        }`}
                      >
                        {visit.status.charAt(0).toUpperCase() + visit.status.slice(1)}
                      </span>
                    </div>

                    <div className="space-y-2 mb-4 p-3 bg-earth-50 dark:bg-earth-700 rounded-lg">
                      <div className="flex justify-between text-sm">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Date:</span>
                        <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                          {visit.scheduled_date
                            ? new Date(visit.scheduled_date).toLocaleDateString()
                            : 'Not yet scheduled'}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Students:</span>
                        <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                          {visit.number_of_students}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Teacher:</span>
                        <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                          {visit.teacher_name}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Requests */}
        {view === 'requests' && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg overflow-hidden">
            {requests.length === 0 ? (
              <div className="p-12 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                No visit requests submitted yet. Submit a request to schedule a visit!
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-earth-100 dark:bg-earth-700 border-b border-lsc-border dark:border-earth-700">
                    <tr>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        Date Requested
                      </th>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        Teacher
                      </th>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        Grade/Students
                      </th>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        Purpose
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
                    {requests.map((request) => (
                      <tr key={request.id} className="hover:bg-earth-50 dark:hover:bg-earth-700 transition">
                        <td className="px-6 py-4 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
                          {request.request_date ? new Date(request.request_date).toLocaleDateString() : '--'}
                        </td>
                        <td className="px-6 py-4 text-lsc-dark dark:text-lsc-cream">{request.teacher_name}</td>
                        <td className="px-6 py-4 text-lsc-dark dark:text-lsc-cream text-sm">
                          {request.grade_level} / {request.number_of_students} students
                        </td>
                        <td className="px-6 py-4 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
                          {request.purpose}
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={`px-3 py-1 rounded-full text-sm font-semibold whitespace-nowrap ${
                              request.status === 'approved'
                                ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-900 dark:text-status-success-200'
                                : request.status === 'scheduled'
                                  ? 'bg-earth-100 dark:bg-earth-800/30 text-earth-900 dark:text-lsc-rose-light/80'
                                  : request.status === 'pending'
                                    ? 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-900 dark:text-status-warning-200'
                                    : 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-900 dark:text-status-danger-200'
                            }`}
                          >
                            {request.status.charAt(0).toUpperCase() + request.status.slice(1)}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right">
                          {request.status === 'pending' && (
                            <Button variant="danger"
                              onClick={() => handleCancelRequest(request.id)}
                            >
                              Cancel
                            </Button>
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

        {/* Request Modal */}
        {showRequestModal && (
          <ModalBackdrop onClose={() => setShowRequestModal(false)} title="Request Library Visit">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full p-8 my-8">
              <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-6">
                Request Library Visit
              </h2>

              <div className="space-y-4 mb-6">
                <div>
                  <label htmlFor={requestedDateId} className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                    Requested Date *
                  </label>
                  <input
                    id={requestedDateId}
                    type="date"
                    required
                    value={requestedDate}
                    onChange={(e) => setRequestedDate(e.target.value)}
                    className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100"
                  />
                </div>

                <div>
                  <label htmlFor={teacherNameId} className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                    Teacher Name *
                  </label>
                  <input
                    id={teacherNameId}
                    type="text"
                    required
                    value={teacherName}
                    onChange={(e) => setTeacherName(e.target.value)}
                    placeholder={t('placeholder.escalationModal.yourName')}
                    className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100 placeholder-earth-500 dark:placeholder-earth-400"
                  />
                </div>

                <div>
                  <label htmlFor={gradeLevelId} className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                    Grade Level *
                  </label>
                  <input
                    id={gradeLevelId}
                    type="text"
                    required
                    value={gradeLevel}
                    onChange={(e) => setGradeLevel(e.target.value)}
                    placeholder={t('placeholder.libraryVisitScheduling.eg3rdGrade')}
                    className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100 placeholder-earth-500 dark:placeholder-earth-400"
                  />
                </div>

                <div>
                  <label htmlFor={numberOfStudentsId} className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                    Number of Students *
                  </label>
                  <input
                    id={numberOfStudentsId}
                    type="number"
                    required
                    min="1"
                    value={numberOfStudents}
                    onChange={(e) => setNumberOfStudents(e.target.value)}
                    placeholder={t('placeholder.libraryVisitScheduling.numberOfStudents')}
                    className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100 placeholder-earth-500 dark:placeholder-earth-400"
                  />
                </div>

                <div>
                  <label htmlFor={purposeId} className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                    Purpose/Goals *
                  </label>
                  <textarea
                    id={purposeId}
                    required
                    value={purpose}
                    onChange={(e) => setPurpose(e.target.value)}
                    placeholder={t('libraryVisitScheduling.whatWouldYouLikeTo')}
                    rows={3}
                    className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100 placeholder-earth-500 dark:placeholder-earth-400"
                  />
                </div>
              </div>

              <div className="flex gap-4">
                <Button variant="primary"
                  onClick={() => setShowRequestModal(false)}
                >
                  Cancel
                </Button>
                <Button variant="primary"
                  onClick={handleSubmitRequest}
                >
                  Submit Request
                </Button>
              </div>
            </div>
          </ModalBackdrop>
        )}
      </div>
    </div>
  )
}