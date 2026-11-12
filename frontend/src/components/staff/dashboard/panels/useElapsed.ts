// SPDX-FileCopyrightText: 2026 Luminary Nerds
// SPDX-License-Identifier: AGPL-3.0-or-later
import { useEffect, useState } from "react"

/** Milliseconds since `sinceIso`, ticking each minute. Null when not provided. */
export function useElapsed(sinceIso: string | null): number | null {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!sinceIso) return
    const id = setInterval(() => setNow(Date.now()), 60_000)
    return () => clearInterval(id)
  }, [sinceIso])
  if (!sinceIso) return null
  const start = new Date(sinceIso).getTime()
  if (isNaN(start)) return null
  return Math.max(0, now - start)
}

export function fmtElapsed(ms: number): string {
  const totalMin = Math.floor(ms / 60_000)
  const h = Math.floor(totalMin / 60)
  const m = totalMin % 60
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}
