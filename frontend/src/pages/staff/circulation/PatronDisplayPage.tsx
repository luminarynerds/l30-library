/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from "react"
import { getCurrentLocale } from '@/i18n'
import {
  CIRC_BROADCAST_CHANNEL,
  type CirculationBroadcastMessage,
  type DisplayItem,
} from "./hooks/useCirculationBroadcast"

interface DisplayState {
  patronFirstName: string
  patronLastInitial: string
  items: DisplayItem[]
  balance: number | null
}

function formatDueDate(d: string | null): string {
  if (!d) return ""
  try {
    return new Date(d).toLocaleDateString(getCurrentLocale(), {
      weekday: "short",
      month: "short",
      day: "numeric",
    })
  } catch {
    return d
  }
}

function formatBalance(b: number | null): string | null {
  if (b == null) return null
  return b.toLocaleString(getCurrentLocale(), { style: "currency", currency: "USD" })
}

export default function PatronDisplayPage(): React.ReactElement {
  const [state, setState] = useState<DisplayState | null>(null)

  useEffect(() => {
    if (typeof BroadcastChannel === "undefined") return
    const channel = new BroadcastChannel(CIRC_BROADCAST_CHANNEL)
    const onMessage = (e: MessageEvent<CirculationBroadcastMessage>) => {
      const msg = e.data
      if (!msg || typeof msg !== "object") return
      if (msg.type === "clear") {
        setState(null)
        return
      }
      if (msg.type === "checkout" || msg.type === "checkin") {
        setState({
          patronFirstName: msg.patronFirstName,
          patronLastInitial: msg.patronLastInitial,
          items: msg.items,
          balance: msg.balance,
        })
      }
    }
    channel.addEventListener("message", onMessage)
    return () => {
      channel.removeEventListener("message", onMessage)
      channel.close()
    }
  }, [])

  if (!state) {
    return (
      <main
        data-testid="patron-display-welcome"
        className="min-h-screen w-full flex flex-col items-center justify-center bg-lsc-cream dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream p-12"
      >
        <h1 className="text-7xl md:text-8xl font-semibold tracking-tight text-center">
          Welcome to the library
        </h1>
        <p className="mt-6 text-3xl md:text-4xl text-center opacity-80">
          A staff member will be with you in a moment.
        </p>
      </main>
    )
  }

  const formattedBalance = formatBalance(state.balance)
  const displayName = `${state.patronFirstName}${
    state.patronLastInitial ? ` ${state.patronLastInitial}` : ""
  }`.trim()

  return (
    <main
      data-testid="patron-display-transaction"
      className="min-h-screen w-full flex flex-col bg-lsc-cream dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream p-10 md:p-14"
    >
      <header className="mb-8">
        <p className="text-2xl md:text-3xl opacity-70">Hello,</p>
        <h1
          data-testid="patron-display-name"
          className="text-6xl md:text-8xl font-semibold tracking-tight mt-2"
        >
          {displayName || "Welcome"}
        </h1>
      </header>

      <section
        data-testid="patron-display-items"
        aria-label="Items in this transaction"
        className="flex-1"
      >
        {state.items.length === 0 ? (
          <p className="text-3xl md:text-4xl opacity-70">No items yet.</p>
        ) : (
          <ul className="space-y-4 md:space-y-6">
            {state.items.map((item, idx) => (
              <li
                key={`${item.title}-${idx}`}
                className="flex flex-col md:flex-row md:items-baseline md:justify-between gap-2 border-b border-lsc-dark/10 dark:border-lsc-cream/10 pb-4"
              >
                <span className="text-3xl md:text-5xl font-medium leading-tight">
                  {item.title}
                </span>
                {item.dueDate && (
                  <span className="text-2xl md:text-3xl opacity-80 whitespace-nowrap">
                    Due {formatDueDate(item.dueDate)}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      {formattedBalance && (
        <footer
          data-testid="patron-display-balance"
          className="mt-10 pt-6 border-t border-lsc-dark/20 dark:border-lsc-cream/20"
        >
          <p className="text-3xl md:text-4xl">
            <span className="opacity-70">Balance:</span>{" "}
            <span className="font-semibold">{formattedBalance}</span>
          </p>
        </footer>
      )}
    </main>
  )
}
