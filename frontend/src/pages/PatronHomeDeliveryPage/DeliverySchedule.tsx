/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from "react"
import {
  Loader2,
  Truck,
  Package,
  Star,
  CheckCircle2,
  CalendarDays,
  ChevronDown,
  ChevronUp,
} from "lucide-react"
import {
  getMyDeliveries,
  getMyUpcomingDeliveries,
  type Delivery,
  type UpcomingDeliveriesInfo,
} from "@/api/homeDeliveryApi"
import { useTranslation} from "@/i18n"
import { clean } from "@/lib/utils"
import { statusBadge, formatStatus, formatDate } from "./types"
import { FeedbackForm } from "./FeedbackForm"
import { t } from '@/i18n'

export function DeliveriesTab() {
  const { t } = useTranslation()
  const [upcoming, setUpcoming] = useState<UpcomingDeliveriesInfo | null>(null)
  const [pastDeliveries, setPastDeliveries] = useState<Delivery[]>([])
  const [loading, setLoading] = useState(true)
  const [feedbackDeliveryId, setFeedbackDeliveryId] = useState<number | null>(null)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      try {
        const [upRes, pastRes] = await Promise.all([
          getMyUpcomingDeliveries().catch(() => null),
          getMyDeliveries({ limit: 20 }).catch(() => ({ deliveries: [], total: 0 })),
        ])
        if (cancelled) return
        setUpcoming(upRes)
        setPastDeliveries(pastRes.deliveries)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-sage" />
      </div>
    )
  }

  const upcomingList = upcoming?.upcoming || []
  const hasAny = upcomingList.length > 0 || pastDeliveries.length > 0

  if (!hasAny) {
    return (
      <div className="rounded-xl border-2 border-sage/20 dark:border-earth-700 bg-cream dark:bg-earth-800 p-8 text-center">
        <Truck className="w-12 h-12 text-sage/40 mx-auto mb-3" />
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t("patronHomeDelivery.noDeliveriesYetYourFirst")}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Upcoming */}
      {upcomingList.length > 0 && (
        <section>
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">Upcoming Deliveries</h2>
          <div className="space-y-3">
            {upcomingList.map(d => (
              <div key={d.id} className="rounded-xl border-2 border-sage/20 dark:border-earth-700 bg-cream dark:bg-earth-800 p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <CalendarDays className="w-5 h-5 text-sage" />
                    <div>
                      <p className="font-medium text-lsc-dark dark:text-lsc-cream">{formatDate(d.scheduled_date)}</p>
                      {d.time_window && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">{d.time_window}</p>}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{d.items_count} item{d.items_count !== 1 ? "s" : ""}</span>
                    <span className={statusBadge(d.status)}>{formatStatus(d.status)}</span>
                  </div>
                </div>
                {d.is_out_for_delivery && (
                  <div className="mt-2 flex items-center gap-2 text-sm text-category-700 dark:text-category-300">
                    <Truck className="w-4 h-4" />
                    <span>{t("patronHomeDelivery.outForDeliveryNow")}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Past */}
      {pastDeliveries.length > 0 && (
        <section>
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">Past Deliveries</h2>
          <div className="space-y-3">
            {pastDeliveries.map(d => (
              <div key={d.id} className="rounded-xl border-2 border-sage/20 dark:border-earth-700 bg-cream dark:bg-earth-800">
                <button
                  onClick={() => setExpandedId(expandedId === d.id ? null : d.id)}
                  className="w-full p-4 flex items-center justify-between text-left min-h-[44px]"
                  aria-expanded={expandedId === d.id}
                  aria-label={`Delivery on ${formatDate(d.scheduled_date)}, ${formatStatus(d.status)}`}
                >
                  <div className="flex items-center gap-3">
                    <Package className="w-5 h-5 text-sage shrink-0" />
                    <div>
                      <p className="font-medium text-lsc-dark dark:text-lsc-cream">{formatDate(d.scheduled_date)}</p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                        {d.items_count} item{d.items_count !== 1 ? "s" : ""}
                        {d.items_delivered > 0 && ` delivered`}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={statusBadge(d.status)}>{formatStatus(d.status)}</span>
                    {expandedId === d.id ? <ChevronUp className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60" /> : <ChevronDown className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60" />}
                  </div>
                </button>
                {expandedId === d.id && (
                  <div className="px-4 pb-4 border-t border-sage/10 dark:border-earth-600 pt-3 space-y-3">
                    {/* Timeline */}
                    <DeliveryTimeline delivery={d} />
                    {/* Items */}
                    {d.items && d.items.length > 0 && (
                      <div>
                        <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Items</p>
                        <ul className="space-y-1">
                          {d.items.map(item => (
                            <li key={item.id} className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 flex items-center gap-2">
                              <span className="w-1.5 h-1.5 rounded-full bg-sage shrink-0" />
                              {item.item_title}{item.item_author && ` by ${item.item_author}`}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {/* Feedback */}
                    {d.status === "delivered" && !d.has_feedback && feedbackDeliveryId !== d.id && (
                      <button
                        onClick={() => setFeedbackDeliveryId(d.id)}
                        className="bg-lsc-rose text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-lsc-rose/90 transition-colors min-h-[44px] flex items-center gap-2"
                        aria-label={`Leave feedback for delivery on ${formatDate(d.scheduled_date)}`}
                      >
                        <Star className="w-4 h-4" /> Leave Feedback
                      </button>
                    )}
                    {d.has_feedback && d.feedback && (
                      <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 text-status-success-600 dark:text-status-success-400" />
                        Feedback submitted ({d.feedback.overall_rating}/5 stars)
                      </div>
                    )}
                    {feedbackDeliveryId === d.id && (
                      <FeedbackForm
                        deliveryId={d.id}
                        onSubmitted={() => {
                          setFeedbackDeliveryId(null)
                          // Refresh the delivery list to show feedback submitted
                          getMyDeliveries({ limit: 20 })
                            .then(res => setPastDeliveries(res.deliveries))
                            .catch(() => {})
                        }}
                        onCancel={() => setFeedbackDeliveryId(null)}
                      />
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

function DeliveryTimeline({ delivery }: { delivery: Delivery }) {
  const steps: { label: string; date?: string; done: boolean }[] = [
    { label: "Scheduled", date: delivery.created_at, done: true },
    { label: "Items Selected", done: ["items_selected", "packed", "out_for_delivery", "delivered", "picked_up"].includes(delivery.status) },
    { label: "Packed", ...(delivery.packed_at ? { date: delivery.packed_at } : {}), done: ["packed", "out_for_delivery", "delivered", "picked_up"].includes(delivery.status) },
    { label: "Out for Delivery", ...(delivery.out_for_delivery_at ? { date: delivery.out_for_delivery_at } : {}), done: ["out_for_delivery", "delivered", "picked_up"].includes(delivery.status) },
    { label: "Delivered", ...(delivery.delivered_at ? { date: delivery.delivered_at } : {}), done: delivery.status === "delivered" || delivery.status === "picked_up" },
  ]

  if (delivery.status === "delivery_failed") {
    steps.push(clean({ label: "Failed", date: delivery.delivery_failed_at, done: true }))
  }

  return (
    <div className="flex items-center gap-1 overflow-x-auto" aria-label={t('aria.deliverySchedule.deliveryProgress')}>
      {steps.map((step, i) => (
        <div key={step.label} className="flex items-center gap-1 shrink-0">
          <div className="flex flex-col items-center">
            <div className={`w-3 h-3 rounded-full ${step.done ? "bg-sage" : "bg-earth-300 dark:bg-earth-600"}`} />
            <span className={`text-[10px] mt-1 whitespace-nowrap ${step.done ? "text-sage font-medium" : "text-lsc-dark/70 dark:text-lsc-cream/60"}`}>
              {step.label}
            </span>
          </div>
          {i < steps.length - 1 && (
            <div className={`w-6 h-0.5 mt-[-12px] ${step.done ? "bg-sage" : "bg-earth-300 dark:bg-earth-600"}`} />
          )}
        </div>
      ))}
    </div>
  )
}
