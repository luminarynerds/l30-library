/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
/**
 * Reconnecting WebSocket Hook
 *
 * Provides a WebSocket connection with automatic reconnection using exponential backoff.
 *
 * Features:
 * - Automatic reconnection on disconnect with exponential backoff (1s, 2s, 4s, 8s... up to 30s max)
 * - Connection state tracking (connecting, connected, disconnected, reconnecting)
 * - Reconnect attempt counter
 * - Manual reconnect capability
 * - Message queue for outgoing messages while disconnected
 * - Automatic message flush on reconnect
 * - Ping/pong keepalive to detect stale connections
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import {
  WS_INITIAL_RECONNECT_DELAY_MS,
  WS_MAX_RECONNECT_DELAY_MS,
  WS_PING_INTERVAL_MS,
  WS_PONG_TIMEOUT_MS,
} from '@/constants/timeouts'

// ==================== Types ====================

export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'reconnecting'

export interface WebSocketMessage {
  action?: string
  channel?: string
  event_type?: string
  [key: string]: unknown
}

export interface UseReconnectingWebSocketOptions {
  /** The WebSocket URL to connect to */
  url: string
  /** Whether the connection should be active */
  enabled?: boolean
  /** Initial subscriptions to set up on connect */
  subscriptions?: string[]
  /** Callback when a message is received */
  onMessage?: (message: WebSocketMessage) => void
  /** Callback when connection state changes */
  onStateChange?: (state: ConnectionState) => void
  /** Callback when an error occurs */
  onError?: (error: Event) => void
  /** Initial reconnect delay in ms (default: 1000) */
  initialReconnectDelay?: number
  /** Maximum reconnect delay in ms (default: 30000) */
  maxReconnectDelay?: number
  /** Ping interval in ms (default: 30000) */
  pingInterval?: number
  /** Pong timeout in ms - how long to wait for pong before considering connection dead (default: 5000) */
  pongTimeout?: number
  /** Maximum reconnect attempts before giving up (default: Infinity) */
  maxReconnectAttempts?: number
}

export interface UseReconnectingWebSocketReturn {
  /** Current connection state */
  connectionState: ConnectionState
  /** Number of reconnect attempts since last successful connection */
  reconnectAttempts: number
  /** Send a message through the WebSocket */
  sendMessage: (message: WebSocketMessage) => void
  /** Subscribe to a channel */
  subscribe: (channel: string) => void
  /** Unsubscribe from a channel */
  unsubscribe: (channel: string) => void
  /** Manually trigger a reconnection */
  reconnect: () => void
  /** Close the connection */
  disconnect: () => void
  /** Whether the socket is currently connected */
  isConnected: boolean
  /** Last error message if any */
  lastError: string | null
}

// ==================== Constants ====================

const DEFAULT_INITIAL_RECONNECT_DELAY = WS_INITIAL_RECONNECT_DELAY_MS
const DEFAULT_MAX_RECONNECT_DELAY = WS_MAX_RECONNECT_DELAY_MS
const DEFAULT_PING_INTERVAL = WS_PING_INTERVAL_MS
const DEFAULT_PONG_TIMEOUT = WS_PONG_TIMEOUT_MS

// ==================== Hook ====================

export function useReconnectingWebSocket(
  options: UseReconnectingWebSocketOptions
): UseReconnectingWebSocketReturn {
  const {
    url,
    enabled = true,
    subscriptions = [],
    onMessage,
    onStateChange,
    onError,
    initialReconnectDelay = DEFAULT_INITIAL_RECONNECT_DELAY,
    maxReconnectDelay = DEFAULT_MAX_RECONNECT_DELAY,
    pingInterval = DEFAULT_PING_INTERVAL,
    pongTimeout = DEFAULT_PONG_TIMEOUT,
    maxReconnectAttempts = Infinity,
  } = options

  // State
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected')
  const [reconnectAttempts, setReconnectAttempts] = useState(0)
  const [lastError, setLastError] = useState<string | null>(null)

  // Refs
  const wsRef = useRef<WebSocket | null>(null)
  const messageQueueRef = useRef<WebSocketMessage[]>([])
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const pongTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const currentReconnectDelayRef = useRef(initialReconnectDelay)
  const isManualDisconnectRef = useRef(false)
  const awaitingPongRef = useRef(false)
  const subscriptionsRef = useRef<Set<string>>(new Set(subscriptions))

  // Update subscriptions ref when prop changes
  useEffect(() => {
    subscriptionsRef.current = new Set(subscriptions)
  }, [subscriptions])

  // Update connection state and notify
  const updateConnectionState = useCallback((state: ConnectionState) => {
    setConnectionState(state)
    onStateChange?.(state)
  }, [onStateChange])

  // Clear all timers
  const clearAllTimers = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current)
      pingIntervalRef.current = null
    }
    if (pongTimeoutRef.current) {
      clearTimeout(pongTimeoutRef.current)
      pongTimeoutRef.current = null
    }
  }, [])

  // Calculate next reconnect delay with exponential backoff
  const getNextReconnectDelay = useCallback(() => {
    const delay = currentReconnectDelayRef.current
    // Double the delay for next time, capped at max
    currentReconnectDelayRef.current = Math.min(delay * 2, maxReconnectDelay)
    return delay
  }, [maxReconnectDelay])

  // Reset reconnect state on successful connection
  const resetReconnectState = useCallback(() => {
    currentReconnectDelayRef.current = initialReconnectDelay
    setReconnectAttempts(0)
    setLastError(null)
  }, [initialReconnectDelay])

  // Send a ping message
  const sendPing = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN && !awaitingPongRef.current) {
      awaitingPongRef.current = true
      wsRef.current.send(JSON.stringify({ action: 'ping' }))

      // Set timeout for pong response
      pongTimeoutRef.current = setTimeout(() => {
        if (awaitingPongRef.current) {
          // Pong not received in time, connection is stale
          Sentry.captureMessage('[WebSocket] Pong timeout - connection appears stale', 'warning')
          wsRef.current?.close()
        }
      }, pongTimeout)
    }
  }, [pongTimeout])

  // Start ping/pong keepalive
  const startPingInterval = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current)
    }
    pingIntervalRef.current = setInterval(sendPing, pingInterval)
  }, [sendPing, pingInterval])

  // Flush queued messages
  const flushMessageQueue = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const queue = messageQueueRef.current
      messageQueueRef.current = []

      for (const message of queue) {
        try {
          wsRef.current.send(JSON.stringify(message))
        } catch (error: unknown) {
          Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
          // Re-queue failed message
          messageQueueRef.current.push(message)
        }
      }
    }
  }, [])

  // Send initial subscriptions
  const sendInitialSubscriptions = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      for (const channel of subscriptionsRef.current) {
        wsRef.current.send(JSON.stringify({ action: 'subscribe', channel }))
      }
    }
  }, [])

  // Connect to WebSocket
  const connect = useCallback(function connect() {
    // Don't connect if disabled or already connecting/connected
    if (!enabled) return
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    if (wsRef.current?.readyState === WebSocket.CONNECTING) return

    // Clear any existing connection
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    clearAllTimers()
    isManualDisconnectRef.current = false
    updateConnectionState('connecting')

    try {
      // Build URL with initial subscriptions as query param
      let wsUrl = url
      if (subscriptions.length > 0) {
        const separator = url.includes('?') ? '&' : '?'
        wsUrl = `${url}${separator}subscriptions=${subscriptions.join(',')}`
      }

      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        updateConnectionState('connected')
        resetReconnectState()

        // Send any additional subscriptions not in URL
        sendInitialSubscriptions()

        // Flush any queued messages
        flushMessageQueue()

        // Start ping/pong keepalive
        startPingInterval()
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage

          // Handle pong response
          if (message.event_type === 'pong') {
            awaitingPongRef.current = false
            if (pongTimeoutRef.current) {
              clearTimeout(pongTimeoutRef.current)
              pongTimeoutRef.current = null
            }
            return
          }

          // Handle subscription confirmations
          if (message.event_type === 'subscribed' || message.event_type === 'unsubscribed') {
            return
          }

          // Forward other messages to callback
          onMessage?.(message)
        } catch (error: unknown) {
          Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
        }
      }

      ws.onerror = (event) => {
        Sentry.captureMessage('[WebSocket] Error', 'error')
        setLastError('WebSocket error occurred')
        onError?.(event)
      }

      ws.onclose = (_event) => {
        clearAllTimers()
        awaitingPongRef.current = false

        // Don't reconnect if manually disconnected
        if (isManualDisconnectRef.current) {
          updateConnectionState('disconnected')
          return
        }

        // Schedule reconnection
        if (reconnectAttempts < maxReconnectAttempts) {
          updateConnectionState('reconnecting')
          const delay = getNextReconnectDelay()
          setReconnectAttempts(prev => prev + 1)

          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, delay)
        } else {
          updateConnectionState('disconnected')
          setLastError(`Max reconnect attempts (${maxReconnectAttempts}) reached`)
        }
      }
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      setLastError('Failed to create WebSocket connection')
      updateConnectionState('disconnected')
    }
  }, [
    enabled,
    url,
    subscriptions,
    onMessage,
    onError,
    maxReconnectAttempts,
    reconnectAttempts,
    clearAllTimers,
    updateConnectionState,
    resetReconnectState,
    getNextReconnectDelay,
    sendInitialSubscriptions,
    flushMessageQueue,
    startPingInterval,
  ])

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    isManualDisconnectRef.current = true
    clearAllTimers()

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    updateConnectionState('disconnected')
  }, [clearAllTimers, updateConnectionState])

  // Manual reconnect
  const reconnect = useCallback(() => {
    disconnect()

    // Reset reconnect state for fresh start
    currentReconnectDelayRef.current = initialReconnectDelay
    setReconnectAttempts(0)
    setLastError(null)
    isManualDisconnectRef.current = false

    // Small delay before reconnecting
    setTimeout(() => {
      connect()
    }, 100)
  }, [disconnect, connect, initialReconnectDelay])

  // Send a message
  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify(message))
      } catch (error: unknown) {
        Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
        // Queue the message for retry
        messageQueueRef.current.push(message)
      }
    } else {
      // Queue message for when connection is restored
      messageQueueRef.current.push(message)
    }
  }, [])

  // Subscribe to a channel
  const subscribe = useCallback((channel: string) => {
    subscriptionsRef.current.add(channel)
    sendMessage({ action: 'subscribe', channel })
  }, [sendMessage])

  // Unsubscribe from a channel
  const unsubscribe = useCallback((channel: string) => {
    subscriptionsRef.current.delete(channel)
    sendMessage({ action: 'unsubscribe', channel })
  }, [sendMessage])

  // Connect on mount and when enabled changes
  useEffect(() => {
    if (enabled) {
      connect()
    } else {
      disconnect()
    }

    return () => {
      disconnect()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, url])

  // Clean up on unmount
  useEffect(() => {
    return () => {
      clearAllTimers()
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [clearAllTimers])

  return useMemo(() => ({
    connectionState,
    reconnectAttempts,
    sendMessage,
    subscribe,
    unsubscribe,
    reconnect,
    disconnect,
    isConnected: connectionState === 'connected',
    lastError,
  }), [
    connectionState,
    reconnectAttempts,
    sendMessage,
    subscribe,
    unsubscribe,
    reconnect,
    disconnect,
    lastError,
  ])
}

export default useReconnectingWebSocket
