/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { X, User, BookOpen, DollarSign, Banknote, Bookmark } from 'lucide-react'
import type { Patron } from '@/api/staff-api/patrons'

const PINNED_PATRON_KEY = 'frontdesk:pinned-patron'
const PIN_EVENT = 'frontdesk:patron-pinned'

function readPinned(): Patron | null {
  try {
    const raw = sessionStorage.getItem(PINNED_PATRON_KEY)
    return raw ? (JSON.parse(raw) as Patron) : null
  } catch {
    return null
  }
}

export default function FrontDeskPatronPin() {
  const [patron, setPatron] = useState<Patron | null>(() => readPinned())

  useEffect(() => {
    const onPinned = (e: Event) => {
      const detail = (e as CustomEvent<Patron>).detail
      setPatron(detail ?? readPinned())
    }
    window.addEventListener(PIN_EVENT, onPinned)
    return () => window.removeEventListener(PIN_EVENT, onPinned)
  }, [])

  if (!patron) return null

  const handleClear = () => {
    try {
      sessionStorage.removeItem(PINNED_PATRON_KEY)
    } catch {
      // ignore
    }
    setPatron(null)
  }

  const fullName = `${patron.first_name ?? ''} ${patron.last_name ?? ''}`.trim() || 'Unknown patron'
  const cardNumber = patron.library_card_number || patron.library_card || null
  const fines = Number(patron.fines_balance ?? 0)
  const currentCheckouts = patron.current_checkouts ?? 0
  const patronHref = `/staff/patrons/${patron.id}`

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4 border border-lsc-border dark:border-earth-700">
      <div className="flex items-start gap-3">
        {patron.photo_url ? (
          <img
            src={patron.photo_url}
            alt=""
            className="w-12 h-12 rounded-full object-cover flex-shrink-0"
          />
        ) : (
          <div className="w-12 h-12 rounded-full bg-lsc-border dark:bg-earth-700 flex items-center justify-center flex-shrink-0">
            <User className="w-6 h-6 text-lsc-dark/40 dark:text-lsc-cream/40" aria-hidden="true" />
          </div>
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream truncate">
                {fullName}
              </div>
              <div className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 truncate">
                ID #{patron.id}
                {cardNumber ? <> &middot; Card {cardNumber}</> : null}
              </div>
            </div>
            <button
              type="button"
              onClick={handleClear}
              aria-label="Clear pinned patron"
              className="text-lsc-dark/40 dark:text-lsc-cream/40 hover:text-lsc-dark dark:hover:text-lsc-cream"
            >
              <X className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
          <div className="mt-2 flex items-center gap-4 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
            <span className="inline-flex items-center gap-1">
              <BookOpen className="w-3.5 h-3.5" aria-hidden="true" />
              {currentCheckouts} out
            </span>
            <span className="inline-flex items-center gap-1">
              <DollarSign className="w-3.5 h-3.5" aria-hidden="true" />
              {fines.toFixed(2)} owed
            </span>
            {patron.current_holds !== undefined ? (
              <span className="text-lsc-dark/60 dark:text-lsc-cream/60">
                {patron.current_holds} holds
              </span>
            ) : null}
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <Link
              to={patronHref}
              className="inline-flex items-center gap-1.5 rounded-lg bg-lsc-rose/10 dark:bg-lsc-rose/20 px-3 py-1.5 text-xs font-medium text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-rose/20 dark:hover:bg-lsc-rose/30 transition-colors"
            >
              <Banknote className="w-3.5 h-3.5" aria-hidden="true" />
              Pay fees
            </Link>
            <Link
              to={patronHref}
              className="inline-flex items-center gap-1.5 rounded-lg bg-lsc-rose/10 dark:bg-lsc-rose/20 px-3 py-1.5 text-xs font-medium text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-rose/20 dark:hover:bg-lsc-rose/30 transition-colors"
            >
              <Bookmark className="w-3.5 h-3.5" aria-hidden="true" />
              Place hold
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
