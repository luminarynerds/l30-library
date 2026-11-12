/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// ==================== Legacy API Re-export ====================
// This file maintains backward compatibility with existing imports from services/api.ts
// All exports are now reorganized in /api/ with domain-based organization
//
// MIGRATION: Prefer importing directly from '@/api' instead of '@/api/api'
// - Old: import { api, someFunction } from '@/services/api'
// - New: import { api, someFunction } from '@/api'

export * from './index'
export { api } from '@/lib/api-client'
export { default } from '@/lib/api-client'
