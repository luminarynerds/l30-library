/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft, FileText, Vote, CheckCircle,
  Download, ChevronDown, ChevronRight, Clock,
  Calendar, AlertCircle, Loader2
} from 'lucide-react'
import api from '../../api/api'
import { API_BASE } from '@/api/types'
import { useTranslation, getCurrentLocale } from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

interface PrepAgendaItem {
  id: number
  title: string
  description?: string
  presenter?: string
  duration_minutes?: number
  order: number
}

interface PrepMotionItem {
  id: number
  title: string
  description?: string
  status: string
  proposed_by?: string
}

interface PrepActionItem {
  id: number
  description: string
  assigned_to?: string
  due_date?: string
  status: string
  from_meeting_date?: string
}

interface PrepPreviousMinutes {
  meeting_id: number
  meeting_date: string
  summary?: string
  key_decisions: string[]
}

interface MeetingPrepPacket {
  meeting_id: number
  meeting_title?: string
  meeting_date: string
  location?: string
  agenda_items: PrepAgendaItem[]
  pending_motions: PrepMotionItem[]
  open_action_items: PrepActionItem[]
  previous_minutes?: PrepPreviousMinutes
  generated_at: string
}

interface CollapsibleSectionProps {
  title: string
  icon: React.ElementType
  count?: number
  children: React.ReactNode
  defaultOpen?: boolean
}

function CollapsibleSection({ title, icon: Icon, count, children, defaultOpen = false }: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-3 px-6 py-4 hover:bg-lsc-cream/50 dark:hover:bg-earth-700/50 transition-colors"
        aria-expanded={isOpen}
      >
        <Icon className="w-5 h-5 text-lsc-rose flex-shrink-0" />
        <span className="flex-1 text-left font-semibold text-lsc-dark dark:text-lsc-cream">{title}</span>
        {count !== undefined && (
          <span className="px-2 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded-full text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/80">
            {count}
          </span>
        )}
        {isOpen ? (
          <ChevronDown className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
        ) : (
          <ChevronRight className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
        )}
      </button>
      {isOpen && (
        <div className="px-6 pb-6 border-t border-lsc-border dark:border-earth-700">
          <div className="pt-4">
            {children}
          </div>
        </div>
      )}
    </div>
  )
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString(getCurrentLocale(), {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

function formatShortDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString(getCurrentLocale(), {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export default function MeetingPrepPage(): React.ReactElement {
  const { t } = useTranslation()
  const { meetingId } = useParams<{ meetingId: string }>()
  const [packet, setPacket] = useState<MeetingPrepPacket | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!meetingId) return
    let cancelled = false

    const fetchPrep = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await api.get(`${API_BASE}/board/meetings/${meetingId}/prep`) as MeetingPrepPacket
        if (!cancelled) setPacket(data)
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load meeting prep data')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchPrep()
    return () => { cancelled = true }
  }, [meetingId])

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-earth-900 dark:via-earth-900 dark:to-lsc-dark">
        <PageContainer className="py-8">
          <Link
            to="/staff/admin/board"
            className="inline-flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/80 hover:text-lsc-rose transition-colors mb-6"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Board Management
          </Link>
          <div className="flex items-center justify-center py-24">
            <Loader2 className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" />
            <span className="ml-3 text-lsc-dark/70 dark:text-lsc-cream/80">Loading prep packet...</span>
          </div>
        </PageContainer>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-earth-900 dark:via-earth-900 dark:to-lsc-dark">
        <PageContainer className="py-8">
          <Link
            to="/staff/admin/board"
            className="inline-flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/80 hover:text-lsc-rose transition-colors mb-6"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Board Management
          </Link>
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <AlertCircle className="w-10 h-10 text-status-danger-500 mb-4" />
            <p className="text-lg font-medium text-lsc-dark dark:text-lsc-cream mb-2">Unable to load prep packet</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors"
            >
              Try Again
            </button>
          </div>
        </PageContainer>
      </div>
    )
  }

  if (!packet) return <></>

  return (
    <>
    <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-earth-900 dark:via-earth-900 dark:to-lsc-dark">
      <PageContainer className="py-8">
        {/* Back Link */}
        <Link
          to="/staff/admin/board"
          className="inline-flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/80 hover:text-lsc-rose transition-colors mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Board Management
        </Link>

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">
              Meeting Prep Packet
            </h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/80 mt-1">
              {packet.meeting_title || `Meeting #${packet.meeting_id}`}
            </p>
            <div className="flex items-center gap-3 mt-3">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/80 rounded-full text-sm">
                <Calendar className="w-4 h-4" />
                {formatDate(packet.meeting_date)}
              </span>
              {packet.location && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/80 rounded-full text-sm">
                  {packet.location}
                </span>
              )}
              <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/80 rounded-full text-sm">
                <Clock className="w-4 h-4" />
                Generated {formatShortDate(packet.generated_at)}
              </span>
            </div>
          </div>
          <button
            disabled
            className="inline-flex items-center gap-2 px-6 py-3 bg-lsc-rose text-white rounded-xl font-medium opacity-50 cursor-not-allowed"
          >
            <Download className="w-5 h-5" />
            Download PDF
          </button>
        </div>

        {/* Prep Sections */}
        <div className="space-y-4">
          {/* Agenda Items */}
          <CollapsibleSection
            title="Agenda Items"
            icon={FileText}
            count={packet.agenda_items.length}
            defaultOpen={true}
          >
            {packet.agenda_items.length === 0 ? (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 italic">No agenda items yet.</p>
            ) : (
              <div className="space-y-3">
                {packet.agenda_items.map((item) => (
                  <div key={item.id} className="p-4 bg-lsc-cream/50 dark:bg-earth-700/30 rounded-lg">
                    <div className="flex items-start justify-between gap-2">
                      <h4 className="font-medium text-lsc-dark dark:text-lsc-cream">{item.title}</h4>
                      {item.duration_minutes != null && (
                        <span className="flex-shrink-0 inline-flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                          <Clock className="w-3 h-3" />
                          {item.duration_minutes} min
                        </span>
                      )}
                    </div>
                    {item.description && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{item.description}</p>
                    )}
                    {item.presenter && (
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">Presenter: {item.presenter}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CollapsibleSection>

          {/* Pending Motions */}
          <CollapsibleSection
            title="Pending Motions"
            icon={Vote}
            count={packet.pending_motions.length}
          >
            {packet.pending_motions.length === 0 ? (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 italic">No pending motions for this meeting.</p>
            ) : (
              <div className="space-y-3">
                {packet.pending_motions.map((motion) => (
                  <div key={motion.id} className="p-4 bg-lsc-cream/50 dark:bg-earth-700/30 rounded-lg">
                    <div className="flex items-start justify-between gap-2">
                      <h4 className="font-medium text-lsc-dark dark:text-lsc-cream">{motion.title}</h4>
                      <span className={`flex-shrink-0 px-2 py-0.5 rounded-full text-xs font-medium ${
                        motion.status === 'pending'
                          ? 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300'
                          : 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300'
                      }`}>
                        {motion.status}
                      </span>
                    </div>
                    {motion.description && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{motion.description}</p>
                    )}
                    {motion.proposed_by && (
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">Proposed by: {motion.proposed_by}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CollapsibleSection>

          {/* Open Action Items */}
          <CollapsibleSection
            title="Open Action Items"
            icon={CheckCircle}
            count={packet.open_action_items.length}
          >
            {packet.open_action_items.length === 0 ? (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 italic">
                {t('meetingPrep.noOpenActionItems')}
              </p>
            ) : (
              <div className="space-y-3">
                {packet.open_action_items.map((item) => (
                  <div key={item.id} className="p-4 bg-lsc-cream/50 dark:bg-earth-700/30 rounded-lg">
                    <div className="flex items-start justify-between gap-2">
                      <p className="font-medium text-lsc-dark dark:text-lsc-cream">{item.description}</p>
                      <span className={`flex-shrink-0 px-2 py-0.5 rounded-full text-xs font-medium ${
                        item.status === 'overdue'
                          ? 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300'
                          : item.status === 'in_progress'
                          ? 'bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-300'
                          : 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300'
                      }`}>
                        {item.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                      {item.assigned_to && <span>Assigned to: {item.assigned_to}</span>}
                      {item.due_date && <span>Due: {formatShortDate(item.due_date)}</span>}
                      {item.from_meeting_date && <span>From: {formatShortDate(item.from_meeting_date)}</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CollapsibleSection>

          {/* Previous Minutes Summary */}
          <CollapsibleSection
            title="Previous Meeting Minutes"
            icon={FileText}
          >
            {!packet.previous_minutes ? (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 italic">No previous minutes available.</p>
            ) : (
              <div className="space-y-4">
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                  From meeting on {formatDate(packet.previous_minutes.meeting_date)}
                </p>
                {packet.previous_minutes.summary && (
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{packet.previous_minutes.summary}</p>
                )}
                {packet.previous_minutes.key_decisions.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">Key Decisions</h4>
                    <ul className="space-y-1">
                      {packet.previous_minutes.key_decisions.map((decision, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          <CheckCircle className="w-4 h-4 text-status-success-600 dark:text-status-success-400 flex-shrink-0 mt-0.5" />
                          {decision}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </CollapsibleSection>
        </div>
      </PageContainer>
    </div>
    </>
  )
}
