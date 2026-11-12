/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect } from 'react'
import { AccessibilitySettingsSection } from '../components/account/AccessibilitySettingsSection'
import PageContainer from '@/components/layout/PageContainer'

export default function AccessibilitySettingsPage(): JSX.Element {
  useEffect(() => {
    document.title = 'Accessibility Settings'
  }, [])

  return (
    <PageContainer width="read" className="py-8">
      <h1 className="sr-only">Accessibility Settings</h1>
      <AccessibilitySettingsSection />
    </PageContainer>
  )
}
