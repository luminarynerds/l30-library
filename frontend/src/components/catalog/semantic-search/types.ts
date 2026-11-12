/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export type SearchMode = 'hybrid' | 'semantic' | 'cross-collection' | 'hidden-gems' | 'similar-authors'

export interface SearchModeConfig {
  id: SearchMode
  label: string
  description: string
  icon: React.ElementType
  color: string
  activeColor: string
}
