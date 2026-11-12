/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { ReactElement, ReactNode } from 'react'
import RequireAuth from '../components/RequireAuth'
import RequireFeature from '../components/RequireFeature'
import RequireStreamingFeature from '../components/RequireStreamingFeature'
import RequirePlatform from '../components/RequirePlatform'

export function withAuth(element: ReactElement, requiredRoles?: string[]): ReactElement {
  return <RequireAuth {...(requiredRoles !== undefined ? { requiredRoles } : {})}>{element}</RequireAuth>
}

export function withFeature(feature: string, element: ReactNode): ReactElement {
  return <RequireFeature feature={feature}>{element}</RequireFeature>
}

export function withAuthFeature(
  feature: string,
  element: ReactElement,
  requiredRoles?: string[],
): ReactElement {
  return (
    <RequireAuth {...(requiredRoles !== undefined ? { requiredRoles } : {})}>
      <RequireFeature feature={feature}>{element}</RequireFeature>
    </RequireAuth>
  )
}


export function withStreamingFeature(element: ReactNode): ReactElement {
  return <RequireStreamingFeature>{element}</RequireStreamingFeature>
}

export function withPlatform(element: ReactNode): ReactElement {
  return <RequirePlatform>{element}</RequirePlatform>
}
