/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef, useCallback } from "react"
import type { Patron, PatronCheckout } from "../types"

export const CIRC_BROADCAST_CHANNEL = "l30-circ"

export interface DisplayItem {
  title: string
  dueDate: string | null
}

export interface CheckoutBroadcastMessage {
  type: "checkout"
  patronFirstName: string
  patronLastInitial: string
  items: DisplayItem[]
  balance: number | null
}

export interface CheckinBroadcastMessage {
  type: "checkin"
  patronFirstName: string
  patronLastInitial: string
  items: DisplayItem[]
  balance: number | null
}

export interface ClearBroadcastMessage {
  type: "clear"
}

export type CirculationBroadcastMessage =
  | CheckoutBroadcastMessage
  | CheckinBroadcastMessage
  | ClearBroadcastMessage

function sanitizeName(patron: Pick<Patron, "first_name" | "last_name">): {
  patronFirstName: string
  patronLastInitial: string
} {
  const first = (patron.first_name ?? "").trim()
  const lastRaw = (patron.last_name ?? "").trim()
  const initial = lastRaw.length > 0 ? `${lastRaw[0]!.toUpperCase()}.` : ""
  return { patronFirstName: first, patronLastInitial: initial }
}

function toDisplayItems(items: PatronCheckout[]): DisplayItem[] {
  return items.map((c) => ({
    title: c.item_title ?? "Untitled",
    dueDate: c.due_date ?? null,
  }))
}

interface UseCirculationBroadcastReturn {
  broadcastCheckout: (
    patron: Pick<Patron, "first_name" | "last_name">,
    items: PatronCheckout[],
    balance: number | null,
  ) => void
  broadcastCheckin: (
    patron: Pick<Patron, "first_name" | "last_name">,
    items: PatronCheckout[],
    balance: number | null,
  ) => void
  broadcastClear: () => void
}

export function useCirculationBroadcast(): UseCirculationBroadcastReturn {
  const channelRef = useRef<BroadcastChannel | null>(null)

  useEffect(() => {
    if (typeof BroadcastChannel === "undefined") return
    const ch = new BroadcastChannel(CIRC_BROADCAST_CHANNEL)
    channelRef.current = ch
    return () => {
      ch.close()
      channelRef.current = null
    }
  }, [])

  const post = useCallback((msg: CirculationBroadcastMessage) => {
    channelRef.current?.postMessage(msg)
  }, [])

  const broadcastCheckout = useCallback(
    (
      patron: Pick<Patron, "first_name" | "last_name">,
      items: PatronCheckout[],
      balance: number | null,
    ) => {
      const { patronFirstName, patronLastInitial } = sanitizeName(patron)
      post({
        type: "checkout",
        patronFirstName,
        patronLastInitial,
        items: toDisplayItems(items),
        balance,
      })
    },
    [post],
  )

  const broadcastCheckin = useCallback(
    (
      patron: Pick<Patron, "first_name" | "last_name">,
      items: PatronCheckout[],
      balance: number | null,
    ) => {
      const { patronFirstName, patronLastInitial } = sanitizeName(patron)
      post({
        type: "checkin",
        patronFirstName,
        patronLastInitial,
        items: toDisplayItems(items),
        balance,
      })
    },
    [post],
  )

  const broadcastClear = useCallback(() => {
    post({ type: "clear" })
  }, [post])

  return { broadcastCheckout, broadcastCheckin, broadcastClear }
}
