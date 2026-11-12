/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export default function SectionDivider(): React.ReactElement {
  return (
    <div className="flex items-center justify-center max-w-[80%] mx-auto" role="separator">
      <div className="flex-1 h-px rounded-full bg-lsc-border dark:bg-earth-700" />
      <div className="mx-3 w-1.5 h-1.5 rotate-45 rounded-sm bg-lsc-border dark:bg-earth-700 flex-shrink-0" />
      <div className="flex-1 h-px rounded-full bg-lsc-border dark:bg-earth-700" />
    </div>
  )
}
