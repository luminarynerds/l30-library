/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Monitor, Languages,
  ScrollText, Music, AlertCircle, ChevronDown, ChevronUp,
  Sparkles, Clock, Zap, ExternalLink, Shield, Search,
  ClipboardCheck,
  ArrowRight, Library, BookOpen, Headphones, Play, X, Info, Star,
  Smartphone, Download, HelpCircle, RefreshCw, Printer,
} from 'lucide-react'
import { clsx } from '@/utils/helpers'
import ExitStrategySection from '@/components/ExitStrategySection'
import StandardPageLayout from '@/components/StandardPageLayout'
import { useTranslation } from '@/i18n'
import { usePageTitle } from '@/hooks/usePageTitle'
import { useBranding } from '@/contexts/BrandingContext'
import { useAuth } from '@/contexts/AuthContext'
import DigitalActivityPanel from '@/components/DigitalActivityPanel'
import { fetchApi } from '@/api/fetchApi'

// Enhanced Resource interface with new fields for better user guidance
interface Resource {
  name: string
  description: string
  icon: React.ElementType
  badge?: string
  badgeColor?: string
  details?: string
  link?: string // Internal link to dedicated page
  // New accessibility and UX fields
  timeEstimate?: string // e.g., "5 minutes"
  difficulty?: 'easy' | 'medium' | 'advanced'
  accountRequirements?: string // e.g., "Library card number only"
  deviceSupport?: string // e.g., "Desktop + Mobile"
  features?: string[] // Key features list
  offlineAccess?: boolean // Can access offline
  downloadLimits?: string // e.g., "5 per week"
  noSignupRequired?: boolean // True when no account/library card needed
  category?: 'books' | 'music' | 'research' | 'languages' | 'news'
  tryItUrl?: string // URL for inline preview (no-signup resources only)
  inLibraryOnly?: boolean // Resource only available on library computers
  // Transparency fields
  privacyPolicyUrl?: string // Link to vendor's privacy policy
  // Getting started + data removal info
  usageGuide?: {
    service: string
    getStarted: string[] // Steps to start using
    dataRemoval: string // How to remove your data when done
    alternativePromo?: {
      title: string
      description: string
      link: string
    }
  }
}

// startHereResources and otherResources moved inside DigitalResourcesPage component

interface ServiceStatusEntry {
  name: string
  status: 'operational' | 'degraded' | 'down'
  last_checked: string
}

// useCaseGuide and faqs moved inside DigitalResourcesPage component for i18n

type QuizInterest = 'books' | 'music' | 'research' | 'languages' | 'news'
type QuizComfort = 'beginner' | 'comfortable' | 'advanced'
type QuizOffline = 'yes' | 'no' | 'any'
interface QuizAnswers { interest: QuizInterest; comfort: QuizComfort; offline: QuizOffline }

const QUIZ_STORAGE_KEY = 'l30-digital-recs-quiz'
function loadQuizAnswers(): QuizAnswers | null {
  try { const raw = localStorage.getItem(QUIZ_STORAGE_KEY); if (!raw) return null; const p = JSON.parse(raw); if (p.interest && p.comfort && p.offline) return p as QuizAnswers; return null } catch { return null }
}
function saveQuizAnswers(a: QuizAnswers): void { localStorage.setItem(QUIZ_STORAGE_KEY, JSON.stringify(a)) }
function clearQuizAnswers(): void { localStorage.removeItem(QUIZ_STORAGE_KEY) }

function scoreResource(resource: Resource, answers: QuizAnswers): number {
  let score = 0
  if (resource.category === answers.interest) score += 10
  const m: Record<QuizComfort, Resource['difficulty'][]> = { beginner: ['easy'], comfortable: ['easy', 'medium'], advanced: ['easy', 'medium', 'advanced'] }
  if (resource.difficulty && m[answers.comfort].includes(resource.difficulty)) { score += 3; if (answers.comfort === 'beginner' && resource.difficulty === 'easy') score += 2 }
  if (answers.offline === 'yes' && resource.offlineAccess) score += 4
  return score
}

function getRecommendations(all: Resource[], a: QuizAnswers): Resource[] {
  return all.map(r => ({ resource: r, score: scoreResource(r, a) })).sort((a, b) => b.score - a.score).filter(s => s.score > 0).slice(0, 3).map(s => s.resource)
}

function RecommendationQuiz({ onComplete }: { onComplete: (answers: QuizAnswers) => void }): React.ReactElement {
  const [step, setStep] = useState(0)
  const [interest, setInterest] = useState<QuizInterest | null>(null)
  const [comfort, setComfort] = useState<QuizComfort | null>(null)
  const optionBtn = 'w-full text-left p-3 rounded-lg border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose-light hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/20 transition-colors text-sm text-lsc-dark dark:text-lsc-cream'
  return (<div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5">
    <div className="flex items-center gap-2 mb-1"><HelpCircle className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" /><h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">Not sure where to start?</h2></div>
    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">Answer 3 quick questions and we&apos;ll highlight the best services for you.</p>
    <div className="flex items-center gap-1.5 mb-4">{[0, 1, 2].map(i => (<div key={i} className={clsx('w-2 h-2 rounded-full transition-colors', i <= step ? 'bg-lsc-rose' : 'bg-lsc-border dark:bg-earth-700')} />))}<span className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 ml-2">{step + 1} of 3</span></div>
    {step === 0 && (<div><p className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-3">What are you most interested in?</p><div className="grid grid-cols-1 sm:grid-cols-2 gap-2">{[{v:'books' as QuizInterest,l:'Books & Reading',I:BookOpen},{v:'music',l:'Music',I:Music},{v:'research',l:'Research & Reviews',I:ScrollText},{v:'languages',l:'Languages',I:Languages}].map(opt => (<button key={opt.v} type="button" onClick={() => {setInterest(opt.v as QuizInterest);setStep(1)}} className={optionBtn}><span className="flex items-center gap-2"><opt.I className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />{opt.l}</span></button>))}</div></div>)}
    {step === 1 && (<div><p className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-3">How comfortable are you with technology?</p><div className="grid grid-cols-1 gap-2">{[{v:'beginner' as QuizComfort,l:'Beginner',d:'I need simple tools'},{v:'comfortable',l:'Comfortable',d:'I use apps regularly'},{v:'advanced',l:'Advanced',d:'I can figure most things out'}].map(opt => (<button key={opt.v} type="button" onClick={() => {setComfort(opt.v as QuizComfort);setStep(2)}} className={optionBtn}><span className="font-medium">{opt.l}</span><span className="text-lsc-dark/50 dark:text-lsc-cream/50 ml-2">{opt.d}</span></button>))}</div></div>)}
    {step === 2 && (<div><p className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-3">Do you need offline access?</p><div className="grid grid-cols-1 gap-2">{[{v:'yes' as QuizOffline,l:'Yes, I need offline access'},{v:'no',l:'No, online is fine'},{v:'any',l:"Doesn't matter"}].map(opt => (<button key={opt.v} type="button" onClick={() => {if(interest&&comfort){const a:QuizAnswers={interest,comfort,offline:opt.v as QuizOffline};saveQuizAnswers(a);onComplete(a)}}} className={optionBtn}>{opt.l}</button>))}</div></div>)}
  </div>)
}

// Shareable / printable summary of the wizard outcome. ND users often act later, not in
// the moment, so this gives them a card they can print or copy with the recommendation +
// first step for each service. Uses print: variants (see ParentResourcesPage) so printing
// this page yields just the card.
function RecommendationSummaryCard({ recommendations }: { recommendations: Resource[] }): React.ReactElement {
  const [copied, setCopied] = useState(false)
  const handlePrint = useCallback(() => { window.print() }, [])
  const handleCopy = useCallback(() => {
    const lines = recommendations.map(r => {
      const step = r.usageGuide?.getStarted[0] ? `\n   First step: ${r.usageGuide.getStarted[0]}` : ''
      const account = r.accountRequirements ? `\n   You need: ${r.accountRequirements}` : ''
      return `\u2022 ${r.name}: ${r.description}${step}${account}`
    })
    const text = `Your recommended digital services\n\n${lines.join('\n\n')}`
    navigator.clipboard?.writeText(text).then(() => {
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    }).catch(() => { /* clipboard unavailable; print is still offered */ })
  }, [recommendations])

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5 print:border-none print:shadow-none">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <h3 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream">Your plan</h3>
          <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-0.5">Print or copy this so you can set it up whenever you are ready.</p>
        </div>
        <div className="flex items-center gap-2 print:hidden">
          <button type="button" onClick={handleCopy} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-lsc-cream dark:bg-lsc-brown/40 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-rose/10 transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose">
            <ClipboardCheck className="w-3.5 h-3.5" aria-hidden="true" />{copied ? 'Copied' : 'Copy'}
          </button>
          <button type="button" onClick={handlePrint} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-lsc-rose text-white hover:bg-lsc-rose/90 transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-earth-800">
            <Printer className="w-3.5 h-3.5" aria-hidden="true" />Print
          </button>
        </div>
      </div>
      <ol className="space-y-3">
        {recommendations.map((r, i) => (
          <li key={r.name} className="flex items-start gap-3">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-lsc-rose text-white text-xs font-bold flex items-center justify-center mt-0.5 print:bg-transparent print:text-lsc-dark print:border print:border-lsc-dark" aria-hidden="true">{i + 1}</span>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">{r.name}</p>
              {r.usageGuide?.getStarted[0] && (
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">First step: {r.usageGuide.getStarted[0]}</p>
              )}
              {r.accountRequirements && (
                <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-0.5">You need: {r.accountRequirements}</p>
              )}
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}

type MobileTab = 'overview' | 'features' | 'getting-started'
function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(false)
  useEffect(() => {
    const mql = window.matchMedia('(max-width: 639px)')
    setIsMobile(mql.matches)
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches)
    mql.addEventListener('change', handler)
    return () => mql.removeEventListener('change', handler)
  }, [])
  return isMobile
}

// localStorage-backed favorites for digital resources
function useFavorites(): {
  favorites: Set<string>
  toggle: (name: string) => void
} {
  const { user } = useAuth()
  const storageKey = user?.id ? `l30-digital-favs-${user.id}` : 'l30-digital-favs'

  const [favorites, setFavorites] = useState<Set<string>>(() => {
    try {
      const stored = localStorage.getItem(storageKey)
      return stored ? new Set(JSON.parse(stored)) : new Set()
    } catch {
      return new Set()
    }
  })

  const toggle = useCallback((name: string) => {
    setFavorites(prev => {
      const next = new Set(prev)
      if (next.has(name)) {
        next.delete(name)
      } else {
        next.add(name)
      }
      try {
        localStorage.setItem(storageKey, JSON.stringify([...next]))
      } catch { /* quota exceeded */ }
      return next
    })
  }, [storageKey])

  return { favorites, toggle }
}

// Sort resources so favorites float to the top (stable order otherwise)
function sortByFavorites(resources: Resource[], favorites: Set<string>): Resource[] {
  if (favorites.size === 0) return resources
  return [...resources].sort((a, b) => {
    const aFav = favorites.has(a.name) ? 0 : 1
    const bFav = favorites.has(b.name) ? 0 : 1
    return aFav - bFav
  })
}

function formatTimeAgo(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime()
  const mins = Math.round(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins === 1) return '1 minute ago'
  if (mins < 60) return `${mins} minutes ago`
  const hrs = Math.round(mins / 60)
  if (hrs === 1) return '1 hour ago'
  return `${hrs} hours ago`
}

// Helper to sanitize IDs by removing spaces and special characters
function sanitizeId(text: string): string {
  return text.replace(/[^a-zA-Z0-9\s-]/g, '').replace(/\s+/g, '-').toLowerCase()
}

// ResourceCard component - Enhanced with metadata, features, and exit strategy
function ResourceCard({ resource, expanded, onToggle, isFavorite, onToggleFavorite, serviceStatus }: {
  resource: Resource
  expanded: boolean
  onToggle: () => void
  isFavorite?: boolean
  onToggleFavorite?: () => void
  serviceStatus?: ServiceStatusEntry
}): React.ReactElement {
  const { t } = useTranslation()
  const resourceId = sanitizeId(resource.name)
  const isMobile = useIsMobile()
  const [activeTab, setActiveTab] = useState<MobileTab>('overview')
  const [showPreview, setShowPreview] = useState(false)
  const [iframeLoaded, setIframeLoaded] = useState(false)

  const handleTryIt = useCallback(() => {
    setShowPreview(true)
    setIframeLoaded(false)
  }, [])

  const handleClosePreview = useCallback(() => {
    setShowPreview(false)
    setIframeLoaded(false)
  }, [])

  return (
    <div id={`resource-card-${resourceId}`} className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm hover:shadow-md transition-shadow relative">
      <button
        onClick={onToggle}
        className="w-full p-5 pr-14 flex items-start gap-4 text-left"
        aria-expanded={expanded}
        aria-controls={`resource-details-${resourceId}`}
      >
        <div className="w-12 h-12 rounded-xl bg-lsc-cream dark:bg-lsc-brown flex items-center justify-center flex-shrink-0">
          <resource.icon className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
              {resource.name}
            </h3>
            {serviceStatus && (
              <span
                title={`${serviceStatus.status === 'operational' ? 'Service operational' : serviceStatus.status === 'degraded' ? 'Service degraded' : 'Service down'} \u2014 Last checked ${formatTimeAgo(serviceStatus.last_checked)}`}
                className={clsx(
                  'inline-block w-2.5 h-2.5 rounded-full flex-shrink-0',
                  serviceStatus.status === 'operational' && 'bg-lsc-green',
                  serviceStatus.status === 'degraded' && 'bg-status-warning-500',
                  serviceStatus.status === 'down' && 'bg-status-danger-600',
                )}
                aria-label={`${resource.name} service ${serviceStatus.status}`}
              />
            )}
            {resource.badge && (
              <span className={clsx('text-xs font-medium', resource.badgeColor)}>
                {resource.badge}
              </span>
            )}
          </div>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            {resource.description}
          </p>

          {/* Quick metadata in collapsed view */}
          {(resource.timeEstimate || resource.difficulty || resource.offlineAccess === true || resource.noSignupRequired) && (
            <div className="flex flex-wrap items-center gap-2 mt-3">
              {resource.timeEstimate && (
                <div className="flex items-center gap-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  <Clock className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                  <span>{t('digitalResources.readyIn', { time: resource.timeEstimate })}</span>
                </div>
              )}
              {resource.difficulty && (
                <span
                  aria-label={`${t('digitalResources.difficulty.label')}: ${t(`digitalResources.difficulty.${resource.difficulty}`)}`}
                  className={clsx(
                    'rounded-full px-2.5 py-1 text-xs font-medium',
                    resource.difficulty === 'easy' && 'bg-status-success-100 dark:bg-status-success-900/40 text-status-success-800 dark:text-status-success-200',
                    resource.difficulty === 'medium' && 'bg-lsc-rose/15 text-lsc-dark dark:text-lsc-cream font-semibold',
                    resource.difficulty === 'advanced' && 'bg-lsc-cream dark:bg-lsc-brown/40 text-lsc-dark dark:text-lsc-cream',
                  )}
                >
                  {t(`digitalResources.difficulty.${resource.difficulty}`)}
                </span>
              )}
              {resource.offlineAccess === true && (
                <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium bg-lsc-cream dark:bg-lsc-brown/40 text-lsc-dark/80 dark:text-lsc-cream/80">
                  {t('digitalResources.chipOffline')}
                </span>
              )}
              {resource.noSignupRequired && (
                <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium bg-lsc-cream dark:bg-lsc-brown/40 text-lsc-dark/80 dark:text-lsc-cream/80">
                  {t('digitalResources.chipNoSignup')}
                </span>
              )}
            </div>
          )}

          {/* Compact decision-making metadata */}
          {(resource.deviceSupport || resource.downloadLimits || (!resource.noSignupRequired && resource.accountRequirements)) && (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
              {resource.deviceSupport && (
                <span className="inline-flex items-center gap-1">
                  <Smartphone className="w-3.5 h-3.5 flex-shrink-0" aria-hidden="true" />
                  {resource.deviceSupport}
                </span>
              )}
              {resource.downloadLimits && (
                <span className="inline-flex items-center gap-1">
                  <Download className="w-3.5 h-3.5 flex-shrink-0" aria-hidden="true" />
                  {resource.downloadLimits}
                </span>
              )}
              {!resource.noSignupRequired && resource.accountRequirements && (
                <span className="inline-flex items-center gap-1">
                  <ClipboardCheck className="w-3.5 h-3.5 flex-shrink-0" aria-hidden="true" />
                  {resource.accountRequirements}
                </span>
              )}
            </div>
          )}
        </div>
        <span className="text-lsc-dark/70 dark:text-lsc-cream/70 flex-shrink-0">
          {expanded ? <ChevronUp aria-hidden="true" className="w-5 h-5" /> : <ChevronDown aria-hidden="true" className="w-5 h-5" />}
        </span>
      </button>
      {onToggleFavorite && (
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onToggleFavorite() }}
          className={clsx(
            'absolute top-4 right-4 p-1.5 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose z-10',
            isFavorite
              ? 'text-lsc-rose dark:text-lsc-rose-light'
              : 'text-lsc-dark/30 dark:text-lsc-cream/30 hover:text-lsc-rose/70 dark:hover:text-lsc-rose-light/70'
          )}
          aria-label={isFavorite ? `Remove ${resource.name} from favorites` : `Add ${resource.name} to favorites`}
          aria-pressed={isFavorite}
        >
          <Star className="w-4 h-4" fill={isFavorite ? 'currentColor' : 'none'} aria-hidden="true" />
        </button>
      )}

      {/* Expanded content with all details */}
      <div id={`resource-details-${resourceId}`} className="px-5 pb-5 pt-0" hidden={!expanded}>
        {expanded && (
          <div className="border-t border-lsc-border dark:border-earth-700 pt-5">

            {/* Mobile tab bar */}
            {isMobile && (
              <nav className="flex gap-1 mb-4 -mx-1" aria-label="Resource details tabs">
                {([
                  { id: 'overview' as MobileTab, label: 'Overview' },
                  { id: 'features' as MobileTab, label: 'Features' },
                  { id: 'getting-started' as MobileTab, label: 'Getting Started' },
                ] as const).map(tab => (
                  <button key={tab.id} type="button" onClick={() => setActiveTab(tab.id)} className={clsx('flex-1 min-h-[44px] px-3 py-2 text-xs font-semibold rounded-lg transition-colors', activeTab === tab.id ? 'bg-lsc-rose text-white' : 'bg-lsc-cream/50 dark:bg-lsc-brown/30 text-lsc-dark/70 dark:text-lsc-cream/70')}>
                    {tab.label}
                  </button>
                ))}
              </nav>
            )}

            {(!isMobile || activeTab === 'overview') && (
              <div className="space-y-5">
            {/* Main description */}
            {resource.details && (
              <div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{resource.details}</p>
              </div>
            )}

            {/* Link to dedicated page if available */}
            {resource.link && (
              <Link
                to={resource.link}
                className="inline-flex items-center gap-2 text-sm font-medium text-lsc-rose dark:text-lsc-rose-light hover:underline"
              >
                {t('digitalResources.explore', { name: resource.name })}
                <ArrowRight className="w-4 h-4" aria-hidden="true" />
              </Link>
            )}

            {/* Try It Now preview for no-signup resources */}
            {resource.noSignupRequired && resource.tryItUrl && (
              <div className="space-y-3">
                {resource.inLibraryOnly && (
                  <div className="flex items-start gap-2 p-3 bg-lsc-cream/50 dark:bg-lsc-brown/30 rounded-lg">
                    <Info className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" aria-hidden="true" />
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {t('digitalResources.inLibraryOnlyNote')}
                    </p>
                  </div>
                )}
                {resource.inLibraryOnly ? (
                  <a
                    href={resource.tryItUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={clsx(
                      'inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                      'bg-lsc-rose text-lsc-white hover:bg-lsc-rose/90',
                      'focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-earth-800',
                    )}
                  >
                    <ExternalLink className="w-4 h-4" aria-hidden="true" />
                    {t('digitalResources.visitInLibrary', { name: resource.name })}
                  </a>
                ) : !showPreview ? (
                  <button
                    type="button"
                    onClick={handleTryIt}
                    className={clsx(
                      'inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                      'bg-lsc-rose text-lsc-white hover:bg-lsc-rose/90',
                      'focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-earth-800',
                    )}
                  >
                    <Play className="w-4 h-4" aria-hidden="true" />
                    {t('digitalResources.tryItNow')}
                  </button>
                ) : (
                  <div className="rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
                    <div className="flex items-center justify-between px-4 py-2 bg-lsc-cream dark:bg-earth-900 border-b border-lsc-border dark:border-earth-700">
                      <span className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                        {resource.name}
                      </span>
                      <button
                        type="button"
                        onClick={handleClosePreview}
                        className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-white dark:hover:bg-earth-700 rounded-lg transition-colors"
                      >
                        <X className="w-3.5 h-3.5" aria-hidden="true" />
                        {t('digitalResources.closePreview')}
                      </button>
                    </div>
                    <div className="relative" style={{ height: '28rem' }}>
                      {!iframeLoaded && (
                        <div className="absolute inset-0 flex items-center justify-center bg-lsc-white dark:bg-earth-800">
                          <div className="text-center space-y-2">
                            <div className="w-6 h-6 border-2 border-lsc-rose border-t-transparent rounded-full motion-safe:animate-spin mx-auto" />
                            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                              {t('digitalResources.loadingPreview')}
                            </p>
                          </div>
                        </div>
                      )}
                      <iframe
                        src={resource.tryItUrl}
                        title={resource.name}
                        className="w-full h-full border-0"
                        sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
                        onLoad={() => setIframeLoaded(true)}
                      />
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Quick facts grid */}
            {(resource.accountRequirements || resource.deviceSupport || resource.downloadLimits) && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {resource.accountRequirements && (
                  <div className="p-3 bg-lsc-cream/50 dark:bg-lsc-brown/30 rounded-lg">
                    <p className="text-xs font-semibold text-lsc-dark dark:text-lsc-cream/90 uppercase tracking-wide mb-1">
                      {t('digitalResources.accountSetup')}
                    </p>
                    <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">{resource.accountRequirements}</p>
                  </div>
                )}
                {resource.deviceSupport && (
                  <div className="p-3 bg-lsc-cream/50 dark:bg-lsc-brown/30 rounded-lg">
                    <p className="text-xs font-semibold text-lsc-dark dark:text-lsc-cream/90 uppercase tracking-wide mb-1">
                      {t('digitalResources.worksOn')}
                    </p>
                    <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">{resource.deviceSupport}</p>
                  </div>
                )}
                {resource.downloadLimits && (
                  <div className="p-3 bg-lsc-cream/50 dark:bg-lsc-brown/30 rounded-lg">
                    <p className="text-xs font-semibold text-lsc-dark dark:text-lsc-cream/90 uppercase tracking-wide mb-1">
                      {t('digitalResources.limits')}
                    </p>
                    <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">{resource.downloadLimits}</p>
                  </div>
                )}
                {resource.offlineAccess !== undefined && (
                  <div className="p-3 bg-lsc-cream/50 dark:bg-lsc-brown/30 rounded-lg">
                    <p className="text-xs font-semibold text-lsc-dark dark:text-lsc-cream/90 uppercase tracking-wide mb-1">
                      {t('digitalResources.offlineAccess')}
                    </p>
                    <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                      {resource.offlineAccess ? t('digitalResources.availableAfterDownload') : t('digitalResources.streamingOnly')}
                    </p>
                  </div>
                )}
              </div>
            )}

              </div>
            )}

            {(!isMobile || activeTab === 'features') && resource.features && resource.features.length > 0 && (
              <div className={clsx(!isMobile && 'mt-5')}>
                <p className="text-xs font-semibold text-lsc-dark dark:text-lsc-cream/90 uppercase tracking-wide mb-2">
                  {t('digitalResources.keyFeatures')}
                </p>
                <ul className="space-y-1">
                  {resource.features.map((feature, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      <Zap className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" aria-hidden="true" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {(!isMobile || activeTab === 'getting-started') && (
              <div className={clsx(!isMobile && 'mt-5', 'space-y-5')}>
            {/* First step shown inline so starting costs zero clicks; later steps stay in the accordion below */}
            {resource.usageGuide && resource.usageGuide.getStarted.length > 0 && (
              <div className="flex items-start gap-3 p-4 bg-lsc-cream/50 dark:bg-lsc-brown/30 rounded-lg">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-lsc-rose text-white text-xs font-bold flex items-center justify-center mt-0.5" aria-hidden="true">1</span>
                <div>
                  <p className="text-xs font-semibold text-lsc-dark dark:text-lsc-cream/90 uppercase tracking-wide mb-1">First step</p>
                  <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">{resource.usageGuide.getStarted[0]}</p>
                </div>
              </div>
            )}
            {/* Exit strategy section - transparency and empowerment */}
            {resource.usageGuide && (
              <ExitStrategySection
                service={resource.usageGuide.service}
                cancelSteps={resource.usageGuide.getStarted}
                timeline={resource.usageGuide.dataRemoval}
                {...(resource.usageGuide.alternativePromo ? { alternativePromo: resource.usageGuide.alternativePromo } : {})}
                defaultExpanded={false}
              />
            )}

            {/* Privacy & Transparency section */}
            {resource.privacyPolicyUrl && (() => {
              const isExternal = resource.privacyPolicyUrl.startsWith('http')
              return (
              <div className="p-4 bg-earth-50 dark:bg-earth-800/50 rounded-lg border border-lsc-border dark:border-earth-700">
                <div className="flex items-start gap-3">
                  <Shield className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 flex-shrink-0 mt-0.5" aria-hidden="true" />
                  <div className="flex-1 space-y-2">
                    <p className="text-xs font-semibold text-lsc-dark dark:text-lsc-cream/90 uppercase tracking-wide">
                      {t('digitalResources.privacyAndData')}
                    </p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {t('digitalResources.thirdPartyPrivacy')}{' '}
                      <a
                        href={resource.privacyPolicyUrl}
                        {...(isExternal ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
                        className="inline-flex items-center gap-1 text-lsc-rose dark:text-lsc-rose-light hover:underline font-medium"
                      >
                        {t('digitalResources.readTheirPrivacyPolicy')}
                        {isExternal && <ExternalLink className="w-3 h-3" aria-hidden="true" />}
                      </a>
                    </p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {t('digitalResources.dontLikeWhatYouSee')}{' '}
                      <a
                        href="/contact?subject=Vendor%20Privacy%20Concern"
                        className="text-lsc-rose dark:text-lsc-rose-light hover:underline font-medium"
                      >
                        {t('digitalResources.tellUs')}
                      </a>
                      {'. '}
                      {t('digitalResources.tellUsVendorPrivacy')}
                    </p>
                  </div>
                </div>
              </div>
              )
            })()}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default function DigitalResourcesPage(): React.ReactElement {
  const branding = useBranding()
  const [serviceStatuses, setServiceStatuses] = useState<Map<string, ServiceStatusEntry>>(new Map())

  useEffect(() => {
    let cancelled = false
    fetchApi('/digital-resources/status')
      .then((data: { services: ServiceStatusEntry[] }) => {
        if (cancelled) return
        const map = new Map<string, ServiceStatusEntry>()
        for (const svc of data.services) map.set(svc.name, svc)
        setServiceStatuses(map)
      })
      .catch(() => {
        // Silently ignore - indicators just won't show
      })
    return () => { cancelled = true }
  }, [])

  usePageTitle('Digital Resources', `Access free digital resources including ebooks, databases, and online learning tools at ${branding.library_short_name}.`)
  const { t } = useTranslation()
  const { favorites, toggle: toggleFavorite } = useFavorites()
  const [quizAnswers, setQuizAnswers] = useState<QuizAnswers | null>(null)
  const [showQuiz, setShowQuiz] = useState(false)
  useEffect(() => { const saved = loadQuizAnswers(); if (saved) setQuizAnswers(saved); else setShowQuiz(true) }, [])
  const handleQuizComplete = useCallback((answers: QuizAnswers) => { setQuizAnswers(answers); setShowQuiz(false) }, [])
  const handleRetakeQuiz = useCallback(() => { clearQuizAnswers(); setQuizAnswers(null); setShowQuiz(true) }, [])
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set(['MetisLibrary']))
  const [activeFilter, setActiveFilter] = useState<string>('all')
  const [faqSearch, setFaqSearch] = useState('')
  const faqGroupOrder = [
    t('digitalResources.faqGroupGettingStarted'),
    t('digitalResources.faqGroupPrivacyData'),
    t('digitalResources.faqGroupAboutServices'),
  ]

  const faqs = useMemo(() => [
    {
      question: t('digitalResources.faq.q1'),
      answer: t('digitalResources.faq.a1'),
      group: t('digitalResources.faqGroupGettingStarted'),
    },
    {
      question: t('digitalResources.faq.q3'),
      answer: t('digitalResources.faq.a3'),
      group: t('digitalResources.faqGroupGettingStarted'),
    },
    {
      question: t('digitalResources.faq.q10'),
      answer: t('digitalResources.faq.a10'),
      group: t('digitalResources.faqGroupGettingStarted'),
    },
    {
      question: t('digitalResources.faq.q8'),
      answer: t('digitalResources.faq.a8'),
      group: t('digitalResources.faqGroupGettingStarted'),
    },
    {
      question: t('digitalResources.faq.q5'),
      answer: t('digitalResources.faq.a5'),
      linkText: t('digitalResources.faq.a5LinkText'),
      linkHref: '/about/ai-policy',
      group: t('digitalResources.faqGroupPrivacyData'),
    },
    {
      question: t('digitalResources.faq.q6'),
      answer: t('digitalResources.faq.a6'),
      group: t('digitalResources.faqGroupPrivacyData'),
    },
    {
      question: t('digitalResources.faq.q2'),
      answer: t('digitalResources.faq.a2'),
      group: t('digitalResources.faqGroupAboutServices'),
    },
    {
      question: t('digitalResources.faq.q4'),
      answer: t('digitalResources.faq.a4'),
      group: t('digitalResources.faqGroupAboutServices'),
    },
    {
      question: t('digitalResources.faq.q7'),
      answer: t('digitalResources.faq.a7'),
      group: t('digitalResources.faqGroupAboutServices'),
    },
    {
      question: t('digitalResources.faq.q9'),
      answer: t('digitalResources.faq.a9'),
      linkText: t('digitalResources.faq.a9LinkText'),
      linkHref: '/about/digital-transition',
      group: t('digitalResources.faqGroupAboutServices'),
    },
  ], [t])

  const filteredFaqs = useMemo(() => {
    if (!faqSearch.trim()) return faqs
    const query = faqSearch.toLowerCase()
    return faqs.filter(faq =>
      faq.question.toLowerCase().includes(query) ||
      faq.answer.toLowerCase().includes(query)
    )
  }, [faqs, faqSearch])

  const startHereResources: Resource[] = useMemo(() => [
    {
      name: 'MetisLibrary',
      category: 'books',
      description: t('digitalResources.metisLibrary.description'),
      icon: Library,
      link: '/indie/discover',
      details: t('digitalResources.metisLibrary.details'),
      timeEstimate: t('digitalResources.metisLibrary.timeEstimate'),
      difficulty: 'easy',
      accountRequirements: t('digitalResources.metisLibrary.accountRequirements'),
      deviceSupport: t('digitalResources.metisLibrary.deviceSupport'),
      features: [
        t('digitalResources.metisLibrary.feature1'),
        t('digitalResources.metisLibrary.feature2'),
        t('digitalResources.metisLibrary.feature3'),
        t('digitalResources.metisLibrary.feature4'),
        t('digitalResources.metisLibrary.feature5'),
        t('digitalResources.metisLibrary.feature6'),
      ],
      offlineAccess: true,
      downloadLimits: t('digitalResources.metisLibrary.downloadLimits'),
      privacyPolicyUrl: '/privacy',
      usageGuide: {
        service: 'MetisLibrary',
        getStarted: [
          t('digitalResources.metisLibrary.guideStep1'),
          t('digitalResources.metisLibrary.guideStep2'),
          t('digitalResources.metisLibrary.guideStep3'),
        ],
        dataRemoval: t('digitalResources.metisLibrary.dataRemoval'),
      },
    },
    {
      name: 'Palace Project',
      category: 'books',
      description: t('digitalResources.palaceProject.description'),
      icon: Headphones,
      badge: 'App',
      badgeColor: 'text-status-success-700 dark:text-status-success-300',
      details: t('digitalResources.palaceProject.details'),
      timeEstimate: t('digitalResources.palaceProject.timeEstimate'),
      difficulty: 'easy',
      accountRequirements: t('digitalResources.palaceProject.accountRequirements'),
      deviceSupport: t('digitalResources.palaceProject.deviceSupport'),
      features: [
        t('digitalResources.palaceProject.feature1'),
        t('digitalResources.palaceProject.feature2'),
        t('digitalResources.palaceProject.feature3'),
        t('digitalResources.palaceProject.feature4'),
        t('digitalResources.palaceProject.feature5'),
      ],
      offlineAccess: true,
      downloadLimits: t('digitalResources.palaceProject.downloadLimits'),
      usageGuide: {
        service: 'Palace Project',
        getStarted: [
          t('digitalResources.palaceProject.guideStep1'),
          t('digitalResources.palaceProject.guideStep2'),
          t('digitalResources.palaceProject.guideStep3'),
        ],
        dataRemoval: t('digitalResources.palaceProject.dataRemoval'),
      },
    },

  ], [t])

  const otherResources: Resource[] = useMemo(() => [
    {
      name: 'Freegal Music',
      category: 'music',
      description: t('digitalResources.streamAndDownloadMillionsOf'),
      icon: Music,
      details: t('digitalResources.freegalMusic.details'),
      timeEstimate: t('digitalResources.freegalMusic.timeEstimate'),
      difficulty: 'easy',
      accountRequirements: t('digitalResources.freegalMusic.accountRequirements'),
      deviceSupport: t('digitalResources.freegalMusic.deviceSupport'),
      features: [t('digitalResources.freegalMusic.feature1'), t('digitalResources.freegalMusic.feature2'), t('digitalResources.freegalMusic.feature3'), t('digitalResources.freegalMusic.feature4'), t('digitalResources.freegalMusic.feature5')],
      offlineAccess: true,
      downloadLimits: t('digitalResources.freegalMusic.downloadLimits'),
      privacyPolicyUrl: 'https://www.freegalmusic.com/privacy-policy',
      usageGuide: {
        service: 'Freegal Music',
        getStarted: [t('digitalResources.freegalMusic.guideStep1'), t('digitalResources.freegalMusic.guideStep2'), t('digitalResources.freegalMusic.guideStep3')],
        dataRemoval: t('digitalResources.freegalMusic.dataRemoval'),
      },
    },
    {
      name: 'Consumer Reports',
      category: 'research',
      description: t('digitalResources.unbiasedProductReviewsAndRatings'),
      icon: ClipboardCheck,
      details: t('digitalResources.consumerReports.details'),
      timeEstimate: t('digitalResources.consumerReports.timeEstimate'),
      difficulty: 'easy',
      accountRequirements: t('digitalResources.consumerReports.accountRequirements'),
      deviceSupport: t('digitalResources.consumerReports.deviceSupport'),
      features: [t('digitalResources.consumerReports.feature1'), t('digitalResources.consumerReports.feature2'), t('digitalResources.consumerReports.feature3'), t('digitalResources.consumerReports.feature4')],
      offlineAccess: false,
      privacyPolicyUrl: 'https://www.consumerreports.org/customerservice/privacy-policy/',
      usageGuide: {
        service: 'Consumer Reports',
        getStarted: [t('digitalResources.consumerReports.guideStep1'), t('digitalResources.consumerReports.guideStep2'), t('digitalResources.consumerReports.guideStep3')],
        dataRemoval: t('digitalResources.consumerReports.dataRemoval'),
      },
    },
    {
      name: 'Mango Languages',
      category: 'languages',
      description: t('digitalResources.learnLanguagesWithConversationBased'),
      icon: Languages,
      details: t('digitalResources.mangoLanguages.details'),
      timeEstimate: t('digitalResources.mangoLanguages.timeEstimate'),
      difficulty: 'medium',
      accountRequirements: t('digitalResources.mangoLanguages.accountRequirements'),
      deviceSupport: t('digitalResources.mangoLanguages.deviceSupport'),
      features: [t('digitalResources.mangoLanguages.feature1'), t('digitalResources.mangoLanguages.feature2'), t('digitalResources.mangoLanguages.feature3'), t('digitalResources.mangoLanguages.feature4'), t('digitalResources.mangoLanguages.feature5')],
      offlineAccess: true,
      privacyPolicyUrl: 'https://mangolanguages.com/legal/privacy-policy/',
      usageGuide: {
        service: 'Mango Languages',
        getStarted: [t('digitalResources.mangoLanguages.guideStep1'), t('digitalResources.mangoLanguages.guideStep2'), t('digitalResources.mangoLanguages.guideStep3')],
        dataRemoval: t('digitalResources.mangoLanguages.dataRemoval'),
      },
    },
    {
      name: 'Ancestry Library Edition',
      category: 'research',
      description: t('digitalResources.billionsOfGenealogyRecordsFor'),
      icon: ScrollText,
      badge: t('digitalResources.ancestryLibrary.badge'),
      badgeColor: 'text-lsc-rose dark:text-lsc-rose-light',
      details: t('digitalResources.ancestryLibrary.details'),
      timeEstimate: t('digitalResources.ancestryLibrary.timeEstimate'),
      difficulty: 'medium',
      accountRequirements: t('digitalResources.ancestryLibrary.accountRequirements'),
      deviceSupport: t('digitalResources.ancestryLibrary.deviceSupport'),
      features: [t('digitalResources.ancestryLibrary.feature1'), t('digitalResources.ancestryLibrary.feature2'), t('digitalResources.ancestryLibrary.feature3'), t('digitalResources.ancestryLibrary.feature4'), t('digitalResources.ancestryLibrary.feature5')],
      offlineAccess: false,
      noSignupRequired: true,
      tryItUrl: 'https://www.ancestrylibrary.com',
      inLibraryOnly: true,
      privacyPolicyUrl: 'https://www.ancestrylibrary.com/c/legal/privacystatement',
      usageGuide: {
        service: 'Ancestry Library Edition',
        getStarted: [
          t('digitalResources.ancestryLibrary.guideStep1'),
          t('digitalResources.ancestryLibrary.guideStep2'),
          t('digitalResources.ancestryLibrary.guideStep3'),
        ],
        dataRemoval: t('digitalResources.ancestryLibrary.dataRemoval'),
      },
    },
  ], [t])

  const filteredStartHere = useMemo(() => activeFilter === 'all' ? startHereResources : startHereResources.filter(r => r.category === activeFilter), [startHereResources, activeFilter])
  const filteredOther = useMemo(() => activeFilter === 'all' ? otherResources : otherResources.filter(r => r.category === activeFilter), [otherResources, activeFilter])

  const allResources = useMemo(() => [...startHereResources, ...otherResources], [startHereResources, otherResources])
  const recommendations = useMemo(() => quizAnswers ? getRecommendations(allResources, quizAnswers) : [], [allResources, quizAnswers])

  const toggleItem = (name: string): void => {
    setExpandedItems(prev => {
      const next = new Set(prev)
      if (next.has(name)) {
        next.delete(name)
      } else {
        next.add(name)
      }
      return next
    })
  }
  return (
    <StandardPageLayout
      title={t('digitalResources.digitalAccessForEveryone')}
      subtitle={t('digitalResources.everyResourceOnThisPage')}
      icon={Monitor}
    >

      {/* Patron digital activity summary - visible to logged-in users */}
      <div className="print:hidden">
        <DigitalActivityPanel />
      </div>

      {showQuiz && !quizAnswers && <div className="print:hidden"><RecommendationQuiz onComplete={handleQuizComplete} /></div>}
      {quizAnswers && recommendations.length > 0 && (
        <section aria-labelledby="recs-heading">
          <div className="flex items-center justify-between mb-4 print:hidden">
            <div className="flex items-center gap-2">
              <Sparkles aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
              <h2 id="recs-heading" className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Recommended for You</h2>
            </div>
            <button type="button" onClick={handleRetakeQuiz} className="inline-flex items-center gap-1.5 text-xs text-lsc-dark/50 dark:text-lsc-cream/50 hover:text-lsc-rose dark:hover:text-lsc-rose-light transition-colors">
              <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" />Retake quiz
            </button>
          </div>
          <RecommendationSummaryCard recommendations={recommendations} />
          <div className="space-y-3 mt-3 print:hidden">{recommendations.map(resource => (<ResourceCard key={resource.name} resource={resource} expanded={expandedItems.has(resource.name)} onToggle={() => toggleItem(resource.name)} serviceStatus={serviceStatuses.get(resource.name)} isFavorite={favorites.has(resource.name)} onToggleFavorite={() => toggleFavorite(resource.name)} />))}</div>
        </section>
      )}

      {/* Secondary browse-by-type row. The wizard is the primary path; this is a lighter
          fallback so it does not compete visually with the recommendation. */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 print:hidden">
        <span className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50">Or browse by type:</span>
        {[
          { key: 'all', label: 'All' },
          { key: 'books', label: 'Books & Reading' },
          { key: 'music', label: 'Music' },
          { key: 'research', label: 'Research' },
          { key: 'languages', label: 'Languages' },
        ].map(f => (
          <button key={f.key} type="button" onClick={() => setActiveFilter(f.key)} aria-pressed={activeFilter === f.key} className={clsx('text-xs transition-colors', activeFilter === f.key ? 'font-semibold text-lsc-rose dark:text-lsc-rose-light underline underline-offset-4' : 'text-lsc-dark/60 dark:text-lsc-cream/60 hover:text-lsc-rose dark:hover:text-lsc-rose-light')}>
            {f.label}
          </button>
        ))}
      </div>

      {/* Start Here */}
      <section aria-labelledby="essentials-heading" className="print:hidden">
        <div className="flex items-center gap-2 mb-4">
          <Sparkles aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          <h2 id="essentials-heading" className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            {t('digitalResources.theEssentials')}
          </h2>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
          {t('digitalResources.theEssentialsDesc')}
        </p>
        <div className="space-y-3">
          {sortByFavorites(filteredStartHere, favorites).map(resource => (
            <ResourceCard
              key={resource.name}
              resource={resource}
              expanded={expandedItems.has(resource.name)}
              onToggle={() => toggleItem(resource.name)}
              isFavorite={favorites.has(resource.name)}
              onToggleFavorite={() => toggleFavorite(resource.name)}
              serviceStatus={serviceStatuses.get(resource.name)}
            />
          ))}
        </div>
      </section>

      {/* Everything Else */}
      <section aria-labelledby="go-deeper-heading" className="print:hidden">
        <h2 id="go-deeper-heading" className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
          {t('digitalResources.goDeeper')}
        </h2>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          {t('digitalResources.goDeeperDesc')}
        </p>
        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mb-6 italic">
          {t('digitalResources.goDeeperGrant')}
        </p>
        <div className="space-y-3">
          {sortByFavorites(filteredOther, favorites).map(resource => (
            <ResourceCard
              key={resource.name}
              resource={resource}
              expanded={expandedItems.has(resource.name)}
              onToggle={() => toggleItem(resource.name)}
              isFavorite={favorites.has(resource.name)}
              onToggleFavorite={() => toggleFavorite(resource.name)}
              serviceStatus={serviceStatuses.get(resource.name)}
            />
          ))}
        </div>
      </section>

      {/* About These Resources - collapsed */}
      <div className="bg-lsc-cream dark:bg-lsc-dark/20 border border-lsc-border dark:border-earth-800 rounded-xl print:hidden">
        <button onClick={() => setExpandedItems(prev => { const next = new Set(prev); if (next.has('__about__')) next.delete('__about__'); else next.add('__about__'); return next })} className="w-full p-4 flex items-center gap-3 text-left" aria-expanded={expandedItems.has('__about__')}>
          <AlertCircle aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0" />
          <span className="flex-1 text-sm font-semibold text-lsc-dark dark:text-lsc-cream">About These Resources</span>
          <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{expandedItems.has('__about__') ? <ChevronUp className="w-5 h-5" aria-hidden="true" /> : <ChevronDown className="w-5 h-5" aria-hidden="true" />}</span>
        </button>
        {expandedItems.has('__about__') && (
          <div className="px-4 pb-4 space-y-3 border-t border-lsc-border dark:border-earth-700 pt-3">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 italic">{t('digitalResources.reassurance')}</p>
            <p className="text-sm text-lsc-dark dark:text-lsc-cream/90"><strong>{t('digitalResources.aboutOurNumbers')}</strong> {t('digitalResources.aboutOurNumbersText')}</p>
          </div>
        )}
      </div>

      {/* Open Content Philosophy */}
      <div className="bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-xl p-5 print:hidden">
        <div className="flex gap-4">
          <Shield aria-hidden="true" className="w-6 h-6 text-status-success-600 dark:text-status-success-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-3">
            <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              {t('digitalResources.whyWeChoseOpenContent')}
            </h2>
            <div className="text-sm text-lsc-dark/80 dark:text-lsc-cream/90 space-y-3">
              <p>
                <strong>{t('digitalResources.wePrioritizeOpenSourceIndie')}</strong> {t('digitalResources.openContentMetisDesc')}
              </p>
              <p>
                <strong>{t('digitalResources.ourPositionOnAiContent')}</strong> {t('digitalResources.openContentAiDesc')}{' '}
                <Link to="/about/ai-policy" className="text-status-success-700 dark:text-status-success-300 hover:underline font-medium">
                  {t('digitalResources.readFullAiPosition')} &rarr;
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Honest Answers */}
      <section aria-labelledby="faq-heading" className="print:hidden">
        <div className="text-center mb-6">
          <div className="flex items-center justify-center gap-2 mb-2">
            <AlertCircle aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            <h2 id="faq-heading" className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              {t('digitalResources.faqHeading')}
            </h2>
          </div>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            {t('digitalResources.faqSubheading')}
          </p>
        </div>

        {/* FAQ search */}
        <div className="relative max-w-md mx-auto mb-8">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/40 dark:text-lsc-cream/40" aria-hidden="true" />
          <input
            type="text"
            value={faqSearch}
            onChange={e => setFaqSearch(e.target.value)}
            placeholder={t('digitalResources.faqSearchPlaceholder')}
            className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-lsc-white dark:bg-earth-900 border border-lsc-border dark:border-earth-700 text-sm text-lsc-dark dark:text-lsc-cream placeholder:text-lsc-dark/40 dark:placeholder:text-lsc-cream/40 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          />
        </div>

        {filteredFaqs.length === 0 ? (
          <p className="text-center text-sm text-lsc-dark/70 dark:text-lsc-cream/70 py-8">
            {t('digitalResources.faqNoResults')}
          </p>
        ) : (
          <div className="space-y-8">
            {faqGroupOrder
              .filter(group => filteredFaqs.some(faq => faq.group === group))
              .map(group => (
              <div key={group}>
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
                  {group}
                </h3>
                <div className="grid md:grid-cols-2 gap-4">
                  {filteredFaqs.filter(faq => faq.group === group).map(faq => (
                    <div
                      key={faq.question}
                      id={`faq-${sanitizeId(faq.question)}`}
                      className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 text-left"
                    >
                      <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                        {faq.question}
                      </h4>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {faq.answer}
                        {'linkHref' in faq && faq.linkHref && (
                          <>
                            {' '}
                            <Link to={faq.linkHref} className="text-lsc-rose dark:text-lsc-rose-light hover:underline font-medium" aria-label={'linkText' in faq && faq.linkText ? undefined : `Learn more about ${faq.question}`}>
                              {'linkText' in faq && faq.linkText ? faq.linkText : t('digitalResources.learnMore')} &rarr;
                            </Link>
                          </>
                        )}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Need help? */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 print:hidden">
        <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-3">
          Need Help Getting Started?
        </h2>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          These services are new and we're happy to walk you through any of them. Stop by the reference desk, call us, or{' '}
          <a href="/contact" className="text-lsc-rose dark:text-lsc-rose-light hover:underline font-medium">
            send us a message
          </a>.
          We also offer free one-on-one tutorials for any digital service.
        </p>
      </div>

    </StandardPageLayout>
  )
}
