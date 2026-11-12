/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useCallback, useEffect } from "react"
import {
  Loader2,
  ListPlus,
  Send,
  Clock,
  CheckCircle2,
  Plus,
  X,
} from "lucide-react"
import toast from "react-hot-toast"
import {
  createItemRequest,
  getMyItemRequests,
  type HomeDeliveryItemRequest,
} from "@/api/homeDeliveryApi"
import { useTranslation} from "@/i18n"
import { clean } from "@/lib/utils"
import { REQUEST_TYPE_OPTIONS, formatStatus, formatDate } from "./types"

export function RequestsTab() {
  const { t } = useTranslation()
  const [requests, setRequests] = useState<HomeDeliveryItemRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)

  const loadRequests = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getMyItemRequests({ limit: 50 })
      setRequests(res.requests)
    } catch {
      toast.error(t("patronHomeDelivery.failedToLoadRequests"))
    } finally {
      setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => { loadRequests() }, [loadRequests])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-sage" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Item Requests</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-sage text-white px-4 py-2 rounded-lg font-medium hover:bg-sage/90 transition-colors min-h-[44px] flex items-center gap-2"
          aria-label={showForm ? "Close request form" : "New item request"}
        >
          {showForm ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
          {showForm ? "Cancel" : "New Request"}
        </button>
      </div>

      {showForm && (
        <ItemRequestForm
          onSubmitted={(req) => {
            setRequests(prev => [req, ...prev])
            setShowForm(false)
            toast.success(t('toast.itemRequests.requestSubmitted'))
          }}
          onCancel={() => setShowForm(false)}
        />
      )}

      {requests.length === 0 && !showForm ? (
        <div className="rounded-xl border-2 border-sage/20 dark:border-earth-700 bg-cream dark:bg-earth-800 p-8 text-center">
          <ListPlus className="w-12 h-12 text-sage/40 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            No item requests yet. Request specific books, authors, or let us surprise you!
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {requests.map(req => (
            <div key={req.id} className="rounded-xl border-2 border-sage/20 dark:border-earth-700 bg-cream dark:bg-earth-800 p-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                      req.request_type === "surprise_me"
                        ? "bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-300"
                        : "bg-sage/10 text-sage dark:bg-sage/20"
                    }`}>
                      {formatStatus(req.request_type)}
                    </span>
                  </div>
                  {req.description && (
                    <p className="text-sm text-lsc-dark dark:text-lsc-cream">{req.description}</p>
                  )}
                  {req.staff_notes && (
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">{req.staff_notes}</p>
                  )}
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50 mt-1">
                    Requested {formatDate(req.created_at)}
                  </p>
                </div>
                <div className="shrink-0 ml-3">
                  {req.fulfilled ? (
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-status-success-700 dark:text-status-success-400">
                      <CheckCircle2 className="w-4 h-4" /> Fulfilled
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-status-warning-700 dark:text-status-warning-400">
                      <Clock className="w-4 h-4" /> Pending
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function ItemRequestForm({
  onSubmitted,
  onCancel,
}: {
  onSubmitted: (req: HomeDeliveryItemRequest) => void
  onCancel: () => void
}) {
  const { t } = useTranslation()
  const [requestType, setRequestType] = useState<HomeDeliveryItemRequest["request_type"]>("specific_title")
  const [details, setDetails] = useState("")
  const [submitting, setSubmitting] = useState(false)

  const inputCls = "w-full px-3 py-2 border border-sage/30 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-sage/50 focus:border-sage min-h-[44px]"

  const detailsPlaceholder: Record<string, string> = {
    specific_title: 'Book title and author (e.g. "The Great Gatsby by F. Scott Fitzgerald")',
    author: 'Author name (e.g. "Toni Morrison")',
    subject: 'Subject or topic (e.g. "World War II history")',
    genre: 'Genre description (e.g. "Cozy mystery with cats")',
    surprise_me: "Any preferences or guidelines for the surprise (optional)",
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (requestType !== "surprise_me" && !details.trim()) {
      toast.error(t("patronHomeDelivery.pleaseProvideDetailsForYour"))
      return
    }
    setSubmitting(true)
    try {
      const req = await createItemRequest(clean({
        request_type: requestType,
        description: details.trim() || undefined,
      }))
      onSubmitted(req)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('toast.itemRequests.failedToSubmitRequest'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-xl border-2 border-sage/20 dark:border-earth-700 bg-cream dark:bg-earth-800 p-6 space-y-4">
      <h3 className="font-serif text-base font-semibold text-lsc-dark dark:text-lsc-cream">New Item Request</h3>
      <div>
        <label htmlFor="req-type" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Request Type</label>
        <select id="req-type" value={requestType} onChange={e => setRequestType(e.target.value as HomeDeliveryItemRequest["request_type"])} className={inputCls}>
          {REQUEST_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>
      <div>
        <label htmlFor="req-details" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
          Details {requestType !== "surprise_me" && "*"}
        </label>
        <textarea
          id="req-details"
          value={details}
          onChange={e => setDetails(e.target.value)}
          className={`${inputCls} min-h-[60px]`}
          placeholder={detailsPlaceholder[requestType]}
          required={requestType !== "surprise_me"}
        />
      </div>
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="bg-sage text-white px-4 py-2 rounded-lg font-medium hover:bg-sage/90 transition-colors disabled:opacity-50 min-h-[44px] flex items-center gap-2"
          aria-label={t('aria.itemRequests.submitItemRequest')}
        >
          {submitting ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Send className="w-4 h-4" />}
          Submit Request
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="border border-sage/30 dark:border-earth-600 text-lsc-dark dark:text-lsc-cream px-4 py-2 rounded-lg font-medium hover:bg-sage/10 transition-colors min-h-[44px]"
          aria-label={t('aria.itemRequests.cancelItemRequest')}
        >
          Cancel
        </button>
      </div>
    </form>
  )
}
