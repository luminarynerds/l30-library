/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Custom hook for managing event personalization data in localStorage
 * Handles user registrations, bookmarked events, and category/audience preferences
 */
import { useState, useCallback, useEffect } from 'react'

// Storage keys
const STORAGE_KEYS = {
  REGISTRATIONS: 'lsc_event_registrations',
  BOOKMARKS: 'lsc_event_bookmarks',
  PREFERENCES: 'lsc_event_preferences',
  USER_EMAIL: 'lsc_event_user_email',
} as const

// Types
export interface StoredRegistration {
  registrationId: number
  eventId: number
  eventTitle: string
  eventStartTime: string
  eventLocation: string | null
  registeredAt: string
  status: string
  reminderRequested: boolean
}

export interface EventPreferences {
  categories: string[]
  audiences: string[]
}

export interface EventPersonalizationState {
  // User email for anonymous tracking
  userEmail: string | null
  // Map of eventId -> registration info
  registrations: Map<number, StoredRegistration>
  // Set of bookmarked event IDs
  bookmarks: Set<number>
  // User's preferred categories and audiences
  preferences: EventPreferences
}

// Helper functions for localStorage
function safeLocalStorage() {
  try {
    const testKey = '__test__'
    localStorage.setItem(testKey, testKey)
    localStorage.removeItem(testKey)
    return true
  } catch {
    return false
  }
}

function loadFromStorage<T>(key: string, defaultValue: T): T {
  if (!safeLocalStorage()) return defaultValue
  try {
    const stored = localStorage.getItem(key)
    if (!stored) return defaultValue
    return JSON.parse(stored) as T
  } catch {
    return defaultValue
  }
}

function saveToStorage<T>(key: string, value: T): void {
  if (!safeLocalStorage()) return
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // Silently fail if storage is full or unavailable
  }
}

function removeFromStorage(key: string): void {
  if (!safeLocalStorage()) return
  localStorage.removeItem(key)
}

export function useEventPersonalization() {
  // State
  const [userEmail, setUserEmailState] = useState<string | null>(() =>
    loadFromStorage<string | null>(STORAGE_KEYS.USER_EMAIL, null)
  )

  const [registrations, setRegistrationsState] = useState<Map<number, StoredRegistration>>(() => {
    const stored = loadFromStorage<Record<number, StoredRegistration>>(STORAGE_KEYS.REGISTRATIONS, {})
    return new Map(Object.entries(stored).map(([k, v]) => [Number(k), v]))
  })

  const [bookmarks, setBookmarksState] = useState<Set<number>>(() => {
    const stored = loadFromStorage<number[]>(STORAGE_KEYS.BOOKMARKS, [])
    return new Set(stored)
  })

  const [preferences, setPreferencesState] = useState<EventPreferences>(() =>
    loadFromStorage<EventPreferences>(STORAGE_KEYS.PREFERENCES, { categories: [], audiences: [] })
  )

  // Persist registrations to localStorage when they change
  useEffect(() => {
    const obj = Object.fromEntries(registrations)
    saveToStorage(STORAGE_KEYS.REGISTRATIONS, obj)
  }, [registrations])

  // Persist bookmarks to localStorage when they change
  useEffect(() => {
    saveToStorage(STORAGE_KEYS.BOOKMARKS, Array.from(bookmarks))
  }, [bookmarks])

  // Persist preferences to localStorage when they change
  useEffect(() => {
    saveToStorage(STORAGE_KEYS.PREFERENCES, preferences)
  }, [preferences])

  // Persist user email to localStorage when it changes
  useEffect(() => {
    if (userEmail) {
      saveToStorage(STORAGE_KEYS.USER_EMAIL, userEmail)
    } else {
      removeFromStorage(STORAGE_KEYS.USER_EMAIL)
    }
  }, [userEmail])

  // User email management
  const setUserEmail = useCallback((email: string | null) => {
    setUserEmailState(email ? email.toLowerCase().trim() : null)
  }, [])

  // Registration management
  const addRegistration = useCallback((registration: StoredRegistration) => {
    setRegistrationsState(prev => {
      const next = new Map(prev)
      next.set(registration.eventId, registration)
      return next
    })
  }, [])

  const removeRegistration = useCallback((eventId: number) => {
    setRegistrationsState(prev => {
      const next = new Map(prev)
      next.delete(eventId)
      return next
    })
  }, [])

  const isRegistered = useCallback((eventId: number) => {
    return registrations.has(eventId)
  }, [registrations])

  const getRegistration = useCallback((eventId: number) => {
    return registrations.get(eventId) ?? null
  }, [registrations])

  const getUpcomingRegistrations = useCallback(() => {
    const now = new Date()
    return Array.from(registrations.values())
      .filter(reg => new Date(reg.eventStartTime) > now && reg.status !== 'cancelled')
      .sort((a, b) => new Date(a.eventStartTime).getTime() - new Date(b.eventStartTime).getTime())
  }, [registrations])

  // Bookmark management
  const toggleBookmark = useCallback((eventId: number) => {
    setBookmarksState(prev => {
      const next = new Set(prev)
      if (next.has(eventId)) {
        next.delete(eventId)
      } else {
        next.add(eventId)
      }
      return next
    })
  }, [])

  const addBookmark = useCallback((eventId: number) => {
    setBookmarksState(prev => new Set(prev).add(eventId))
  }, [])

  const removeBookmark = useCallback((eventId: number) => {
    setBookmarksState(prev => {
      const next = new Set(prev)
      next.delete(eventId)
      return next
    })
  }, [])

  const isBookmarked = useCallback((eventId: number) => {
    return bookmarks.has(eventId)
  }, [bookmarks])

  const getBookmarkedEventIds = useCallback(() => {
    return Array.from(bookmarks)
  }, [bookmarks])

  // Preferences management
  const setPreferences = useCallback((newPreferences: EventPreferences) => {
    setPreferencesState(newPreferences)
  }, [])

  const updatePreferences = useCallback((partial: Partial<EventPreferences>) => {
    setPreferencesState(prev => ({ ...prev, ...partial }))
  }, [])

  const toggleCategory = useCallback((category: string) => {
    setPreferencesState(prev => {
      const categories = prev.categories.includes(category)
        ? prev.categories.filter(c => c !== category)
        : [...prev.categories, category]
      return { ...prev, categories }
    })
  }, [])

  const toggleAudience = useCallback((audience: string) => {
    setPreferencesState(prev => {
      const audiences = prev.audiences.includes(audience)
        ? prev.audiences.filter(a => a !== audience)
        : [...prev.audiences, audience]
      return { ...prev, audiences }
    })
  }, [])

  const hasPreferences = useCallback(() => {
    return preferences.categories.length > 0 || preferences.audiences.length > 0
  }, [preferences])

  const matchesPreferences = useCallback((eventCategory: string | null, eventAudience: string | null): boolean => {
    // If no preferences set, everything matches
    if (preferences.categories.length === 0 && preferences.audiences.length === 0) {
      return false // Return false so "For You" section only shows when preferences are set
    }

    const categoryMatch = preferences.categories.length === 0 ||
      Boolean(eventCategory && preferences.categories.includes(eventCategory))
    const audienceMatch = preferences.audiences.length === 0 ||
      Boolean(eventAudience && preferences.audiences.includes(eventAudience))

    return categoryMatch || audienceMatch
  }, [preferences])

  // Clear all data
  const clearAll = useCallback(() => {
    setUserEmailState(null)
    setRegistrationsState(new Map())
    setBookmarksState(new Set())
    setPreferencesState({ categories: [], audiences: [] })
    removeFromStorage(STORAGE_KEYS.USER_EMAIL)
    removeFromStorage(STORAGE_KEYS.REGISTRATIONS)
    removeFromStorage(STORAGE_KEYS.BOOKMARKS)
    removeFromStorage(STORAGE_KEYS.PREFERENCES)
  }, [])

  return {
    // User email
    userEmail,
    setUserEmail,

    // Registrations
    registrations: Array.from(registrations.values()),
    registrationsCount: registrations.size,
    addRegistration,
    removeRegistration,
    isRegistered,
    getRegistration,
    getUpcomingRegistrations,

    // Bookmarks
    bookmarks: Array.from(bookmarks),
    bookmarksCount: bookmarks.size,
    toggleBookmark,
    addBookmark,
    removeBookmark,
    isBookmarked,
    getBookmarkedEventIds,

    // Preferences
    preferences,
    setPreferences,
    updatePreferences,
    toggleCategory,
    toggleAudience,
    hasPreferences,
    matchesPreferences,

    // Utility
    clearAll,
  }
}

export type UseEventPersonalizationReturn = ReturnType<typeof useEventPersonalization>
