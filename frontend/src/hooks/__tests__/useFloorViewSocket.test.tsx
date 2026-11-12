/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'

vi.mock('../../utils/tokenStore', () => ({
  getAccessToken: vi.fn(() => 'test.jwt.token'),
}))

import { getAccessToken } from '../../utils/tokenStore'
import { useFloorViewSocket } from '../useFloorViewSocket'

class FakeWebSocket {
  static instances: FakeWebSocket[] = []
  static OPEN = 1
  url: string
  protocols?: string | string[]
  readyState = 0
  onopen: (() => void) | null = null
  onmessage: ((msg: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null

  constructor(url: string, protocols?: string | string[]) {
    this.url = url
    this.protocols = protocols
    FakeWebSocket.instances.push(this)
  }

  close() {
    this.readyState = 3
  }
}

const RealWebSocket = globalThis.WebSocket

function onlySocket(): FakeWebSocket {
  expect(FakeWebSocket.instances).toHaveLength(1)
  const socket = FakeWebSocket.instances[0]
  if (!socket) throw new Error('no socket created')
  return socket
}

describe('useFloorViewSocket', () => {
  beforeEach(() => {
    FakeWebSocket.instances = []
    vi.stubGlobal('WebSocket', FakeWebSocket)
    vi.mocked(getAccessToken).mockReturnValue('test.jwt.token')
  })

  afterEach(() => {
    vi.stubGlobal('WebSocket', RealWebSocket)
  })

  it('sends the JWT as the bearer subprotocol, never in the URL', () => {
    const { unmount } = renderHook(() => useFloorViewSocket(() => {}))

    const socket = onlySocket()
    expect(socket.protocols).toEqual(['bearer', 'test.jwt.token'])
    expect(socket.url).not.toContain('token=')
    expect(socket.url).not.toContain('test.jwt.token')
    expect(socket.url).toContain('/computers/staff/floor/ws')

    unmount()
  })

  it('goes live on open and delivers parsed events', async () => {
    const events: unknown[] = []
    const { result, unmount } = renderHook(() => useFloorViewSocket((e) => events.push(e)))

    const socket = onlySocket()
    socket.readyState = 1
    act(() => socket.onopen?.())
    await waitFor(() => expect(result.current.status).toBe('live'))

    socket.onmessage?.({ data: '{"type":"session_started","computer_id":3}' })
    expect(events).toEqual([{ type: 'session_started', computer_id: 3 }])

    unmount()
  })

  it('falls back when there is no access token', () => {
    vi.mocked(getAccessToken).mockReturnValue(null)
    const { result, unmount } = renderHook(() => useFloorViewSocket(() => {}))

    expect(result.current.status).toBe('fallback')
    expect(FakeWebSocket.instances).toHaveLength(0)

    unmount()
  })
})
