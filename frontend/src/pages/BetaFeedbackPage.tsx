/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo, useState } from 'react'
import { MessageSquare, Bug, Lightbulb, HelpCircle, Heart, Send, CheckCircle } from 'lucide-react'
import StandardPageLayout from '@/components/StandardPageLayout'
import { fetchApi } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'
import { useTranslation} from '@/i18n'

export default function BetaFeedbackPage() {
  const { t } = useTranslation()

  const FEEDBACK_TYPES = useMemo(() => [
    { value: 'BUG', label: 'Bug Report', icon: Bug, description: t('betaFeedback.somethingIsBrokenOrNot') },
    { value: 'SUGGESTION', label: 'Suggestion', icon: Lightbulb, description: t('betaFeedback.anIdeaToMakeThings') },
    { value: 'CONFUSION', label: 'Confusing', icon: HelpCircle, description: t('betaFeedback.somethingWasHardToUnderstand') },
    { value: 'PRAISE', label: 'Something Great', icon: Heart, description: t('betaFeedback.somethingYouReallyLiked') },
    { value: 'other', label: 'Other', icon: MessageSquare, description: t('betaFeedback.anythingElseOnYourMind') },
  ], [t])
  const [type, setType] = useState('')
  const [subject, setSubject] = useState('')
  const [description, setDescription] = useState('')
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)

    try {
      const token = getAccessToken()
      await fetchApi('/beta-feedback/', {
        method: 'POST',
        body: JSON.stringify({
          type,
          subject,
          description,
          page_url: document.referrer || window.location.href,
          browser_info: navigator.userAgent.slice(0, 300),
          ...(!token && email ? { email } : {}),
        }),
      })

      setSubmitted(true)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "We couldn't submit your feedback just yet. Please try again in a moment.")
    } finally {
      setSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <StandardPageLayout title="Thank You!" subtitle={t('betaFeedback.yourFeedbackHelpsUsBuild')} icon={CheckCircle}>
        <div className="max-w-lg mx-auto text-center py-12">
          <div className="w-16 h-16 bg-status-success-100 dark:bg-status-success-900/30 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-8 h-8 text-status-success-600 dark:text-status-success-400" />
          </div>
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">Feedback received!</h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
            We read every piece of feedback. If you included your email, we may follow up with questions.
          </p>
          <button
            onClick={() => { setSubmitted(false); setType(''); setSubject(''); setDescription(''); }}
            className="px-6 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors"
          >
            Submit Another
          </button>
        </div>
      </StandardPageLayout>
    )
  }

  return (
    <StandardPageLayout title="Beta Feedback" subtitle={t('betaFeedback.helpUsShapeTheLibrary')} icon={MessageSquare}>
      <form onSubmit={handleSubmit} className="max-w-2xl mx-auto space-y-8 py-4">
        {/* Type Selection */}
        <fieldset>
          <legend className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-3">{t('betaFeedback.whatKindOfFeedback')}</legend>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {FEEDBACK_TYPES.map((ft) => {
              const Icon = ft.icon
              const selected = type === ft.value
              return (
                <button
                  key={ft.value}
                  type="button"
                  onClick={() => setType(ft.value)}
                  className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all text-center ${
                    selected
                      ? 'border-lsc-rose bg-lsc-rose/5 dark:bg-lsc-rose/10'
                      : 'border-lsc-border dark:border-earth-700 hover:border-lsc-rose/50'
                  }`}
                >
                  <Icon className={`w-6 h-6 ${selected ? 'text-lsc-rose' : 'text-lsc-dark/70 dark:text-lsc-cream/50'}`} />
                  <span className={`text-sm font-medium ${selected ? 'text-lsc-rose' : 'text-lsc-dark dark:text-lsc-cream'}`}>
                    {ft.label}
                  </span>
                  <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">{ft.description}</span>
                </button>
              )
            })}
          </div>
        </fieldset>

        {/* Subject */}
        <div>
          <label htmlFor="subject" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
            Subject <span className="text-status-danger-500">*</span>
          </label>
          <input
            id="subject"
            type="text"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder={t('placeholder.betaFeedback.briefSummary')}
            maxLength={200}
            required
            className="w-full px-4 py-3 border-2 border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          />
        </div>

        {/* Description */}
        <div>
          <label htmlFor="description" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
            Details <span className="text-status-danger-500">*</span>
          </label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder={type === 'BUG' ? 'What happened? What did you expect to happen? Steps to reproduce...' : 'Tell us more...'}
            rows={5}
            required
            minLength={10}
            className="w-full px-4 py-3 border-2 border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent resize-y"
          />
        </div>

        {/* Email (shown only if not logged in) */}
        {!getAccessToken() && (
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Email (optional, for follow-up)
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder={t('placeholder.betaFeedback.youremailcom')}
              className="w-full px-4 py-3 border-2 border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-lsc-dark text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            />
          </div>
        )}

        {error && (
          <div className="p-3 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg text-status-danger-700 dark:text-status-danger-300 text-sm">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={!type || !subject || !description || submitting}
          className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
        >
          <Send className="w-4 h-4" />
          {submitting ? 'Submitting...' : 'Send Feedback'}
        </button>
      </form>
    </StandardPageLayout>
  )
}