/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  Scale,
  ChevronRight,
  Loader2,
  CheckCircle,
  FileText,
  BookOpen,
  HelpCircle,
  RotateCcw,
  Download,
  AlertCircle,
  Users,
  ArrowRight,
} from 'lucide-react'
import {
  startFormFinderWizard,
  submitWizardAnswer,
  completeWizard,
  requestWizardHelp,
  type FormFinderResultsResponse,
  type FormFinderQuestion,
} from '@/api/legal-api'
import toast from 'react-hot-toast'
import { useTranslation } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import PageContainer from '@/components/layout/PageContainer'

type WizardStatus = 'idle' | 'loading' | 'active' | 'complete' | 'referred' | 'error'

interface WizardState {
  sessionToken: string | null
  currentStep: string | null
  status: string
  nextQuestion: FormFinderQuestion | null
  progressPercentage: number
  answers: Record<string, string | string[]>
}

function ProgressBar({ percentage }: { percentage: number }) {
  return (
    <div className="w-full bg-lsc-border dark:bg-earth-700 rounded-full h-2">
      <div
        className="bg-lsc-rose h-2 rounded-full transition-all duration-500"
        style={{ width: `${Math.max(5, percentage)}%` }}
      />
    </div>
  )
}

function QuestionCard({
  question,
  currentAnswer,
  onAnswer,
  submitting,
}: {
  question: FormFinderQuestion
  currentAnswer?: string | string[]
  onAnswer: (answer: string | string[]) => void
  submitting: boolean
}) {
  const { t } = useTranslation()
  const [localAnswer, setLocalAnswer] = useState<string | string[]>(currentAnswer ?? '')

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- resync local draft when the question or its saved answer changes
    setLocalAnswer(currentAnswer ?? '')
  }, [question.slug, currentAnswer])

  const handleSubmit = () => {
    if (!localAnswer || (Array.isArray(localAnswer) && localAnswer.length === 0)) return
    onAnswer(localAnswer)
  }

  const canSubmit = Array.isArray(localAnswer)
    ? localAnswer.length > 0
    : localAnswer.trim().length > 0

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
      <div className="mb-6">
        <p className="text-lg font-medium text-lsc-dark dark:text-earth-50 leading-relaxed">
          {question.question_text}
        </p>
        {question.help_text && (
          <div className="flex items-start gap-2 mt-3 p-3 bg-earth-50 dark:bg-earth-800/20 rounded-lg">
            <HelpCircle className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" />
            <p className="text-sm text-earth-800 dark:text-lsc-rose-light/80">{question.help_text}</p>
          </div>
        )}
      </div>

      {/* Question type: multiple choice / select */}
      {(question.question_type === 'select' || question.question_type === 'radio') && question.options.length > 0 && (
        <div className="space-y-2">
          {(question.options as Array<{ value: string; label: string; description?: string }>).map(option => (
            <button
              key={option.value}
              onClick={() => setLocalAnswer(option.value)}
              className={`w-full text-left px-4 py-3 rounded-xl border-2 transition-all ${
                localAnswer === option.value
                  ? 'border-lsc-rose bg-lsc-rose/5 dark:bg-lsc-rose/10'
                  : 'border-lsc-border dark:border-earth-700 hover:border-lsc-rose/50'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className={`w-4 h-4 rounded-full border-2 flex-shrink-0 ${
                  localAnswer === option.value
                    ? 'border-lsc-rose bg-lsc-rose'
                    : 'border-lsc-border dark:border-earth-700'
                }`}>
                  {localAnswer === option.value && (
                    <div className="w-full h-full rounded-full bg-lsc-white dark:bg-earth-800 scale-50 block" />
                  )}
                </div>
                <div>
                  <p className="font-medium text-lsc-dark dark:text-earth-50">{option.label}</p>
                  {option.description && (
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">{option.description}</p>
                  )}
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Question type: checkbox (multi-select) */}
      {question.question_type === 'checkbox' && question.options.length > 0 && (
        <div className="space-y-2">
          {(question.options as Array<{ value: string; label: string; description?: string }>).map(option => {
            const selected = Array.isArray(localAnswer) ? localAnswer.includes(option.value) : false
            return (
              <button
                key={option.value}
                onClick={() => {
                  const current = Array.isArray(localAnswer) ? localAnswer : []
                  if (selected) {
                    setLocalAnswer(current.filter(v => v !== option.value))
                  } else {
                    setLocalAnswer([...current, option.value])
                  }
                }}
                className={`w-full text-left px-4 py-3 rounded-xl border-2 transition-all ${
                  selected
                    ? 'border-lsc-rose bg-lsc-rose/5 dark:bg-lsc-rose/10'
                    : 'border-lsc-border dark:border-earth-700 hover:border-lsc-rose/50'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-4 h-4 rounded border-2 flex-shrink-0 flex items-center justify-center ${
                    selected ? 'border-lsc-rose bg-lsc-rose' : 'border-lsc-border dark:border-earth-700'
                  }`}>
                    {selected && <CheckCircle className="w-3 h-3 text-white" />}
                  </div>
                  <p className="font-medium text-lsc-dark dark:text-earth-50">{option.label}</p>
                </div>
              </button>
            )
          })}
        </div>
      )}

      {/* Question type: text input */}
      {(question.question_type === 'text' || question.question_type === 'textarea') && (
        <textarea
          value={Array.isArray(localAnswer) ? localAnswer.join(', ') : localAnswer}
          onChange={e => setLocalAnswer(e.target.value)}
          placeholder={t('legalDocumentWizard.typeYourAnswerHere')}
          rows={question.question_type === 'textarea' ? 4 : 2}
          className="w-full px-4 py-3 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50 resize-none focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
        />
      )}

      {/* Submit button */}
      <div className="mt-6">
        <button
          onClick={handleSubmit}
          disabled={!canSubmit || submitting}
          className="flex items-center gap-2 px-6 py-3 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 font-medium disabled:opacity-50 transition-colors"
        >
          {submitting ? (
            <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
          {submitting ? t('legalDocumentWizard.processing', 'Processing...') : t('legalDocumentWizard.continue', 'Continue')}
        </button>
      </div>
    </div>
  )
}

function WizardResults({ results }: { results: FormFinderResultsResponse }) {
  const { t } = useTranslation()
  const hasForms = results.recommended_forms.length > 0
  const hasPackets = results.recommended_packets.length > 0
  const hasGuides = results.recommended_guides.length > 0

  if (!hasForms && !hasPackets && !hasGuides) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-8 border border-lsc-border dark:border-earth-700 text-center">
        <AlertCircle className="w-12 h-12 mx-auto text-status-warning-500 mb-4" />
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50 mb-2">
          {t('legalDocumentWizard.yourSituationMayBe', 'Your situation may be complex')}
        </h3>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
          {t('legalDocumentWizard.weCouldntFindSpecific', "We couldn't find specific forms for your situation. This may mean you need personalized legal help.")}
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <a
            href="/legal"
            className="flex items-center gap-2 px-5 py-2.5 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 font-medium text-sm"
          >
            <Users className="w-4 h-4" />
            {t('legalCalculators.findLegalAid', 'Find Legal Aid')}
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-xl p-5">
        <div className="flex items-start gap-3">
          <CheckCircle className="w-5 h-5 text-status-success-600 dark:text-status-success-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-serif font-semibold text-status-success-800 dark:text-status-success-200 mb-1">
              {t('legalDocumentWizard.weFoundResourcesFor', 'We found resources for your situation')}
            </h3>
            <p className="text-sm text-status-success-700 dark:text-status-success-300">
              {t('legalDocumentWizard.basedOnYourAnswers', 'Based on your answers, here are the forms, packets, and guides most relevant to your legal situation.')}
              {results.jurisdiction_state && ` ${t('legalDocumentWizard.showingResourcesForX', { location: results.jurisdiction_county ? `${results.jurisdiction_state}, ${results.jurisdiction_county}` : results.jurisdiction_state })}`}
            </p>
          </div>
        </div>
      </div>

      {/* Recommended Forms */}
      {hasForms && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <FileText className="w-5 h-5 text-lsc-rose" />
            <h2 className="font-serif text-base font-semibold text-lsc-dark dark:text-earth-50">
              {t('legalDocumentWizard.recommendedFormsX', { count: results.recommended_forms.length })}
            </h2>
          </div>
          <div className="space-y-3">
            {results.recommended_forms.map(form => (
              <div key={form.id} className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <p className="font-medium text-lsc-dark dark:text-earth-50">
                      {form.plain_language_title || form.title}
                    </p>
                    {form.plain_language_title && form.plain_language_title !== form.title && (
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{form.title}</p>
                    )}
                    <div className="flex items-center gap-3 mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {form.form_number && <span className="font-mono">{form.form_number}</span>}
                      {form.jurisdiction && <span>{form.jurisdiction}</span>}
                      <span className={`px-1.5 py-0.5 rounded ${form.difficulty_level === 'simple' ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300' : form.difficulty_level === 'moderate' ? 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300' : 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300'}`}>
                        {form.difficulty_level}
                      </span>
                      {form.filing_fee !== null && form.filing_fee !== undefined && (
                        <span>{t('legalDocumentWizard.filingFeeX', { fee: form.filing_fee })}</span>
                      )}
                    </div>
                    {form.when_to_use && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">{form.when_to_use}</p>
                    )}
                  </div>
                  {form.form_url && (
                    <a
                      href={form.form_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1.5 px-3 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm font-medium flex-shrink-0"
                    >
                      <Download className="w-4 h-4" />
                      {t('common.download')}
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommended Packets */}
      {hasPackets && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <FileText className="w-5 h-5 text-category-600" />
            <h2 className="font-serif text-base font-semibold text-lsc-dark dark:text-earth-50">
              {t('legalDocumentWizard.formPacketsX', { count: results.recommended_packets.length })}
            </h2>
          </div>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
            {t('legalDocumentWizard.formPacketsBundleAllThe', 'Form packets bundle all the forms you need for a specific legal process.')}
          </p>
          <div className="space-y-3">
            {results.recommended_packets.map(packet => (
              <div key={packet.id} className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="font-medium text-lsc-dark dark:text-earth-50">{packet.name}</p>
                    {packet.description && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{packet.description}</p>
                    )}
                    <div className="flex items-center gap-3 mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      <span>{t('legalDocumentWizard.countForms', { count: packet.form_count })}</span>
                      {packet.jurisdiction && <span>{packet.jurisdiction}</span>}
                      {packet.total_filing_fee !== null && packet.total_filing_fee !== undefined && (
                        <span>{t('legalDocumentWizard.totalFeesX', { fee: packet.total_filing_fee })}</span>
                      )}
                    </div>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-xs ${packet.is_active ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300' : 'bg-earth-100 dark:bg-earth-900/30 text-lsc-dark/70 dark:text-lsc-cream/70'}`}>
                    {packet.is_active ? t('legalDocumentWizard.available', 'Available') : t('legalDocumentWizard.unavailable', 'Unavailable')}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommended Guides */}
      {hasGuides && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <BookOpen className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            <h2 className="font-serif text-base font-semibold text-lsc-dark dark:text-earth-50">
              {t('legalDocumentWizard.recommendedGuidesX', { count: results.recommended_guides.length })}
            </h2>
          </div>
          <div className="space-y-3">
            {results.recommended_guides.map(guide => (
              <div key={guide.id} className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="font-medium text-lsc-dark dark:text-earth-50">{guide.title}</p>
                    {guide.summary && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{guide.summary}</p>
                    )}
                    <div className="flex items-center gap-3 mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {guide.topic_name && <span>{guide.topic_name}</span>}
                      <span>{t('legalDocumentWizard.levelX', { level: guide.reading_level })}</span>
                    </div>
                  </div>
                  <a
                    href={`/legal?guide=${guide.id}`}
                    className="flex items-center gap-1.5 px-3 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-earth-50 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 text-sm font-medium flex-shrink-0"
                  >
                    {t('legalDocumentWizard.read', 'Read')} <ArrowRight className="w-3 h-3" />
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Printable Checklist */}
      {results.printable_checklist && results.printable_checklist.length > 0 && (
        <div className="bg-lsc-cream dark:bg-earth-900/50 rounded-xl p-5 border border-lsc-border dark:border-earth-700">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-earth-50 mb-3">{t('legalDocumentWizard.yourChecklist', 'Your Checklist')}</h3>
          <div className="space-y-2">
            {(results.printable_checklist as Array<{ item: string; form_number?: string; completed: boolean }>).map((item, idx) => (
              <div key={idx} className="flex items-center gap-3 text-sm text-lsc-dark dark:text-earth-50">
                <div className="w-4 h-4 border-2 border-lsc-border dark:border-earth-700 rounded flex-shrink-0" />
                <span>{item.item}</span>
                {item.form_number && <span className="font-mono text-xs text-lsc-dark/70 dark:text-lsc-cream/70">({item.form_number})</span>}
              </div>
            ))}
          </div>
          <button
            onClick={() => window.print()}
            className="flex items-center gap-2 mt-4 px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-earth-50 rounded-lg hover:bg-lsc-white dark:hover:bg-earth-800 text-sm font-medium"
          >
            <Download className="w-4 h-4" />
            {t('legalDocumentWizard.printChecklist', 'Print Checklist')}
          </button>
        </div>
      )}

      {/* Next Steps */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 border border-lsc-border dark:border-earth-700">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-earth-50 mb-3">{t('legalDocumentWizard.needMoreHelp', 'Need More Help?')}</h3>
        <div className="grid sm:grid-cols-2 gap-3">
          <a
            href="/legal"
            className="flex items-center gap-2 px-4 py-2.5 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 text-sm font-medium"
          >
            <Users className="w-4 h-4" />
            {t('legalDocumentWizard.findLegalAidProvider', 'Find Legal Aid Provider')}
          </a>
          <a
            href="/legal?tab=clinics"
            className="flex items-center gap-2 px-4 py-2.5 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-earth-50 rounded-xl hover:bg-lsc-cream dark:hover:bg-earth-700 text-sm font-medium"
          >
            <Scale className="w-4 h-4" />
            {t('legalDocumentWizard.attendALegalClinic', 'Attend a Legal Clinic')}
          </a>
        </div>
      </div>
    </div>
  )
}

export default function LegalDocumentWizardPage(): React.ReactElement {
  const { t } = useTranslation()
  const [wizardStatus, setWizardStatus] = useState<WizardStatus>('idle')
  const [wizardState, setWizardState] = useState<WizardState>({
    sessionToken: null,
    currentStep: null,
    status: 'idle',
    nextQuestion: null,
    progressPercentage: 0,
    answers: {},
  })
  const [results, setResults] = useState<FormFinderResultsResponse | null>(null)
  const [helpReason, setHelpReason] = useState('')
  const [showHelpDialog, setShowHelpDialog] = useState(false)

  const startMutation = useMutation({
    mutationFn: () => startFormFinderWizard(),
    onSuccess: (data) => {
      setWizardState({
        sessionToken: data.session_token,
        currentStep: data.current_step,
        status: data.status,
        nextQuestion: data.next_question,
        progressPercentage: data.progress_percentage,
        answers: {},
      })
      setWizardStatus('active')
    },
    onError: () => {
      setWizardStatus('error')
      toast.error(t('legalDocumentWizard.failedToStartWizardPlease'))
    },
  })

  const answerMutation = useMutation({
    mutationFn: (data: { questionSlug: string; answer: string | string[] }) =>
      submitWizardAnswer(wizardState.sessionToken!, {
        question_slug: data.questionSlug,
        answer: data.answer as string,
      }),
    onSuccess: (data) => {
      setWizardState(prev => ({
        ...prev,
        currentStep: data.current_step,
        status: data.status,
        nextQuestion: data.next_question,
        progressPercentage: data.progress_percentage,
      }))

      // If wizard is complete, get results
      if (data.status === 'complete' || !data.next_question) {
        completeMutation.mutate()
      }
    },
    onError: () => toast.error(t('legalDocumentWizard.failedToSubmitAnswerPlease')),
  })

  const completeMutation = useMutation({
    mutationFn: () => completeWizard(wizardState.sessionToken!),
    onSuccess: (data) => {
      setResults(data)
      setWizardStatus('complete')
    },
    onError: () => toast.error(t('legalDocumentWizard.failedToCompleteWizardPlease')),
  })

  const helpMutation = useMutation({
    mutationFn: (reason: string) => requestWizardHelp(wizardState.sessionToken!, reason),
    onSuccess: () => {
      setWizardStatus('referred')
      setShowHelpDialog(false)
    },
    onError: () => toast.error(t('legalDocumentWizard.failedToSubmitHelpRequest')),
  })

  const handleStart = () => {
    setWizardStatus('loading')
    startMutation.mutate()
  }

  const handleAnswer = (answer: string | string[]) => {
    if (!wizardState.sessionToken || !wizardState.nextQuestion) return
    setWizardState(prev => ({
      ...prev,
      answers: { ...prev.answers, [wizardState.nextQuestion!.slug]: answer },
    }))
    answerMutation.mutate({ questionSlug: wizardState.nextQuestion.slug, answer })
  }

  const handleReset = () => {
    setWizardStatus('idle')
    setWizardState({
      sessionToken: null,
      currentStep: null,
      status: 'idle',
      nextQuestion: null,
      progressPercentage: 0,
      answers: {},
    })
    setResults(null)
    setShowHelpDialog(false)
  }

  const isSubmitting = answerMutation.isPending || completeMutation.isPending

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark">
      {/* Header */}
      <div className="bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700">
        <PageContainer width="form" className="py-8">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-lsc-cream dark:bg-earth-800/30 rounded-xl">
              <Scale className="w-7 h-7 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <div>
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-earth-50">
                {t('legalDocumentWizard.legalDocumentFinder', 'Legal Document Finder')}
              </h1>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mt-1">
                {t('legalDocumentWizard.answerAFewPlainlanguage', 'Answer a few plain-language questions to find the right forms and guides for your situation.')}
              </p>
            </div>
          </div>
        </PageContainer>
      </div>

      {/* Disclaimer */}
      <PageContainer width="form" className="pt-4">
        <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-700 rounded-xl p-3">
          <p className="text-xs text-status-warning-800 dark:text-status-warning-200">
            <strong>{t('legalDocumentWizard.note', 'Note:')}</strong> {t('legalDocumentWizard.thisToolProvidesGeneralInformation', 'This tool provides general information and helps you find legal forms. It does not provide legal advice. For your specific situation, please consult a qualified attorney or legal aid organization.')}
          </p>
        </div>
      </PageContainer>

      <PageContainer width="form" className="py-6">
        {/* Idle State */}
        {wizardStatus === 'idle' && (
          <div className="space-y-6">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-8 border border-lsc-border dark:border-earth-700 text-center">
              <Scale className="w-16 h-16 mx-auto text-lsc-rose mb-4" />
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50 mb-3">
                {t('legalDocumentWizard.findTheRightLegal', 'Find the Right Legal Forms')}
              </h2>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6 max-w-lg mx-auto">
                {t('legalDocumentWizard.thisWizardWillAsk', 'This wizard will ask you a series of plain-language questions about your legal situation and recommend the forms, packets, and guides that match your needs.')}
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <button
                  onClick={handleStart}
                  className="flex items-center gap-2 px-6 py-3 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 font-medium"
                >
                  {t('legalDocumentWizard.startTheWizard', 'Start the Wizard')}
                  <ChevronRight className="w-5 h-5" />
                </button>
                <a
                  href="/legal"
                  className="flex items-center gap-2 px-6 py-3 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-earth-50 rounded-xl hover:bg-lsc-cream dark:hover:bg-earth-700 font-medium"
                >
                  {t('legalDocumentWizard.browseAllResources', 'Browse All Resources')}
                </a>
              </div>
            </div>

            {/* How It Works */}
            <div>
              <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-3 uppercase tracking-wide">{t('legalDocumentWizard.howItWorks', 'How it works')}</h3>
              <div className="grid sm:grid-cols-3 gap-4">
                {[
                  { step: '1', title: t('legalDocumentWizard.answerQuestions', 'Answer questions'), desc: t('legalDocumentWizard.weAskPlainlanguageQuestions', 'We ask plain-language questions about your situation.') },
                  { step: '2', title: t('legalDocumentWizard.getMatched', 'Get matched'), desc: t('legalDocumentWizard.ourSystemFindsThe', 'Our system finds the forms and guides that fit your needs.') },
                  { step: '3', title: t('legalDocumentWizard.downloadAmpProceed', 'Download & proceed'), desc: t('legalDocumentWizard.accessYourFormsInstructions', 'Access your forms, instructions, and get connected to legal aid.') },
                ].map(item => (
                  <div key={item.step} className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
                    <div className="w-7 h-7 bg-lsc-rose text-white rounded-full flex items-center justify-center text-sm font-bold mb-3">
                      {item.step}
                    </div>
                    <p className="font-medium text-lsc-dark dark:text-earth-50 text-sm mb-1">{item.title}</p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{item.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Loading State */}
        {wizardStatus === 'loading' && (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <Loader2 className="w-10 h-10 motion-safe:animate-spin text-lsc-rose mx-auto mb-4" />
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('legalDocumentWizard.startingYourWizardSession')}</p>
            </div>
          </div>
        )}

        {/* Active Wizard */}
        {wizardStatus === 'active' && wizardState.nextQuestion && (
          <div className="space-y-6">
            {/* Progress */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {wizardState.progressPercentage > 0 ? t('legalDocumentWizard.percentCompleteX', { percent: wizardState.progressPercentage }) : t('legalDocumentWizard.gettingStarted', 'Getting started...')}
                </span>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setShowHelpDialog(true)}
                    className="flex items-center gap-1.5 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-earth-50"
                  >
                    <HelpCircle className="w-4 h-4" />
                    {t('legalDocumentWizard.needHelp', 'Need help?')}
                  </button>
                  <button
                    onClick={handleReset}
                    className="flex items-center gap-1.5 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-earth-50"
                  >
                    <RotateCcw className="w-4 h-4" />
                    {t('legalDocumentWizard.startOver', 'Start over')}
                  </button>
                </div>
              </div>
              <ProgressBar percentage={wizardState.progressPercentage} />
            </div>

            {/* Question */}
            <QuestionCard
              question={wizardState.nextQuestion}
              {...(wizardState.answers[wizardState.nextQuestion.slug] != null ? { currentAnswer: wizardState.answers[wizardState.nextQuestion.slug] } : {})}
              onAnswer={handleAnswer}
              submitting={isSubmitting}
            />
          </div>
        )}

        {/* Processing Results */}
        {(wizardStatus === 'active' && !wizardState.nextQuestion && isSubmitting) && (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <Loader2 className="w-10 h-10 motion-safe:animate-spin text-lsc-rose mx-auto mb-4" />
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('legalDocumentWizard.findingTheBestResourcesFor')}</p>
            </div>
          </div>
        )}

        {/* Results */}
        {wizardStatus === 'complete' && results && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50">{t('legalDocumentWizard.yourRecommendedResources', 'Your Recommended Resources')}</h2>
              <button
                onClick={handleReset}
                className="flex items-center gap-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-earth-50"
              >
                <RotateCcw className="w-4 h-4" />
                {t('legalDocumentWizard.startOverCaps', 'Start Over')}
              </button>
            </div>
            <WizardResults results={results} />
          </div>
        )}

        {/* Referred State */}
        {wizardStatus === 'referred' && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-8 border border-lsc-border dark:border-earth-700 text-center">
            <CheckCircle className="w-12 h-12 mx-auto text-status-success-600 mb-4" />
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50 mb-3">{t('legalDocumentWizard.helpRequestSubmitted', 'Help Request Submitted')}</h2>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6 max-w-md mx-auto">
              {t('legalDocumentWizard.aStaffMemberWill', 'A staff member will follow up to assist you with your legal question. In the meantime, you can also:')}
            </p>
            <div className="space-y-3 text-left max-w-md mx-auto">
              {[
                t('legalDocumentWizard.visitTheLibrarysLegal', "Visit the library's legal resource desk"),
                t('legalDocumentWizard.scheduleAnAppointmentWith', 'Schedule an appointment with the self-help center'),
                t('legalDocumentWizard.browseAvailableLegalAid', 'Browse available legal aid providers'),
              ].map((step, idx) => (
                <div key={idx} className="flex items-start gap-2 text-sm text-lsc-dark dark:text-earth-50">
                  <ChevronRight className="w-4 h-4 text-lsc-rose flex-shrink-0 mt-0.5" />
                  {step}
                </div>
              ))}
            </div>
            <div className="flex gap-3 justify-center mt-6">
              <a href="/legal" className="px-5 py-2.5 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 font-medium text-sm">
                {t('legalDocumentWizard.browseLegalResources', 'Browse Legal Resources')}
              </a>
              <button onClick={handleReset} className="px-5 py-2.5 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-earth-50 rounded-xl hover:bg-lsc-cream dark:hover:bg-earth-700 font-medium text-sm">
                {t('legalDocumentWizard.startNewSearch', 'Start New Search')}
              </button>
            </div>
          </div>
        )}

        {/* Error State */}
        {wizardStatus === 'error' && (
          <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-8 text-center">
            <AlertCircle className="w-12 h-12 mx-auto text-status-danger-500 mb-4" />
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50 mb-2">{t('legalDocumentWizard.weHitASnag', 'We hit a snag')}</h2>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">{t('legalDocumentWizard.weWereUnableToStart')}</p>
            <div className="flex gap-3 justify-center">
              <button onClick={handleReset} className="px-5 py-2.5 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 font-medium text-sm">
                {t('legalDocumentWizard.tryAgain', 'Try Again')}
              </button>
              <a href="/legal" className="px-5 py-2.5 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-earth-50 rounded-xl hover:bg-lsc-cream dark:hover:bg-earth-700 font-medium text-sm">
                {t('legalDocumentWizard.browseResources', 'Browse Resources')}
              </a>
            </div>
          </div>
        )}
      </PageContainer>

      {/* Help Dialog */}
      {showHelpDialog && (
        <ModalBackdrop onClose={() => setShowHelpDialog(false)} title={t('legalDocumentWizard.requestHumanHelp', 'Request Human Help')}>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl w-full max-w-md">
            <div className="p-6">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50 mb-2">{t('legalDocumentWizard.requestHumanHelp', 'Request Human Help')}</h2>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                {t('legalDocumentWizard.tellUsWhatYou', 'Tell us what you need help with and a staff member will follow up with you.')}
              </p>
              <textarea
                value={helpReason}
                onChange={e => setHelpReason(e.target.value)}
                rows={4}
                placeholder={t('legalDocumentWizard.describeWhatYouNeedHelp')}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-earth-50 resize-none"
              />
            </div>
            <div className="flex justify-end gap-3 px-6 pb-6">
              <button
                onClick={() => setShowHelpDialog(false)}
                className="px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-earth-50 text-sm"
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={() => helpMutation.mutate(helpReason)}
                disabled={!helpReason.trim() || helpMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm font-medium disabled:opacity-50"
              >
                {helpMutation.isPending && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
                {t('legalDocumentWizard.requestHelp', 'Request Help')}
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}
    </div>
  )
}
