/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef, useState } from 'react'
import { getAccessToken } from '../utils/tokenStore'
import { API_BASE } from '../api/types'

export type FloorEventType =
  | 'connected'
  | 'session_started'
  | 'session_ended'
  | 'session_reopened'
  | 'session_extended'
  | 'extension_requested'
  | 'extension_approved'
  | 'computer_status_changed'

export interface FloorEvent {
  type: FloorEventType
  computer_id?: number
  reservation_id?: number
  extension_id?: number
  status?: string
  by_staff?: boolean
  extra_minutes?: number
}

export type FloorSocketStatus = 'connecting' | 'live' | 'fallback' | 'closed'

const MAX_RETRIES = 5
const BACKOFF_BASE_MS = 1000
const BACKOFF_MAX_MS = 15000

function buildSocketUrl(): string {
  // API_BASE is typically "/api/v1" so this resolves to "/api/v1/computers/staff/floor/ws"
  // relative to the page origin, with ws/wss chosen by current scheme.
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const path = `${API_BASE}/computers/staff/floor/ws`
  return `${proto}//${window.location.host}${path}`
}

export function useFloorViewSocket(onEvent: (event: FloorEvent) => void) {
  const [status, setStatus] = useState<FloorSocketStatus>('connecting')
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  useEffect(() => {
    let socket: WebSocket | null = null
    let retryCount = 0
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    let cancelled = false

    const connect = () => {
      const token = getAccessToken()
      if (!token) {
        setStatus('fallback')
        return
      }
      setStatus(retryCount === 0 ? 'connecting' : 'connecting')
      let url: string
      try {
        url = buildSocketUrl()
      } catch {
        setStatus('fallback')
        return
      }
      try {
        // The token rides the bearer subprotocol instead of the query string
        // so it never lands in nginx access logs.
        socket = new WebSocket(url, ['bearer', token])
      } catch {
        scheduleReconnect()
        return
      }

      socket.onopen = () => {
        retryCount = 0
        setStatus('live')
      }

      socket.onmessage = (msg) => {
        try {
          const data = JSON.parse(msg.data) as FloorEvent
          onEventRef.current(data)
        } catch {
          /* ignore malformed frames */
        }
      }

      socket.onerror = () => {
        // Errors precede a close; the close handler decides retry policy.
      }

      socket.onclose = () => {
        if (cancelled) return
        scheduleReconnect()
      }
    }

    const scheduleReconnect = () => {
      if (cancelled) return
      retryCount += 1
      if (retryCount > MAX_RETRIES) {
        setStatus('fallback')
        return
      }
      const delay = Math.min(BACKOFF_BASE_MS * 2 ** (retryCount - 1), BACKOFF_MAX_MS)
      reconnectTimer = setTimeout(connect, delay)
    }

    connect()

    return () => {
      cancelled = true
      setStatus('closed')
      if (reconnectTimer) clearTimeout(reconnectTimer)
      if (socket && socket.readyState <= WebSocket.OPEN) {
        try { socket.close() } catch { /* noop */ }
      }
    }
  }, [])

  return { status }
}
