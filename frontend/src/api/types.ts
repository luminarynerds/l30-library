/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

// Shared types used across multiple domains
export interface MessageResponse {
  message: string
}
