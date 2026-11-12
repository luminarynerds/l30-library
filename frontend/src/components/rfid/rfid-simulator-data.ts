/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { BarChart3, Cpu, Tag, AlertTriangle, RefreshCw, List } from "lucide-react"

export const TABS = [
  { id: "overview", label: "Overview", icon: BarChart3 },
  { id: "readers", label: "Simulated Readers", icon: Cpu },
  { id: "tags", label: "Tag Simulation", icon: Tag },
  { id: "security", label: "Security Alerts", icon: AlertTriangle },
  { id: "autoscan", label: "Auto-Scan", icon: RefreshCw },
  { id: "results", label: "Test Results", icon: List },
]
