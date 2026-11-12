/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getMarketingReminders,
  updateMarketingMilestone,
  type ProgramMarketingMilestone,
} from '@/api/program-planning-api'
import { Bell, Check, Loader2, MessageSquareText } from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation } from '@/i18n'

function MarketingRemindersTab() {
  const { t } = useTranslation();
  const queryClient = useQueryClient()
  const [daysAhead, setDaysAhead] = useState(14)
  const [expandedNotes, setExpandedNotes] = useState<Set<number>>(new Set())
  const [notesDraft, setNotesDraft] = useState<Record<number, string>>({})

  const { data: reminders, isLoading } = useQuery({
    queryKey: ['marketing-reminders', daysAhead],
    queryFn: () => getMarketingReminders(daysAhead),
  })

  const toggleComplete = useMutation({
    mutationFn: ({ id, completed }: { id: number; completed: boolean }) =>
      updateMarketingMilestone(id, { completed }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['marketing-reminders'] })
      toast.success('Milestone updated')
    },
    onError: () => toast.error('Failed to update milestone'),
  })

  const saveNotes = useMutation({
    mutationFn: ({ id, notes }: { id: number; notes: string }) =>
      updateMarketingMilestone(id, { notes: notes || null }),
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({ queryKey: ['marketing-reminders'] })
      setExpandedNotes(prev => { const next = new Set(prev); next.delete(vars.id); return next })
      toast.success('Notes saved')
    },
    onError: () => toast.error('Failed to save notes'),
  })

  const handleToggleNotes = (reminder: ProgramMarketingMilestone) => {
    setExpandedNotes(prev => {
      const next = new Set(prev)
      if (next.has(reminder.id)) {
        next.delete(reminder.id)
      } else {
        next.add(reminder.id)
        setNotesDraft(d => ({ ...d, [reminder.id]: reminder.notes ?? '' }))
      }
      return next
    })
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          Upcoming Marketing Milestones
        </h2>
        <select
          value={daysAhead}
          onChange={e => setDaysAhead(parseInt(e.target.value))}
          className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
        >
          <option value={7}>Next 7 days</option>
          <option value={14}>Next 14 days</option>
          <option value={30}>Next 30 days</option>
          <option value={60}>Next 60 days</option>
        </select>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-earth-600 dark:text-earth-200" />
        </div>
      ) : !reminders?.length ? (
        <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
          <Bell className="w-12 h-12 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('programPlanning.noUpcomingMarketingMilestonesAll')}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {reminders.map(reminder => {
            const isOverdue = new Date(reminder.due_date) <= new Date()
            const notesOpen = expandedNotes.has(reminder.id)
            return (
              <div key={reminder.id} className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
                <div className={`flex items-center gap-3 p-4 ${reminder.completed ? 'opacity-60' : ''}`}>
                  <button
                    type="button"
                    onClick={() => toggleComplete.mutate({ id: reminder.id, completed: !reminder.completed })}
                    className={`flex-shrink-0 w-5 h-5 rounded border flex items-center justify-center transition-colors ${
                      reminder.completed
                        ? 'bg-status-success-600 border-status-success-600 text-white'
                        : 'border-lsc-border dark:border-earth-600 hover:border-status-success-500'
                    }`}
                    aria-label={reminder.completed ? 'Mark incomplete' : 'Mark complete'}
                  >
                    {reminder.completed && <Check className="w-3 h-3" />}
                  </button>
                  <div aria-hidden="true" className={`w-2 h-2 rounded-full flex-shrink-0 ${isOverdue ? 'bg-status-danger-500' : 'bg-status-warning-500'}`} />
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm font-medium text-lsc-dark dark:text-lsc-cream ${reminder.completed ? 'line-through' : ''}`}>
                      {reminder.description}
                    </p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {reminder.milestone_type.replace(/_/g, ' ')} &middot; Due: {new Date(reminder.due_date).toLocaleDateString()}
                    </p>
                    {!notesOpen && reminder.notes && (
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 truncate mt-0.5">{reminder.notes}</p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => handleToggleNotes(reminder)}
                    className={`flex-shrink-0 p-1 rounded hover:bg-earth-100 dark:hover:bg-earth-700 transition-colors ${
                      reminder.notes ? 'text-status-info-500 dark:text-status-info-400' : 'text-lsc-dark/30 dark:text-lsc-cream/40'
                    }`}
                    aria-label="Toggle notes"
                  >
                    <MessageSquareText className="w-4 h-4" />
                  </button>
                  <span className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${
                    reminder.completed
                      ? 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900 dark:text-status-success-200'
                      : isOverdue
                        ? 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900 dark:text-status-danger-200'
                        : 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900 dark:text-status-warning-200'
                  }`}>
                    {reminder.completed ? 'Done' : isOverdue ? 'Overdue' : 'Upcoming'}
                  </span>
                </div>
                {notesOpen && (
                  <div className="px-4 pb-4 flex gap-2">
                    <label htmlFor={`reminder-note-${reminder.id}`} className="sr-only">
                      {t('aria.marketingReminders.noteFor', 'Note for {{name}}').replace('{{name}}', reminder.description)}
                    </label>
                    <input
                      id={`reminder-note-${reminder.id}`}
                      type="text"
                      value={notesDraft[reminder.id] ?? ''}
                      onChange={e => setNotesDraft(d => ({ ...d, [reminder.id]: e.target.value }))}
                      onKeyDown={e => {
                        if (e.key === 'Enter') saveNotes.mutate({ id: reminder.id, notes: notesDraft[reminder.id] ?? '' })
                      }}
                      placeholder="Add a note..."
                      className="flex-1 px-3 py-1.5 text-sm rounded border border-lsc-border dark:border-earth-700 bg-earth-50 dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream placeholder:text-lsc-dark/30 dark:placeholder:text-lsc-cream/40"
                    />
                    <button
                      type="button"
                      onClick={() => saveNotes.mutate({ id: reminder.id, notes: notesDraft[reminder.id] ?? '' })}
                      className="px-3 py-1.5 text-sm bg-status-info-600 text-white rounded hover:bg-status-info-700 transition-colors"
                    >
                      Save
                    </button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default MarketingRemindersTab
