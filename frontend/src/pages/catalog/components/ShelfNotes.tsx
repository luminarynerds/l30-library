/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { StickyNote, Loader2, Plus, ChevronDown, EyeOff, Trash2 } from "lucide-react"
import toast from "react-hot-toast"
import { clsx } from "@/utils/helpers"
import { useAuth } from "@/contexts/AuthContext"
import { apiClient } from "@/lib/api-client"
import { Button } from "@/components/ui/Button"

type ShelfNoteCategory = "content_warning" | "recommendation" | "context" | "accessibility" | "other"

interface ShelfNoteData {
  id: number
  catalog_item_id: number
  user_id: number
  user_first_name: string
  content: string
  category: ShelfNoteCategory
  is_approved: boolean
  created_at: string
}

const STAFF_ROLES = new Set(["super_admin", "admin", "director", "staff"])

const CATEGORY_LABELS: Record<ShelfNoteCategory, string> = {
  content_warning: "Content Warning",
  recommendation: "Recommendation",
  context: "Context",
  accessibility: "Accessibility",
  other: "Other",
}
const CATEGORY_COLORS: Record<ShelfNoteCategory, string> = {
  content_warning: "bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-300",
  recommendation: "bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300",
  context: "bg-status-info-100 text-status-info-700 dark:bg-status-info-900/30 dark:text-status-info-300",
  accessibility: "bg-category-100 text-category-700 dark:bg-category-900/30 dark:text-category-300",
  other: "bg-earth-100 text-earth-700 dark:bg-earth-700 dark:text-earth-300",
}

interface ShelfNotesProps {
  itemId: number
}

export function ShelfNotes({ itemId }: ShelfNotesProps): React.ReactElement {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [content, setContent] = useState("")
  const [category, setCategory] = useState<ShelfNoteCategory>("other")

  const isStaff = !!user && STAFF_ROLES.has(user.role)

  const { data: notes, isLoading } = useQuery({
    queryKey: ["shelf-notes", itemId],
    queryFn: () => apiClient<ShelfNoteData[]>(`/catalog/items/${itemId}/shelf-notes`),
  })

  const createMutation = useMutation({
    mutationFn: (payload: { content: string; category: ShelfNoteCategory }) =>
      apiClient<ShelfNoteData>(`/catalog/items/${itemId}/shelf-notes`, {
        method: "POST",
        body: payload,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["shelf-notes", itemId] })
      setContent("")
      setCategory("other")
      setShowForm(false)
      toast.success("Note added.")
    },
    onError: () => {
      toast.error("Could not add note. Please try again.")
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (noteId: number) =>
      apiClient<void>(`/catalog/items/${itemId}/shelf-notes/${noteId}`, {
        method: "DELETE",
        skipJsonParse: true,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["shelf-notes", itemId] })
      toast.success("Note deleted.")
    },
    onError: () => {
      toast.error("Could not delete note.")
    },
  })

  const hideMutation = useMutation({
    mutationFn: (noteId: number) =>
      apiClient<ShelfNoteData>(`/catalog/items/${itemId}/shelf-notes/${noteId}/hide`, {
        method: "PATCH",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["shelf-notes", itemId] })
      toast.success("Note hidden from public view.")
    },
    onError: () => {
      toast.error("Could not hide note.")
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!content.trim()) return
    createMutation.mutate({ content: content.trim(), category })
  }

  return (
    <div className="p-6 md:p-8">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
          <StickyNote aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          Community Notes
        </h2>
        {user && !showForm && (
          <Button variant="secondary" size="sm" onClick={() => setShowForm(true)}>
            <Plus className="w-4 h-4" aria-hidden="true" />
            <span>Add a note</span>
          </Button>
        )}
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-6 p-4 bg-lsc-cream dark:bg-lsc-dark rounded-xl border border-lsc-border dark:border-earth-700">
          <div className="mb-3">
            <label htmlFor="shelf-note-category" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Category
            </label>
            <div className="relative">
              <select
                id="shelf-note-category"
                value={category}
                onChange={(e) => setCategory(e.target.value as ShelfNoteCategory)}
                className="w-full appearance-none rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream px-3 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              >
                {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
              <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/50 dark:text-lsc-cream/50 pointer-events-none" aria-hidden="true" />
            </div>
          </div>
          <div className="mb-3">
            <label htmlFor="shelf-note-content" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Note
            </label>
            <textarea
              id="shelf-note-content"
              value={content}
              onChange={(e) => setContent(e.target.value.slice(0, 280))}
              rows={3}
              maxLength={280}
              placeholder="Share something helpful about this item..."
              className="w-full rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-lsc-rose resize-none"
            />
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 text-right mt-1">
              {content.length}/280
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="primary" size="sm" type="submit" disabled={!content.trim() || createMutation.isPending}>
              {createMutation.isPending ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : "Submit"}
            </Button>
            <Button variant="tertiary" size="sm" type="button" onClick={() => { setShowForm(false); setContent(""); setCategory("other") }}>
              Cancel
            </Button>
          </div>
        </form>
      )}
      {isLoading && (
        <div className="flex items-center justify-center py-6">
          <Loader2 className="w-5 h-5 motion-safe:animate-spin text-lsc-rose" aria-label="Loading notes" />
        </div>
      )}

      {!isLoading && (!notes || notes.length === 0) && (
        <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/50">
          No community notes yet.{user ? " Be the first to add one!" : ""}
        </p>
      )}

      {notes && notes.length > 0 && (
        <ul className="space-y-3">
          {notes.map((note) => {
            const isOwn = !!user && note.user_id === user.id
            const canDelete = isOwn || isStaff
            return (
              <li key={note.id} className="p-3 bg-lsc-cream dark:bg-lsc-dark rounded-lg border border-lsc-border dark:border-earth-700">
                <div className="flex items-start justify-between gap-2 mb-1">
                  <div className="flex items-center gap-2">
                    <span className={clsx("text-xs font-medium px-2 py-0.5 rounded-full", CATEGORY_COLORS[note.category])}>
                      {CATEGORY_LABELS[note.category]}
                    </span>
                    <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      {note.user_first_name}
                    </span>
                  </div>
                  {(isStaff || canDelete) && (
                    <div className="flex items-center gap-1">
                      {isStaff && note.is_approved && (
                        <button
                          type="button"
                          onClick={() => hideMutation.mutate(note.id)}
                          disabled={hideMutation.isPending}
                          aria-label="Hide note from public view"
                          title="Hide from public view"
                          className="p-1 rounded text-lsc-dark/50 dark:text-lsc-cream/50 hover:text-status-warning-700 dark:hover:text-status-warning-300"
                        >
                          <EyeOff className="w-4 h-4" aria-hidden="true" />
                        </button>
                      )}
                      {canDelete && (
                        <button
                          type="button"
                          onClick={() => deleteMutation.mutate(note.id)}
                          disabled={deleteMutation.isPending}
                          aria-label="Delete note"
                          title="Delete note"
                          className="p-1 rounded text-lsc-dark/50 dark:text-lsc-cream/50 hover:text-status-danger-700 dark:hover:text-status-danger-300"
                        >
                          <Trash2 className="w-4 h-4" aria-hidden="true" />
                        </button>
                      )}
                    </div>
                  )}
                </div>
                <p className="text-sm text-lsc-dark dark:text-lsc-cream">{note.content}</p>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
