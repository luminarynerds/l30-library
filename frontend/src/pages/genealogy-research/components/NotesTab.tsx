/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import {
  Search, Plus,
  Lightbulb, Eye,
  Check, AlertTriangle, Star, MessageSquare, Loader,
  CheckCircle, Circle
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation} from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface ResearchNote {
  id: number;
  title: string;
  content: string;
  note_type: string;
  priority: number;
  is_pinned: boolean;
  is_resolved: boolean;
  sources?: string;
  created_at: string;
}


function AddNoteModal({ projectId, onClose, onCreated }: {
  projectId: number
  onClose: () => void
  onCreated: () => void
}) {
  const { t } = useTranslation()
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    note_type: 'observation',
    priority: 1,
    is_pinned: false,
    sources: '',
  })
  const [saving, setSaving] = useState(false)

  async function handleSubmit() {
    if (!formData.title.trim() || !formData.content.trim()) return
    try {
      setSaving(true)
      const { researchNotesApi } = await import('@/api/genealogy-research-api')
      await researchNotesApi.create(projectId, {
        ...formData,
        project_id: projectId,
        is_resolved: false,
      } as Record<string, unknown>)
      toast.success(t('toast.notesTab.researchNoteCreated'))
      onCreated()
    } catch {
      toast.error(t('genealogyResearchPageContent.failedToCreateNote'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <ModalBackdrop onClose={onClose} title="New Research Note">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto">
        <h2 className="font-serif text-xl font-bold mb-5 text-lsc-dark dark:text-lsc-cream">New Research Note</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Title *</label>
            <input type="text" value={formData.title} onChange={e => setFormData(p => ({ ...p, title: e.target.value }))}
              placeholder={t('genealogyResearchPageContent.briefTitleForThisNote')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Note Type</label>
            <select value={formData.note_type} onChange={e => setFormData(p => ({ ...p, note_type: e.target.value }))}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm">
              {[
                { value: 'observation', label: t('genealogyResearchPageContent.observationWhatYouFound') },
                { value: 'hypothesis', label: t('genealogyResearchPageContent.hypothesisTheoryToTest') },
                { value: 'brick_wall', label: t('genealogyResearchPageContent.brickWallResearchObstacle') },
                { value: 'breakthrough', label: 'Breakthrough – Key discovery' },
                { value: 'question', label: 'Question – Open question' },
                { value: 'todo', label: 'To-Do – Action item' },
              ].map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Content *</label>
            <textarea value={formData.content} onChange={e => setFormData(p => ({ ...p, content: e.target.value }))}
              rows={5} placeholder={t('genealogyResearchPageContent.detailedNoteContentObservationsOr')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm resize-none" />
          </div>
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Priority: {['Low', 'Medium', 'High'][formData.priority]}
            </label>
            <input type="range" min={0} max={2} value={formData.priority}
              onChange={e => setFormData(p => ({ ...p, priority: Number(e.target.value) }))}
              className="w-full accent-status-warning-500" />
          </div>
          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Sources</label>
            <input type="text" value={formData.sources} onChange={e => setFormData(p => ({ ...p, sources: e.target.value }))}
              placeholder={t('genealogyResearchPageContent.documentIdsUrlsOrCitations')}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm" />
          </div>
          <label className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 cursor-pointer">
            <input type="checkbox" checked={formData.is_pinned} onChange={e => setFormData(p => ({ ...p, is_pinned: e.target.checked }))} className="rounded accent-status-warning-500" />
            Pin this note to the top
          </label>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <button onClick={onClose} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-800">Cancel</button>
          <button onClick={handleSubmit} disabled={!formData.title.trim() || !formData.content.trim() || saving}
            className="px-5 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700 disabled:opacity-50 font-medium">
            {saving ? 'Saving...' : 'Save Note'}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}

export default function ResearchNotesTab({ projectId }: { projectId: number }) {
  const { t } = useTranslation();
  const [notes, setNotes] = useState<ResearchNote[]>([])
  const [loading, setLoading] = useState(true)
  const [showAddNote, setShowAddNote] = useState(false)
  const [typeFilter, setTypeFilter] = useState('')
  const [unresolvedOnly, setUnresolvedOnly] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    loadNotes()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, typeFilter, unresolvedOnly])

  async function loadNotes() {
    try {
      setLoading(true)
      const { researchNotesApi } = await import('@/api/genealogy-research-api')
      const data = await researchNotesApi.list(projectId, {
        ...(typeFilter ? { note_type: typeFilter } : {}),
        ...(unresolvedOnly ? { unresolved_only: true } : {}),
      })
      setNotes(data)
    } catch {
      toast.error(t('genealogyResearchPageContent.failedToLoadNotes'))
    } finally {
      setLoading(false)
    }
  }

  async function handleToggleResolved(note: ResearchNote) {
    try {
      const { researchNotesApi } = await import('@/api/genealogy-research-api')
      await researchNotesApi.update(projectId, note.id, { is_resolved: !note.is_resolved })
      toast.success(note.is_resolved ? 'Marked as unresolved' : 'Marked as resolved')
      loadNotes()
    } catch {
      toast.error(t('genealogyResearchPageContent.failedToUpdateNote'))
    }
  }

  async function handleTogglePinned(note: ResearchNote) {
    try {
      const { researchNotesApi } = await import('@/api/genealogy-research-api')
      await researchNotesApi.update(projectId, note.id, { is_pinned: !note.is_pinned })
      loadNotes()
    } catch {
      toast.error(t('genealogyResearchPageContent.failedToUpdateNote2'))
    }
  }

  const noteTypeIcons: Record<string, React.ReactNode> = {
    observation: <Eye className="w-4 h-4 text-earth-600" />,
    hypothesis: <Lightbulb className="w-4 h-4 text-status-warning-500" />,
    brick_wall: <AlertTriangle className="w-4 h-4 text-status-danger-500" />,
    breakthrough: <Star className="w-4 h-4 text-status-success-500" />,
    question: <Search className="w-4 h-4 text-category-500" />,
    todo: <Check className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />,
  }

  const noteTypeColors: Record<string, string> = {
    observation: 'border-l-blue-400',
    hypothesis: 'border-l-status-warning-400',
    brick_wall: 'border-l-red-500',
    breakthrough: 'border-l-green-500',
    question: 'border-l-category-400',
    todo: 'border-l-earth-400',
  }

  const filteredNotes = searchQuery
    ? notes.filter(n =>
        n.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        n.content.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : notes

  const unresolvedCount = notes.filter(n => !n.is_resolved).length

  if (loading) {
    return <div className="flex justify-center py-12"><Loader className="w-6 h-6 motion-safe:animate-spin" /></div>
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Research Notes</h2>
          {unresolvedCount > 0 && (
            <p className="text-sm text-status-warning-600 dark:text-status-warning-400 mt-0.5">
              {unresolvedCount} unresolved note{unresolvedCount !== 1 ? 's' : ''}
            </p>
          )}
        </div>
        <button
          onClick={() => setShowAddNote(true)}
          className="flex items-center gap-2 px-3 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700 text-sm"
        >
          <Plus className="w-4 h-4" />
          Add Note
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[180px]">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-lsc-dark/70 dark:text-lsc-cream/70" />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder={t('placeholder.notesTab.filterNotes')}
            aria-label={t('aria.notesTab.filterNotes')}
            className="w-full pl-9 pr-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm text-lsc-dark dark:text-lsc-cream"
          />
        </div>
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
          className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-sm text-lsc-dark dark:text-lsc-cream">
          <option value="">All Types</option>
          {['observation', 'hypothesis', 'brick_wall', 'breakthrough', 'question', 'todo'].map(t => (
            <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 cursor-pointer">
          <input type="checkbox" checked={unresolvedOnly} onChange={e => setUnresolvedOnly(e.target.checked)} className="rounded accent-status-warning-500" />
          Unresolved only
        </label>
      </div>

      {filteredNotes.length === 0 ? (
        <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
          <MessageSquare className="w-12 h-12 mx-auto text-lsc-dark/70 dark:text-lsc-cream/70 mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
            {notes.length === 0
              ? 'No research notes yet. Document your findings, hypotheses, and brick walls.'
              : 'No notes match your current filters.'}
          </p>
          {notes.length === 0 && (
            <button onClick={() => setShowAddNote(true)} className="px-4 py-2 bg-status-warning-600 text-white rounded-lg hover:bg-status-warning-700">
              Add First Note
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {filteredNotes.map((note) => (
            <div key={note.id} className={`bg-lsc-white dark:bg-earth-800 rounded-lg border-l-4 border border-lsc-border dark:border-earth-700 p-4 ${
              note.is_pinned ? 'border-l-status-warning-400 !border-status-warning-200 dark:border-status-warning-800 dark:!border-status-warning-800' : (noteTypeColors[note.note_type] || 'border-l-earth-400')
            } ${note.is_resolved ? 'opacity-60' : ''}`}>
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-0.5">
                  {noteTypeIcons[note.note_type] || <MessageSquare className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h4 className={`font-medium text-sm ${note.is_resolved ? 'line-through text-earth-600' : 'text-lsc-dark dark:text-lsc-cream'}`}>
                      {note.title}
                    </h4>
                    {note.is_pinned && <Star className="w-3 h-3 text-status-warning-500" />}
                    {note.is_resolved && <span className="text-xs px-1.5 py-0.5 bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 rounded-full">Resolved</span>}
                    {note.priority > 0 && (
                      <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                        note.priority >= 2 ? 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300' :
                        note.priority >= 1 ? 'bg-status-warning-100 text-status-warning-700' : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'
                      }`}>
                        {['Low', 'Medium', 'High'][note.priority]} priority
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 line-clamp-2" title={note.content}>{note.content}</p>
                  <div className="flex items-center gap-3 mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    <span className="capitalize">{note.note_type.replace(/_/g, ' ')}</span>
                    <span>{new Date(note.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <div className="flex gap-1 flex-shrink-0">
                  <button
                    onClick={() => handleToggleResolved(note)}
                    className={`p-1.5 rounded hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-700 ${note.is_resolved ? 'text-status-success-500' : 'text-lsc-dark/70 dark:text-lsc-cream/70'}`}
                    title={note.is_resolved ? 'Mark unresolved' : 'Mark resolved'}
                  >
                    {note.is_resolved ? <CheckCircle className="w-4 h-4" /> : <Circle className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={() => handleTogglePinned(note)}
                    className={`p-1.5 rounded hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-700 ${note.is_pinned ? 'text-status-warning-500' : 'text-lsc-dark/70 dark:text-lsc-cream/70'}`}
                    title={note.is_pinned ? 'Unpin' : 'Pin note'}
                  >
                    <Star className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showAddNote && (
        <AddNoteModal
          projectId={projectId}
          onClose={() => setShowAddNote(false)}
          onCreated={() => { setShowAddNote(false); loadNotes() }}
        />
      )}
    </div>
  )
}
