/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export interface StreamingFeatureCarrier {
  streaming_enabled?: boolean
  configuration?: Record<string, unknown> | null
}

export function isStreamingEnabled(features: StreamingFeatureCarrier | null): boolean {
  if (!features) return true

  // Check the direct boolean field from organization features
  if (typeof features.streaming_enabled === 'boolean') {
    return features.streaming_enabled
  }

  // Fall back to configuration blob
  const config = features.configuration
  if (!config || typeof config !== 'object') return true

  const topLevel = config.streaming_enabled
  if (typeof topLevel === 'boolean') {
    return topLevel
  }

  const nestedStreaming = config.streaming
  if (nestedStreaming && typeof nestedStreaming === 'object' && !Array.isArray(nestedStreaming)) {
    const nestedEnabled = (nestedStreaming as Record<string, unknown>).enabled
    if (typeof nestedEnabled === 'boolean') {
      return nestedEnabled
    }
  }

  return true
}
