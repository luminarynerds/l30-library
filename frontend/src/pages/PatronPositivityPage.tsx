/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { FormEvent, useMemo, useState } from 'react'
import { Heart, Send } from 'lucide-react'
import { submitPatronPositivity } from '../api/public-positivity-api'
import { useTranslation} from '@/i18n'
import { clean } from '@/lib/utils'

export default function PatronPositivityPage(): React.ReactElement {
  const { t } = useTranslation()

  const entryTypeOptions = useMemo(() => [
    { value: 'feedback', label: 'Positive Feedback' },
    { value: 'thank-you', label: 'Thank You' },
    { value: 'story', label: t('patronPositivity.aStoryToShare') },
  ], [t])
  const [entryType, setEntryType] = useState('feedback')
  const [text, setText] = useState('')
  const [patronName, setPatronName] = useState('')
  const [patronEmail, setPatronEmail] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    const trimmed = text.trim()
    if (trimmed.length < 10) { setError('Please write at least 10 characters.'); return }
    try {
      setIsSubmitting(true); setError(null)
      await submitPatronPositivity(clean({ entry_type: entryType, text: trimmed, patron_name: patronName.trim() || undefined, patron_email: patronEmail.trim() || undefined }))
      setSubmitted(true)
    } catch (err) { setError(err instanceof Error ? err.message : "We couldn't save that just yet. Please try again.") } finally { setIsSubmitting(false) }
  }

  if (submitted) {
    return (
      <div className="min-h-screen bg-lsc-cream/30 dark:bg-earth-900 flex items-center justify-center px-4">
        <div className="max-w-md w-full text-center">
          <Heart className="w-12 h-12 text-lsc-rose mx-auto" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mt-4">Thank you!</h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">{t('patronPositivity.ourStaffWillReviewYour')}</p>
          <button onClick={() => { setSubmitted(false); setText(''); setPatronName(''); setPatronEmail(''); setEntryType('feedback') }} className="mt-6 inline-flex items-center gap-2 rounded-lg bg-lsc-rose text-white px-4 py-2 font-medium hover:bg-lsc-rose-dark transition-colors">Share another experience</button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-lsc-cream/30 dark:bg-earth-900">
      <div className="max-w-xl mx-auto px-4 py-12">
        <div className="text-center mb-8">
          <Heart className="w-10 h-10 text-lsc-rose mx-auto" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mt-3">{t('patronPositivity.shareYourLibraryExperience')}</h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">{t('patronPositivity.hadAPositiveExperienceAt')}</p>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-soft-sm p-6">
          {error && <div className="mb-4 rounded-lg bg-status-danger-50 dark:bg-status-danger-900/20 p-3"><p className="text-sm text-status-danger-800 dark:text-status-danger-200">{error}</p></div>}
          <form onSubmit={handleSubmit} className="space-y-4">
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream">{t('patronPositivity.whatKindOfExperience')}<select value={entryType} onChange={e => setEntryType(e.target.value)} className="mt-1 w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2">{entryTypeOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</select></label>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream">{t('patronPositivity.tellUsAboutIt')}<textarea required minLength={10} value={text} onChange={e => setText(e.target.value)} className="mt-1 w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2 min-h-[120px]" placeholder={t('patronPositivity.whatHappenedHowDidThe')} /></label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream">Your name (optional)<input type="text" value={patronName} onChange={e => setPatronName(e.target.value)} className="mt-1 w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2" placeholder={t('placeholder.patronPositivity.firstName')} /></label>
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream">Your email (optional)<input type="email" value={patronEmail} onChange={e => setPatronEmail(e.target.value)} className="mt-1 w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 px-3 py-2" placeholder={t('placeholder.guestPassForm.emailexamplecom')} /></label>
            </div>
            <div className="pt-2"><button type="submit" disabled={isSubmitting} className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-lsc-rose text-white px-4 py-3 font-medium hover:bg-lsc-rose-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed"><Send className="w-4 h-4" />{isSubmitting ? 'Submitting...' : 'Submit your experience'}</button></div>
          </form>
        </div>
      </div>
    </div>
  )
}
