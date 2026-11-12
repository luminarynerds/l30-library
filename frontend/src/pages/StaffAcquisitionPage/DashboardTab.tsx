/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import AcquisitionDashboard from "../../components/acquisition/AcquisitionDashboard"
import AcquisitionErrorBoundary from "../../components/acquisition/AcquisitionErrorBoundary"
import { formatMoney } from "./types"

interface DashboardTabProps {
  token: string
  onNavigateTab: (tab: string) => void
}

export default function DashboardTab({ token, onNavigateTab }: DashboardTabProps) {
  return (
    <AcquisitionErrorBoundary fallbackMessage="Failed to load dashboard">
      <AcquisitionDashboard
        token={token}
        formatMoney={formatMoney}
        onNavigateTab={onNavigateTab}
      />
    </AcquisitionErrorBoundary>
  )
}
