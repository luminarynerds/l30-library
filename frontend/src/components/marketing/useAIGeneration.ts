/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { COPY_FEEDBACK_DURATION_MS } from '@/constants/timeouts'
import toast from 'react-hot-toast'
import { useAuth } from '@/contexts/AuthContext'
import {
  generateContent,
  saveContent,
  getPrograms,
  getEvents,
  checkAIStatus,
  CONTENT_TYPE_OPTIONS,
  type ContentType,
  type GenerateContentResponse,
} from '@/api/marketing-hub-api'
import { useTranslation } from '@/i18n'
import { clean } from '@/lib/utils'

export interface PromptTemplate {
  id: string
  label: string
  prompt: string
  contentType: ContentType
}

export interface TonePreset {
  value: string
  label: string
}

export const TONE_PRESETS: ReadonlyArray<TonePreset> = [
  { value: '', label: 'Default' },
  { value: 'playful', label: 'Playful' },
  { value: 'professional', label: 'Professional' },
  { value: 'urgent', label: 'Urgent' },
  { value: 'warm', label: 'Warm' },
  { value: 'enthusiastic', label: 'Enthusiastic' },
  { value: 'informative', label: 'Informative' },
]

export const BUILT_IN_TEMPLATES: ReadonlyArray<PromptTemplate> = [
  { id: 'builtin:social_post:event-reminder', label: 'Quick event reminder', prompt: 'Write a friendly reminder post for an upcoming library event. Include the date, time, location, and a clear call to action.', contentType: 'social_post' },
  { id: 'builtin:social_post:new-arrival', label: 'New arrival announcement', prompt: 'Write a short, upbeat post announcing a new arrival at the library. Highlight what makes it interesting and invite people to come check it out.', contentType: 'social_post' },
  { id: 'builtin:social_post:story-time', label: 'Story time invite', prompt: 'Write a warm invitation to weekly story time for kids and caregivers. Mention the day, time, and that all are welcome.', contentType: 'social_post' },
  { id: 'builtin:social_post:hours-change', label: 'Library hours change', prompt: 'Write a clear, factual post letting patrons know the library hours are changing. Include the new hours and the date the change takes effect.', contentType: 'social_post' },
  { id: 'builtin:newsletter:monthly-intro', label: 'Monthly intro', prompt: 'Write a warm monthly newsletter introduction from the library. Set the tone for the month, mention one or two highlights, and invite readers to keep reading.', contentType: 'newsletter' },
  { id: 'builtin:newsletter:featured-collection', label: 'Featured collection', prompt: 'Write a newsletter section featuring a library collection. Describe what is in it, who it is for, and how to find it.', contentType: 'newsletter' },
  { id: 'builtin:newsletter:staff-pick', label: 'Staff pick', prompt: 'Write a short staff pick section for the newsletter. Introduce the staff member, the title they picked, and one reason they love it.', contentType: 'newsletter' },
  { id: 'builtin:newsletter:events-roundup', label: 'Upcoming events roundup', prompt: 'Write a roundup of upcoming library events for the newsletter. Use a short intro, then a clear list with date, time, and a one-line description for each.', contentType: 'newsletter' },
  { id: 'builtin:flyer:event-flyer', label: 'Event flyer', prompt: 'Write flyer copy for a library event. Include a strong headline, the date, time, location, who it is for, and how to sign up.', contentType: 'flyer' },
  { id: 'builtin:flyer:program-signup', label: 'Program signup', prompt: 'Write flyer copy inviting patrons to sign up for a library program. Explain the program briefly, who can join, and how to register.', contentType: 'flyer' },
  { id: 'builtin:flyer:hours-posted', label: 'Hours posted notice', prompt: 'Write a clear, scannable flyer notice posting the library hours. Keep it factual and easy to read at a glance.', contentType: 'flyer' },
  { id: 'builtin:program_promo:kickoff', label: 'Reading challenge kickoff', prompt: 'Write a kickoff announcement for a reading challenge. Build excitement, explain how it works, list the dates, and invite patrons to join.', contentType: 'program_promo' },
  { id: 'builtin:program_promo:mid-program', label: 'Mid-program update', prompt: 'Write a mid-program update for a reading challenge. Celebrate progress so far, remind patrons how much time is left, and encourage them to keep going.', contentType: 'program_promo' },
  { id: 'builtin:program_promo:final-push', label: 'Final week push', prompt: 'Write a final week push for a reading challenge. Create gentle urgency, remind patrons of the deadline, and encourage them to log their last reads.', contentType: 'program_promo' },
  { id: 'builtin:event_promo:author-visit', label: 'Author visit', prompt: 'Write promotional copy for an author visit at the library. Introduce the author, mention their work, and include the date, time, and how to attend.', contentType: 'event_promo' },
  { id: 'builtin:event_promo:workshop-signup', label: 'Workshop signup', prompt: 'Write promotional copy for a library workshop. Describe what attendees will learn, who it is for, and how to sign up.', contentType: 'event_promo' },
  { id: 'builtin:event_promo:family-event', label: 'Family event', prompt: 'Write promotional copy for a family-friendly library event. Make it warm and welcoming, list the activities, and include date, time, and any age guidance.', contentType: 'event_promo' },
  { id: 'builtin:event_promo:teen-night', label: 'Teen night', prompt: 'Write promotional copy for a teen night event at the library. Use a fun, inviting voice, mention what teens will do, and include the date and time.', contentType: 'event_promo' },
]

const CUSTOM_TEMPLATES_STORAGE_KEY = 'marketing-hub:custom-templates:v1'

function loadCustomTemplates(): PromptTemplate[] {
  try {
    const raw = localStorage.getItem(CUSTOM_TEMPLATES_STORAGE_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter((item): item is PromptTemplate => {
      if (!item || typeof item !== 'object') return false
      const t = item as Record<string, unknown>
      return (
        typeof t.id === 'string' &&
        typeof t.label === 'string' &&
        typeof t.prompt === 'string' &&
        typeof t.contentType === 'string'
      )
    })
  } catch {
    return []
  }
}

function persistCustomTemplates(templates: PromptTemplate[]): void {
  try {
    localStorage.setItem(CUSTOM_TEMPLATES_STORAGE_KEY, JSON.stringify(templates))
  } catch {
    // localStorage may throw (Safari private mode, quota); fail silently
  }
}

export function getPlaceholder(contentType: ContentType): string {
  switch (contentType) {
    case 'social_post':
      return 'e.g., Write a Bluesky post announcing our Summer Reading Program kickoff this Saturday...'
    case 'newsletter':
      return 'e.g., Write a newsletter section highlighting our new graphic novel collection and upcoming author visit...'
    case 'flyer':
      return 'e.g., Create flyer text for our Teen Book Club meeting every Wednesday in March...'
    case 'program_promo':
      return 'e.g., Write promotional content for our reading challenge, emphasizing the prizes and fun activities...'
    case 'event_promo':
      return 'e.g., Create an announcement for our author meet-and-greet event, making it sound exciting and welcoming...'
    default:
      return 'Describe what marketing content you need...'
  }
}

export const chipUnselected =
  'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 border border-lsc-border dark:border-earth-700 hover:bg-lsc-cream dark:hover:bg-earth-700'
export const chipSelected = 'bg-lsc-rose text-white border border-lsc-rose'

interface UseAIGenerationOptions {
  onContentGenerated?: (text: string, contentType: string) => void
}

export function useAIGeneration({ onContentGenerated }: UseAIGenerationOptions = {}) {
  const { t } = useTranslation()
  const { token } = useAuth()

  const [contentType, setContentType] = useState<ContentType>('social_post')
  const [instructions, setInstructions] = useState('')
  const [selectedProgramId, setSelectedProgramId] = useState<number | undefined>()
  const [selectedEventId, setSelectedEventId] = useState<number | undefined>()
  const [tone, setTone] = useState('')
  const [temperature, setTemperature] = useState(0.7)
  const [showAdvanced, setShowAdvanced] = useState(false)

  const [customTemplates, setCustomTemplates] = useState<PromptTemplate[]>(() => loadCustomTemplates())
  const [showSaveTemplate, setShowSaveTemplate] = useState(false)
  const [newTemplateLabel, setNewTemplateLabel] = useState('')

  const [result, setResult] = useState<GenerateContentResponse | null>(null)
  const [copied, setCopied] = useState(false)

  const instructionsRef = useRef<HTMLTextAreaElement | null>(null)
  const newTemplateLabelRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    persistCustomTemplates(customTemplates)
  }, [customTemplates])

  useEffect(() => {
    if (showSaveTemplate) {
      newTemplateLabelRef.current?.focus()
    }
  }, [showSaveTemplate])

  const { data: aiStatus } = useQuery({
    queryKey: ['marketing-hub-ai-status'],
    queryFn: () => checkAIStatus(token!),
    staleTime: 30000,
    enabled: !!token,
  })

  const { data: programs = [] } = useQuery({
    queryKey: ['marketing-hub-programs'],
    queryFn: () => getPrograms(token!),
    staleTime: 60000,
    enabled: !!token,
  })

  const { data: events = [] } = useQuery({
    queryKey: ['marketing-hub-events'],
    queryFn: () => getEvents(token!),
    staleTime: 60000,
    enabled: !!token,
  })

  const generateMutation = useMutation({
    mutationFn: () =>
      generateContent(token!, clean({
        content_type: contentType,
        instructions,
        program_id: selectedProgramId,
        event_id: selectedEventId,
        tone: tone || undefined,
        temperature,
      })),
    onSuccess: (data) => {
      setResult(data)
      if (data.success && data.generated_text) {
        onContentGenerated?.(data.generated_text, contentType)
      }
    },
    onError: (error: Error) => {
      toast.error(error.message)
    },
  })

  const saveMutation = useMutation({
    mutationFn: () =>
      saveContent(token!, clean({
        content_type: contentType,
        generated_text: result?.generated_text ?? '',
        user_prompt: instructions,
        model_used: result?.model_used ?? undefined,
        temperature,
        generation_time_ms: result?.generation_time_ms ?? undefined,
        program_id: selectedProgramId,
        event_id: selectedEventId,
        context_data: result?.context_data ?? undefined,
      })),
    onSuccess: () => {
      toast.success(t('components.marketing.aIContentGenerator.contentSavedToHistory'))
    },
    onError: (error: Error) => {
      toast.error(error.message)
    },
  })

  const handleGenerate = (e: React.FormEvent) => {
    e.preventDefault()
    if (!instructions.trim()) return
    setCopied(false)
    generateMutation.mutate()
  }

  const handleCopy = async () => {
    if (result?.generated_text) {
      try {
        await navigator.clipboard.writeText(result.generated_text)
        setCopied(true)
        toast.success(t('toast.copiedToClipboard'))
        setTimeout(() => setCopied(false), COPY_FEEDBACK_DURATION_MS)
      } catch {
        toast.error(t('components.marketing.aIContentGenerator.failedToCopyToClipboard'))
      }
    }
  }

  const handleRegenerate = () => {
    setCopied(false)
    generateMutation.mutate()
  }

  const handleApplyTemplate = (template: PromptTemplate) => {
    setInstructions(template.prompt)
    setTimeout(() => {
      const el = instructionsRef.current
      if (el) {
        el.focus()
        const len = el.value.length
        try {
          el.setSelectionRange(len, len)
        } catch {
          // setSelectionRange may throw on certain input types; ignore
        }
      }
    }, 0)
  }

  const handleSaveTemplate = () => {
    const label = newTemplateLabel.trim()
    const prompt = instructions.trim()
    if (!label || !prompt) return
    const template: PromptTemplate = {
      id: `custom:${contentType}:${Date.now()}`,
      label,
      prompt,
      contentType,
    }
    setCustomTemplates((prev) => [...prev, template])
    setNewTemplateLabel('')
    setShowSaveTemplate(false)
    toast.success(`Saved template "${label}"`)
  }

  const handleDeleteTemplate = (template: PromptTemplate) => {
    if (!window.confirm(`Delete template "${template.label}"?`)) return
    setCustomTemplates((prev) => prev.filter((tpl) => tpl.id !== template.id))
    toast.success(`Deleted template "${template.label}"`)
  }

  const builtInForType = useMemo(
    () => BUILT_IN_TEMPLATES.filter((tpl) => tpl.contentType === contentType),
    [contentType],
  )
  const customForType = useMemo(
    () => customTemplates.filter((tpl) => tpl.contentType === contentType),
    [customTemplates, contentType],
  )

  const selectedContentOption = CONTENT_TYPE_OPTIONS.find((o) => o.value === contentType)
  const canSaveAsTemplate = instructions.trim().length > 0

  return {
    t,
    contentType, setContentType,
    instructions, setInstructions,
    selectedProgramId, setSelectedProgramId,
    selectedEventId, setSelectedEventId,
    tone, setTone,
    temperature, setTemperature,
    showAdvanced, setShowAdvanced,
    customTemplates,
    showSaveTemplate, setShowSaveTemplate,
    newTemplateLabel, setNewTemplateLabel,
    result, copied,
    instructionsRef, newTemplateLabelRef,
    aiStatus, programs, events,
    generateMutation, saveMutation,
    handleGenerate, handleCopy, handleRegenerate,
    handleApplyTemplate, handleSaveTemplate, handleDeleteTemplate,
    builtInForType, customForType,
    selectedContentOption, canSaveAsTemplate,
  }
}
