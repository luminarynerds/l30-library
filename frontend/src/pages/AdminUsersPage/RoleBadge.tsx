/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import { ROLE_BADGE_CONFIG } from './constants'

const RoleBadge: React.FC<{ role: string }> = ({ role }) => {
  const config = ROLE_BADGE_CONFIG[role] || {
    bg: 'bg-earth-100 dark:bg-earth-700',
    text: 'text-lsc-dark/70 dark:text-lsc-cream/70',
    darkBg: 'dark:bg-earth-900/30',
    darkText: 'dark:text-earth-300',
  }

  return (
    <span
      className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${config.bg} ${config.text} ${config.darkBg} ${config.darkText}`}
    >
      {role.replace('_', ' ')}
    </span>
  )
}

export default RoleBadge
