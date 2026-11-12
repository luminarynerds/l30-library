/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useRef } from 'react'
import { useTranslation} from '../i18n/I18nContext'
import toast from 'react-hot-toast'
import { API_BASE } from '@/api/types'
import { fetchApi } from '@/api/fetchApi'
import { getAccessToken } from '@/utils/tokenStore'
import { AdminShell } from '../components/shells/AdminShell'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface Certification {
  id: number
  teacher_name: string
  school_name: string
  certification_level: string
  certification_name: string
  certification_number: string | null
  date_earned: string | null
  expires_at: string | null
  required_modules_completed: number
  total_modules_required: number
  status: 'active' | 'expired' | 'pending'
}

const LEVEL_COLORS: { [key: string]: string } = {
  bronze: 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-900 dark:text-status-warning-200',
  silver: 'bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream',
  gold: 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-900 dark:text-status-warning-200',
  platinum: 'bg-category-100 dark:bg-category-900/30 text-category-900 dark:text-category-200',
}

export default function ReadingAmbassadorPage() {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [certifications, setCertifications] = useState<Certification[]>([])
  const [selectedSchoolId, setSelectedSchoolId] = useState<string>('')
  const [schools, setSchools] = useState<Array<{ id: string; name: string }>>([])
  const [filterLevel, setFilterLevel] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [selectedCert, setSelectedCert] = useState<Certification | null>(null)
  const [showCertModal, setShowCertModal] = useState(false)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newCert, setNewCert] = useState({
    user_id: '',
    partner_id: '',
    certification_level: 'bronze',
    certification_name: 'Reading Ambassador - Bronze',
  })

  const fetchedRef = useRef(false)

  const fetchSchools = async () => {
    try {
      const data = await fetchApi('/school-partnerships/schools')
      const list = Array.isArray(data) ? data : data.schools || []
      const mapped = list.map((s: { id: number; name: string }) => ({
        id: String(s.id),
        name: s.name,
      }))
      setSchools(mapped)
      if (mapped.length > 0) {
        setSelectedSchoolId(mapped[0].id)
      } else {
        setLoading(false)
      }
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('readingAmbassador.failedToLoadSchools'))
      setLoading(false)
    }
  }


  useEffect(() => {
    if (fetchedRef.current) return
    fetchedRef.current = true
    fetchSchools()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const fetchCertifications = async () => {
    if (!selectedSchoolId) return
    setLoading(true)
    try {
      const data = await fetchApi(
        `/school-partnerships/ambassador-certifications/${selectedSchoolId}`
      )
      setCertifications(data.certifications || [])
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('readingAmbassador.failedToLoadCertifications'))
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    if (selectedSchoolId) {
      fetchCertifications()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSchoolId])

  const handleDownloadCertificate = async (certId: number) => {
    try {
      // Binary download (PDF blob); fetchApi parses JSON, so keep raw fetch
      // with manual Authorization header.
      const token = getAccessToken()
      // eslint-disable-next-line no-restricted-syntax -- Ambassador cert PDF binary download
      const response = await fetch(
        `${API_BASE}/school-partnerships/ambassador-certifications/${certId}/download`,
        { headers: token ? { Authorization: `Bearer ${token}` } : {} }
      )
      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `reading-ambassador-certificate-${certId}.pdf`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
        toast.success(t('toast.certificateVerification.certificateDownloaded'))
      }
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('readingAmbassador.failedToDownloadCertificate'))
    }
  }

  const handleRenew = async (certId: number) => {
    try {
      await fetchApi(
        `/school-partnerships/ambassador-certifications/${certId}/renew`,
        { method: 'POST' }
      )
      toast.success('Certification renewed successfully')
      fetchCertifications()
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error('Failed to renew certification')
    }
  }

  const handleCreateCertification = async () => {
    if (!newCert.user_id || !newCert.partner_id) {
      toast.error('Please fill in all required fields')
      return
    }
    try {
      await fetchApi(
        '/school-partnerships/ambassador-certifications',
        {
          method: 'POST',
          body: JSON.stringify({
            user_id: parseInt(newCert.user_id),
            partner_id: parseInt(newCert.partner_id),
            certification_level: newCert.certification_level,
            certification_name: newCert.certification_name,
          }),
        }
      )
      toast.success('Certification created successfully')
      setShowCreateModal(false)
      setNewCert({ user_id: '', partner_id: '', certification_level: 'bronze', certification_name: 'Reading Ambassador - Bronze' })
      fetchCertifications()
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      const message = (error && typeof error === 'object' && 'message' in error) ? String((error as { message: unknown }).message) : 'Failed to create certification'
      toast.error(message)
    }
  }

  const filteredCerts = certifications.filter((cert) => {
    return (
      (filterLevel === '' || cert.certification_level === filterLevel) &&
      (filterStatus === '' || cert.status === filterStatus)
    )
  })

  const levels = [...new Set(certifications.map((c) => c.certification_level))]
  const statuses = [...new Set(certifications.map((c) => c.status))]

  return (
    <AdminShell
      title="Reading Ambassadors"
      subtitle="Certified teachers leading reading initiatives in schools"
      actions={
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 transition text-sm font-medium whitespace-nowrap"
        >
          + New Certification
        </button>
      }
    >
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6">
            <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
              Total Ambassadors
            </h3>
            <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">
              {certifications.length}
            </p>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6">
            <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
              Active
            </h3>
            <p className="text-3xl font-bold text-status-success-600 dark:text-status-success-400">
              {certifications.filter((c) => c.status === 'active').length}
            </p>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6">
            <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
              Pending
            </h3>
            <p className="text-3xl font-bold text-status-warning-600 dark:text-status-warning-400">
              {certifications.filter((c) => c.status === 'pending').length}
            </p>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6">
            <h3 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
              Expired
            </h3>
            <p className="text-3xl font-bold text-status-danger-600 dark:text-status-danger-400">
              {certifications.filter((c) => c.status === 'expired').length}
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label htmlFor="school-filter" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                School
              </label>
              <select
                id="school-filter"
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
              <label htmlFor="level-filter" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                Level
              </label>
              <select
                id="level-filter"
                value={filterLevel}
                onChange={(e) => setFilterLevel(e.target.value)}
                className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100"
              >
                <option value="">-- All Levels --</option>
                {levels.map((level) => (
                  <option key={level} value={level}>
                    {level}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="status-filter" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                Status
              </label>
              <select
                id="status-filter"
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100"
              >
                <option value="">-- All Status --</option>
                {statuses.map((status) => (
                  <option key={status} value={status}>
                    {status.charAt(0).toUpperCase() + status.slice(1)}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Certifications */}
        {loading ? (
          <div aria-live="polite" className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
            Loading certifications...
          </div>
        ) : filteredCerts.length === 0 ? (
          <div aria-live="polite" className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-12 text-center">
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              No reading ambassador certifications found.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredCerts.map((cert) => (
              <div
                key={cert.id}
                className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6 hover:shadow-lg transition"
              >
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream mb-1">
                      {cert.teacher_name}
                    </h3>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{cert.school_name}</p>
                    <p className="text-xs text-earth-600 dark:text-earth-400 italic">{cert.certification_name}</p>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-semibold ${LEVEL_COLORS[cert.certification_level.toLowerCase()] || 'bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream'}`}
                  >
                    {cert.certification_level}
                  </span>
                </div>

                <div className="space-y-2 mb-4">
                  <div className="flex justify-between text-sm">
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Earned:</span>
                    <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                      {cert.date_earned ? new Date(cert.date_earned).toLocaleDateString() : 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Expires:</span>
                    <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                      {cert.expires_at ? new Date(cert.expires_at).toLocaleDateString() : 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Cert #:</span>
                    <span className="font-mono text-xs text-lsc-dark dark:text-lsc-cream">
                      {cert.certification_number}
                    </span>
                  </div>
                  {cert.total_modules_required > 0 && (
                    <div className="flex justify-between text-sm">
                      <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Training:</span>
                      <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
                        {cert.required_modules_completed}/{cert.total_modules_required} modules
                      </span>
                    </div>
                  )}
                </div>

                <div className="mb-4">
                  <span
                    className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${
                      cert.status === 'active'
                        ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-900 dark:text-status-success-200'
                        : cert.status === 'pending'
                          ? 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-900 dark:text-status-warning-200'
                          : 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-900 dark:text-status-danger-200'
                    }`}
                  >
                    {cert.status.charAt(0).toUpperCase() + cert.status.slice(1)}
                  </span>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      setSelectedCert(cert)
                      setShowCertModal(true)
                    }}
                    aria-label={`View certificate for ${cert.teacher_name}`}
                    className="flex-1 px-3 py-2 bg-earth-600 text-white rounded-lg hover:bg-earth-700 focus-visible:ring-2 focus-visible:ring-earth-500 focus-visible:ring-offset-2 transition text-sm font-medium"
                  >
                    View
                  </button>
                  <button
                    onClick={() => handleDownloadCertificate(cert.id)}
                    aria-label={`Download certificate for ${cert.teacher_name}`}
                    className="flex-1 px-3 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 transition text-sm font-medium"
                  >
                    Download
                  </button>
                  {cert.status === 'expired' && (
                    <button
                      onClick={() => handleRenew(cert.id)}
                      className="flex-1 px-3 py-2 bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 focus-visible:ring-2 focus-visible:ring-status-success-500 focus-visible:ring-offset-2 transition text-sm font-medium"
                    >
                      Renew
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Certificate Detail Modal */}
        {showCertModal && selectedCert && (
          <ModalBackdrop onClose={() => setShowCertModal(false)} title="Reading Ambassador Certificate">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-2xl w-full p-8 my-8">
              <h2 id="cert-modal-title" className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-8 text-center">
                Reading Ambassador Certificate
              </h2>

              <div className="border-4 border-status-warning-400 rounded-lg p-8 bg-status-warning-50 dark:bg-status-warning-900/10 text-center space-y-6 mb-8">
                <div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">This certifies that</p>
                  <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">
                    {selectedCert.teacher_name}
                  </p>
                </div>

                <div>
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">has achieved the status of</p>
                  <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream uppercase">
                    {selectedCert.certification_level} Reading Ambassador
                  </p>
                </div>

                <div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                    for exceptional service to reading programs
                  </p>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    at {selectedCert.school_name}
                  </p>
                </div>

                <div className="border-t-2 border-lsc-border dark:border-earth-700 pt-6">
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Date Earned</p>
                  <p className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                    {selectedCert.date_earned ? new Date(selectedCert.date_earned).toLocaleDateString() : 'N/A'}
                  </p>
                </div>

                <div>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Certificate Number</p>
                  <p className="text-sm font-mono text-lsc-dark dark:text-lsc-cream">
                    {selectedCert.certification_number}
                  </p>
                </div>
              </div>

              <div className="flex gap-4">
                <button
                  onClick={() => setShowCertModal(false)}
                  className="flex-1 px-4 py-2 bg-earth-200 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-earth-300 dark:hover:bg-earth-600 transition"
                >
                  Close
                </button>
                <button
                  onClick={() => {
                    handleDownloadCertificate(selectedCert.id)
                    setShowCertModal(false)
                  }}
                  className="flex-1 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition"
                >
                  Download PDF
                </button>
              </div>
            </div>
          </ModalBackdrop>
        )}

        {/* Create Certification Modal */}
        {showCreateModal && (
          <ModalBackdrop onClose={() => setShowCreateModal(false)} title="New Ambassador Certification">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-lg w-full p-8 my-8">
              <h2 id="create-cert-title" className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-6">
                New Ambassador Certification
              </h2>

              <div className="space-y-4">
                <div>
                  <label htmlFor="create-user-id" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                    User ID
                  </label>
                  <input
                    id="create-user-id"
                    type="number"
                    value={newCert.user_id}
                    onChange={(e) => setNewCert({ ...newCert, user_id: e.target.value })}
                    className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100"
                    placeholder="Teacher's user ID"
                  />
                </div>

                <div>
                  <label htmlFor="create-school" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                    School
                  </label>
                  <select
                    id="create-school"
                    value={newCert.partner_id}
                    onChange={(e) => setNewCert({ ...newCert, partner_id: e.target.value })}
                    className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100"
                  >
                    <option value="">-- Select School --</option>
                    {schools.map((school) => (
                      <option key={school.id} value={school.id}>
                        {school.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label htmlFor="create-level" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                    Level
                  </label>
                  <select
                    id="create-level"
                    value={newCert.certification_level}
                    onChange={(e) => {
                      const level = e.target.value
                      setNewCert({
                        ...newCert,
                        certification_level: level,
                        certification_name: `Reading Ambassador - ${level.charAt(0).toUpperCase() + level.slice(1)}`,
                      })
                    }}
                    className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100"
                  >
                    <option value="bronze">Bronze</option>
                    <option value="silver">Silver</option>
                    <option value="gold">Gold</option>
                    <option value="platinum">Platinum</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="create-cert-name" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                    Certification Name
                  </label>
                  <input
                    id="create-cert-name"
                    type="text"
                    value={newCert.certification_name}
                    onChange={(e) => setNewCert({ ...newCert, certification_name: e.target.value })}
                    className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100"
                  />
                </div>
              </div>

              <div className="flex gap-4 mt-6">
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-4 py-2 bg-earth-200 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-earth-300 dark:hover:bg-earth-600 transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateCertification}
                  className="flex-1 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 transition"
                >
                  Create
                </button>
              </div>
            </div>
          </ModalBackdrop>
        )}
    </AdminShell>
  )
}
