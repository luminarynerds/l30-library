/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import DutyHero from '../panels/DutyHero'
import BoardAttentionItems from '../panels/BoardAttentionItems'
import BoardQuickActions from '../panels/BoardQuickActions'
import BoardStatusByArea from '../panels/BoardStatusByArea'
import BoardActivity from '../panels/BoardActivity'

export default function BoardOpsDashboard() {
  return (
    <div className="space-y-6">
      <div className="motion-safe:animate-dashboard-enter-0">
        {/* eslint-disable-next-line jsx-a11y/aria-role -- role here is a custom component prop, not a DOM ARIA role */}
        <DutyHero role="board_ops" />
      </div>
      <div className="motion-safe:animate-dashboard-enter-1">
        <BoardAttentionItems />
      </div>
      <div className="motion-safe:animate-dashboard-enter-2">
        <BoardQuickActions />
      </div>
      <div className="motion-safe:animate-dashboard-enter-3">
        <BoardStatusByArea />
      </div>
      <div className="motion-safe:animate-dashboard-enter-4">
        <BoardActivity />
      </div>
    </div>
  )
}
