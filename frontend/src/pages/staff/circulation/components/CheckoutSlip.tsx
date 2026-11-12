/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useEffect, useState } from "react"
import { Printer, Mail, Check, Loader2 } from "lucide-react"
import toast from "react-hot-toast"
import { fetchApi, isApiError } from "@/lib/api-client"
import type { Checkout } from "@/api/api"
import type { Patron } from "../types"
import { useTranslation, getCurrentLocale } from "@/i18n"

const STORAGE_KEY = "l30.circ.slip.lastChoice"
type LastChoice = "print" | "email" | null

interface CheckoutSlipProps {
  checkout: Checkout
  patron: Patron
  token: string | null
}

interface EmailSlipResponse {
  message: string
  sent: boolean
}

function loadLastChoice(): LastChoice {
  try {
    const v = window.localStorage.getItem(STORAGE_KEY)
    if (v === "print" || v === "email") return v
  } catch {
    /* private mode: no-op */
  }
  return null
}

function saveLastChoice(choice: LastChoice) {
  try {
    if (choice) window.localStorage.setItem(STORAGE_KEY, choice)
  } catch {
    /* private mode: no-op */
  }
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return ""
  try {
    return new Date(iso).toLocaleDateString(getCurrentLocale(), {
      month: "short",
      day: "numeric",
      year: "numeric",
    })
  } catch {
    return iso
  }
}

export function CheckoutSlip({
  checkout,
  patron,
  token,
}: CheckoutSlipProps): React.ReactElement {
  const { t } = useTranslation()
  const [lastChoice, setLastChoice] = useState<LastChoice>(() => loadLastChoice())
  const [emailing, setEmailing] = useState(false)
  const [emailSent, setEmailSent] = useState(false)

  const rememberChoice = useCallback((choice: LastChoice) => {
    saveLastChoice(choice)
    setLastChoice(choice)
  }, [])

  // Reset the "sent" pill when a new checkout slip mounts/updates.
  useEffect(() => {
    setEmailSent(false)
  }, [checkout.id])

  const handlePrint = useCallback(() => {
    rememberChoice("print")
    // Scope the print stylesheet to OUR print dialog only via a body class.
    // Other window.print() callers (Ctrl+P shortcut) get the normal page,
    // not a hide-everything stylesheet.
    document.body.classList.add("l30-printing-slip")
    const cleanup = () => document.body.classList.remove("l30-printing-slip")
    window.addEventListener("afterprint", cleanup, { once: true })
    window.print()
    // Belt-and-suspenders: if afterprint never fires (jsdom/happy-dom,
    // headless), clear the class on next tick.
    setTimeout(cleanup, 0)
  }, [rememberChoice])

  const handleEmail = useCallback(async () => {
    if (!token || !patron.email) return
    setEmailing(true)
    rememberChoice("email")
    try {
      const res = await fetchApi<EmailSlipResponse>(
        "/staff/circulation/email-slip",
        {
          method: "POST",
          token,
          body: { checkout_id: checkout.id },
        },
      )
      setEmailSent(res.sent)
      if (res.sent) {
        toast.success(t('staffCirculation.slip.emailedToast'))
      } else {
        toast(res.message || t('staffCirculation.slip.emailFailedToast'))
      }
    } catch (err: unknown) {
      const msg = isApiError(err) ? err.detail || t('staffCirculation.slip.sendFailedToast') : t('staffCirculation.slip.sendFailedToast')
      toast.error(msg)
    } finally {
      setEmailing(false)
    }
  }, [token, patron.email, checkout.id, rememberChoice, t])

  const hasEmail = Boolean(patron.email)
  const patronName = `${patron.first_name ?? ""} ${patron.last_name ?? ""}`.trim() || t('staffCirculation.slip.patronFallback')
  const itemTitle = checkout.item_title || t('staffCirculation.slip.libraryItemFallback')
  const dueLabel = formatDate(checkout.due_date)
  const coLabel = formatDate(checkout.checked_out_at)

  return (
    <div
      className="mt-3 flex flex-col gap-2 rounded-lg border border-lsc-border bg-lsc-cream/40 p-3 dark:border-earth-700 dark:bg-earth-900/40"
      data-testid="checkout-slip-toolbar"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('staffCirculation.slip.sendSlip')}
        </span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handlePrint}
            aria-label={t('staffCirculation.slip.printAria')}
            className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
              lastChoice === "print"
                ? "border-lsc-rose bg-lsc-rose/10 text-lsc-rose ring-1 ring-lsc-rose/30"
                : "border-lsc-border bg-lsc-white text-lsc-dark hover:bg-lsc-cream dark:border-earth-700 dark:bg-earth-800 dark:text-lsc-cream"
            }`}
          >
            <Printer aria-hidden="true" className="h-4 w-4" />
            {t('staffCirculation.slip.print')}
          </button>
          <button
            type="button"
            onClick={handleEmail}
            disabled={!hasEmail || emailing}
            aria-label={
              hasEmail
                ? t('staffCirculation.slip.emailAria')
                : t('staffCirculation.slip.noEmailAria')
            }
            title={hasEmail ? undefined : t('staffCirculation.slip.noEmailTitle')}
            className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
              lastChoice === "email" && hasEmail
                ? "border-lsc-rose bg-lsc-rose/10 text-lsc-rose ring-1 ring-lsc-rose/30"
                : "border-lsc-border bg-lsc-white text-lsc-dark hover:bg-lsc-cream dark:border-earth-700 dark:bg-earth-800 dark:text-lsc-cream"
            }`}
          >
            {emailing ? (
              <Loader2 aria-hidden="true" className="h-4 w-4 motion-safe:animate-spin" />
            ) : emailSent ? (
              <Check aria-hidden="true" className="h-4 w-4" />
            ) : (
              <Mail aria-hidden="true" className="h-4 w-4" />
            )}
            {t('staffCirculation.slip.email')}
          </button>
        </div>
      </div>

      {/* Always-mounted printable slip. The print stylesheet (index.css)
        hides everything except `.l30-print-slip` during print. */}
      <div className="l30-print-slip" aria-hidden="true">
        <div className="l30-print-slip__header">{t('staffCirculation.slip.header')}</div>
        <div className="l30-print-slip__meta">{coLabel}</div>
        <div className="l30-print-slip__patron">{patronName}</div>
        <div className="l30-print-slip__item">
          <div className="l30-print-slip__title">{itemTitle}</div>
          {checkout.item_author && (
            <div className="l30-print-slip__author">{t('staffCirculation.slip.byAuthor', { author: checkout.item_author })}</div>
          )}
        </div>
        <div className="l30-print-slip__due">
          {t('staffCirculation.slip.dueLabel')} <strong>{dueLabel}</strong>
        </div>
        <div className="l30-print-slip__footer">{t('staffCirculation.slip.thankYou')}</div>
      </div>
    </div>
  )
}
