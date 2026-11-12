/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { getUserInitials, getAvatarColor } from './constants'
import type { AdminUser } from '../../api/staff-api'

const UserAvatar: React.FC<{ user: AdminUser; size?: 'sm' | 'md' }> = ({ user, size = 'md' }) => {
  const initials = getUserInitials(user.first_name, user.last_name, user.email)
  const colorClass = getAvatarColor(user.id)
  const sizeClasses = size === 'sm' ? 'w-8 h-8 text-xs' : 'w-10 h-10 text-sm'

  return (
    <div
      className={`${sizeClasses} ${colorClass} rounded-full flex items-center justify-center text-white font-semibold flex-shrink-0`}
      title={user.email}
    >
      {initials}
    </div>
  )
}

export default UserAvatar
