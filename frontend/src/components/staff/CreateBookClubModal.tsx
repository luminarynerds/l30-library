/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import { Modal } from "../ui/Modal"
import { fetchApi } from "@/lib/api-client"
import { getAccessToken } from "@/utils/tokenStore"
import { t } from "@/i18n"

interface BookClubData {
  id: number
  name: string
  description: string | null
  max_members: number | null
  meeting_frequency: string | null
  is_public: boolean
}

interface Props {
  onClose: () => void
  onCreated: () => void
  editing?: BookClubData | null
}

export function CreateBookClubModal({ onClose, onCreated, editing }: Props) {
  const isEdit = !!editing
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    name: editing?.name ?? "",
    description: editing?.description ?? "",
    max_members: editing?.max_members?.toString() ?? "",
    meeting_frequency: editing?.meeting_frequency ?? "",
    is_public: editing?.is_public ?? true,
  })

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
  ) => {
    const { name, value, type } = e.target
    const checkInput = e.target as HTMLInputElement
    setFormData({
      ...formData,
      [name]: type === "checkbox" ? checkInput.checked : value,
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const token = getAccessToken()
      const payload = {
        name: formData.name,
        description: formData.description || undefined,
        max_members: formData.max_members ? parseInt(formData.max_members) : undefined,
        meeting_frequency: formData.meeting_frequency || undefined,
        is_public: formData.is_public,
      }

      if (isEdit) {
        await fetchApi(`/book-clubs/${editing!.id}`, {
          method: "PATCH",
          body: payload,
          ...(token ? { token } : {}),
        })
      } else {
        await fetchApi("/book-clubs", {
          method: "POST",
          body: payload,
          ...(token ? { token } : {}),
        })
      }
      onCreated()
      onClose()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : `Failed to ${isEdit ? "update" : "create"} book club`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal isOpen={true} onClose={onClose} title={isEdit ? "Edit Book Club" : "New Book Club"} size="lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 text-sm bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-700 dark:text-status-danger-300 rounded-lg">
            {error}
          </div>
        )}

        <div>
          <label htmlFor="bc-name" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Club Name *</label>
          <input id="bc-name" name="name" type="text" value={formData.name} onChange={handleChange} required maxLength={255} placeholder="e.g. Mystery Lovers Monthly"
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" />
        </div>

        <div>
          <label htmlFor="bc-description" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Description</label>
          <textarea id="bc-description" name="description" value={formData.description} onChange={handleChange} rows={3} maxLength={1000} placeholder="What this book club is about..."
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="bc-max-members" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Max Members</label>
            <input id="bc-max-members" name="max_members" type="number" min="1" value={formData.max_members} onChange={handleChange} placeholder="Unlimited"
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose" />
            {isEdit &&
              editing?.max_members != null &&
              formData.max_members !== "" &&
              Number.isFinite(parseInt(formData.max_members)) &&
              parseInt(formData.max_members) > editing.max_members && (
                <p className="mt-1.5 text-xs text-status-warning-700 dark:text-status-warning-300">
                  {t("staffBookClubs.editAdvisory")}
                </p>
              )}
          </div>
          <div>
            <label htmlFor="bc-frequency" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Meeting Frequency</label>
            <select id="bc-frequency" name="meeting_frequency" value={formData.meeting_frequency} onChange={handleChange}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose">
              <option value="">Not set</option>
              <option value="Weekly">Weekly</option>
              <option value="Biweekly">Biweekly</option>
              <option value="Monthly">Monthly</option>
              <option value="Quarterly">Quarterly</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <input id="bc-public" name="is_public" type="checkbox" checked={formData.is_public} onChange={handleChange}
            className="rounded border-lsc-border dark:border-earth-600 text-lsc-rose focus:ring-lsc-rose" />
          <label htmlFor="bc-public" className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Public (visible to all patrons)</label>
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button type="button" onClick={onClose} disabled={loading}
            className="px-4 py-2 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-earth-50 dark:hover:bg-earth-700 transition-colors">
            Cancel
          </button>
          <button type="submit" disabled={loading}
            className="px-4 py-2 text-sm font-medium text-white bg-lsc-rose rounded-lg hover:bg-lsc-rose/90 transition-colors disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2">
            {loading ? (isEdit ? "Saving..." : "Creating...") : (isEdit ? "Save Changes" : "Create Club")}
          </button>
        </div>
      </form>
    </Modal>
  )
}
