/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { AlertCircle, X, Loader } from 'lucide-react'
import { useTranslation } from '@/i18n'
import {
  AGENT_DEPARTMENTS,
  AGENT_PERSONALITIES,
} from '../../api/library-agents-api'
import type { LibraryAgent, AgentCreateData } from '../../api/library-agents-api'
import FocusTrap from 'focus-trap-react'

interface AgentFormProps {
  agent?: LibraryAgent | null
  onSave: (data: AgentCreateData) => Promise<void>
  onClose: () => void
  isSaving: boolean
}


export function AgentFormModal({ agent, onSave, onClose, isSaving }: AgentFormProps) {
  const { t } = useTranslation();
  const [form, setForm] = useState<AgentCreateData>({
    name: agent?.name || '',
    nickname: agent?.nickname || '',
    role: agent?.role || '',
    department: agent?.department || AGENT_DEPARTMENTS[0],
    bio: agent?.bio || '',
    personality: agent?.personality || 'friendly',
    tone: agent?.tone || '',
    specialties: agent?.specialties || [],
    can_help_with: agent?.can_help_with || [],
    avatar_color: agent?.avatar_color || 'orange',
    initials: agent?.initials || '',
    emoji: agent?.emoji || '',
    greeting_message: agent?.greeting_message || '',
  })
  const [specialtyInput, setSpecialtyInput] = useState('')
  const [helpInput, setHelpInput] = useState('')
  const [error, setError] = useState<string | null>(null)

  const setField = <K extends keyof AgentCreateData>(key: K, value: AgentCreateData[K]) => {
    setForm(prev => ({ ...prev, [key]: value }))
  }

  const addSpecialty = () => {
    if (specialtyInput.trim() && !form.specialties?.includes(specialtyInput.trim())) {
      setField('specialties', [...(form.specialties || []), specialtyInput.trim()])
      setSpecialtyInput('')
    }
  }

  const removeSpecialty = (s: string) => {
    setField('specialties', (form.specialties || []).filter(x => x !== s))
  }

  const addHelp = () => {
    if (helpInput.trim() && !form.can_help_with?.includes(helpInput.trim())) {
      setField('can_help_with', [...(form.can_help_with || []), helpInput.trim()])
      setHelpInput('')
    }
  }

  const removeHelp = (h: string) => {
    setField('can_help_with', (form.can_help_with || []).filter(x => x !== h))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim() || !form.role.trim() || !form.bio.trim()) {
      setError('Name, role, and bio are required.')
      return
    }
    setError(null)
    await onSave(form)
  }

  const inputClass = "w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-cream/30 dark:bg-earth-900/50 text-sm text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:border-lsc-rose"
  const labelClass = "block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onKeyDown={(e) => { if (e.key === 'Escape') onClose() }}>
      <FocusTrap active={true} focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: true, fallbackFocus: () => document.body }}>
      <div
        className="bg-lsc-white dark:bg-earth-900 rounded-xl shadow-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto"
        role="dialog"
        aria-modal="true"
        aria-label={agent ? 'Edit agent' : 'Create new agent'}
      >
        <div className="sticky top-0 bg-lsc-white dark:bg-earth-900 border-b border-lsc-border dark:border-earth-700 px-6 py-4 flex items-center justify-between">
          <h2 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream text-lg">
            {agent ? `Edit ${agent.name}` : 'Create New Agent'}
          </h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-800 transition-colors"
            aria-label={t('aria.authModals.close')}
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-600 dark:text-status-danger-400 text-sm px-4 py-3 rounded-lg flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
              {error}
            </div>
          )}

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="agent-name" className={labelClass}>Name *</label>
              <input id="agent-name" type="text" value={form.name} onChange={e => setField('name', e.target.value)} className={inputClass} placeholder={t('placeholder.adminLibraryAgents.egMarlene')} required />
            </div>
            <div>
              <label htmlFor="agent-nickname" className={labelClass}>Nickname</label>
              <input id="agent-nickname" type="text" value={form.nickname || ''} onChange={e => setField('nickname', e.target.value)} className={inputClass} placeholder={t('placeholder.adminLibraryAgents.egTheDirector')} />
            </div>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="agent-role" className={labelClass}>Role *</label>
              <input id="agent-role" type="text" value={form.role} onChange={e => setField('role', e.target.value)} className={inputClass} placeholder={t('placeholder.adminLibraryAgents.egLibraryDirector')} required />
            </div>
            <div>
              <label htmlFor="agent-department" className={labelClass}>Department *</label>
              <select id="agent-department" value={form.department} onChange={e => setField('department', e.target.value)} className={inputClass}>
                {AGENT_DEPARTMENTS.map(d => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="agent-bio" className={labelClass}>Bio *</label>
            <textarea
              id="agent-bio"
              value={form.bio}
              onChange={e => setField('bio', e.target.value)}
              rows={3}
              className={inputClass}
              placeholder={t('admin.adminLibraryAgents.aBriefDescriptionOfWho')}
              required
            />
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="agent-personality" className={labelClass}>Personality</label>
              <select id="agent-personality" value={form.personality || 'friendly'} onChange={e => setField('personality', e.target.value)} className={inputClass}>
                {AGENT_PERSONALITIES.map(p => (
                  <option key={p.value} value={p.value}>{p.label} — {p.description}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="agent-tone" className={labelClass}>Tone</label>
              <input id="agent-tone" type="text" value={form.tone || ''} onChange={e => setField('tone', e.target.value)} className={inputClass} placeholder={t('placeholder.adminLibraryAgents.egWarmAndConversational')} />
            </div>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="agent-initials" className={labelClass}>Initials</label>
              <input id="agent-initials" type="text" value={form.initials || ''} onChange={e => setField('initials', e.target.value)} className={inputClass} placeholder={t('placeholder.adminLibraryAgents.egMh')} maxLength={3} />
            </div>
            <div>
              <label htmlFor="agent-color" className={labelClass}>Avatar Color</label>
              <select id="agent-color" value={form.avatar_color || 'orange'} onChange={e => setField('avatar_color', e.target.value)} className={inputClass}>
                {['orange', 'blue', 'green', 'purple', 'teal', 'indigo', 'pink', 'red'].map(c => (
                  <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="agent-greeting" className={labelClass}>Greeting Message</label>
            <textarea
              id="agent-greeting"
              value={form.greeting_message || ''}
              onChange={e => setField('greeting_message', e.target.value)}
              rows={2}
              className={inputClass}
              placeholder={t('admin.adminLibraryAgents.whatTheAgentSaysWhen')}
            />
          </div>

          <div>
            <label className={labelClass}>Specialties</label>
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                value={specialtyInput}
                onChange={e => setSpecialtyInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addSpecialty())}
                className={inputClass}
                placeholder={t('placeholder.adminLibraryAgents.addASpecialty')}
              />
              <button type="button" onClick={addSpecialty} className="px-3 py-2 bg-lsc-rose text-white rounded-lg text-sm hover:bg-lsc-rose/90 transition-colors whitespace-nowrap">
                Add
              </button>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {form.specialties?.map(s => (
                <span key={s} className="flex items-center gap-1 px-2 py-1 bg-lsc-cream dark:bg-earth-700 rounded-lg text-xs text-lsc-dark dark:text-lsc-cream">
                  {s}
                  <button type="button" onClick={() => removeSpecialty(s)} className="text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-status-danger-600" aria-label={`Remove specialty: ${s}`}>
                    <X className="w-3 h-3" aria-hidden="true" />
                  </button>
                </span>
              ))}
            </div>
          </div>

          <div>
            <label className={labelClass}>Can Help With</label>
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                value={helpInput}
                onChange={e => setHelpInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addHelp())}
                className={inputClass}
                placeholder={t('admin.adminLibraryAgents.addAHelpTopic')}
              />
              <button type="button" onClick={addHelp} className="px-3 py-2 bg-lsc-rose text-white rounded-lg text-sm hover:bg-lsc-rose/90 transition-colors whitespace-nowrap">
                Add
              </button>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {form.can_help_with?.map(h => (
                <span key={h} className="flex items-center gap-1 px-2 py-1 bg-lsc-cream dark:bg-earth-700 rounded-lg text-xs text-lsc-dark dark:text-lsc-cream">
                  {h}
                  <button type="button" onClick={() => removeHelp(h)} className="text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-status-danger-600" aria-label={`Remove topic: ${h}`}>
                    <X className="w-3 h-3" aria-hidden="true" />
                  </button>
                </span>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="px-4 py-2 rounded-lg bg-lsc-rose text-white text-sm font-medium hover:bg-lsc-rose/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              {isSaving && <Loader className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />}
              {agent ? 'Save Changes' : 'Create Agent'}
            </button>
          </div>
        </form>
      </div>
      </FocusTrap>
    </div>
  )
}
