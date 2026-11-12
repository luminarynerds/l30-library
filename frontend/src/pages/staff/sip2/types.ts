/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { SIP2Terminal } from "@/api/sip2-api"
import { getCurrentLocale } from '@/i18n'

export type ViewMode = "terminals" | "transactions"
export type ModalType = "terminal" | "detail" | null

export interface TerminalFormData {
  terminal_id: string
  name: string
  description: string
  location: string
  institution_id: string
  password: string
  is_active: boolean
  allow_checkout: boolean
  allow_checkin: boolean
  allow_renewal: boolean
  allow_patron_info: boolean
}

export const EMPTY_TERMINAL_FORM: TerminalFormData = {
  terminal_id: "",
  name: "",
  description: "",
  location: "",
  institution_id: "",
  password: "",
  is_active: true,
  allow_checkout: true,
  allow_checkin: true,
  allow_renewal: true,
  allow_patron_info: true,
}

export const PAGE_SIZE = 20

export function terminalToFormData(terminal: SIP2Terminal): TerminalFormData {
  return {
    terminal_id: terminal.terminal_id,
    name: terminal.name,
    description: terminal.description || "",
    location: terminal.location || "",
    institution_id: terminal.institution_id || "",
    password: "",
    is_active: terminal.is_active,
    allow_checkout: terminal.allow_checkout,
    allow_checkin: terminal.allow_checkin,
    allow_renewal: terminal.allow_renewal,
    allow_patron_info: terminal.allow_patron_info,
  }
}

export function formatDate(dateStr: string | null) {
  if (!dateStr) return "Never"
  return new Date(dateStr).toLocaleString(getCurrentLocale(), {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}
