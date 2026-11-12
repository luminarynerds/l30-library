/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export * from './legal-api'
export * from './genealogy-api'
export * from './genealogy-research-api'
export * from './knowledge-base-api'
export * from './guide-feedback-api'
export * from './sparql-api'
export * from './bankruptcy-api'

// ==================== Conflict Resolutions ====================
// recordGuideHelpful: legal-api vs guide-feedback-api → prefer guide-feedback-api (specialized)
export { recordGuideHelpful } from './guide-feedback-api'
