/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Timeout and Delay Constants
 *
 * Centralized timeout/delay values used across the frontend.
 * All values are in milliseconds.
 */

// ==================== Toast / Notification Durations ====================

/** Default duration for toast notifications (5 seconds) */
export const TOAST_DURATION_MS = 5000

/** Duration to show success feedback before clearing (3 seconds) */
export const SUCCESS_FEEDBACK_DURATION_MS = 3000

/** Duration to show "copied to clipboard" feedback (2 seconds) */
export const COPY_FEEDBACK_DURATION_MS = 2000

/** Duration for brief visual feedback indicators like retry/save status (2 seconds) */
export const BRIEF_FEEDBACK_DURATION_MS = 2000

// ==================== Polling Intervals ====================

/** Default polling interval for print queue and similar (5 seconds) */
export const POLL_INTERVAL_MS = 5000

/** Default auto-refresh interval for dashboards and stats (30 seconds) */
export const DASHBOARD_REFRESH_INTERVAL_MS = 30000

// ==================== WebSocket ====================

/** Maximum WebSocket reconnection delay (30 seconds) */
export const WS_MAX_RECONNECT_DELAY_MS = 30000

/** WebSocket ping/keepalive interval (30 seconds) */
export const WS_PING_INTERVAL_MS = 30000

/** WebSocket pong response timeout (5 seconds) */
export const WS_PONG_TIMEOUT_MS = 5000

/** Initial WebSocket reconnection delay (1 second) */
export const WS_INITIAL_RECONNECT_DELAY_MS = 1000

// ==================== Auto-Save ====================

/** Default debounce delay for auto-save features (2 seconds) */
export const AUTOSAVE_DEBOUNCE_MS = 2000

/** Default auto-save interval to persistent storage (30 seconds) */
export const AUTOSAVE_INTERVAL_MS = 30000
