/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useRef } from "react"
import { sendJourneyEvent, type JourneyEventPayload, type JourneyType } from "@/api/journey-tracker-api"

export type { JourneyType }

interface JourneyTrackerOptions {
  journeyType: JourneyType
  isNewUser?: boolean
  accessibilityMode?: boolean
}

function generateSessionId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export function useJourneyTracker(options: JourneyTrackerOptions) {
  const { journeyType, isNewUser, accessibilityMode } = options
  const sessionIdRef = useRef<string>(generateSessionId())
  const sequenceRef = useRef<number>(0)
  const startTimeRef = useRef<number>(Date.now())
  const lastEventTimeRef = useRef<number>(Date.now())

  const trackStage = useCallback(
    (stageName: string, properties?: Record<string, unknown>, errorCode?: string) => {
      sequenceRef.current += 1
      const now = Date.now()
      const timeSinceStart = now - startTimeRef.current
      const timeSincePrevious = now - lastEventTimeRef.current
      lastEventTimeRef.current = now

      const event: JourneyEventPayload = {
        journey_type: journeyType,
        session_id: sessionIdRef.current,
        stage_name: stageName,
        event_sequence: sequenceRef.current,
        time_since_journey_start_ms: timeSinceStart,
      }

      if (sequenceRef.current > 1) {
        event.time_since_previous_event_ms = timeSincePrevious
      }
      if (properties) {
        event.properties = properties
      }
      if (errorCode) {
        event.error_code = errorCode
      }

      sendJourneyEvent(event, { ...(isNewUser ? { isNewUser } : {}), ...(accessibilityMode ? { accessibilityMode } : {}) }).catch(() => {
        // Fire-and-forget: analytics should never block UX
      })
    },
    [journeyType, isNewUser, accessibilityMode]
  )

  const reset = useCallback(() => {
    sessionIdRef.current = generateSessionId()
    sequenceRef.current = 0
    startTimeRef.current = Date.now()
    lastEventTimeRef.current = Date.now()
  }, [])

  return { trackStage, reset, sessionId: sessionIdRef.current }
}
