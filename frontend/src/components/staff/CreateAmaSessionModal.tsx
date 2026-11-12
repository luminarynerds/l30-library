/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Modal } from '../ui/Modal'
import { createAmaSession, updateAmaSession } from '@/api/domains/content/ama-api'

interface AmaSessionData {
  id: number
  title: string
  description?: string | null
  // Author info is nested by the API, matching AmaSession.
  author: {
    indie_author_id: number | null
    guest_author_name: string | null
    guest_author_bio: string | null
  }
  scheduled_start: string
  scheduled_end: string
}

interface Props {
  onClose: () => void
  onCreated: () => void
  editing?: AmaSessionData | null
}

type AuthorMode = 'indie' | 'guest'

function toLocalDatetime(iso: string | null): string {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toISOString().slice(0, 16)
  } catch { return '' }
}

export function CreateAmaSessionModal({ onClose, onCreated, editing }: Props) {
  const isEdit = !!editing
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [authorMode, setAuthorMode] = useState<AuthorMode>(
    editing?.author?.indie_author_id ? 'indie' : 'guest'
  )
  const [formData, setFormData] = useState({
    title: editing?.title ?? '',
    description: editing?.description ?? '',
    author_id: editing?.author?.indie_author_id?.toString() ?? '',
    guest_author_name: editing?.author?.guest_author_name ?? '',
    guest_author_bio: editing?.author?.guest_author_bio ?? '',
    scheduled_start: toLocalDatetime(editing?.scheduled_start ?? null),
    scheduled_end: toLocalDatetime(editing?.scheduled_end ?? null),
  })

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
  ) => {
    setFormData({ ...formData, [e.target.name]: e.target.value })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const payload = {
        title: formData.title,
        ...(formData.description ? { description: formData.description } : {}),
        ...(authorMode === 'indie'
          ? { author_id: parseInt(formData.author_id) }
          : {
              guest_author_name: formData.guest_author_name,
              ...(formData.guest_author_bio ? { guest_author_bio: formData.guest_author_bio } : {}),
            }),
        ...(formData.scheduled_start
          ? { scheduled_start: new Date(formData.scheduled_start).toISOString() }
          : {}),
        ...(formData.scheduled_end
          ? { scheduled_end: new Date(formData.scheduled_end).toISOString() }
          : {}),
      }

      if (isEdit) {
        await updateAmaSession(editing!.id, payload)
      } else {
        await createAmaSession(payload)
      }
      onCreated()
      onClose()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : `Failed to ${isEdit ? 'update' : 'create'} AMA session`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal isOpen={true} onClose={onClose} title={isEdit ? 'Edit AMA Session' : 'New AMA Session'} size="lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 text-sm bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-700 dark:text-status-danger-300 rounded-lg">
            {error}
          </div>
        )}

        <div>
          <label htmlFor="ama-title" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
            Title *
          </label>
          <input
            id="ama-title"
            name="title"
            type="text"
            value={formData.title}
            onChange={handleChange}
            required
            placeholder="e.g. AMA with Jane Smith"
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          />
        </div>

        <div>
          <label htmlFor="ama-description" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
            Description
          </label>
          <textarea
            id="ama-description"
            name="description"
            value={formData.description}
            onChange={handleChange}
            rows={3}
            placeholder="What this AMA is about..."
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          />
        </div>

        <fieldset>
          <legend className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">Author</legend>
          <div className="flex gap-2 mb-3">
            <button type="button" onClick={() => setAuthorMode('guest')}
              className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${authorMode === 'guest' ? 'bg-lsc-rose text-white border-lsc-rose' : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 border-lsc-border dark:border-earth-700 hover:border-lsc-rose'}`}>
              Guest Author
            </button>
            <button type="button" onClick={() => setAuthorMode('indie')}
              className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${authorMode === 'indie' ? 'bg-lsc-rose text-white border-lsc-rose' : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 border-lsc-border dark:border-earth-700 hover:border-lsc-rose'}`}>
              Indie Author (in system)
            </button>
          </div>
          {authorMode === 'guest' ? (
            <div className="space-y-3">
              <div>
                <label htmlFor="ama-guest-name" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Author Name *</label>
                <input id="ama-guest-name" name="guest_author_name" type="text" value={formData.guest_author_name} onChange={handleChange} required={authorMode === 'guest'}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" />
              </div>
              <div>
                <label htmlFor="ama-guest-bio" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Author Bio</label>
                <textarea id="ama-guest-bio" name="guest_author_bio" value={formData.guest_author_bio} onChange={handleChange} rows={2}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" />
              </div>
            </div>
          ) : (
            <div>
              <label htmlFor="ama-author-id" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Author ID *</label>
              <input id="ama-author-id" name="author_id" type="number" min="1" value={formData.author_id} onChange={handleChange} required={authorMode === 'indie'} placeholder="Indie author ID"
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" />
            </div>
          )}
        </fieldset>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="ama-start" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Start Date/Time</label>
            <input id="ama-start" name="scheduled_start" type="datetime-local" value={formData.scheduled_start} onChange={handleChange}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" />
          </div>
          <div>
            <label htmlFor="ama-end" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">End Date/Time</label>
            <input id="ama-end" name="scheduled_end" type="datetime-local" value={formData.scheduled_end} onChange={handleChange}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" />
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button type="button" onClick={onClose} disabled={loading}
            className="px-4 py-2 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-earth-50 dark:hover:bg-earth-700 transition-colors">
            Cancel
          </button>
          <button type="submit" disabled={loading}
            className="px-4 py-2 text-sm font-medium text-white bg-lsc-rose rounded-lg hover:bg-lsc-rose/90 transition-colors disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2">
            {loading ? (isEdit ? 'Saving...' : 'Creating...') : (isEdit ? 'Save Changes' : 'Create Session')}
          </button>
        </div>
      </form>
    </Modal>
  )
}
