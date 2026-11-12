/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import FrontDeskSchedule from "./FrontDeskSchedule"
import DeskSchedulePanel from "./DeskSchedulePanel"

type Tab = "programs" | "coverage"

export default function FrontDeskToday() {
  const [tab, setTab] = useState<Tab>("programs")

  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60">Today</p>
        <div className="flex items-center gap-1 ml-auto">
          <button
            onClick={() => setTab("programs")}
            className={`text-xs font-medium px-2 py-1 rounded-lg transition-colors ${
              tab === "programs"
                ? "bg-lsc-rose/10 text-lsc-rose dark:bg-lsc-rose/20 dark:text-lsc-rose-light"
                : "text-lsc-dark/50 dark:text-lsc-cream/50 hover:text-lsc-dark dark:hover:text-lsc-cream"
            }`}
          >
            Programs
          </button>
          <button
            onClick={() => setTab("coverage")}
            className={`text-xs font-medium px-2 py-1 rounded-lg transition-colors ${
              tab === "coverage"
                ? "bg-lsc-rose/10 text-lsc-rose dark:bg-lsc-rose/20 dark:text-lsc-rose-light"
                : "text-lsc-dark/50 dark:text-lsc-cream/50 hover:text-lsc-dark dark:hover:text-lsc-cream"
            }`}
          >
            Coverage
          </button>
        </div>
      </div>
      {tab === "programs" ? <FrontDeskSchedule /> : <DeskSchedulePanel />}
    </div>
  )
}
