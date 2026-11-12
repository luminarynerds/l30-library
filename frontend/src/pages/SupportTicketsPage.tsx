/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { Ticket, Clock } from 'lucide-react'
import { AdminShell } from '../components/shells/AdminShell'
import api from '@/lib/api-client'

interface SupportTicket {
  id: number
  ticket_number: string
  name: string
  email: string
  phone: string | null
  guide_title: string | null
  step_number: number | null
  total_steps: number | null
  issue_description: string
  contact_method: string
  status: string
  submitted_at: string | null
  created_at: string | null
}

const STATUS_COLORS: Record<string, string> = {
  open: 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-900 dark:text-status-warning-200',
  in_progress: 'bg-status-info-100 dark:bg-status-info-900/30 text-status-info-900 dark:text-status-info-200',
  resolved: 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-900 dark:text-status-success-200',
  closed: 'bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream',
}

function summarize(ticket: SupportTicket): string {
  const issue = ticket.issue_description?.trim() ?? ''
  const firstLine = issue.split('\n')[0] ?? ''
  if (firstLine.length > 120) return `${firstLine.slice(0, 117)}...`
  return firstLine || ticket.guide_title || ticket.ticket_number
}

export default function SupportTicketsPage() {
  const [tickets, setTickets] = useState<SupportTicket[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [statusFilter, setStatusFilter] = useState('')

  const fetchTickets = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ limit: '50' })
      if (statusFilter) params.set('status_filter', statusFilter)
      const data = await api.get<{ tickets: SupportTicket[]; total: number }>(
        `/support/tickets?${params}`
      )
      setTickets(data.tickets)
      setTotal(data.total)
    } catch {
      // endpoint may not have data yet
      setTickets([])
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    fetchTickets()
  }, [statusFilter])

  return (
    <AdminShell
      title="Support Tickets"
      subtitle="Tickets submitted from guided walkthroughs and patron support requests"
      icon={<Ticket className="w-6 h-6" />}
    >
      {/* Filter */}
      <div className="flex items-center gap-4 mb-6">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100 text-sm"
        >
          <option value="">All statuses</option>
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
        </select>
        <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {total} ticket{total !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Tickets list */}
      {loading ? (
        <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
          Loading tickets...
        </div>
      ) : tickets.length === 0 ? (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-12 text-center">
          <Ticket className="w-12 h-12 mx-auto mb-4 text-lsc-dark/30 dark:text-lsc-cream/30" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            No support tickets yet. Tickets are created when patrons request help from a guided walkthrough.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {tickets.map((ticket) => {
            const timestamp = ticket.submitted_at || ticket.created_at
            return (
              <div
                key={ticket.ticket_number}
                className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-5 hover:shadow-md transition"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-lsc-dark dark:text-lsc-cream truncate">
                      {summarize(ticket)}
                    </h3>
                    <div className="flex items-center gap-3 mt-2 text-sm text-lsc-dark/60 dark:text-lsc-cream/60">
                      <span>{ticket.name}</span>
                      {ticket.guide_title && <span>{ticket.guide_title}</span>}
                      <span>{ticket.contact_method}</span>
                      {timestamp && (
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {new Date(timestamp).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap ${STATUS_COLORS[ticket.status] || STATUS_COLORS.open}`}
                  >
                    {ticket.status.replace('_', ' ')}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </AdminShell>
  )
}
