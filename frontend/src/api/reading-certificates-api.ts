/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from "@/lib/api-client"

export interface ReadingCertificate {
  id: number
  certificate_code: string
  registration_id: number
  user_id: number
  title: string
  issued_to: string
  program_name: string
  completion_date: string
  status: "draft" | "generated" | "verified" | "emailed" | "revoked"
  created_at: string
  verified_at: string | null
  verified_by_id: number | null
  emailed_at: string | null
  pdf_url: string | null
}

export interface PaginatedCertificatesResponse {
  items: ReadingCertificate[]
  total: number
  limit: number
  offset: number
}

export async function getMyReadingCertificates(
  limit = 50,
  offset = 0
): Promise<PaginatedCertificatesResponse> {
  return fetchApi<PaginatedCertificatesResponse>(
    "/reading/certificates/my/certificates",
    { params: { limit, offset } }
  )
}
