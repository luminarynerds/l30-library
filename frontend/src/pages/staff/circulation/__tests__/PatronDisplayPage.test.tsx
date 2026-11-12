/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import { act, render, screen } from "@testing-library/react"
import PatronDisplayPage from "../PatronDisplayPage"
import { CIRC_BROADCAST_CHANNEL } from "../hooks/useCirculationBroadcast"

// happy-dom does not implement BroadcastChannel. Install a minimal in-memory
// implementation keyed by channel name so we can capture subscribers from the
// component and dispatch synthetic messages.
type Listener = (e: MessageEvent) => void
const channelListeners: Map<string, Set<Listener>> = new Map()
const instances: MockBroadcastChannel[] = []

class MockBroadcastChannel {
  name: string
  listeners: Set<Listener> = new Set()
  postMessage = vi.fn()
  closed = false

  constructor(name: string) {
    this.name = name
    instances.push(this)
    if (!channelListeners.has(name)) channelListeners.set(name, new Set())
  }

  addEventListener(type: string, cb: Listener): void {
    if (type !== "message") return
    this.listeners.add(cb)
    channelListeners.get(this.name)!.add(cb)
  }

  removeEventListener(type: string, cb: Listener): void {
    if (type !== "message") return
    this.listeners.delete(cb)
    channelListeners.get(this.name)?.delete(cb)
  }

  close(): void {
    this.closed = true
    for (const cb of this.listeners) {
      channelListeners.get(this.name)?.delete(cb)
    }
    this.listeners.clear()
  }
}

function dispatch(name: string, data: unknown): void {
  const subs = channelListeners.get(name)
  if (!subs) return
  for (const cb of subs) {
    cb({ data } as MessageEvent)
  }
}

beforeEach(() => {
  channelListeners.clear()
  instances.length = 0
  ;(globalThis as unknown as { BroadcastChannel: typeof MockBroadcastChannel }).BroadcastChannel =
    MockBroadcastChannel
})

afterEach(() => {
  delete (globalThis as unknown as { BroadcastChannel?: unknown }).BroadcastChannel
})

describe("PatronDisplayPage", () => {
  it("subscribes to the l30-circ BroadcastChannel on mount", () => {
    render(<PatronDisplayPage />)
    expect(instances.length).toBe(1)
    expect(instances[0]!.name).toBe(CIRC_BROADCAST_CHANNEL)
    expect(instances[0]!.listeners.size).toBe(1)
  })

  it("renders the welcome state when no message has arrived", () => {
    render(<PatronDisplayPage />)
    expect(screen.getByTestId("patron-display-welcome")).toBeInTheDocument()
    expect(screen.getByText(/welcome to the library/i)).toBeInTheDocument()
  })

  it("renders sanitized name (first + initial only) on checkout message", () => {
    render(<PatronDisplayPage />)
    act(() => {
      dispatch(CIRC_BROADCAST_CHANNEL, {
        type: "checkout",
        patronFirstName: "Felicity",
        patronLastInitial: "T.",
        items: [
          { title: "A Confederacy of Dunces", dueDate: "2026-06-01T00:00:00Z" },
        ],
        balance: 0,
      })
    })
    const name = screen.getByTestId("patron-display-name")
    expect(name.textContent).toBe("Felicity T.")
    expect(screen.getByText(/A Confederacy of Dunces/)).toBeInTheDocument()
    // Sanitization: no full surname leaks through.
    expect(screen.queryByText(/Toole/i)).not.toBeInTheDocument()
  })

  it("clears the view back to welcome on a clear message", () => {
    render(<PatronDisplayPage />)
    act(() => {
      dispatch(CIRC_BROADCAST_CHANNEL, {
        type: "checkout",
        patronFirstName: "Felicity",
        patronLastInitial: "T.",
        items: [{ title: "Dunces", dueDate: null }],
        balance: null,
      })
    })
    expect(screen.getByTestId("patron-display-transaction")).toBeInTheDocument()

    act(() => {
      dispatch(CIRC_BROADCAST_CHANNEL, { type: "clear" })
    })
    expect(screen.getByTestId("patron-display-welcome")).toBeInTheDocument()
    expect(screen.queryByTestId("patron-display-transaction")).not.toBeInTheDocument()
  })
})
