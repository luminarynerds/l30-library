/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect } from 'react'
import {
  MessageCircle, CheckCircle2, AlertCircle, Loader, Clock,
  Send, User, Mail, Phone, FileText, HelpCircle, ArrowRight,
  ChevronDown, ChevronUp, Search,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { clsx } from '@/utils/helpers'
import { useAuth } from '@/contexts/AuthContext'
import { useBranding } from '@/contexts/BrandingContext'
import {
  genealogyInquiriesApi,
  genealogyEnrollmentApi,
  type GenealogyInquiry,
  type CourseEnrollment,
} from '@/api/genealogy-api'
import { useTranslation} from '@/i18n'
import { t } from '@/i18n'

// ============================================================================
// Status badge helper
// ============================================================================

function getStatusConfig(t: (key: string, paramsOrFallback?: string) => string): Record<string, { label: string; color: string; icon: React.ReactNode; description: string }> {
  return {
    new: {
      label: t('genealogyInquiry.statusSubmitted', 'Submitted'),
      color: 'bg-earth-50 text-lsc-rose border-lsc-border dark:bg-earth-800/20 dark:text-lsc-rose-light dark:border-earth-700',
      icon: <Send className="w-3.5 h-3.5" />,
      description: t('genealogyInquiry.yourInquiryHasBeenReceived'),
    },
    in_progress: {
      label: t('genealogyInquiry.statusInProgress', 'In Progress'),
      color: 'bg-status-warning-50 text-status-warning-700 border-status-warning-200 dark:bg-status-warning-900/20 dark:text-status-warning-300 dark:border-status-warning-800',
      icon: <Search className="w-3.5 h-3.5" />,
      description: t('genealogyInquiry.aGenealogistIsActivelyResearching'),
    },
    responded: {
      label: t('genealogyInquiry.statusResponded', 'Responded'),
      color: 'bg-status-success-50 text-status-success-700 border-status-success-200 dark:bg-status-success-900/20 dark:text-status-success-300 dark:border-status-success-800',
      icon: <CheckCircle2 className="w-3.5 h-3.5" />,
      description: t('genealogyInquiry.aGenealogistHasRespondedToYourInquiry', 'A genealogist has responded to your inquiry. Check your email!'),
    },
    closed: {
      label: t('genealogyInquiry.statusClosed', 'Closed'),
      color: 'bg-earth-100 text-earth-600 border-lsc-border dark:bg-earth-700 dark:text-earth-300 dark:border-earth-700',
      icon: <FileText className="w-3.5 h-3.5" />,
      description: t('genealogyInquiry.thisInquiryHasBeenResolved'),
    },
  }
}

function StatusBadge({ status }: { status: string }) {
  const { t } = useTranslation()
  const statusConfig = getStatusConfig(t)
  const config = (statusConfig[status] ?? statusConfig.new)!
  return (
    <span className={clsx('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium', config.color)}>
      {config.icon}
      {config.label}
    </span>
  )
}

// ============================================================================
// Progress Indicator
// ============================================================================

const STATUS_STEPS = ['new', 'in_progress', 'responded', 'closed']

function InquiryProgressBar({ status }: { status: string }) {
  const { t } = useTranslation()
  const statusConfig = getStatusConfig(t)
  const currentIdx = STATUS_STEPS.indexOf(status)

  return (
    <div className="flex items-center gap-2 mt-4">
      {STATUS_STEPS.slice(0, 3).map((step, idx) => {
        const isPast = idx < currentIdx
        const isCurrent = idx === currentIdx
        const config = statusConfig[step]!

        return (
          <div key={step} className="flex items-center flex-1 last:flex-none">
            <div
              className={clsx(
                'flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-full transition-colors',
                isPast
                  ? 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300'
                  : isCurrent
                    ? 'bg-lsc-rose/10 text-lsc-rose dark:bg-lsc-rose/20 dark:text-lsc-rose-light'
                    : 'bg-earth-100 text-earth-600 dark:bg-earth-700 dark:text-earth-300'
              )}
            >
              {isPast ? (
                <CheckCircle2 className="w-3 h-3" />
              ) : (
                config.icon
              )}
              {config.label}
            </div>
            {idx < 2 && (
              <ArrowRight
                className={clsx(
                  'w-4 h-4 mx-1 flex-shrink-0',
                  isPast ? 'text-status-success-400' : 'text-earth-300 dark:text-earth-300'
                )}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

// ============================================================================
// Inquiry Card (for status tracking)
// ============================================================================

function InquiryCard({ inquiry }: { inquiry: GenealogyInquiry }) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)
  const statusConfig = getStatusConfig(t)
  const config = (statusConfig[inquiry.status] ?? statusConfig.new)!

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-5 flex items-start gap-4 text-left hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 transition-colors"
        aria-expanded={expanded}
      >
        <div className="w-10 h-10 rounded-lg bg-lsc-rose/10 flex items-center justify-center flex-shrink-0">
          <MessageCircle className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 flex-wrap">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream capitalize">
              {inquiry.research_topic.replace(/-/g, ' ')}
            </h3>
            <StatusBadge status={inquiry.status} />
          </div>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 line-clamp-1" title={inquiry.description}>
            {inquiry.description}
          </p>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {t('genealogyInquiry.submittedOn', { date: new Date(inquiry.created_at).toLocaleDateString() })}
          </p>
        </div>
        <div className="flex-shrink-0 text-lsc-dark/70 dark:text-lsc-cream/70">
          {expanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-lsc-border dark:border-earth-700 p-5 space-y-4">
          {/* Progress bar */}
          <div>
            <p className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider mb-2">
              {t('genealogyInquiry.statusProgress', 'Status Progress')}
            </p>
            <InquiryProgressBar status={inquiry.status} />
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
              {config.description}
            </p>
          </div>

          {/* Description */}
          <div>
            <p className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider mb-1">
              {t('genealogyInquiry.yourQuestion', 'Your Question')}
            </p>
            <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg p-3">
              {inquiry.description}
            </p>
          </div>

          {inquiry.current_challenges && (
            <div>
              <p className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider mb-1">
                {t('genealogyInquiry.challengesMentioned', 'Challenges Mentioned')}
              </p>
              <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg p-3">
                {inquiry.current_challenges}
              </p>
            </div>
          )}

          {/* Response from genealogist */}
          {inquiry.response_from_genealogist && (
            <div className="bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-lg p-4">
              <p className="text-xs font-semibold text-status-success-800 dark:text-status-success-200 uppercase tracking-wider mb-2 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                {t('genealogyInquiry.responseFromTheGenealogyDesk', 'Response from the Genealogy Desk')}
              </p>
              <p className="text-sm text-status-success-900 dark:text-status-success-100 whitespace-pre-wrap">
                {inquiry.response_from_genealogist}
              </p>
              {inquiry.responded_at && (
                <p className="text-xs text-status-success-700 dark:text-status-success-300 mt-2">
                  {t('genealogyInquiry.respondedOn', { date: new Date(inquiry.responded_at).toLocaleDateString() })}
                </p>
              )}
            </div>
          )}

          {inquiry.status === 'new' && (
            <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-lg p-3 flex gap-2">
              <Clock className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" />
              <p className="text-xs text-earth-900 dark:text-earth-200">
                {t('genealogyInquiry.staffRespondsWithinPrefix', 'Our staff typically responds within')}{' '}
                <strong>{t('genealogyInquiry.twoBusinessDays', '2 business days')}</strong>{' '}
                {t('genealogyInquiry.usingPreferredContactMethod', { contact: inquiry.preferred_contact })}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Submission Form
// ============================================================================

function getResearchTopics(t: (key: string, fallback?: string) => string) {
  return [
    { value: 'getting-started', label: t('genealogyInquiry.gettingStartedWithGenealogy') },
    { value: 'vital-records', label: t('genealogyInquiry.vitalRecordsBirthMarriageDeath') },
    { value: 'census', label: t('genealogyInquiry.censusRecords', 'Census Records') },
    { value: 'immigration', label: t('genealogyInquiry.immigrationAndNaturalization', 'Immigration & Naturalization') },
    { value: 'military', label: t('genealogyInquiry.militaryRecords', 'Military Records') },
    { value: 'land-records', label: t('genealogyInquiry.landAndPropertyRecords', 'Land & Property Records') },
    { value: 'dna', label: t('genealogyInquiry.dnaTestingAndInterpretation', 'DNA Testing & Interpretation') },
    { value: 'local-resources', label: t('genealogyInquiry.localAndRegionalResources', 'Local & Regional Resources') },
    { value: 'using-databases', label: t('genealogyInquiry.usingAncestryOrFamilysearch') },
    { value: 'roadblock', label: t('genealogyInquiry.imStuckGenealogyRoadblock', "I'm Stuck (Genealogy Roadblock)") },
    { value: 'other', label: t('genealogyInquiry.other', 'Other') },
  ]
}

function SubmissionForm({ onSuccess }: { onSuccess: (inquiry: GenealogyInquiry) => void }) {
  const branding = useBranding()
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
    preferredContact: 'email',
    researchTopic: '',
    description: '',
    currentChallenges: '',
  })
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.firstName.trim() || !formData.lastName.trim() || !formData.email.trim() || !formData.researchTopic || !formData.description.trim()) {
      toast.error(t('toast.genealogyInquiry.pleaseFillInAllRequired'))
      return
    }
    setIsSubmitting(true)
    try {
      const inquiry = await genealogyInquiriesApi.create({
        first_name: formData.firstName,
        last_name: formData.lastName,
        email: formData.email,
        phone: formData.phone || null,
        preferred_contact: formData.preferredContact,
        research_topic: formData.researchTopic,
        description: formData.description,
        current_challenges: formData.currentChallenges || null,
      })
      toast.success(t('toast.genealogyInquiry.inquirySubmittedStaffWillRespond', 'Inquiry submitted! Our staff will respond within 2 business days.'))
      onSuccess(inquiry)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('toast.genealogyInquiry.failedToSubmitYourInquiry'))
    } finally {
      setIsSubmitting(false)
    }
  }

  const inputClass = 'w-full px-4 py-2.5 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose'

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Personal Information */}
      <div>
        <h3 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <User className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          {t('genealogyInquiry.yourInformation', 'Your Information')}
        </h3>
        <div className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="firstName" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1.5">
                {t('genealogyInquiry.firstNameLabel', 'First Name')} <span className="text-status-danger-500">*</span>
              </label>
              <input
                type="text"
                id="firstName"
                name="firstName"
                value={formData.firstName}
                onChange={handleChange}
                required
                className={inputClass}
                placeholder={t('placeholder.authModals.jane')}
              />
            </div>
            <div>
              <label htmlFor="lastName" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1.5">
                {t('genealogyInquiry.lastNameLabel', 'Last Name')} <span className="text-status-danger-500">*</span>
              </label>
              <input
                type="text"
                id="lastName"
                name="lastName"
                value={formData.lastName}
                onChange={handleChange}
                required
                className={inputClass}
                placeholder={t('placeholder.genealogyInquiry.smith')}
              />
            </div>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1.5">
                <span className="flex items-center gap-1">
                  <Mail className="w-4 h-4" />
                  {t('genealogyInquiry.emailLabel', 'Email')} <span className="text-status-danger-500">*</span>
                </span>
              </label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
                className={inputClass}
                placeholder={t('placeholder.genealogyInquiry.janeexamplecom')}
              />
            </div>
            <div>
              <label htmlFor="phone" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1.5">
                <span className="flex items-center gap-1">
                  <Phone className="w-4 h-4" />
                  {t('genealogyInquiry.phoneOptional', 'Phone (Optional)')}
                </span>
              </label>
              <input
                type="tel"
                id="phone"
                name="phone"
                value={formData.phone}
                onChange={handleChange}
                className={inputClass}
              />
            </div>
          </div>
          <div>
            <label htmlFor="preferredContact" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1.5">
              {t('genealogyInquiry.preferredContactMethod', 'Preferred Contact Method')}
            </label>
            <select
              id="preferredContact"
              name="preferredContact"
              value={formData.preferredContact}
              onChange={handleChange}
              className={inputClass}
            >
              <option value="email">{t('genealogyInquiry.emailLabel', 'Email')}</option>
              <option value="phone">{t('genealogyInquiry.phoneLabel', 'Phone')}</option>
              <option value="either">{t('genealogyInquiry.eitherWorks', 'Either works')}</option>
            </select>
          </div>
        </div>
      </div>

      {/* Research Question */}
      <div className="border-t border-lsc-border dark:border-earth-700 pt-6">
        <h3 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <FileText className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          {t('genealogyInquiry.yourResearchQuestion', 'Your Research Question')}
        </h3>
        <div className="space-y-4">
          <div>
            <label htmlFor="researchTopic" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1.5">
              {t('genealogyInquiry.topicArea', 'Topic Area')} <span className="text-status-danger-500">*</span>
            </label>
            <select
              id="researchTopic"
              name="researchTopic"
              value={formData.researchTopic}
              onChange={handleChange}
              required
              className={inputClass}
            >
              <option value="">{t('genealogyInquiry.selectATopic', '-- Select a topic --')}</option>
              {getResearchTopics(t).map(topic => (
                <option key={topic.value} value={topic.value}>{topic.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="description" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1.5">
              {t('genealogyInquiry.describeYourQuestionOrResearch', 'Describe Your Question or Research Goal')} <span className="text-status-danger-500">*</span>
            </label>
            <textarea
              id="description"
              name="description"
              value={formData.description}
              onChange={handleChange}
              required
              rows={5}
              className={clsx(inputClass, 'resize-none')}
              placeholder={t('genealogyInquiry.tellUsAboutYourResearch', 'Tell us about your research. What are you trying to find? What have you already tried? Include names, dates, and locations if you know them.')}
            />
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              {t('genealogyInquiry.theMoreDetailYouProvide', 'The more detail you provide, the better our staff can help you.')}
            </p>
          </div>
          <div>
            <label htmlFor="currentChallenges" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1.5">
              {t('genealogyInquiry.whatHasBeenYourBiggest', 'What Has Been Your Biggest Challenge? (Optional)')}
            </label>
            <textarea
              id="currentChallenges"
              name="currentChallenges"
              value={formData.currentChallenges}
              onChange={handleChange}
              rows={3}
              className={clsx(inputClass, 'resize-none')}
              placeholder={t('placeholder.genealogyInquiry.egICantFind')}
            />
          </div>
        </div>
      </div>

      {/* Accessibility Note */}
      <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-lg p-4 flex gap-3">
        <HelpCircle className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" />
        <div className="text-sm text-earth-900 dark:text-earth-200">
          <strong>{t('genealogyInquiry.needHelpWithTheForm')}</strong>
          {branding.phone ? (
            <>
              {' '}{t('genealogyInquiry.callTheLibraryAtPrefix', 'Call the library at')}{' '}
              <a
                href={`tel:${branding.phone.replace(/\D/g, '')}`}
                className="text-lsc-rose dark:text-lsc-rose-light hover:underline"
              >
                {branding.phone}
              </a>
              {' '}{t('genealogyInquiry.andAskForTheGenealogyDesk', "and ask for the genealogy desk. We're happy to take your inquiry by phone.")}
            </>
          ) : (
            <>{' '}{t('genealogyInquiry.callTheLibraryAndAskForGenealogy', "Call the library and ask for the genealogy desk. We're happy to take your inquiry by phone.")}</>
          )}
        </div>
      </div>

      {/* Submit */}
      <div className="flex items-center gap-4">
        <button
          type="submit"
          disabled={isSubmitting}
          className={clsx(
            'flex items-center gap-2 px-6 py-3 rounded-lg font-medium text-white transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-earth-800',
            isSubmitting
              ? 'bg-lsc-rose/50 cursor-not-allowed'
              : 'bg-lsc-rose hover:bg-lsc-rose/90'
          )}
          aria-busy={isSubmitting}
        >
          {isSubmitting && <Loader className="w-4 h-4 motion-safe:animate-spin" />}
          <Send className="w-4 h-4" />
          {isSubmitting ? t('genealogyInquiry.submitting', 'Submitting...') : t('genealogyInquiry.submitInquiry', 'Submit Inquiry')}
        </button>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('genealogyInquiry.responseWithinTwoBusinessDays', 'Response within 2 business days')}
        </p>
      </div>
    </form>
  )
}

// ============================================================================
// Main Page Component
// ============================================================================

type ActiveTab = 'submit' | 'track'

export default function GenealogyInquiryPage(): React.ReactElement {
  const { t } = useTranslation()
  const { isAuthenticated } = useAuth()
  const [activeTab, setActiveTab] = useState<ActiveTab>('submit')
  const [myInquiries, setMyInquiries] = useState<GenealogyInquiry[]>([])
  const [myEnrollments, setMyEnrollments] = useState<CourseEnrollment[]>([])
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [submittedInquiry, setSubmittedInquiry] = useState<GenealogyInquiry | null>(null)

  const loadMyHistory = async () => {
    setIsLoadingHistory(true)
    try {
      const enrollments = await genealogyEnrollmentApi.getMyEnrollments()
      setMyEnrollments(enrollments)
    } catch {
      // Silently fail - user may not have any history
    } finally {
      setIsLoadingHistory(false)
    }
  }


  useEffect(() => {
    if (isAuthenticated && activeTab === 'track') {
      loadMyHistory()
    }
  }, [isAuthenticated, activeTab])

  const handleInquirySubmitted = (inquiry: GenealogyInquiry) => {
    setSubmittedInquiry(inquiry)
    setMyInquiries(prev => [inquiry, ...prev])
  }

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center space-y-3">
        <div className="flex justify-center mb-4">
          <div className="w-16 h-16 rounded-full bg-lsc-rose/10 dark:bg-lsc-rose/20 flex items-center justify-center">
            <MessageCircle className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
          </div>
        </div>
        <h1 className="text-3xl md:text-4xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          {t('genealogyInquiry.genealogyResearchInquiry', 'Genealogy Research Inquiry')}
        </h1>
        <p className="text-lg text-lsc-dark/70 dark:text-lsc-cream/70 max-w-xl mx-auto">
          {t('genealogyInquiry.submitAResearchQuestionAndGetHelp', 'Submit a research question and get personalized help from our local history desk.')}
        </p>
      </div>

      {/* About the Desk */}
      <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-xl p-5 border border-lsc-border dark:border-earth-700 flex items-start gap-4">
        <div className="w-12 h-12 rounded-full bg-lsc-rose/20 flex items-center justify-center flex-shrink-0 text-lsc-rose dark:text-lsc-rose-light">
          <MessageCircle className="w-6 h-6" />
        </div>
        <div>
          <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('genealogyInquiry.localHistoryAndGenealogyDesk', 'Local History & Genealogy Desk')}
          </h2>
          <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 mt-1">
            {t('genealogyInquiry.ourStaffSpecializesIn', 'Our staff specializes in vital records, census research, immigration records, and breaking through research "brick walls."')}
          </p>
        </div>
      </div>

      {/* Success state */}
      {submittedInquiry && (
        <div className="bg-status-success-50 dark:bg-status-success-900/20 border-2 border-status-success-200 dark:border-status-success-800 rounded-xl p-6">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="w-6 h-6 text-status-success-600 dark:text-status-success-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-serif font-semibold text-status-success-900 dark:text-status-success-100 text-lg mb-1">
                {t('genealogyInquiry.inquirySubmittedSuccessfully', 'Inquiry Submitted Successfully!')}
              </h3>
              <p className="text-status-success-800 dark:text-status-success-200 text-sm">
                {t('genealogyInquiry.staffWillRespondToYourQuestionPrefix', 'Our staff will respond to your question within')}{' '}
                <strong>{t('genealogyInquiry.twoBusinessDays', '2 business days')}</strong>{' '}
                {t('genealogyInquiry.viaContactMethod', { contact: submittedInquiry.preferred_contact })}
              </p>
              <div className="mt-3">
                <InquiryProgressBar status={submittedInquiry.status} />
              </div>
              <button
                onClick={() => setSubmittedInquiry(null)}
                className="mt-4 text-sm text-status-success-700 dark:text-status-success-300 underline hover:no-underline"
              >
                {t('genealogyInquiry.submitAnotherInquiry', 'Submit another inquiry')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div>
        <div className="border-b border-lsc-border dark:border-earth-700 mb-6">
          <nav className="flex gap-1" role="tablist">
            {[
              { id: 'submit' as ActiveTab, label: t('genealogyInquiry.submitNewInquiry', 'Submit New Inquiry'), icon: <Send className="w-4 h-4" /> },
              { id: 'track' as ActiveTab, label: t('genealogyInquiry.myHistory', 'My History'), icon: <Clock className="w-4 h-4" /> },
            ].map(tab => (
              <button
                key={tab.id}
                role="tab"
                aria-selected={activeTab === tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={clsx(
                  'flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors -mb-px',
                  activeTab === tab.id
                    ? 'border-lsc-rose text-lsc-rose dark:text-lsc-rose-light'
                    : 'border-transparent text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream'
                )}
              >
                {tab.icon}
                {tab.label}
                {tab.id === 'track' && myInquiries.length > 0 && (
                  <span className="ml-1 text-xs bg-lsc-rose text-white px-1.5 py-0.5 rounded-full">
                    {myInquiries.length}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        {/* Submit Tab */}
        {activeTab === 'submit' && !submittedInquiry && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
            <SubmissionForm onSuccess={handleInquirySubmitted} />
          </div>
        )}

        {/* Track Tab */}
        {activeTab === 'track' && (
          <div className="space-y-4">
            {!isAuthenticated ? (
              <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl p-6 text-center">
                <AlertCircle className="w-10 h-10 text-status-warning-600 dark:text-status-warning-400 mx-auto mb-3" />
                <h3 className="font-serif font-semibold text-status-warning-900 dark:text-status-warning-100 mb-2">
                  {t('genealogyInquiry.signInToTrackInquiries', 'Sign In to Track Inquiries')}
                </h3>
                <p className="text-sm text-status-warning-800 dark:text-status-warning-200 mb-4">
                  {t('genealogyInquiry.logInWithYourLibraryAccount', 'Log in with your library account to see the status of your genealogy inquiries and course enrollments.')}
                </p>
                <a
                  href="/login"
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2"
                >
                  {t('genealogyInquiry.signIn', 'Sign In')}
                </a>
              </div>
            ) : isLoadingHistory ? (
              <div className="flex items-center justify-center py-12">
                <Loader className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
                <span className="ml-3 text-lsc-dark/70 dark:text-lsc-cream/70">{t('genealogyInquiry.loadingYourHistory', 'Loading your history...')}</span>
              </div>
            ) : (
              <>
                {/* Inquiries submitted this session */}
                {myInquiries.length > 0 && (
                  <div className="space-y-3">
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                      {t('genealogyInquiry.recentInquiriesThisSession', 'Recent Inquiries This Session')}
                    </h3>
                    {myInquiries.map(inquiry => (
                      <InquiryCard key={inquiry.id} inquiry={inquiry} />
                    ))}
                  </div>
                )}

                {/* Course Enrollments */}
                {myEnrollments.length > 0 && (
                  <div className="space-y-3">
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                      {t('genealogyInquiry.myCourseEnrollments', 'My Course Enrollments')}
                    </h3>
                    {myEnrollments.map(enrollment => (
                      <div key={enrollment.id} className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4 flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                            {t('genealogyInquiry.courseHashId', { courseId: enrollment.course_id })}
                          </p>
                          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                            {t('genealogyInquiry.enrolledOn', { date: new Date(enrollment.enrolled_at).toLocaleDateString() })}
                          </p>
                        </div>
                        <span className={clsx(
                          'text-xs px-2.5 py-1 rounded-full font-medium',
                          enrollment.status === 'completed'
                            ? 'bg-status-success-50 text-status-success-700 dark:bg-status-success-900/20 dark:text-status-success-300'
                            : 'bg-earth-50 text-lsc-rose dark:bg-earth-800/20 dark:text-lsc-rose-light'
                        )}>
                          {enrollment.status.charAt(0).toUpperCase() + enrollment.status.slice(1)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {myInquiries.length === 0 && myEnrollments.length === 0 && (
                  <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
                    <MessageCircle className="w-12 h-12 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-3" />
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                      {t('genealogyInquiry.noHistoryYet', 'No History Yet')}
                    </h3>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                      {t('genealogyInquiry.submitYourFirstInquiry', 'Submit your first genealogy inquiry to get started.')}
                    </p>
                    <button
                      onClick={() => setActiveTab('submit')}
                      className="inline-flex items-center gap-2 px-5 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2"
                    >
                      <Send className="w-4 h-4" />
                      {t('genealogyInquiry.submitAnInquiry', 'Submit an Inquiry')}
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* Help Resources */}
      <div className="grid md:grid-cols-2 gap-4">
        <a
          href="/genealogy/training"
          className="flex items-center gap-4 p-4 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose hover:shadow-md transition-all group"
        >
          <div className="w-10 h-10 rounded-lg bg-lsc-rose/10 flex items-center justify-center flex-shrink-0 group-hover:bg-lsc-rose/20 transition-colors">
            <FileText className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <div>
            <p className="font-semibold text-lsc-dark dark:text-lsc-cream text-sm">{t('genealogyInquiry.genealogyTrainingCourses', 'Genealogy Training Courses')}</p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('genealogyInquiry.learnResearchSkillsWithFree')}</p>
          </div>
          <ArrowRight className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70 ml-auto group-hover:text-lsc-rose transition-colors" />
        </a>
        <a
          href="/genealogy/archives"
          className="flex items-center gap-4 p-4 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose hover:shadow-md transition-all group"
        >
          <div className="w-10 h-10 rounded-lg bg-lsc-rose/10 flex items-center justify-center flex-shrink-0 group-hover:bg-lsc-rose/20 transition-colors">
            <Search className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <div>
            <p className="font-semibold text-lsc-dark dark:text-lsc-cream text-sm">{t('genealogyInquiry.communityArchives', 'Community Archives')}</p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('genealogyInquiry.browseHistoricalRecordsContributedBy')}</p>
          </div>
          <ArrowRight className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70 ml-auto group-hover:text-lsc-rose transition-colors" />
        </a>
      </div>
    </div>
  )
}
