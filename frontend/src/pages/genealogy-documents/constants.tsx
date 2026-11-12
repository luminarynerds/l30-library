/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { FileText, FileImage, Scroll, BookOpen } from 'lucide-react'

export const DOCUMENT_TYPES = [
  'birth_certificate', 'death_certificate', 'marriage_certificate', 'divorce_record',
  'census_record', 'immigration_record', 'emigration_record', 'naturalization_record',
  'military_record', 'draft_registration', 'pension_record', 'land_record',
  'probate_record', 'will', 'photograph', 'letter', 'diary',
  'newspaper_clipping', 'obituary', 'church_record', 'school_record',
  'medical_record', 'passport', 'other',
]

export const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-earth-100 text-earth-600 dark:bg-earth-700 dark:text-earth-300',
  processing: 'bg-earth-100 text-lsc-rose dark:bg-earth-800/30 dark:text-lsc-rose-light',
  ocr_complete: 'bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300',
  verified: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  needs_review: 'bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-300',
  error: 'bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-300',
}

const DOC_TYPE_ICONS: Record<string, React.ReactNode> = {
  photograph: <FileImage className="w-5 h-5 text-category-500" />,
  letter: <Scroll className="w-5 h-5 text-status-warning-500" />,
  diary: <BookOpen className="w-5 h-5 text-status-success-500" />,
}

export function getDocIcon(docType: string) {
  return DOC_TYPE_ICONS[docType] || <FileText className="w-5 h-5 text-earth-600" />
}
