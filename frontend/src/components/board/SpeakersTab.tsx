/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { Mic, Plus, Play, Square, ChevronUp } from 'lucide-react'
import type { PublicComment, PublicCommentSubmit } from '../../api/board-public-comments-api'

interface SpeakersTabProps {
  speakerComments: PublicComment[]
  showSpeakerForm: boolean
  setShowSpeakerForm: (v: boolean) => void
  speakerForm: PublicCommentSubmit & { type: 'in_person' | 'virtual' }
  setSpeakerForm: (v: PublicCommentSubmit & { type: 'in_person' | 'virtual' }) => void
  submitting: boolean
  activeSpeaker: number | null
  getStatusColor: (status: PublicComment['status']) => string
  getCommentTypeIcon: (type: PublicComment['comment_type']) => React.ReactNode
  onRegisterSpeaker: (e: React.FormEvent) => void
  onStartSpeaking: (id: number) => void
  onStopSpeaking: (id: number) => void
}

export function SpeakersTab({
  speakerComments,
  showSpeakerForm,
  setShowSpeakerForm,
  speakerForm,
  setSpeakerForm,
  submitting,
  activeSpeaker,
  getStatusColor,
  getCommentTypeIcon,
  onRegisterSpeaker,
  onStartSpeaking,
  onStopSpeaking,
}: SpeakersTabProps) {
  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button
          onClick={() => setShowSpeakerForm(!showSpeakerForm)}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90"
        >
          {showSpeakerForm ? <ChevronUp className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
          Register Speaker
        </button>
      </div>

      {showSpeakerForm && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            Register New Speaker
          </h3>
          <form onSubmit={onRegisterSpeaker} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium mb-1 dark:text-earth-200">Name *</label>
                <input
                  type="text"
                  value={speakerForm.commenter_name}
                  onChange={(e) => setSpeakerForm({ ...speakerForm, commenter_name: e.target.value })}
                  required
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1 dark:text-earth-200">Type *</label>
                <select
                  value={speakerForm.type}
                  onChange={(e) => setSpeakerForm({ ...speakerForm, type: e.target.value as 'in_person' | 'virtual' })}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900"
                >
                  <option value="in_person">In-Person</option>
                  <option value="virtual">Virtual</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1 dark:text-earth-200">Email</label>
                <input
                  type="email"
                  value={speakerForm.commenter_email || ''}
                  onChange={(e) => setSpeakerForm({ ...speakerForm, commenter_email: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1 dark:text-earth-200">Organization</label>
                <input
                  type="text"
                  value={speakerForm.organization || ''}
                  onChange={(e) => setSpeakerForm({ ...speakerForm, organization: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1 dark:text-earth-200">Topic/Subject</label>
              <input
                type="text"
                value={speakerForm.subject || ''}
                onChange={(e) => setSpeakerForm({ ...speakerForm, subject: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900"
              />
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={submitting}
                className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50"
              >
                {submitting ? 'Registering...' : 'Register Speaker'}
              </button>
              <button
                type="button"
                onClick={() => setShowSpeakerForm(false)}
                className="px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-earth-700 dark:text-lsc-cream"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {speakerComments.length === 0 ? (
        <div className="p-8 text-center bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
          <Mic className="w-12 h-12 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No speakers registered</p>
        </div>
      ) : (
        speakerComments
          .sort((a, b) => (a.speaker_order || 0) - (b.speaker_order || 0))
          .map((comment) => (
            <div
              key={comment.id}
              className={`bg-lsc-white dark:bg-earth-800 rounded-lg border p-6 ${
                activeSpeaker === comment.id
                  ? 'border-status-success-500 ring-2 ring-status-success-500/50'
                  : 'border-lsc-border dark:border-earth-700'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-lsc-cream dark:bg-earth-700 flex items-center justify-center font-bold text-lsc-dark dark:text-lsc-cream">
                    {comment.speaker_order || '-'}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-lsc-dark dark:text-lsc-cream">
                        {comment.commenter_name}
                      </span>
                      {getCommentTypeIcon(comment.comment_type)}
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(comment.status)}`}>
                        {comment.status?.replace('_', ' ') ?? 'pending'}
                      </span>
                    </div>
                    {comment.subject && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {comment.subject}
                      </p>
                    )}
                    {comment.time_allocated_seconds && (
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        Duration: {Math.floor(comment.time_allocated_seconds / 60)}m {comment.time_allocated_seconds % 60}s
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {comment.status === 'approved' && !comment.actual_start_time && (
                    <button
                      onClick={() => onStartSpeaking(comment.id)}
                      className="flex items-center gap-1 px-3 py-1 text-sm bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300 hover:bg-status-success-200 dark:hover:bg-status-success-900/50 rounded-lg"
                    >
                      <Play className="w-4 h-4" />
                      Start
                    </button>
                  )}
                  {activeSpeaker === comment.id && (
                    <button
                      onClick={() => onStopSpeaking(comment.id)}
                      className="flex items-center gap-1 px-3 py-1 text-sm bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-300 hover:bg-status-danger-200 dark:hover:bg-status-danger-900/50 rounded-lg"
                    >
                      <Square className="w-4 h-4" />
                      Stop
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
      )}
    </div>
  )
}
