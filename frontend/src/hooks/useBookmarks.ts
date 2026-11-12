/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback } from 'react'

export type BookmarkType = 'collection' | 'guide' | 'form'

export interface Bookmark {
  id: number
  type: BookmarkType
  title: string
  savedAt: string
  description?: string
}

const BOOKMARKS_STORAGE_KEY = 'lsc_bookmarks'

export function useBookmarks() {
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([])
  const [isLoaded, setIsLoaded] = useState(false)

  // Load bookmarks from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(BOOKMARKS_STORAGE_KEY)
      if (stored) {
        // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time localStorage hydration on mount
        setBookmarks(JSON.parse(stored))
      }
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
    setIsLoaded(true)
  }, [])

  // Save bookmarks to localStorage whenever they change
  useEffect(() => {
    if (isLoaded) {
      try {
        localStorage.setItem(BOOKMARKS_STORAGE_KEY, JSON.stringify(bookmarks))
      } catch (error: unknown) {
        Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      }
    }
  }, [bookmarks, isLoaded])

  const isBookmarked = useCallback(
    (id: number, type: BookmarkType) => {
      return bookmarks.some((b) => b.id === id && b.type === type)
    },
    [bookmarks]
  )

  const toggleBookmark = useCallback(
    (
      id: number,
      type: BookmarkType,
      title: string,
      description?: string
    ) => {
      setBookmarks((prev) => {
        if (isBookmarked(id, type)) {
          return prev.filter((b) => !(b.id === id && b.type === type))
        } else {
          return [
            ...prev,
            {
              id,
              type,
              title,
              ...(description && { description }),
              savedAt: new Date().toISOString(),
            },
          ]
        }
      })
    },
    [isBookmarked]
  )

  const removeBookmark = useCallback((id: number, type: BookmarkType) => {
    setBookmarks((prev) => prev.filter((b) => !(b.id === id && b.type === type)))
  }, [])

  const clearAllBookmarks = useCallback(() => {
    setBookmarks([])
  }, [])

  const getBookmarksByType = useCallback(
    (type: BookmarkType) => {
      return bookmarks.filter((b) => b.type === type)
    },
    [bookmarks]
  )

  return {
    bookmarks,
    isBookmarked,
    toggleBookmark,
    removeBookmark,
    clearAllBookmarks,
    getBookmarksByType,
    isLoaded,
  }
}
