/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useMemo } from 'react'
import { Upload, BookOpen, CheckCircle2, AlertCircle, ChevronDown, ChevronUp, HelpCircle, Loader, EyeOff } from 'lucide-react'
import toast from 'react-hot-toast'
import { Button } from '@/components/ui/Button'
import { fetchApi } from '@/api/fetchApi'
import { useTranslation } from '@/i18n'
import { useBranding } from '@/contexts/BrandingContext'
import { useAuth } from '@/contexts/AuthContext'
import { apiClient } from '@/lib/api-client'

const STAFF_ROLES = new Set(['super_admin', 'admin', 'director', 'staff'])

interface PublishedSubmission {
  id: number
  submitter_name: string
  material_type: string
  title: string
  description: string
  date_or_period?: string
  location?: string
  file_url?: string
  file_type?: string
  published_at: string
}

interface Step {
  id: string
  title: string
  description: string
  details: string
  examples: string[]
}

function StepCard({ step, isExpanded, onToggle }: { step: Step; isExpanded: boolean; onToggle: () => void }) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
      <Button variant="secondary"
        onClick={onToggle}
        aria-expanded={isExpanded}
        aria-controls={`step-${step.id}`}
      >
        <div>
          {step.id.charAt(0).toUpperCase()}
        </div>
        <div>
          <h3>
            {step.title}
          </h3>
          <p>
            {step.description}
          </p>
        </div>
        <div>
          {isExpanded ? (
            <ChevronUp aria-hidden="true" />
          ) : (
            <ChevronDown aria-hidden="true" />
          )}
        </div>
      </Button>

      {isExpanded && (
        <div id={`step-${step.id}`} className="px-5 pb-5 border-t border-lsc-border dark:border-earth-700 space-y-4">
          <p className="text-lsc-dark/80 dark:text-lsc-cream/80">
            {step.details}
          </p>

          <div>
            <p className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider mb-2">
              Examples:
            </p>
            <ul className="space-y-2">
              {step.examples.map((example, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                  <CheckCircle2 className="w-4 h-4 text-status-success-600 dark:text-status-success-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
                  <span>{example}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}

export default function CommunityArchivesPage(): React.ReactElement {
  const branding = useBranding()
  const { t } = useTranslation()
  const { user } = useAuth()
  const isStaff = !!user && STAFF_ROLES.has(user.role)
  const [expandedStep, setExpandedStep] = useState<string | null>('prepare')
  const [hidingId, setHidingId] = useState<number | null>(null)

  const [faqOpen, setFaqOpen] = useState<Record<string, boolean>>({})
  const [submissions, setSubmissions] = useState<PublishedSubmission[]>([])
  const [isLoadingSubmissions, setIsLoadingSubmissions] = useState(true)
  const [stats, setStats] = useState({ active_courses: 0, pending_inquiries: 0, published_submissions: 0 })

  const handleHide = async (id: number) => {
    setHidingId(id)
    try {
      await apiClient<unknown>(`/genealogy/archives/${id}/hide`, { method: 'PATCH' })
      setSubmissions(prev => prev.filter(s => s.id !== id))
      toast.success('Submission hidden from public view.')
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error('Could not hide submission.')
    } finally {
      setHidingId(null)
    }
  }

  const submissionSteps: Step[] = useMemo(() => [
    {
      id: 'prepare',
      title: '1. Prepare Your Materials',
      description: 'Gather the items you want to contribute to the community archive.',
      details: 'Look for photographs, documents, letters, newspapers, yearbooks, maps, or other historical materials related to our community. Physical items, high-quality scans, or digital files are all welcome.',
      examples: [
        'Old family photographs or portraits',
        'Letters and correspondence',
        'Newspaper clippings about local events',
        'Handwritten diaries or journals',
        'Historical documents or permits',
        'School yearbooks',
        'Maps or blueprints',
        'Business records',
      ],
    },
    {
      id: 'digitize',
      title: '2. Digitize (If Needed)',
      description: 'Convert physical materials to digital format for preservation.',
      details: 'If you have physical items, we can help you scan them. We recommend high-resolution color scans (at least 300 DPI) to preserve quality. We also accept items already in digital format (JPG, PDF, etc.).',
      examples: [
        'Photographs: Color scan at 300+ DPI',
        'Documents: Black & white scan at 300+ DPI',
        'Large items: We can scan at the library for free',
        'Already digital? Just upload the file directly',
      ],
    },
    {
      id: 'describe',
      title: '3. Add Description & Metadata',
      description: 'Tell us about the material — who, what, when, and why it matters.',
      details: 'Provide context about what you\'re submitting. Include the date (if known), location, people involved, and why it\'s historically significant. This helps researchers find your contribution.',
      examples: [
        'Date or time period (e.g., "circa 1950s" or "January 15, 1987")',
        'Location (street name, building, neighborhood)',
        'People involved (names of people in photos or documents)',
        'Event or context (what was happening, why this matters)',
        'Your name as contributor (optional - you can stay anonymous)',
      ],
    },
    {
      id: 'review',
      title: '4. Review & Rights',
      description: 'Confirm permissions and complete the submission process.',
      details: 'Confirm that you have the right to share this material. Most community submissions are made available to the public under a Creative Commons license, which means others can view and learn from them. You retain ownership, but agree to share with the community.',
      examples: [
        'You own the material (taken by you or given to you)',
        'You have permission from the copyright holder',
        'Material is old enough to be in public domain',
        'You understand it will be publicly accessible',
      ],
    },
  // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [t])

  useEffect(() => {
    const loadData = async () => {
      try {
        const dashData = await fetchApi('/genealogy/dashboard')
        setStats({
          active_courses: dashData.active_courses || 0,
          pending_inquiries: dashData.pending_inquiries || 0,
          published_submissions: dashData.published_submissions || 0,
        })

        const submissionsData = await fetchApi('/genealogy/archives/public?limit=10')
        setSubmissions(submissionsData)
      } catch (error: unknown) {
        Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
        toast.error(t('communityArchives.failedToLoadSomeData'))
      } finally {
        setIsLoadingSubmissions(false)
      }
    }

    loadData()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const faqs = [
    {
      id: 'physical-items',
      question: 'What if I have physical items I want to donate?',
      answer: 'You can bring them to the library, and we\'ll help you scan them for free if you\'d like. We can keep the originals (with your permission) as part of our permanent collection, or return them to you after scanning.',
    },
    {
      id: 'privacy',
      question: 'Can I keep something private?',
      answer: 'Yes. You can submit items with restricted access (for example, items visible only to library staff or researchers with permission). Tell us about any privacy concerns when you submit.',
    },
    {
      id: 'permissions',
      question: 'What if I don\'t own the original?',
      answer: 'That\'s okay. If someone gave you the item, we just need written permission from the original owner (email is fine). For very old items, copyright usually isn\'t an issue.',
    },
    {
      id: 'timeline',
      question: 'How long does the process take?',
      answer: 'Your contribution is published to the community archive immediately. Library staff may follow up with questions or curate the listing afterwards.',
    },
    {
      id: 'credit',
      question: 'Will I get credit for my contribution?',
      answer: 'Yes, unless you choose to remain anonymous. We always acknowledge contributors and link to their submissions.',
    },
  ]

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="text-center space-y-3">
        <div className="flex justify-center mb-4">
          <div className="w-16 h-16 rounded-full bg-lsc-rose/10 flex items-center justify-center">
            <Upload className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
          </div>
        </div>
        <h1 className="text-3xl md:text-4xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          Community Archives
        </h1>
        <p className="text-lg text-lsc-dark/70 dark:text-lsc-cream/70">
          Help preserve our community's history. Share photographs, documents, and memories from local life.
        </p>
      </div>

      {/* What Are Community Archives? */}
      <div className="bg-lsc-cream dark:bg-earth-700/50 rounded-xl p-6 border border-lsc-border dark:border-earth-700 space-y-3">
        <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream text-lg">
          What Are Community Archives?
        </h2>
        <p className="text-lsc-dark/80 dark:text-lsc-cream/80">
          Community archives are collections created and preserved by people like you. They're a way to keep local stories alive-photographs of old buildings, memories of community events, documents from local businesses, family histories, and more.
        </p>
        <p className="text-lsc-dark/80 dark:text-lsc-cream/80">
          Your contribution helps future generations understand what life was like in our community.
        </p>
      </div>

      {/* Key Points */}
      <div className="grid md:grid-cols-3 gap-4">
        {[
          { icon: BookOpen, title: 'Preserve History', desc: 'Keep local stories alive' },
          { icon: Upload, title: 'Easy to Share', desc: 'Simple submission process' },
          { icon: CheckCircle2, title: 'Your Choice', desc: 'Control who can access items' },
        ].map((item, idx) => {
          const Icon = item.icon
          return (
            <div key={idx} className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700 text-center">
              <Icon className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light mx-auto mb-3" aria-hidden="true" />
              <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                {item.title}
              </h3>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {item.desc}
              </p>
            </div>
          )
        })}
      </div>

      {/* How It Works - Submission Steps */}
      <div className="space-y-4">
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          How to Submit Your Materials
        </h2>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          The process is straightforward. Click each step below to learn more.
        </p>

        <div className="space-y-3">
          {submissionSteps.map(step => (
            <StepCard
              key={step.id}
              step={step}
              isExpanded={expandedStep === step.id}
              onToggle={() => setExpandedStep(expandedStep === step.id ? null : step.id)}
            />
          ))}
        </div>
      </div>

      {/* What We Accept */}
      <div className="space-y-4">
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          What We Accept
        </h2>
        <div className="grid md:grid-cols-2 gap-4">
          {[
            ['Photographs', 'Printed photos, slides, negatives'],
            ['Documents', 'Letters, certificates, permits, records'],
            ['Newspapers', 'Clippings or full pages'],
            ['Maps & Plans', 'Historical maps, blueprints, drawings'],
            ['Business Records', 'Advertisements, invoices, ledgers'],
            ['School Materials', 'Yearbooks, report cards, programs'],
            ['Personal Items', 'Diaries, journals, scrapbooks'],
            ['Audio & Video', 'Recordings, oral histories, films'],
          ].map((item, idx) => (
            <div key={idx} className="p-4 bg-lsc-cream/50 dark:bg-earth-700/30 rounded-lg">
              <p className="font-medium text-lsc-dark dark:text-lsc-cream">{item[0]}</p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{item[1]}</p>
            </div>
          ))}
        </div>
      </div>

      {/* FAQ - Progressive Disclosure */}
      <div className="space-y-4">
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
          <HelpCircle className="w-6 h-6" aria-hidden="true" />
          Common Questions
        </h2>

        <div className="space-y-2">
          {faqs.map(faq => (
            <div
              key={faq.id}
              className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 overflow-hidden"
            >
              <Button variant="secondary"
                onClick={() => setFaqOpen(prev => ({ ...prev, [faq.id]: !prev[faq.id] }))}
                aria-expanded={faqOpen[faq.id]}
              >
                <span>
                  {faq.question}
                </span>
                <div>
                  {faqOpen[faq.id] ? (
                    <ChevronUp aria-hidden="true" />
                  ) : (
                    <ChevronDown aria-hidden="true" />
                  )}
                </div>
              </Button>

              {faqOpen[faq.id] && (
                <div className="px-4 pb-4 border-t border-lsc-border dark:border-earth-700 text-lsc-dark/80 dark:text-lsc-cream/80">
                  {faq.answer}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Published Submissions */}
      {submissions.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            Recently Published
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Browse items our community has shared. {stats.published_submissions} items published so far.
          </p>
          {isLoadingSubmissions ? (
            <div className="flex items-center justify-center py-8">
              <Loader className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
              <span className="ml-3 text-lsc-dark/70 dark:text-lsc-cream/70">Loading items...</span>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 gap-4">
              {submissions.map(submission => (
                <div key={submission.id} className="bg-lsc-white dark:bg-earth-800 rounded-lg p-5 border border-lsc-border dark:border-earth-700 hover:shadow-md transition-shadow">
                  <div className="flex items-start gap-3 mb-3">
                    <div className="w-10 h-10 rounded-lg bg-lsc-rose/10 flex items-center justify-center flex-shrink-0">
                      <BookOpen className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream truncate" title={submission.title}>
                        {submission.title}
                      </h3>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        {submission.material_type}
                      </p>
                    </div>
                  </div>

                  <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 mb-3 line-clamp-2" title={submission.description}>
                    {submission.description}
                  </p>

                  <div className="space-y-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    {submission.date_or_period && (
                      <p><strong>Date:</strong> {submission.date_or_period}</p>
                    )}
                    {submission.location && (
                      <p><strong>Location:</strong> {submission.location}</p>
                    )}
                  </div>

                  <div className="mt-3 pt-3 border-t border-lsc-border dark:border-earth-700 flex items-center justify-between gap-2">
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      Shared by <strong>{submission.submitter_name}</strong>
                    </p>
                    {isStaff && (
                      <button
                        type="button"
                        onClick={() => handleHide(submission.id)}
                        disabled={hidingId === submission.id}
                        aria-label="Hide submission from public view"
                        title="Hide from public view (staff)"
                        className="inline-flex items-center gap-1 text-xs text-lsc-dark/60 dark:text-lsc-cream/60 hover:text-status-warning-700 dark:hover:text-status-warning-300 px-2 py-1 rounded"
                      >
                        <EyeOff className="w-3.5 h-3.5" aria-hidden="true" />
                        {hidingId === submission.id ? 'Hiding...' : 'Hide'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Call to Action */}
      <div className="bg-gradient-to-r from-lsc-rose/10 to-lsc-rose/5 dark:from-lsc-rose/20 dark:to-lsc-rose/10 border-2 border-lsc-rose/30 dark:border-lsc-rose/40 rounded-xl p-8 text-center space-y-4">
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          Ready to Share Your History?
        </h2>
        <p className="text-lsc-dark/80 dark:text-lsc-cream/80 max-w-xl mx-auto">
          Bring your items to the library, or start an online submission. Our team will help you prepare your contribution.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Button variant="primary"
            onClick={() => {
              // Scroll to submission form or navigate
              window.location.href = '#submission-form'
            }}
          >
            Start a Submission
          </Button>
          <a
            href="/genealogy/ask-genealogist"
            className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-lsc-cream dark:bg-earth-800 hover:bg-lsc-border dark:hover:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg font-medium transition-colors border border-lsc-border dark:border-earth-700 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-earth-800"
          >
            Ask a Question
          </a>
        </div>
      </div>

      {/* Contact Info */}
      <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded-xl p-6 space-y-3">
        <h3 className="font-serif font-semibold text-earth-900 dark:text-earth-200 flex items-center gap-2">
          <AlertCircle className="w-5 h-5" aria-hidden="true" />
          Questions?
        </h3>
        <p className="text-earth-900 dark:text-earth-200">
          Contact Marlene Williams at <strong>{branding.contact_email}</strong> or call the library with questions about submitting items.
        </p>
      </div>
    </div>
  )
}