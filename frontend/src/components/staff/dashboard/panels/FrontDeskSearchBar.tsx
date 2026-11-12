/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { searchPatrons, Patron } from '@/api/staff-api/patrons'

const PINNED_PATRON_KEY = 'frontdesk:pinned-patron'
const PIN_EVENT = 'frontdesk:patron-pinned'
const SCAN_PATTERN = /^[A-Za-z0-9]{6,20}$/
const SCAN_MAX_GAP_MS = 200

export default function FrontDeskSearchBar() {
  const [query, setQuery] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const lastKeystrokeAt = useRef<number>(0)
  const navigate = useNavigate()
  const { token } = useAuth()

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [])

  const looksLikeScan = (value: string): boolean => {
    if (!SCAN_PATTERN.test(value)) return false
    const gap = Date.now() - lastKeystrokeAt.current
    return gap <= SCAN_MAX_GAP_MS
  }

  const pinPatron = (patron: Patron) => {
    try {
      sessionStorage.setItem(PINNED_PATRON_KEY, JSON.stringify(patron))
    } catch {
      // ignore quota / private-mode errors
    }
    window.dispatchEvent(new CustomEvent(PIN_EVENT, { detail: patron }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const value = query.trim()
    if (!value) return

    if (token && looksLikeScan(value)) {
      try {
        const result = await searchPatrons(token, value, 1, undefined, undefined, 5)
        const first = result.patrons[0]
        if (first) {
          pinPatron(first)
          setQuery('')
          return
        }
      } catch {
        // Scan lookup failed; fall through to the full search page below.
      }
    }

    navigate(`/staff/patrons?search=${encodeURIComponent(value)}`)
    setQuery('')
  }

  return (
    <form onSubmit={handleSubmit} className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4">
      <div className="flex items-center gap-3">
        <Search className="w-5 h-5 text-lsc-dark/40 dark:text-lsc-cream/40" aria-hidden="true" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={e => {
            lastKeystrokeAt.current = Date.now()
            setQuery(e.target.value)
          }}
          placeholder="Scan card, scan barcode, or look up patron / item / hold..."
          className="flex-1 bg-transparent text-sm text-lsc-dark dark:text-lsc-cream placeholder:text-lsc-dark/40 dark:placeholder:text-lsc-cream/40 focus:outline-none"
        />
        <kbd className="text-[10px] text-lsc-dark/40 dark:text-lsc-cream/40 border border-lsc-border dark:border-earth-700 px-1.5 py-0.5 rounded">
          {typeof navigator !== 'undefined' && navigator.platform?.includes('Mac') ? '⌘' : 'Ctrl'}K
        </kbd>
      </div>
    </form>
  )
}
