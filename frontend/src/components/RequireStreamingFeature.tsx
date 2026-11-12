/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ReactNode } from 'react'
import { useOrganizationFeatures } from '../contexts/OrganizationFeaturesContext'
import { isStreamingEnabled } from '@/utils/streamingFeature'
import FeatureDisabledNotice from './FeatureDisabledNotice'

interface RequireStreamingFeatureProps {
  children: ReactNode
}

export default function RequireStreamingFeature({
  children,
}: RequireStreamingFeatureProps) {
  const { features, loading } = useOrganizationFeatures()

  if (loading) {
    return <>{children}</>
  }

  // When streaming is off, render an in-place "turned off" notice instead of
  // a bare 404 or redirect.
  if (!isStreamingEnabled(features)) {
    return <FeatureDisabledNotice feature="streaming_enabled" />
  }

  return <>{children}</>
}
