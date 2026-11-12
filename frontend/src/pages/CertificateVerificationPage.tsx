/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams, useSearchParams } from 'react-router-dom'
import {
  Award,
  Search,
  CheckCircle,
  XCircle,
  Loader2,
  Download,
  Calendar,
  User,
  BookOpen,
  Shield,
} from 'lucide-react'
import {
  verifyCertificate,
  getMyCertificates,
  downloadCertificate,
} from '@/api/api'
import { useAuth } from '@/contexts/AuthContext'
import toast from 'react-hot-toast'
import { useTranslation} from '@/i18n'
import { useBranding } from '@/contexts/BrandingContext'
import PageContainer from '@/components/layout/PageContainer'

export default function CertificateVerificationPage(): React.ReactElement {
  const branding = useBranding()
  const { t } = useTranslation()
  const { user } = useAuth()
  const [searchParams] = useSearchParams()
  const params = useParams<{ certNumber?: string }>()
  // Prefer path param (/verify/:certNumber) over ?code=... over empty.
  const initialCode = (params.certNumber || searchParams.get('code') || '').trim()

  const [certificateNumber, setCertificateNumber] = useState(initialCode)
  const [searchedCode, setSearchedCode] = useState(initialCode)

  // Verification query
  const { data: verificationResult, isLoading: verifying } = useQuery({
    queryKey: ['certificate', 'verify', searchedCode],
    queryFn: () => verifyCertificate(searchedCode),
    enabled: !!searchedCode,
    retry: false,
  })

  // Privacy-respecting recipient name for the public verify panel:
  // prefer backend-supplied first name, else fall back to the first token
  // of user_name. Never render the full surname publicly.
  const recipientFirstName = verificationResult
    ? (verificationResult.recipient_first_name?.trim() || verificationResult.user_name?.trim().split(/\s+/)[0] || '')
    : ''

  // My certificates query
  const { data: myCertificates, isLoading: loadingMyCerts } = useQuery({
    queryKey: ['certificates', 'mine'],
    queryFn: getMyCertificates,
    enabled: !!user,
  })

  const handleVerify = (e: React.FormEvent) => {
    e.preventDefault()
    if (certificateNumber.trim()) {
      setSearchedCode(certificateNumber.trim())
    }
  }

  const handleDownload = async (courseId: number, courseName: string) => {
    try {
      const blob = await downloadCertificate(courseId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `certificate-${courseName.toLowerCase().replace(/\+/g, '-')}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      toast.success(t('toast.certificateVerification.certificateDownloaded'))
    } catch {
      toast.error(t('certificateVerification.failedToDownloadCertificate'))
    }
  }

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900">
      <PageContainer className="py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-lsc-rose/20 mb-4">
            <Shield className="w-8 h-8 text-lsc-rose" />
          </div>
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Certificate Verification</h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">{t('certificateVerification.verifyTheAuthenticityOfLearning')}</p>
        </div>

        {/* Verification Form */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-6 mb-8">
          <form onSubmit={handleVerify} className="flex gap-3">
            <div className="relative flex-1">
              <Award className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
              <input
                type="text"
                value={certificateNumber}
                onChange={(e) => setCertificateNumber(e.target.value)}
                placeholder={t('certificateVerification.enterCertificateNumberEG')}
                className="w-full pl-10 pr-4 py-3 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <button
              type="submit"
              disabled={verifying || !certificateNumber.trim()}
              className="px-6 py-3 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50 flex items-center gap-2"
            >
              {verifying ? <Loader2 className="w-5 h-5 motion-safe:animate-spin" /> : <Search className="w-5 h-5" />}
              Verify
            </button>
          </form>
        </div>

        {/* Verification Result */}
        {searchedCode && (
          <div className="mb-8">
            {verifying ? (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-8 text-center">
                <Loader2 className="w-12 h-12 motion-safe:animate-spin text-lsc-rose mx-auto mb-4" />
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Verifying certificate...</p>
              </div>
            ) : verificationResult?.is_valid ? (
              <div className="bg-status-success-50 dark:bg-status-success-900/20 rounded-lg border border-status-success-200 dark:border-status-success-800 p-6">
                <div className="flex items-start gap-4">
                  <div className="p-3 rounded-full bg-status-success-100 dark:bg-status-success-900/40">
                    <CheckCircle className="w-8 h-8 text-status-success-600 dark:text-status-success-400" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="font-serif text-xl font-bold text-status-success-800 dark:text-status-success-200">Verified</h3>
                      <span aria-label="Verified" className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-status-success-100 dark:bg-status-success-900/40 text-status-success-800 dark:text-status-success-200">
                        <CheckCircle className="w-3.5 h-3.5" /> Verified
                      </span>
                    </div>
                    <p className="text-status-success-700 dark:text-status-success-300 mb-4">
                      Issued by {branding.library_name}.
                    </p>

                    <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 space-y-3">
                      <div className="flex items-center gap-3">
                        <User className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                        <div>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Recipient</p>
                          <p className="font-medium text-lsc-dark dark:text-lsc-cream">{recipientFirstName || 'Library Learner'}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <BookOpen className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                        <div>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Course</p>
                          <p className="font-medium text-lsc-dark dark:text-lsc-cream">{verificationResult.course_title}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Calendar className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                        <div>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Issued</p>
                          <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                            {new Date(verificationResult.issued_at).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Award className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                        <div>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Certificate Number</p>
                          <p className="font-mono font-medium text-lsc-dark dark:text-lsc-cream">{verificationResult.certificate_number}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-status-danger-50 dark:bg-status-danger-900/20 rounded-lg border border-status-danger-200 dark:border-status-danger-800 p-6">
                <div className="flex items-start gap-4">
                  <div className="p-3 rounded-full bg-status-danger-100 dark:bg-status-danger-900/40">
                    <XCircle className="w-8 h-8 text-status-danger-600 dark:text-status-danger-400" />
                  </div>
                  <div>
                    <h3 className="font-serif text-xl font-bold text-status-danger-800 dark:text-status-danger-200 mb-2">Certificate Not Found</h3>
                    <p className="text-status-danger-700 dark:text-status-danger-300">
                      No certificate found with this number. Please check the number and try again.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* My Certificates */}
        {user && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700">
            <div className="p-4 border-b border-lsc-border dark:border-earth-700">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                <Award className="w-5 h-5 text-lsc-rose" />
                My Certificates
              </h2>
            </div>

            {loadingMyCerts ? (
              <div className="flex items-center justify-center h-32">
                <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
              </div>
            ) : myCertificates && myCertificates.length > 0 ? (
              <div className="divide-y divide-earth-200 dark:divide-earth-700">
                {myCertificates.map((cert) => (
                  <div key={cert.id} className="p-4 flex items-center justify-between hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-700/50">
                    <div className="flex items-center gap-4">
                      <div className="p-2 rounded-full bg-lsc-rose/20">
                        <Award className="w-6 h-6 text-lsc-rose" />
                      </div>
                      <div>
                        <p className="font-medium text-lsc-dark dark:text-lsc-cream">{cert.course_title}</p>
                        <div className="flex items-center gap-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                          <span>Issued: {new Date(cert.issued_at).toLocaleDateString()}</span>
                          <span className="font-mono">{cert.certificate_number}</span>
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDownload(cert.course_id, cert.course_title)}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-200 dark:hover:bg-earth-600"
                    >
                      <Download className="w-4 h-4" />
                      Download
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                <Award className="w-12 h-12 mx-auto mb-4 text-earth-300 dark:text-earth-300" />
                <p>{t('certificateVerification.noCertificatesYetCompleteA')}</p>
              </div>
            )}
          </div>
        )}

        {/* Info Box */}
        <div className="mt-8 bg-earth-50 dark:bg-earth-800/20 rounded-lg border border-lsc-border dark:border-earth-700 p-4">
          <h4 className="font-medium text-earth-800 dark:text-lsc-rose-light/80 mb-2">About Certificate Verification</h4>
          <p className="text-sm text-lsc-rose dark:text-lsc-rose-light">
            Each certificate issued by {branding.library_name} has a unique certificate number.
            Employers, institutions, or other parties can use this page to verify the authenticity
            of any certificate by entering its unique number.
          </p>
        </div>
      </PageContainer>
    </div>
  )
}
