/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { getPresidentSignoffs, SignOffItem } from '@/api/staff-api/board-dashboard'
import { FileSignature } from 'lucide-react'

export default function PresidentSignOffQueue() {
  const { token } = useAuth()
  const [items, setItems] = useState<SignOffItem[]>([])

  useEffect(() => {
    if (!token) return
    getPresidentSignoffs(token).then(r => setItems(r.items)).catch(() => {})
  }, [token])

  if (items.length === 0) return null

  return (
    <div>
      <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60 mb-2">Needs your sign-off</p>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm divide-y divide-lsc-border dark:divide-earth-700">
        {items.map(item => (
          <div key={item.id} className="flex items-center gap-3 px-4 py-4">
            <FileSignature className="w-5 h-5 text-lsc-dark/40 dark:text-lsc-cream/40 flex-shrink-0" aria-hidden="true" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{item.title}</p>
              <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-0.5">{item.description}</p>
            </div>
            <Link to={item.action_url} className="flex-shrink-0 px-3 py-1.5 text-xs font-medium rounded-xl bg-lsc-cream dark:bg-lsc-brown/30 text-lsc-dark dark:text-lsc-cream motion-safe:hover:scale-[1.03] motion-safe:active:scale-[0.98] hover:ring-2 hover:ring-lsc-rose/50 transition-all">
              {item.action_label}
            </Link>
          </div>
        ))}
      </div>
    </div>
  )
}
