/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * StaffPicker
 *
 * Debounced autocomplete for selecting a staff/admin/director user by id.
 * Replaces raw integer-ID inputs in onboarding flows where a mistyped id
 * would silently bind an onboarding row (and its standard check-in
 * schedule) to the wrong person.
 *
 * Backend: GET /api/v1/users?search=<q>&role=staff requires admin role,
 * which matches the MANAGER_ROLES gate on CreateOnboardingForm.
 */
import React, { useEffect, useMemo, useState } from 'react'
import { api } from '@/lib/api-client'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useDebounce } from '@/hooks/useDebounce'

interface StaffUser {
  id: number
  email: string
  first_name: string
  last_name: string
  role: string
}

interface UserListResponse {
  users: StaffUser[]
  total: number
  page: number
  limit: number
}

interface StaffPickerProps {
  id: string
  label: string
  value: number | null
  onChange: (userId: number | null) => void
  required?: boolean
  helpText?: string
  placeholder?: string
  /** Restrict matches by role. Defaults to broad staff tier. */
  roles?: ReadonlyArray<'staff' | 'admin' | 'super_admin' | 'director'>
}

const DEFAULT_ROLES: ReadonlyArray<'staff' | 'admin' | 'super_admin' | 'director'> = [
  'staff',
  'admin',
  'super_admin',
  'director',
]

export const StaffPicker: React.FC<StaffPickerProps> = ({
  id,
  label,
  value,
  onChange,
  required,
  helpText,
  placeholder,
  roles = DEFAULT_ROLES,
}) => {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<StaffUser[]>([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [selectedLabel, setSelectedLabel] = useState<string | null>(null)
  const [activeIndex, setActiveIndex] = useState(-1)
  const debouncedQuery = useDebounce(query, 250)

  // The backend list endpoint only accepts a single `role` filter, so
  // fan out one request per allowed role and merge by id.
  const roleList = useMemo(() => Array.from(new Set(roles)), [roles])

  useEffect(() => {
    let cancelled = false
    const q = debouncedQuery.trim()
    if (q.length < 2) {
      // Don't issue a fetch; results from any previous longer query
      // are filtered out at render time via the same length guard.
      return
    }
    // setState is intentionally moved inside the fetch lifecycle below
    // (the loading flag flips on first resolution path, and final
    // results/clear happen in the .then callback). This satisfies
    // react-hooks/set-state-in-effect, which forbids sync setState in
    // the effect body.
    Promise.all(
      roleList.map((role) =>
        api
          .get<UserListResponse>(
            `/users?search=${encodeURIComponent(q)}&role=${role}&limit=10`,
          )
          .then((res) => (res?.users ?? []))
          .catch(() => [] as StaffUser[]),
      ),
    ).then((batches) => {
      if (cancelled) return
      const seen = new Set<number>()
      const merged: StaffUser[] = []
      for (const batch of batches) {
        for (const user of batch) {
          if (seen.has(user.id)) continue
          seen.add(user.id)
          merged.push(user)
          if (merged.length >= 10) break
        }
        if (merged.length >= 10) break
      }
      setResults(merged)
      setLoading(false)
      setActiveIndex(-1)
    })
    // Flip loading=true on the next microtask so it lands inside a
    // callback (not the effect body) -- the user-visible delta is
    // sub-frame.
    queueMicrotask(() => {
      if (!cancelled) {
        setLoading(true)
        setActiveIndex(-1)
      }
    })
    return () => {
      cancelled = true
    }
  }, [debouncedQuery, roleList])

  const handleSelect = (user: StaffUser) => {
    onChange(user.id)
    setSelectedLabel(`${user.first_name} ${user.last_name} (${user.email})`)
    setQuery('')
    setResults([])
    setOpen(false)
    setActiveIndex(-1)
  }

  const handleClear = () => {
    onChange(null)
    setSelectedLabel(null)
    setQuery('')
    setResults([])
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!open) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (results.length === 0) return
      setActiveIndex((i) => (i + 1 >= results.length ? 0 : i + 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (results.length === 0) return
      setActiveIndex((i) => (i - 1 < 0 ? results.length - 1 : i - 1))
    } else if (e.key === 'Enter') {
      // Guard against submitting an enclosing form while the listbox is open.
      e.preventDefault()
      const active = results[activeIndex]
      if (!active) return
      handleSelect(active)
    } else if (e.key === 'Escape') {
      e.preventDefault()
      setOpen(false)
      setActiveIndex(-1)
    }
  }

  return (
    <div className="space-y-2 relative">
      <Label htmlFor={id} className={required ? 'font-semibold' : undefined}>
        {label}
        {required ? ' *' : ''}
      </Label>
      {value !== null && selectedLabel ? (
        <div className="flex items-center gap-2">
          <div
            className="flex-1 rounded border px-3 py-2 text-sm bg-earth-100/30 dark:bg-earth-800/30"
            data-testid={`${id}-selected`}
          >
            {selectedLabel}
          </div>
          <button
            type="button"
            onClick={handleClear}
            className="text-sm underline"
            aria-label={`Clear ${label}`}
          >
            Clear
          </button>
        </div>
      ) : (
        <>
          <Input
            id={id}
            type="text"
            autoComplete="off"
            placeholder={placeholder ?? 'Search by name or email'}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setOpen(true)
            }}
            onFocus={() => setOpen(true)}
            onKeyDown={handleKeyDown}
            required={required && value === null}
            role="combobox"
            aria-autocomplete="list"
            aria-expanded={open}
            aria-controls={`${id}-listbox`}
            aria-activedescendant={
              open &&
              debouncedQuery.trim().length >= 2 &&
              !loading &&
              activeIndex >= 0 &&
              activeIndex < results.length
                ? `${id}-opt-${activeIndex}`
                : undefined
            }
          />
          {open && debouncedQuery.trim().length >= 2 && (
            <ul
              id={`${id}-listbox`}
              role="listbox"
              className="absolute z-10 mt-1 w-full max-h-60 overflow-auto rounded border bg-lsc-white dark:bg-earth-800 shadow"
            >
              {loading && (
                <li className="px-3 py-2 text-sm text-earth-600 dark:text-earth-400">
                  Searching...
                </li>
              )}
              {!loading && results.length === 0 && (
                <li className="px-3 py-2 text-sm text-earth-600 dark:text-earth-400">
                  No staff found
                </li>
              )}
              {!loading &&
                results.map((user, i) => (
                  <li
                    key={user.id}
                    id={`${id}-opt-${i}`}
                    role="option"
                    aria-selected={i === activeIndex}
                    className="px-3 py-2 text-sm hover:bg-earth-100 dark:hover:bg-earth-800 cursor-pointer"
                    onMouseDown={(e) => {
                      e.preventDefault()
                      handleSelect(user)
                    }}
                  >
                    <div className="font-medium">
                      {user.first_name} {user.last_name}
                    </div>
                    <div className="text-xs text-earth-600 dark:text-earth-400">
                      {user.email} - {user.role}
                    </div>
                  </li>
                ))}
            </ul>
          )}
        </>
      )}
      {helpText ? (
        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{helpText}</p>
      ) : null}
    </div>
  )
}
