/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export interface RepresentativeInfo {
  name: string
  office: string
  party: string
  level: 'federal' | 'state' | 'local'
  phones?: string[]
  emails?: string[]
  urls?: string[]
  photoUrl?: string
  channels?: { type: string; id: string }[]
}

export interface CivicLookupResponse {
  officials: RepresentativeInfo[]
  error?: string
  not_configured?: boolean
}

export interface ResourceItem {
  name: string
  description: string
  url: string
}
