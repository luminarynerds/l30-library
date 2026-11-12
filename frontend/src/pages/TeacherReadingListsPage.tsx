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

// Shapes mirror the backend response models (snake_case, plural arrays,
// embedded items[]). See SharedReadingListResponse / SharedReadingListItemResponse
// in backend/app/schemas/reading.py. fetchApi does no key transform, so the
// component reads these fields as the API emits them.
interface ReadingListItem {
  id: number
  isbn?: string | null
  title: string
  author?: string | null
  reading_level?: string | null
  description?: string | null
  librarian_notes?: string | null
  teacher_notes?: string | null
}

interface ReadingList {
  id: number
  name: string
  description?: string | null
  curriculum_alignment?: string | null
  grade_levels: string[]
  reading_levels: string[]
  topics: string[]
  items?: ReadingListItem[]
}

interface ListRequest {
  listId: number
  listTitle: string
  requestDate: string
  status: 'pending' | 'approved' | 'fulfilled' | 'rejected'
  copies?: number
}

export default function TeacherReadingListsPage() {
  const { t } = useTranslation()
  const schoolSelectId = useId()
  const gradeSelectId = useId()
  const topicSelectId = useId()
  const searchInputId = useId()
  const requestCopiesId = useId()
  const [loading, setLoading] = useState(true)
  const [lists, setLists] = useState<ReadingList[]>([])
  const [selectedList, setSelectedList] = useState<ReadingList | null>(null)
  const [listItems, setListItems] = useState<ReadingListItem[]>([])
  const [listRequests, setListRequests] = useState<ListRequest[]>([])
  const [selectedSchoolId, setSelectedSchoolId] = useState<string>('')
  const [schools, setSchools] = useState<Array<{ id: string; name: string }>>([])
  const [showListModal, setShowListModal] = useState(false)
  const [showRequestModal, setShowRequestModal] = useState(false)
  const [requestCopies, setRequestCopies] = useState(1)
  const [view, setView] = useState<'browse' | 'requests' | 'classroom'>('browse')
  const [searchQuery, setSearchQuery] = useState('')
  const [filterGrade, setFilterGrade] = useState('')
  const [filterTopic, setFilterTopic] = useState('')

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
      toast.error(t('teacherReadingLists.failedToLoadSchools'))
    }
  }


  useEffect(() => {
    fetchSchools()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const fetchListRequests = async () => {
    if (!selectedSchoolId) return
    try {
      const data = await fetchApi(`/school-partnerships/schools/${selectedSchoolId}/reading-list-requests`)
      const list = Array.isArray(data) ? data : (data?.requests ?? [])
      setListRequests(list)
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }


  const fetchLists = async () => {
    if (!selectedSchoolId) return
    setLoading(true)
    try {
      const data = await fetchApi(`/school-partnerships/schools/${selectedSchoolId}/reading-lists`)
      const list = Array.isArray(data) ? data : (data?.lists ?? [])
      setLists(list)
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('teacherReadingLists.failedToLoadReadingLists'))
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    if (selectedSchoolId) {
      fetchLists()
      fetchListRequests()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSchoolId])

  const fetchListItems = async (listId: number) => {
    try {
      const data = await fetchApi(`/school-partnerships/reading-lists/${listId}`)
      setListItems(data.items || [])
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('teacherReadingLists.failedToLoadReadingList'))
    }
  }

  const handleViewList = async (list: ReadingList) => {
    setSelectedList(list)
    await fetchListItems(list.id)
    setShowListModal(true)
  }

  const handleRequestList = async () => {
    if (!selectedList || !selectedSchoolId) return

    try {
      await fetchApi(`/school-partnerships/schools/${selectedSchoolId}/reading-lists/${selectedList.id}/request`, {
        method: 'POST',
        body: JSON.stringify({
          copies: requestCopies,
          notes: '',
        }),
      })
      toast.success(t('toast.teacherReadingLists.readingListRequestedTitle', { title: selectedList.name }))
      setShowRequestModal(false)
      setRequestCopies(1)
      fetchListRequests()
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('teacherReadingLists.failedToRequestReadingList'))
    }
  }

  const filteredLists = lists.filter((list) => {
    const q = searchQuery.toLowerCase()
    return (
      (searchQuery === '' ||
        list.name.toLowerCase().includes(q) ||
        (list.description ?? '').toLowerCase().includes(q)) &&
      (filterGrade === '' || (list.grade_levels ?? []).includes(filterGrade)) &&
      (filterTopic === '' || (list.topics ?? []).includes(filterTopic))
    )
  })

  const topics = [...new Set(lists.flatMap((l) => l.topics ?? []))]
  const grades = [...new Set(lists.flatMap((l) => l.grade_levels ?? []))]

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="font-serif text-4xl font-bold text-lsc-dark dark:text-lsc-cream mb-4">
            Shared Reading Lists
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Discover curated reading lists for your classroom
          </p>
        </div>

        {/* Controls */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
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

            <div>
              <label htmlFor={gradeSelectId} className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                Grade Level
              </label>
              <select
                id={gradeSelectId}
                value={filterGrade}
                onChange={(e) => setFilterGrade(e.target.value)}
                className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100"
              >
                <option value="">-- All Grades --</option>
                {grades.map((grade) => (
                  <option key={grade} value={grade}>
                    {grade}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor={topicSelectId} className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                Topic
              </label>
              <select
                id={topicSelectId}
                value={filterTopic}
                onChange={(e) => setFilterTopic(e.target.value)}
                className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100"
              >
                <option value="">-- All Topics --</option>
                {topics.map((topic) => (
                  <option key={topic} value={topic}>
                    {topic}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor={searchInputId} className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                Search
              </label>
              <input
                id={searchInputId}
                type="text"
                placeholder={t('placeholder.teacherReadingLists.searchLists')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100 placeholder-earth-500 dark:placeholder-earth-400"
              />
            </div>
          </div>

          <div role="group" aria-label="Reading lists view" className="flex gap-2 justify-center">
            <button
              type="button"
              onClick={() => setView('browse')}
              aria-pressed={view === 'browse'}
              className={`min-h-[44px] px-6 py-2 rounded-lg font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-earth-600 focus-visible:ring-offset-2 ${
                view === 'browse'
                  ? 'bg-earth-600 text-white'
                  : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream'
              }`}
            >
              Browse Lists
            </button>
            <button
              type="button"
              onClick={() => setView('requests')}
              aria-pressed={view === 'requests'}
              className={`min-h-[44px] px-6 py-2 rounded-lg font-medium transition relative focus:outline-none focus-visible:ring-2 focus-visible:ring-earth-600 focus-visible:ring-offset-2 ${
                view === 'requests'
                  ? 'bg-earth-600 text-white'
                  : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream'
              }`}
            >
              My Requests
              {listRequests.length > 0 && (
                <span aria-label={`${listRequests.length} requests`} className="absolute -top-2 -right-2 bg-status-danger-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
                  {listRequests.length}
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Browse View */}
        {view === 'browse' && (
          <div className="space-y-6">
            {loading ? (
              <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
                Loading reading lists...
              </div>
            ) : filteredLists.length === 0 ? (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-12 text-center">
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                  No reading lists found matching your criteria.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredLists.map((list) => (
                  <div
                    key={list.id}
                    className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6 hover:shadow-lg transition"
                  >
                    <div className="mb-4">
                      <h3 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream mb-2">
                        {list.name}
                      </h3>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
                        {list.description}
                      </p>
                    </div>

                    <div className="flex flex-wrap gap-2 mb-4">
                      {(list.grade_levels ?? []).map((grade) => (
                        <span key={`g-${grade}`} className="px-2 py-1 text-xs rounded-full bg-earth-100 dark:bg-earth-800 text-earth-900 dark:text-earth-200">
                          Grade {grade}
                        </span>
                      ))}
                      {(list.topics ?? []).map((topic) => (
                        <span key={`t-${topic}`} className="px-2 py-1 text-xs rounded-full bg-category-100 dark:bg-category-900 text-category-900 dark:text-category-100">
                          {topic}
                        </span>
                      ))}
                      <span className="px-2 py-1 text-xs rounded-full bg-status-success-100 dark:bg-status-success-900 text-status-success-900 dark:text-status-success-100">
                        {list.items?.length ?? 0} books
                      </span>
                    </div>

                    {list.curriculum_alignment && (
                      <div className="mb-4 p-3 bg-earth-50 dark:bg-earth-700 rounded-lg">
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">
                          {list.curriculum_alignment}
                        </p>
                      </div>
                    )}

                    <div className="flex gap-2">
                      <button
                        onClick={() => handleViewList(list)}
                        className="flex-1 px-4 py-2 bg-earth-600 text-white rounded-lg hover:bg-earth-700 transition text-sm font-medium"
                      >
                        View Details
                      </button>
                      <button
                        onClick={() => {
                          setSelectedList(list)
                          setShowRequestModal(true)
                        }}
                        className="flex-1 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition text-sm font-medium"
                      >
                        Request
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Requests View */}
        {view === 'requests' && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg overflow-hidden">
            {listRequests.length === 0 ? (
              <div className="p-12 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                No reading list requests yet. Browse and request lists to get started!
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-earth-100 dark:bg-earth-700 border-b border-lsc-border dark:border-earth-700">
                    <tr>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        Reading List
                      </th>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        Request Date
                      </th>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        Copies
                      </th>
                      <th className="px-6 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                        Status
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-earth-200 dark:divide-earth-700">
                    {listRequests.map((request) => (
                      <tr
                        key={request.listId}
                        className="hover:bg-earth-50 dark:hover:bg-earth-700 transition"
                      >
                        <td className="px-6 py-4 text-lsc-dark dark:text-lsc-cream font-medium">
                          {request.listTitle}
                        </td>
                        <td className="px-6 py-4 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
                          {new Date(request.requestDate).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 text-lsc-dark dark:text-lsc-cream">
                          {request.copies || '--'}
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={`px-3 py-1 rounded-full text-sm font-semibold ${
                              request.status === 'fulfilled'
                                ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-900 dark:text-status-success-200'
                                : request.status === 'approved'
                                  ? 'bg-earth-100 dark:bg-earth-800/30 text-earth-900 dark:text-lsc-rose-light/80'
                                  : request.status === 'pending'
                                    ? 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-900 dark:text-status-warning-200'
                                    : 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-900 dark:text-status-danger-200'
                            }`}
                          >
                            {request.status.charAt(0).toUpperCase() + request.status.slice(1)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* List Details Modal */}
        {showListModal && selectedList && (
          <ModalBackdrop onClose={() => setShowListModal(false)} title="Reading List Details">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-2xl w-full p-8 my-8">
              <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
                {selectedList.name}
              </h2>

              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">{selectedList.description}</p>

              <div className="grid grid-cols-2 gap-4 mb-6 p-4 bg-earth-50 dark:bg-earth-700 rounded-lg">
                <div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Grade Levels</p>
                  <p className="font-semibold text-lsc-dark dark:text-lsc-cream">
                    {(selectedList.grade_levels ?? []).join(', ') || '--'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Topics</p>
                  <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{(selectedList.topics ?? []).join(', ') || '--'}</p>
                </div>
                <div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Number of Books</p>
                  <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{listItems.length}</p>
                </div>
                <div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Alignment</p>
                  <p className="font-semibold text-lsc-dark dark:text-lsc-cream">
                    {selectedList.curriculum_alignment || '--'}
                  </p>
                </div>
              </div>

              <div className="mb-6">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
                  Books in this List
                </h3>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {listItems.map((item) => (
                    <div
                      key={item.id}
                      className="p-3 bg-earth-50 dark:bg-earth-700 rounded-lg"
                    >
                      <p className="font-semibold text-lsc-dark dark:text-lsc-cream">
                        {item.title}{item.author ? ` by ${item.author}` : ''}
                      </p>
                      {item.reading_level && (
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          Level: {item.reading_level}
                        </p>
                      )}
                      {item.librarian_notes && (
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                          📝 {item.librarian_notes}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex gap-4">
                <button
                  onClick={() => setShowListModal(false)}
                  className="flex-1 px-4 py-2 bg-earth-200 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-earth-300 dark:hover:bg-earth-600 transition"
                >
                  Close
                </button>
                <button
                  onClick={() => {
                    setShowListModal(false)
                    setShowRequestModal(true)
                  }}
                  className="flex-1 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition"
                >
                  Request This List
                </button>
              </div>
            </div>
          </ModalBackdrop>
        )}

        {/* Request Modal */}
        {showRequestModal && selectedList && (
          <ModalBackdrop onClose={() => setShowRequestModal(false)} title="Request Reading List">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full p-8">
              <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
                Request Reading List
              </h2>

              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                <span className="font-semibold">{selectedList.name}</span>
              </p>

              <div className="mb-6">
                <label htmlFor={requestCopiesId} className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
                  Number of Copies
                </label>
                <input
                  id={requestCopiesId}
                  type="number"
                  min="1"
                  max="50"
                  value={requestCopies}
                  onChange={(e) => setRequestCopies(parseInt(e.target.value) || 1)}
                  className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100"
                />
              </div>

              <div className="flex gap-4">
                <button
                  onClick={() => {
                    setShowRequestModal(false)
                    setRequestCopies(1)
                  }}
                  className="flex-1 px-4 py-2 bg-earth-200 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-earth-300 dark:hover:bg-earth-600 transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleRequestList}
                  className="flex-1 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition"
                >
                  Request
                </button>
              </div>
            </div>
          </ModalBackdrop>
        )}
      </div>
    </div>
  )
}