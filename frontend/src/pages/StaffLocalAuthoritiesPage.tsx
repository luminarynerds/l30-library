/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from "../components/shells/AdminShell"
import {
  BookOpen,
  Search,
  Plus,
  Pencil,
  Trash2,
  Loader2,
  X,
  AlertTriangle,
} from "lucide-react"
import toast from "react-hot-toast"
import { fetchApi } from "@/api/fetchApi"
import { t } from "@/i18n"

const AUTHORITY_TYPES = [
  "name_personal",
  "name_corporate",
  "name_meeting",
  "name_jurisdiction",
  "subject_topic",
  "subject_geographic",
  "subject_temporal",
  "subject_genre",
  "title_uniform",
  "title_series",
  "other",
] as const

type AuthorityType = (typeof AUTHORITY_TYPES)[number]

const STATUSES = ["provisional", "active", "deprecated"] as const
type AuthorityStatus = (typeof STATUSES)[number]

interface LocalAuthority {
  id: number
  authority_type: AuthorityType
  status: AuthorityStatus
  label: string
  label_normalized: string
  scope_note?: string | null
  source_notes?: string | null
  variants?: string[] | null
  use_instead_id?: number | null
  library_system_id?: number | null
  created_at: string
  updated_at: string
}

interface LocalAuthorityListResponse {
  total: number
  items: LocalAuthority[]
}

interface FormState {
  authority_type: AuthorityType
  status: AuthorityStatus
  label: string
  scope_note: string
  source_notes: string
  variants: string
}

const EMPTY_FORM: FormState = {
  authority_type: "subject_topic",
  status: "provisional",
  label: "",
  scope_note: "",
  source_notes: "",
  variants: "",
}

const STATUS_CLASSES: Record<AuthorityStatus, string> = {
  provisional: "bg-lsc-cream text-lsc-dark",
  active: "bg-status-success-700 text-white",
  deprecated: "bg-status-danger-600 text-white",
}

function humanType(t: AuthorityType): string {
  return t.replace(/_/g, " ")
}

export default function StaffLocalAuthoritiesPage(): React.ReactElement {
  const { user, token, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()

  const [items, setItems] = useState<LocalAuthority[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [query, setQuery] = useState("")
  const [typeFilter, setTypeFilter] = useState<AuthorityType | "">("")
  const [statusFilter, setStatusFilter] = useState<AuthorityStatus | "">("")
  const [page, setPage] = useState(0)
  const pageSize = 25

  const [editing, setEditing] = useState<LocalAuthority | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    if (!authLoading && (!user || !["staff", "admin", "super_admin"].includes(user.role))) {
      toast.error("Staff access required")
      navigate("/account")
    }
  }, [authLoading, user, navigate])

  const fetchItems = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const params = new URLSearchParams({
        limit: String(pageSize),
        offset: String(page * pageSize),
      })
      if (query.trim()) params.set("q", query.trim())
      if (typeFilter) params.set("authority_type", typeFilter)
      if (statusFilter) params.set("status", statusFilter)

      const data: LocalAuthorityListResponse = await fetchApi(`/local-authorities?${params}`)
      setItems(data.items)
      setTotal(data.total)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error("Could not load local authorities")
    } finally {
      setIsLoading(false)
    }
  }, [token, query, typeFilter, statusFilter, page])

  useEffect(() => {
    void fetchItems()
  }, [fetchItems])

  const openCreateForm = () => {
    setEditing(null)
    setForm(EMPTY_FORM)
    setShowForm(true)
  }

  const openEditForm = (record: LocalAuthority) => {
    setEditing(record)
    setForm({
      authority_type: record.authority_type,
      status: record.status,
      label: record.label,
      scope_note: record.scope_note ?? "",
      source_notes: record.source_notes ?? "",
      variants: (record.variants ?? []).join("\n"),
    })
    setShowForm(true)
  }

  const closeForm = () => {
    setShowForm(false)
    setEditing(null)
    setForm(EMPTY_FORM)
  }

  const submitForm = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token) return
    if (!form.label.trim()) {
      toast.error("Label is required")
      return
    }
    setIsSaving(true)
    try {
      const variantList = form.variants
        .split("\n")
        .map((v) => v.trim())
        .filter(Boolean)
      const body = {
        authority_type: form.authority_type,
        status: form.status,
        label: form.label.trim(),
        scope_note: form.scope_note.trim() || null,
        source_notes: form.source_notes.trim() || null,
        variants: variantList.length ? variantList : null,
      }
      const path = editing
        ? `/local-authorities/${editing.id}`
        : `/local-authorities`
      const method = editing ? "PATCH" : "POST"

      await fetchApi(path, {
        method,
        body: JSON.stringify(body),
      })
      toast.success(editing ? "Authority updated" : "Authority created")
      closeForm()
      void fetchItems()
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : "Save failed"
      toast.error(msg)
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    } finally {
      setIsSaving(false)
    }
  }

  const deleteRecord = async (record: LocalAuthority) => {
    if (!token) return
    if (!window.confirm(`Delete "${record.label}"? This cannot be undone.`)) return
    try {
      await fetchApi(`/local-authorities/${record.id}`, {
        method: "DELETE",
      })
      toast.success("Authority deleted")
      void fetchItems()
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : "Delete failed"
      toast.error(msg)
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(0)
    void fetchItems()
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <AdminShell title="Local Authorities">
      <div className="space-y-6">
        <div className="flex flex-wrap items-end gap-3 justify-between">
          <form onSubmit={handleSearchSubmit} className="flex flex-wrap gap-3 flex-1">
            <div className="relative flex-1 min-w-[240px]">
              <Search
                className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/50 dark:text-lsc-cream/50"
                aria-hidden
              />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search heading or scope note"
                className="w-full pl-9 pr-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
              />
            </div>
            <select
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value as AuthorityType | "")
                setPage(0)
              }}
              aria-label={t('aria.staffLocalAuthorities.filterByType', 'Filter by authority type')}
              className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            >
              <option value="">All types</option>
              {AUTHORITY_TYPES.map((authorityType) => (
                <option key={authorityType} value={authorityType}>
                  {humanType(authorityType)}
                </option>
              ))}
            </select>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value as AuthorityStatus | "")
                setPage(0)
              }}
              aria-label={t('aria.staffLocalAuthorities.filterByStatus', 'Filter by status')}
              className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
            >
              <option value="">All statuses</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium"
            >
              Search
            </button>
          </form>
          <button
            type="button"
            onClick={openCreateForm}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium"
          >
            <Plus className="w-4 h-4" /> New authority
          </button>
        </div>

        <div className="rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 overflow-hidden">
          {isLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <BookOpen className="w-12 h-12 opacity-50 text-lsc-dark/70 dark:text-lsc-cream/70" />
              <h3 className="mt-3 font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                No local authorities yet
              </h3>
              <p className="mt-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Create one to start tracking local headings.
              </p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-lsc-cream dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream">
                <tr>
                  <th className="text-left px-4 py-2 font-medium">Heading</th>
                  <th className="text-left px-4 py-2 font-medium">Type</th>
                  <th className="text-left px-4 py-2 font-medium">Status</th>
                  <th className="text-left px-4 py-2 font-medium">Updated</th>
                  <th className="text-right px-4 py-2 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                {items.map((record) => (
                  <tr key={record.id} className="hover:bg-lsc-cream/40 dark:hover:bg-earth-700/40">
                    <td className="px-4 py-2 text-lsc-dark dark:text-lsc-cream">
                      <div className="font-medium">{record.label}</div>
                      {record.scope_note && (
                        <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-1">
                          {record.scope_note}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                      {humanType(record.authority_type)}
                    </td>
                    <td className="px-4 py-2">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${STATUS_CLASSES[record.status]}`}
                      >
                        {record.status}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                      {new Date(record.updated_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => openEditForm(record)}
                          className="p-2 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700"
                          aria-label={`Edit ${record.label}`}
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() => deleteRecord(record)}
                          className="p-2 rounded-lg text-status-danger-600 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20"
                          aria-label={`Delete ${record.label}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {total > pageSize && (
          <div className="flex items-center justify-between text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            <span>
              {total} record{total === 1 ? "" : "s"} · page {page + 1} of {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="px-3 py-1.5 rounded-lg border border-lsc-border dark:border-earth-700 disabled:opacity-50 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700"
              >
                Previous
              </button>
              <button
                type="button"
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="px-3 py-1.5 rounded-lg border border-lsc-border dark:border-earth-700 disabled:opacity-50 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-2xl rounded-xl bg-lsc-white dark:bg-earth-800 shadow-lg border border-lsc-border dark:border-earth-700">
            <div className="flex items-start justify-between p-5 border-b border-lsc-border dark:border-earth-700">
              <h2 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                {editing ? "Edit local authority" : "New local authority"}
              </h2>
              <button
                type="button"
                onClick={closeForm}
                className="p-1 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700"
                aria-label="Close"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={submitForm} className="p-5 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <label className="block">
                  <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Type</span>
                  <select
                    value={form.authority_type}
                    onChange={(e) =>
                      setForm({ ...form, authority_type: e.target.value as AuthorityType })
                    }
                    className="mt-1 w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  >
                    {AUTHORITY_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {humanType(t)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block">
                  <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">Status</span>
                  <select
                    value={form.status}
                    onChange={(e) =>
                      setForm({ ...form, status: e.target.value as AuthorityStatus })
                    }
                    className="mt-1 w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  >
                    {STATUSES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <label className="block">
                <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  Authorized heading
                </span>
                <input
                  type="text"
                  required
                  value={form.label}
                  onChange={(e) => setForm({ ...form, label: e.target.value })}
                  className="mt-1 w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
              </label>

              <label className="block">
                <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  Scope note
                </span>
                <textarea
                  rows={3}
                  value={form.scope_note}
                  onChange={(e) => setForm({ ...form, scope_note: e.target.value })}
                  className="mt-1 w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
              </label>

              <label className="block">
                <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  Variant headings (one per line)
                </span>
                <textarea
                  rows={3}
                  value={form.variants}
                  onChange={(e) => setForm({ ...form, variants: e.target.value })}
                  placeholder="Alternate forms, see-from references"
                  className="mt-1 w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
              </label>

              <label className="block">
                <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                  Source notes
                </span>
                <textarea
                  rows={2}
                  value={form.source_notes}
                  onChange={(e) => setForm({ ...form, source_notes: e.target.value })}
                  placeholder="Citations supporting the authorized form (MARC 670 equivalent)"
                  className="mt-1 w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
              </label>

              {editing?.status === "deprecated" && (
                <div className="flex items-start gap-2 rounded-lg bg-lsc-cream dark:bg-earth-900 p-3 text-sm text-lsc-dark dark:text-lsc-cream">
                  <AlertTriangle className="w-4 h-4 mt-0.5 text-lsc-rose" />
                  <span>
                    This authority is deprecated. Existing AuthorityLink rows still resolve to it
                    until they are re-pointed.
                  </span>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeForm}
                  className="px-4 py-2 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium disabled:opacity-50"
                >
                  {isSaving && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
                  {editing ? "Save changes" : "Create authority"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AdminShell>
  )
}
