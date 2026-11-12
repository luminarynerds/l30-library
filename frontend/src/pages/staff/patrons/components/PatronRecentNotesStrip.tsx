/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useEffect, useMemo, useState } from "react"
import { ChevronDown, ChevronRight, Plus, X, Loader2 } from "lucide-react"
import toast from "react-hot-toast"
import {
  getPatronNotes,
  createPatronNote,
  getNoteCategoryColor,
  getNoteCategories,
  type PatronNote,
  type NoteCategory,
} from "@/api/domains/patron/patron-communication-api"
import { useTranslation } from "@/i18n"

interface PatronRecentNotesStripProps {
  token: string | null
  patronId: number
  userId: number | null | undefined
  onOpenNote: (noteId: number) => void
  onNoteCreated?: () => void
}

const STRIP_LIMIT = 3
const BODY_PREVIEW_CHARS = 80

function collapseKey(userId: number | null | undefined): string {
  return `recent-notes-collapsed:${userId ?? "anon"}`
}

function formatRelative(iso: string | null): string {
  if (!iso) return ""
  const diff = Date.now() - new Date(iso).getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)
  if (minutes < 1) return "just now"
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days < 30) return `${days}d ago`
  return `${Math.floor(days / 30)}mo ago`
}

export function PatronRecentNotesStrip({
  token,
  patronId,
  userId,
  onOpenNote,
  onNoteCreated,
}: PatronRecentNotesStripProps): React.ReactElement {
  const { t } = useTranslation()
  const [notes, setNotes] = useState<PatronNote[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [showComposer, setShowComposer] = useState(false)
  const [composerCategory, setComposerCategory] = useState<NoteCategory>("general")
  const [composerBody, setComposerBody] = useState("")
  const [isSaving, setIsSaving] = useState(false)

  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(collapseKey(userId)) === "1"
    } catch {
      return false
    }
  })

  useEffect(() => {
    try {
      localStorage.setItem(collapseKey(userId), collapsed ? "1" : "0")
    } catch {
      // localStorage unavailable -- ignore
    }
  }, [collapsed, userId])

  const refresh = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const res = await getPatronNotes(token, patronId, { limit: STRIP_LIMIT })
      setNotes(res.notes)
    } catch {
      // Silently fail -- the full Communication tab will surface errors
    } finally {
      setIsLoading(false)
    }
  }, [token, patronId])

  useEffect(() => {
    refresh()
  }, [refresh])

  const categories = useMemo(() => getNoteCategories(), [])

  const handleSave = async () => {
    if (!token) return
    const body = composerBody.trim()
    if (!body) {
      toast.error(t("staffPatrons.recentNotes.bodyRequired", "Note body cannot be empty"))
      return
    }
    setIsSaving(true)
    // Optimistic prepend with a temporary id <0 so React keys are unique.
    const optimisticId = -Date.now()
    const optimistic: PatronNote = {
      id: optimisticId,
      patron_id: patronId,
      author_id: null,
      author_name: null,
      category: composerCategory,
      content: body,
      created_at: new Date().toISOString(),
      updated_at: null,
    }
    setNotes((prev) => [optimistic, ...prev].slice(0, STRIP_LIMIT))
    setComposerBody("")
    setShowComposer(false)
    try {
      const saved = await createPatronNote(token, patronId, {
        content: body,
        category: composerCategory,
      })
      setNotes((prev) =>
        [saved, ...prev.filter((n) => n.id !== optimisticId)].slice(0, STRIP_LIMIT)
      )
      toast.success(t("staffPatrons.recentNotes.saved", "Note saved"))
      onNoteCreated?.()
    } catch (err) {
      // Roll back optimistic entry
      setNotes((prev) => prev.filter((n) => n.id !== optimisticId))
      toast.error(err instanceof Error ? err.message : t("staffPatrons.recentNotes.saveFailed", "Failed to save note"))
    } finally {
      setIsSaving(false)
    }
  }

  const headerId = `recent-notes-header-${patronId}`
  const regionId = `recent-notes-region-${patronId}`

  return (
    <div className="mt-4 border border-lsc-border dark:border-earth-700 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-lsc-cream/40 dark:bg-earth-800/60">
        <button
          id={headerId}
          onClick={() => setCollapsed((v) => !v)}
          aria-expanded={!collapsed}
          aria-controls={regionId}
          className="flex items-center gap-2 text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:opacity-80 transition-opacity"
        >
          {collapsed ? (
            <ChevronRight className="w-4 h-4" aria-hidden="true" />
          ) : (
            <ChevronDown className="w-4 h-4" aria-hidden="true" />
          )}
          {t("staffPatrons.recentNotes.heading", "Recent notes")}
          <span className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
            ({notes.length})
          </span>
        </button>
        {!collapsed && !showComposer && (
          <button
            onClick={() => setShowComposer(true)}
            className="flex items-center gap-1 text-xs px-2 py-1 rounded border border-lsc-border dark:border-earth-700 hover:bg-lsc-white dark:hover:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
          >
            <Plus className="w-3 h-3" />
            {t("staffPatrons.recentNotes.addNote", "Add note")}
          </button>
        )}
      </div>

      {!collapsed && (
        <div
          id={regionId}
          role="region"
          aria-labelledby={headerId}
          className="px-4 py-3 space-y-2 bg-lsc-white dark:bg-earth-800"
        >
          {showComposer && (
            <div className="border border-lsc-border dark:border-earth-700 rounded p-2 space-y-2 bg-lsc-cream/20 dark:bg-earth-800/40">
              <div className="flex items-center gap-2">
                <label className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70" htmlFor={`note-cat-${patronId}`}>
                  {t("staffPatrons.recentNotes.categoryLabel", "Category")}
                </label>
                <select
                  id={`note-cat-${patronId}`}
                  value={composerCategory}
                  onChange={(e) => setComposerCategory(e.target.value as NoteCategory)}
                  className="text-xs px-2 py-1 rounded border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                >
                  {categories.map((c) => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </select>
                <button
                  onClick={() => { setShowComposer(false); setComposerBody("") }}
                  className="ml-auto p-1 text-lsc-dark/60 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream"
                  aria-label={t("staffPatrons.recentNotes.cancelAria", "Cancel new note")}
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <textarea
                value={composerBody}
                onChange={(e) => setComposerBody(e.target.value)}
                placeholder={t("staffPatrons.recentNotes.placeholder", "Write a note about this patron...")}
                rows={2}
                className="w-full text-sm px-2 py-1 rounded border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              />
              <div className="flex justify-end">
                <button
                  onClick={handleSave}
                  disabled={isSaving}
                  className="flex items-center gap-1 text-xs px-3 py-1 rounded bg-lsc-rose hover:bg-lsc-rose/90 text-white disabled:opacity-50"
                >
                  {isSaving && <Loader2 className="w-3 h-3 animate-spin" />}
                  {t("staffPatrons.recentNotes.save", "Save")}
                </button>
              </div>
            </div>
          )}

          {isLoading && notes.length === 0 ? (
            <div className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 py-2">
              {t("staffPatrons.recentNotes.loading", "Loading notes...")}
            </div>
          ) : notes.length === 0 ? (
            <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 py-2 flex items-center gap-3">
              <span>{t("staffPatrons.recentNotes.empty", "No notes yet")}</span>
              {!showComposer && (
                <button
                  onClick={() => setShowComposer(true)}
                  className="underline text-lsc-rose dark:text-lsc-rose-light"
                >
                  {t("staffPatrons.recentNotes.addFirst", "Add the first")}
                </button>
              )}
            </div>
          ) : (
            <ul className="space-y-1">
              {notes.map((note) => {
                const preview = note.content.length > BODY_PREVIEW_CHARS
                  ? `${note.content.slice(0, BODY_PREVIEW_CHARS)}...`
                  : note.content
                return (
                  <li key={note.id}>
                    <button
                      onClick={() => onOpenNote(note.id)}
                      disabled={note.id < 0}
                      className="w-full text-left flex items-center gap-2 px-2 py-1 rounded hover:bg-lsc-cream/40 dark:hover:bg-earth-700 disabled:cursor-default"
                    >
                      <span
                        className={`shrink-0 w-2 h-2 rounded-full ${getNoteCategoryColor(note.category).split(" ").filter((c) => c.startsWith("bg-")).join(" ")}`}
                        aria-hidden="true"
                      />
                      <span className="text-sm text-lsc-dark dark:text-lsc-cream truncate flex-1">
                        {preview}
                      </span>
                      <span className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 shrink-0">
                        {formatRelative(note.updated_at || note.created_at)}
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
