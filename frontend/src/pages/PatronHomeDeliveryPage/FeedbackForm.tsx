/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import { Loader2, Send, Star } from "lucide-react"
import toast from "react-hot-toast"
import { submitDeliveryFeedback } from "@/api/homeDeliveryApi"
import { useTranslation} from "@/i18n"
import { clean } from "@/lib/utils"
import { t } from '@/i18n'

function StarRating({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <div className="flex gap-1" role="radiogroup" aria-label={t('aria.feedbackForm.rating')}>
      {[1, 2, 3, 4, 5].map(n => (
        <button
          key={n}
          type="button"
          onClick={() => onChange(n)}
          aria-label={`${n} star${n > 1 ? "s" : ""}`}
          aria-checked={value === n}
          role="radio"
          className="min-h-[44px] min-w-[44px] flex items-center justify-center"
        >
          <Star
            className={`w-6 h-6 transition-colors ${n <= value ? "fill-status-warning-400 text-status-warning-400" : "text-lsc-dark/70 dark:text-earth-600"}`}
          />
        </button>
      ))}
    </div>
  )
}

export function FeedbackForm({
  deliveryId,
  onSubmitted,
  onCancel,
}: {
  deliveryId: number
  onSubmitted: () => void
  onCancel: () => void
}) {
  const { t } = useTranslation()
  const [rating, setRating] = useState(0)
  const [comments, setComments] = useState("")
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (rating === 0) {
      toast.error(t("patronHomeDelivery.pleaseSelectARating"))
      return
    }
    setSubmitting(true)
    try {
      await submitDeliveryFeedback(deliveryId, clean({
        overall_rating: rating,
        comments: comments.trim() || undefined,
      }))
      toast.success(t("patronHomeDelivery.thankYouForYourFeedback"))
      onSubmitted()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('toast.feedbackForm.failedToSubmitFeedback'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 border border-sage/20 dark:border-earth-600 rounded-lg p-4 bg-lsc-white dark:bg-earth-900/50">
      <div>
        <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Overall Rating *</label>
        <StarRating value={rating} onChange={setRating} />
      </div>
      <div>
        <label htmlFor={`fb-comments-${deliveryId}`} className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Comments (optional)</label>
        <textarea
          id={`fb-comments-${deliveryId}`}
          value={comments}
          onChange={e => setComments(e.target.value)}
          className="w-full px-3 py-2 border border-sage/30 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream min-h-[60px]"
          placeholder={t("patronHomeDelivery.tellUsAboutYourExperience")}
        />
      </div>
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="bg-sage text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-sage/90 transition-colors disabled:opacity-50 min-h-[44px] flex items-center gap-2"
          aria-label={t('aria.feedbackForm.submitFeedback')}
        >
          {submitting ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Send className="w-4 h-4" />}
          Submit
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="border border-sage/30 dark:border-earth-600 text-lsc-dark dark:text-lsc-cream px-4 py-2 rounded-lg text-sm font-medium hover:bg-sage/10 transition-colors min-h-[44px]"
          aria-label={t('aria.feedbackForm.cancelFeedback')}
        >
          Cancel
        </button>
      </div>
    </form>
  )
}
