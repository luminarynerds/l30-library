/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import DutyHero from '../panels/DutyHero'
import PresidentSignOffQueue from '../panels/PresidentSignOffQueue'
import PresidentNextMeetingPanel from '../panels/PresidentNextMeeting'
import PresidentComingUp from '../panels/PresidentComingUp'

export default function BoardPresidentDashboard() {
  return (
    <div className="space-y-6">
      <div className="motion-safe:animate-dashboard-enter-0">
        {/* eslint-disable-next-line jsx-a11y/aria-role -- role here is a custom component prop, not a DOM ARIA role */}
        <DutyHero role="board_president" />
      </div>
      <div className="motion-safe:animate-dashboard-enter-1">
        <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/70">A few things need you this week. Nothing\u2019s on fire.</p>
      </div>
      <div className="motion-safe:animate-dashboard-enter-2">
        <PresidentSignOffQueue />
      </div>
      <div className="motion-safe:animate-dashboard-enter-3">
        <PresidentNextMeetingPanel />
      </div>
      <div className="motion-safe:animate-dashboard-enter-4">
        <PresidentComingUp />
      </div>
    </div>
  )
}
