/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Staff Support Triage
 *
 * Three-tab queue (Unassigned / In progress / Closed) for support tickets
 * created via /contact. Mirrors the pattern of RepairQueuePage and the
 * existing SupportTicketsPage but adds claim/release/respond + SLA badge.
 *
 * Mounted at /staff/support/triage. Staff can view, claim, release,
 * respond, and mark resolved. Admin+ can close and reassign.
 */
import { useMemo, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  AlertTriangle,
  Clock,
  Loader2,
  MessageSquare,
  Search,
  Send,
  User as UserIcon,
  X,
} from "lucide-react"
import toast from "react-hot-toast"
import { AdminShell } from "../../components/shells/AdminShell"
import { useAuth } from "../../contexts/AuthContext"
import {
  listTriageTickets,
  patchTriageTicket,
  postTriageResponse,
  listTriageEvents,
  SUPPORT_CATEGORIES,
  type TriageTicket,
  type TriageEvent,
  type TicketStatus,
} from "../../api/support-api"

type Tab = "unassigned" | "in_progress" | "closed"

const TABS: Array<{ value: Tab; label: string }> = [
  { value: "unassigned", label: "Unassigned" },
  { value: "in_progress", label: "In progress" },
  { value: "closed", label: "Closed" },
]

const CATEGORY_LABELS: Record<string, string> = Object.fromEntries(
  SUPPORT_CATEGORIES.map((c) => [c.value, c.label])
)

function brief(text: string, n: number = 80): string {
  if (!text) return ""
  const first = text.split("\n")[0] ?? ""
  if (first.length <= n) return first
  return `${first.slice(0, n - 1)}…`
}

function formatTimestamp(s: string | null | undefined): string {
  if (!s) return ""
  return new Date(s).toLocaleString()
}

export default function StaffSupportTriagePage(): React.ReactElement {
  const { user } = useAuth()
  const isAdmin =
    !!user && ["admin", "super_admin", "director"].includes(user.role || "")

  const [tab, setTab] = useState<Tab>("unassigned")
  const [category, setCategory] = useState<string>("")
  const [search, setSearch] = useState("")
  const [searchInput, setSearchInput] = useState("")
  const [submittedFrom, setSubmittedFrom] = useState("")
  const [submittedTo, setSubmittedTo] = useState("")
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const queryClient = useQueryClient()

  const filters = useMemo(
    () => ({
      status_filter: tab,
      category: category || undefined,
      search: search || undefined,
      submitted_from: submittedFrom || undefined,
      submitted_to: submittedTo || undefined,
      limit: 50,
    }),
    [tab, category, search, submittedFrom, submittedTo]
  )

  const listQuery = useQuery({
    queryKey: ["support-triage", filters],
    queryFn: () => listTriageTickets(filters),
  })

  const tickets = listQuery.data?.tickets ?? []
  const total = listQuery.data?.total ?? 0

  // Refresh helpers ---------------------------------------------------------
  const refreshList = () =>
    queryClient.invalidateQueries({ queryKey: ["support-triage"] })

  const claimMutation = useMutation({
    mutationFn: ({ id, assignToSelf }: { id: number; assignToSelf: boolean }) =>
      patchTriageTicket(id, {
        assigned_to_id: assignToSelf ? (user?.id ?? -1) : -1,
        ...(assignToSelf ? { status: "in_progress" as TicketStatus } : {}),
      }),
    onSuccess: (data) => {
      toast.success(
        data.assigned_to_id === null ? "Released" : "Claimed"
      )
      refreshList()
    },
    onError: (err: unknown) => {
      toast.error(
        err instanceof Error ? err.message : "Could not update ticket"
      )
    },
  })

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: TicketStatus }) =>
      patchTriageTicket(id, { status }),
    onSuccess: () => {
      toast.success("Status updated")
      refreshList()
    },
    onError: (err: unknown) => {
      toast.error(
        err instanceof Error ? err.message : "Could not update status"
      )
    },
  })

  const onSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setSearch(searchInput.trim())
  }

  return (
    <AdminShell
      title="Support triage"
      subtitle="Patron submissions from /contact and guided walkthroughs"
      icon={<MessageSquare className="w-6 h-6" />}
    >
      {/* Tabs */}
      <div
        role="tablist"
        aria-label="Ticket status tabs"
        className="flex gap-2 border-b border-lsc-border dark:border-earth-700 mb-4"
      >
        {TABS.map((t) => (
          <button
            key={t.value}
            role="tab"
            aria-selected={tab === t.value}
            onClick={() => setTab(t.value)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition ${
              tab === t.value
                ? "border-lsc-rose text-lsc-rose"
                : "border-transparent text-lsc-dark/60 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-end gap-3 mb-4">
        <div className="flex flex-col">
          <label
            htmlFor="triage-category"
            className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mb-1"
          >
            Category
          </label>
          <select
            id="triage-category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100 text-sm"
          >
            <option value="">All categories</option>
            {SUPPORT_CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col">
          <label
            htmlFor="triage-from"
            className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mb-1"
          >
            From
          </label>
          <input
            id="triage-from"
            type="date"
            value={submittedFrom}
            onChange={(e) => setSubmittedFrom(e.target.value)}
            className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100 text-sm"
          />
        </div>

        <div className="flex flex-col">
          <label
            htmlFor="triage-to"
            className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mb-1"
          >
            To
          </label>
          <input
            id="triage-to"
            type="date"
            value={submittedTo}
            onChange={(e) => setSubmittedTo(e.target.value)}
            className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100 text-sm"
          />
        </div>

        <form onSubmit={onSearch} className="flex items-end gap-2">
          <div className="flex flex-col">
            <label
              htmlFor="triage-search"
              className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mb-1"
            >
              Search
            </label>
            <div className="relative">
              <input
                id="triage-search"
                type="search"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Name, email, message, or ticket #"
                className="pl-9 pr-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100 text-sm w-72"
              />
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-lsc-dark/40 dark:text-lsc-cream/40" />
            </div>
          </div>
          <button
            type="submit"
            className="px-3 py-2 bg-lsc-rose text-white rounded-lg text-sm font-medium hover:bg-lsc-rose/90"
          >
            Apply
          </button>
        </form>

        <div className="ml-auto text-sm text-lsc-dark/60 dark:text-lsc-cream/60">
          {total} ticket{total === 1 ? "" : "s"}
        </div>
      </div>

      {/* Body */}
      {listQuery.isLoading ? (
        <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
          <Loader2 className="w-6 h-6 mx-auto animate-spin" />
          <p className="mt-2">Loading tickets...</p>
        </div>
      ) : listQuery.isError ? (
        <div className="bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-900 dark:text-status-danger-200 rounded-xl p-4">
          Could not load tickets. Check your connection and try again.
        </div>
      ) : tickets.length === 0 ? (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-12 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
          No tickets match these filters.
        </div>
      ) : (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-earth-50 dark:bg-earth-900 text-left">
              <tr>
                <th className="px-4 py-2 font-medium">Ticket</th>
                <th className="px-4 py-2 font-medium">Category</th>
                <th className="px-4 py-2 font-medium">Patron</th>
                <th className="px-4 py-2 font-medium">Submitted</th>
                <th className="px-4 py-2 font-medium">Age</th>
                <th className="px-4 py-2 font-medium">Brief</th>
                <th className="px-4 py-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {tickets.map((t) => (
                <tr
                  key={t.id}
                  className="border-t border-earth-100 dark:border-earth-700 hover:bg-earth-50 dark:hover:bg-earth-900/50 cursor-pointer"
                  onClick={() => setSelectedId(t.id)}
                >
                  <td className="px-4 py-3 font-mono text-xs">
                    <button
                      type="button"
                      className="text-left underline-offset-2 hover:underline focus-visible:ring-2"
                      onClick={() => setSelectedId(t.id)}
                    >
                      {t.ticket_number}
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    {t.category ? CATEGORY_LABELS[t.category] || t.category : "—"}
                  </td>
                  <td className="px-4 py-3">
                    {t.name?.trim() ? t.name : "anonymous"}
                  </td>
                  <td className="px-4 py-3">
                    {formatTimestamp(t.submitted_at)}
                  </td>
                  <td className="px-4 py-3">
                    <AgeBadge ticket={t} />
                  </td>
                  <td className="px-4 py-3 max-w-md">{brief(t.issue_description)}</td>
                  <td
                    className="px-4 py-3"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="flex gap-2">
                      {t.assigned_to_id === null ? (
                        <button
                          type="button"
                          onClick={() =>
                            claimMutation.mutate({ id: t.id, assignToSelf: true })
                          }
                          className="px-2 py-1 text-xs rounded bg-lsc-rose text-white hover:bg-lsc-rose/90"
                        >
                          Claim
                        </button>
                      ) : t.assigned_to_id === user?.id ? (
                        <button
                          type="button"
                          onClick={() =>
                            claimMutation.mutate({
                              id: t.id,
                              assignToSelf: false,
                            })
                          }
                          className="px-2 py-1 text-xs rounded bg-earth-200 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-earth-300"
                        >
                          Release
                        </button>
                      ) : (
                        <span className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
                          #{t.assigned_to_id}
                        </span>
                      )}
                      {isAdmin && t.status !== "closed" && (
                        <button
                          type="button"
                          onClick={() =>
                            statusMutation.mutate({ id: t.id, status: "closed" })
                          }
                          className="px-2 py-1 text-xs rounded border border-lsc-border dark:border-earth-700"
                        >
                          Close
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedId !== null && (
        <TicketDrawer
          ticketId={selectedId}
          isAdmin={isAdmin}
          onClose={() => {
            setSelectedId(null)
            refreshList()
          }}
        />
      )}
    </AdminShell>
  )
}

function AgeBadge({ ticket }: { ticket: TriageTicket }): React.ReactElement {
  const age = ticket.age_business_days ?? 0
  const sla = ticket.sla_business_days ?? 2
  const breached = ticket.sla_breached
  const tone = breached
    ? "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-900 dark:text-status-danger-200"
    : "bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${tone}`}
      title={`SLA ${sla} business day${sla === 1 ? "" : "s"}`}
    >
      {breached ? (
        <AlertTriangle className="w-3 h-3" aria-hidden="true" />
      ) : (
        <Clock className="w-3 h-3" aria-hidden="true" />
      )}
      {age} bd
    </span>
  )
}

// ============================================================
// Detail drawer
// ============================================================

function TicketDrawer({
  ticketId,
  isAdmin,
  onClose,
}: {
  ticketId: number
  isAdmin: boolean
  onClose: () => void
}): React.ReactElement {
  const queryClient = useQueryClient()
  const ticketQuery = useQuery({
    queryKey: ["support-triage", "ticket", ticketId],
    queryFn: () =>
      listTriageTickets({ limit: 200 }).then((r) =>
        r.tickets.find((t) => t.id === ticketId) || null
      ),
  })
  const eventsQuery = useQuery({
    queryKey: ["support-triage", "events", ticketId],
    queryFn: () => listTriageEvents(ticketId),
  })

  const [response, setResponse] = useState("")
  const [setStatus, setSetStatus] = useState<"" | "in_progress" | "resolved" | "closed">(
    ""
  )
  const [notes, setNotes] = useState("")

  const ticket = ticketQuery.data

  const responseMutation = useMutation({
    mutationFn: () =>
      postTriageResponse(
        ticketId,
        response.trim(),
        setStatus === "" ? undefined : (setStatus as "in_progress" | "resolved" | "closed")
      ),
    onSuccess: () => {
      toast.success("Response logged")
      setResponse("")
      setSetStatus("")
      queryClient.invalidateQueries({ queryKey: ["support-triage"] })
    },
    onError: (err: unknown) => {
      toast.error(err instanceof Error ? err.message : "Failed to log response")
    },
  })

  const notesMutation = useMutation({
    mutationFn: () => patchTriageTicket(ticketId, { internal_notes: notes }),
    onSuccess: () => {
      toast.success("Notes saved")
      queryClient.invalidateQueries({ queryKey: ["support-triage"] })
    },
  })

  const statusMutation = useMutation({
    mutationFn: (status: TicketStatus) =>
      patchTriageTicket(ticketId, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["support-triage"] })
    },
  })

  // Initialize notes from loaded ticket once
  if (ticket && notes === "" && ticket.internal_notes) {
    // Lazy single-shot init; using effect would cause a flicker.
    // The user can clear back to empty intentionally; we don't override later.
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Ticket detail"
      className="fixed inset-0 z-40 flex"
    >
      <div
        className="flex-1 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <aside className="w-full max-w-2xl bg-lsc-white dark:bg-earth-800 shadow-lg overflow-y-auto">
        <header className="sticky top-0 bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700 px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">
              {ticket?.ticket_number ?? "Ticket"}
            </h2>
            {ticket && (
              <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60">
                {ticket.status.replace("_", " ")}
                {" • "}
                {ticket.category
                  ? CATEGORY_LABELS[ticket.category] || ticket.category
                  : "uncategorized"}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close ticket detail"
            className="p-2 rounded hover:bg-earth-100 dark:hover:bg-earth-700"
          >
            <X className="w-5 h-5" />
          </button>
        </header>

        <div className="p-6 space-y-6">
          {ticketQuery.isLoading || !ticket ? (
            <div className="py-8 text-center">
              <Loader2 className="w-6 h-6 mx-auto animate-spin" />
            </div>
          ) : (
            <>
              <section>
                <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                  <UserIcon className="w-4 h-4" aria-hidden="true" />
                  Patron
                </h3>
                <dl className="text-sm grid grid-cols-2 gap-2">
                  <dt className="text-lsc-dark/60 dark:text-lsc-cream/60">Name</dt>
                  <dd>{ticket.name?.trim() || "anonymous"}</dd>
                  <dt className="text-lsc-dark/60 dark:text-lsc-cream/60">Email</dt>
                  <dd>
                    <a
                      href={`mailto:${ticket.email}`}
                      className="underline"
                    >
                      {ticket.email}
                    </a>
                  </dd>
                  {ticket.phone && (
                    <>
                      <dt className="text-lsc-dark/60 dark:text-lsc-cream/60">Phone</dt>
                      <dd>
                        <a href={`tel:${ticket.phone}`} className="underline">
                          {ticket.phone}
                        </a>
                      </dd>
                    </>
                  )}
                  <dt className="text-lsc-dark/60 dark:text-lsc-cream/60">Contact preference</dt>
                  <dd>{ticket.contact_method}</dd>
                  <dt className="text-lsc-dark/60 dark:text-lsc-cream/60">Submitted</dt>
                  <dd>{formatTimestamp(ticket.submitted_at)}</dd>
                  <dt className="text-lsc-dark/60 dark:text-lsc-cream/60">Age</dt>
                  <dd>
                    {ticket.age_business_days} business day
                    {ticket.age_business_days === 1 ? "" : "s"}
                    {" • SLA "}
                    {ticket.sla_business_days} bd
                  </dd>
                </dl>
              </section>

              <section>
                <h3 className="text-sm font-semibold mb-2">Message</h3>
                <pre className="whitespace-pre-wrap font-sans text-sm bg-earth-50 dark:bg-earth-900 rounded p-3">
                  {ticket.issue_description}
                </pre>
              </section>

              <section>
                <h3 className="text-sm font-semibold mb-2">Internal notes</h3>
                <textarea
                  value={notes || ticket.internal_notes || ""}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={4}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded dark:bg-earth-700 text-sm"
                  placeholder="Staff-only notes (not sent to patron)"
                />
                <div className="mt-2 flex justify-end">
                  <button
                    type="button"
                    onClick={() => notesMutation.mutate()}
                    disabled={notesMutation.isPending}
                    className="px-3 py-1.5 text-sm rounded bg-earth-200 dark:bg-earth-700"
                  >
                    Save notes
                  </button>
                </div>
              </section>

              <section>
                <h3 className="text-sm font-semibold mb-2">Respond to patron</h3>
                <textarea
                  value={response}
                  onChange={(e) => setResponse(e.target.value)}
                  rows={4}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded dark:bg-earth-700 text-sm"
                  placeholder="Reply text. Will be logged in the ticket history."
                />
                <div className="mt-2 flex items-center justify-between gap-2">
                  <select
                    value={setStatus}
                    onChange={(e) =>
                      setSetStatus(e.target.value as typeof setStatus)
                    }
                    className="px-2 py-1.5 text-sm border border-lsc-border dark:border-earth-700 rounded dark:bg-earth-700"
                  >
                    <option value="">Leave status</option>
                    <option value="in_progress">Mark in progress</option>
                    <option value="resolved">Mark resolved</option>
                    {isAdmin && <option value="closed">Close ticket</option>}
                  </select>
                  <button
                    type="button"
                    onClick={() => responseMutation.mutate()}
                    disabled={!response.trim() || responseMutation.isPending}
                    className="px-3 py-1.5 text-sm rounded bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50 inline-flex items-center gap-1"
                  >
                    <Send className="w-4 h-4" aria-hidden="true" />
                    Log response
                  </button>
                </div>
                <p className="mt-2 text-xs text-lsc-dark/50 dark:text-lsc-cream/50">
                  TODO: outbound email will deliver this once the contact-page
                  wiring lands. The response is recorded in the audit log either
                  way.
                </p>
              </section>

              <section>
                <h3 className="text-sm font-semibold mb-2">Quick actions</h3>
                <div className="flex flex-wrap gap-2">
                  {ticket.status !== "in_progress" && (
                    <button
                      type="button"
                      onClick={() => statusMutation.mutate("in_progress")}
                      className="px-3 py-1.5 text-sm rounded border border-lsc-border dark:border-earth-700"
                    >
                      Mark in progress
                    </button>
                  )}
                  {ticket.status !== "resolved" && (
                    <button
                      type="button"
                      onClick={() => statusMutation.mutate("resolved")}
                      className="px-3 py-1.5 text-sm rounded border border-lsc-border dark:border-earth-700"
                    >
                      Mark resolved
                    </button>
                  )}
                  {isAdmin && ticket.status !== "closed" && (
                    <button
                      type="button"
                      onClick={() => statusMutation.mutate("closed")}
                      className="px-3 py-1.5 text-sm rounded border border-lsc-border dark:border-earth-700"
                    >
                      Close
                    </button>
                  )}
                </div>
              </section>

              <section>
                <h3 className="text-sm font-semibold mb-2">History</h3>
                {eventsQuery.isLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <ol className="space-y-2 text-sm">
                    {(eventsQuery.data ?? []).map((e: TriageEvent) => (
                      <li
                        key={e.id}
                        className="border-l-2 border-earth-200 dark:border-earth-700 pl-3"
                      >
                        <div className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
                          {formatTimestamp(e.created_at)}{" "}
                          {e.actor_identifier ? `· ${e.actor_identifier}` : ""}
                        </div>
                        <div>
                          <span className="font-medium">
                            {e.event_type.replace(/_/g, " ")}
                          </span>
                          {e.from_value || e.to_value
                            ? `: ${e.from_value ?? "—"} → ${e.to_value ?? "—"}`
                            : ""}
                        </div>
                        {e.note && (
                          <pre className="mt-1 whitespace-pre-wrap font-sans text-xs bg-earth-50 dark:bg-earth-900 rounded p-2">
                            {e.note}
                          </pre>
                        )}
                      </li>
                    ))}
                  </ol>
                )}
              </section>
            </>
          )}
        </div>
      </aside>
    </div>
  )
}
