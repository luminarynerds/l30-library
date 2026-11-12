/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import toast from 'react-hot-toast'
import { FileText, Loader2, Send, Copy } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { useAccessibility } from '@/features/accessibility/hooks/useAccessibility'
import type { LetterTemplate } from '@/components/ban-tracker/types'
import { useLetterTemplates } from './hooks'
import { getTargetLevelBadge } from './helpers'
import type { RepresentativeInfo } from './types'

interface LetterComposerSectionProps {
  selectedRep: RepresentativeInfo | null
}

export default function LetterComposerSection({
  selectedRep,
}: LetterComposerSectionProps): React.ReactElement {
  const { t } = useTranslation()
  const { settings: a11y } = useAccessibility()
  const { templates, loading: templatesLoading } = useLetterTemplates()
  const [selectedTemplate, setSelectedTemplate] = useState<LetterTemplate | null>(null)
  const [letterBody, setLetterBody] = useState('')

  const handleSelectTemplate = (tpl: LetterTemplate): void => {
    setSelectedTemplate(tpl)
    setLetterBody(tpl.body_template)
    setTimeout(
      () =>
        document
          .getElementById('letter-body')
          ?.scrollIntoView({ behavior: a11y.reduceMotion ? 'auto' : 'smooth', block: 'center' }),
      100,
    )
  }

  const handleCopyLetter = async (): Promise<void> => {
    if (!selectedTemplate) return
    const text = `Subject: ${selectedTemplate.subject_line}\n\n${letterBody}`
    try {
      await navigator.clipboard.writeText(text)
      toast.success(t('advocacy.letterCopiedToClipboard'))
    } catch {
      toast.error(t('advocacy.couldNotCopyToClipboard'))
    }
  }

  const handleEmailLetter = (): void => {
    if (!selectedTemplate) return
    const subject = encodeURIComponent(selectedTemplate.subject_line)
    const body = encodeURIComponent(letterBody)
    const to = selectedRep?.emails?.[0] ? encodeURIComponent(selectedRep.emails[0]) : ''
    window.open(`mailto:${to}?subject=${subject}&body=${body}`, '_blank')
  }

  const showComposer = selectedTemplate !== null || templates.length === 0

  return (
    <section aria-labelledby="letter-heading">
      <div className="flex items-center gap-2 mb-4">
        <FileText className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
        <h2 id="letter-heading" className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">
          Write a Letter
        </h2>
      </div>

      {templatesLoading ? (
        <div className="flex items-center gap-2 py-6 text-lsc-dark/70 dark:text-lsc-cream/60">
          <Loader2 className="w-5 h-5 motion-safe:animate-spin" aria-hidden="true" />
          <span className="text-sm">Loading templates...</span>
        </div>
      ) : templates.length > 0 ? (
        <div className="mb-6">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
            Choose a template to get started:
          </p>
          <div className="flex flex-wrap gap-3">
            {templates.map((tpl) => (
              <button
                key={tpl.id}
                onClick={() => handleSelectTemplate(tpl)}
                className={`px-4 py-3 rounded-xl border text-left transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose ${
                  selectedTemplate?.id === tpl.id
                    ? 'border-lsc-rose bg-lsc-rose/5 dark:bg-lsc-rose/10'
                    : 'border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 hover:border-lsc-rose/50'
                }`}
              >
                <p className="font-semibold text-sm text-lsc-dark dark:text-lsc-cream">{tpl.title}</p>
                <span
                  className={`mt-1 inline-block px-2 py-0.5 text-xs font-medium rounded-full ${getTargetLevelBadge(tpl.target_level)}`}
                >
                  {tpl.target_level}
                </span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="mb-6 p-4 bg-earth-50 dark:bg-earth-800/50 rounded-xl border border-lsc-border dark:border-earth-700">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            No letter templates are available yet. You can still compose your own letter using the form below.
          </p>
        </div>
      )}

      {showComposer && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
          {selectedRep && (
            <div className="flex items-center gap-2 mb-4 text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              <Send className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
              <span>
                To: {selectedRep.name}, {selectedRep.office}
              </span>
            </div>
          )}

          {selectedTemplate && (
            <div className="mb-4">
              <label className="block text-xs font-semibold uppercase tracking-wide text-lsc-dark/70 dark:text-lsc-cream/60 mb-1">
                Subject
              </label>
              <div className="px-4 py-2 bg-earth-50 dark:bg-earth-900/50 border border-lsc-border dark:border-earth-700 rounded-lg text-sm text-lsc-dark dark:text-lsc-cream">
                {selectedTemplate.subject_line}
              </div>
            </div>
          )}

          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mb-3 bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-700 rounded-lg px-3 py-2">
            Placeholder fields like{' '}
            <code className="font-mono text-status-warning-700 dark:text-status-warning-300">{'{your_name}'}</code>,{' '}
            <code className="font-mono text-status-warning-700 dark:text-status-warning-300">{'{your_address}'}</code>,{' '}
            <code className="font-mono text-status-warning-700 dark:text-status-warning-300">{'{rep_name}'}</code>, and{' '}
            <code className="font-mono text-status-warning-700 dark:text-status-warning-300">{'{library_name}'}</code>{' '}
            should be replaced with your personal details before sending.
          </p>

          <div className="mb-4">
            <label
              htmlFor="letter-body"
              className="block text-xs font-semibold uppercase tracking-wide text-lsc-dark/70 dark:text-lsc-cream/60 mb-1"
            >
              Letter Body
            </label>
            <textarea
              id="letter-body"
              value={letterBody}
              onChange={(e) => setLetterBody(e.target.value)}
              rows={12}
              className="w-full px-4 py-3 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream placeholder-earth-400 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:border-transparent resize-y text-sm leading-relaxed"
              placeholder={
                selectedTemplate
                  ? ''
                  : 'Write your letter here. Personalized letters are more effective than form letters — share your own connection to your library and why intellectual freedom matters to you.'
              }
            />
          </div>

          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mb-4 italic">
            Customize the letter below to add your personal perspective — personalized letters are more impactful.
          </p>

          <div className="flex flex-wrap gap-3">
            <button
              onClick={handleCopyLetter}
              disabled={!letterBody.trim()}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-lsc-rose text-white font-semibold rounded-xl hover:bg-lsc-rose/90 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose dark:focus:ring-offset-earth-800 disabled:opacity-50 text-sm"
            >
              <Copy className="w-4 h-4" aria-hidden="true" />
              Copy to Clipboard
            </button>

            <button
              onClick={handleEmailLetter}
              disabled={!letterBody.trim()}
              className="inline-flex items-center gap-2 px-5 py-2.5 border border-earth-300 dark:border-earth-600 text-lsc-dark dark:text-lsc-cream font-semibold rounded-xl hover:border-lsc-rose hover:text-lsc-rose dark:hover:text-lsc-rose-light transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose dark:focus:ring-offset-earth-800 disabled:opacity-50 text-sm"
            >
              <Send className="w-4 h-4" aria-hidden="true" />
              Open in Email
            </button>
          </div>
        </div>
      )}
    </section>
  )
}
