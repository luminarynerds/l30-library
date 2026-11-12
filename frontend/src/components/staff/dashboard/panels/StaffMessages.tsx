/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { MessageSquare } from 'lucide-react'
import { listPosts, BoardPost } from '@/api/domains/staff/staff-message-board-api'

export default function StaffMessages() {
  const [posts, setPosts] = useState<BoardPost[]>([])

  useEffect(() => {
    listPosts(1, 5)
      .then(r => setPosts(r.posts))
      .catch(() => {})
  }, [])

  if (posts.length === 0) return null

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60 flex items-center gap-1.5">
          <MessageSquare className="w-3.5 h-3.5" aria-hidden="true" />
          Staff messages
        </p>
        <Link to="/staff/message-board" className="text-[11px] text-lsc-rose hover:underline">
          View all
        </Link>
      </div>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm divide-y divide-lsc-border dark:divide-earth-700">
        {posts.map(post => (
          <Link key={post.id} to={`/staff/message-board/${post.id}`} className="flex items-start gap-3 px-4 py-2.5 hover:bg-earth-50 dark:hover:bg-earth-700/50 transition-colors">
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-lsc-dark dark:text-lsc-cream truncate">
                {post.pinned && <span className="text-lsc-rose mr-1">&#x25cf;</span>}
                {post.title}
              </p>
              <p className="text-[11px] text-lsc-dark/40 dark:text-lsc-cream/40 mt-0.5">
                {post.author?.full_name ?? 'Staff'} &middot; {post.category}
              </p>
            </div>
            {post.reply_count > 0 && (
              <span className="text-[11px] text-lsc-dark/40 dark:text-lsc-cream/40 flex-shrink-0 mt-0.5">
                {post.reply_count}
              </span>
            )}
          </Link>
        ))}
      </div>
    </div>
  )
}
