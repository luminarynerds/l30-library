/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ReactNode } from 'react'
import { useOrganizationFeatures } from '../contexts/OrganizationFeaturesContext'
import FeatureDisabledNotice from './FeatureDisabledNotice'

interface RequireFeatureProps {
  children: ReactNode
  feature: string
}

export default function RequireFeature({
  children,
  feature,
}: RequireFeatureProps) {
  const { features, loading } = useOrganizationFeatures()

  // Render children optimistically while features are loading.
  // This avoids a blocking spinner that creates a visible loading waterfall
  // (Suspense skeleton → spinner → page skeletons). Children handle their own
  // loading states, and if the feature turns out disabled we redirect then.
  if (loading) {
    return <>{children}</>
  }

  // Check if the feature is enabled
  const featureValue = features?.[feature as keyof typeof features]
  const isEnabled = typeof featureValue === 'boolean' ? featureValue : false

  // When the feature is off, render an in-place "turned off" notice instead
  // of a bare 404 or redirect.
  if (!isEnabled) {
    return <FeatureDisabledNotice feature={feature} />
  }

  return <>{children}</>
}
