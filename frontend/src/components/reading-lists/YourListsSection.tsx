/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { BookOpen, ChevronRight } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useMyReadingLists } from '@/hooks/useMyReadingLists'

export function YourListsSection() {
  const { user } = useAuth()
  const { data: lists, isLoading } = useMyReadingLists()

  if (!user || isLoading || !lists || lists.length === 0) return null

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          Your Lists
        </h2>
        <Link
          to="/account?tab=lists"
          className="text-xs font-medium text-status-info-600 hover:underline dark:text-status-info-400 flex items-center gap-0.5"
        >
          Manage lists
          <ChevronRight className="w-3.5 h-3.5" aria-hidden="true" />
        </Link>
      </div>
      <div className="flex gap-3 overflow-x-auto pb-2">
        {lists.map((list) => (
          <Link
            key={list.id}
            to={`/account?tab=lists&list=${list.id}`}
            className="min-w-[180px] rounded-lg border border-lsc-dark/10 bg-lsc-white p-4 shadow-sm hover:shadow-md dark:border-lsc-cream/10 dark:bg-lsc-dark/60 transition-shadow flex-shrink-0"
          >
            <BookOpen className="w-5 h-5 text-status-info-500 dark:text-status-info-400 mb-2" aria-hidden="true" />
            <h3 className="text-sm font-bold text-lsc-dark dark:text-lsc-cream truncate" title={list.name}>
              {list.name}
            </h3>
            <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/50 mt-1">
              {list.item_count ?? 0} {list.item_count === 1 ? 'item' : 'items'}
            </p>
          </Link>
        ))}
      </div>
    </div>
  )
}
