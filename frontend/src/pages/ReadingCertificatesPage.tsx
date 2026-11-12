/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from "@tanstack/react-query"
import { Award, Printer, BookOpen, Calendar } from "lucide-react"
import { useAuth } from "@/contexts/AuthContext"
import { useOrganizationFeatures } from "@/contexts/OrganizationFeaturesContext"
import { getMyReadingCertificates, type ReadingCertificate } from "@/api/reading-certificates-api"
import StandardPageLayout from "@/components/StandardPageLayout"
import { parseDate } from "@/utils/format-utils"
import { getCurrentLocale } from '@/i18n'

function CertificateCard({ cert }: { cert: ReadingCertificate }) {
  const handlePrint = () => {
    const printWindow = window.open("", "_blank")
    if (!printWindow) return
    const completionDate = parseDate(cert.completion_date)?.toLocaleDateString(getCurrentLocale(), {
      year: "numeric", month: "long", day: "numeric",
    }) ?? "-"
    printWindow.document.write([
      "<!DOCTYPE html><html><head><title>Certificate</title>",
      "<style>",
      "body{font-family:Georgia,serif;text-align:center;padding:60px 40px}",
      ".border{border:3px double #b45309;padding:40px;margin:20px}",
      "h1{font-size:28px;color:#92400e;margin:0 0 8px}",
      "h2{font-size:20px;color:#78350f;margin:0 0 24px;font-weight:normal}",
      ".name{font-size:24px;font-weight:bold;margin:16px 0}",
      ".detail{font-size:14px;color:#666;margin:4px 0}",
      ".code{font-family:monospace;font-size:12px;color:#999;margin-top:24px}",
      "</style></head><body><div class=\"border\">",
      "<h1>Certificate of Achievement</h1>",
      "<h2>" + cert.program_name + "</h2>",
      "<p class=\"detail\">Awarded to</p>",
      "<p class=\"name\">" + cert.issued_to + "</p>",
      "<p class=\"detail\">" + cert.title + "</p>",
      "<p class=\"detail\">Completed " + completionDate + "</p>",
      "<p class=\"code\">Certificate #" + cert.certificate_code + "</p>",
      "</div></body></html>",
    ].join(""))
    printWindow.document.close()
    printWindow.print()
  }

  const statusColors: Record<string, string> = {
    verified: "bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300",
    generated: "bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-300",
    emailed: "bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-300",
    draft: "bg-earth-100 text-earth-600 dark:bg-earth-700 dark:text-earth-300",
    revoked: "bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300",
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border-2 border-lsc-rose/20 dark:border-lsc-rose/30 shadow-sm hover:shadow-md transition-shadow">
      <div className="h-2 bg-gradient-to-r from-lsc-rose to-status-warning-500 rounded-t-[10px]" />
      <div className="p-5">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-full bg-lsc-rose/10 dark:bg-lsc-rose/20 flex items-center justify-center flex-shrink-0">
            <Award className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream truncate">
              {cert.program_name}
            </h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
              {cert.title}
            </p>
          </div>
          <span className={`text-xs font-medium px-2 py-1 rounded-full flex-shrink-0 ${statusColors[cert.status] || statusColors.draft}`}>
            {cert.status}
          </span>
        </div>
        <div className="mt-4 flex items-center gap-4 text-sm text-earth-600 dark:text-earth-400">
          <span className="flex items-center gap-1.5">
            <BookOpen className="w-4 h-4" aria-hidden="true" />
            {cert.issued_to}
          </span>
          <span className="flex items-center gap-1.5">
            <Calendar className="w-4 h-4" aria-hidden="true" />
            {parseDate(cert.completion_date)?.toLocaleDateString() ?? "-"}
          </span>
        </div>
        <div className="mt-3 pt-3 border-t border-earth-100 dark:border-earth-700 flex items-center justify-between">
          <span className="text-xs font-mono text-earth-600 dark:text-earth-500">
            #{cert.certificate_code}
          </span>
          <button
            onClick={handlePrint}
            className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-200 dark:hover:bg-earth-600 transition-colors min-h-[44px]"
            aria-label={`Print certificate for ${cert.program_name}`}
          >
            <Printer className="w-4 h-4" aria-hidden="true" />
            Print
          </button>
        </div>
      </div>
    </div>
  )
}

export default function ReadingCertificatesPage(): React.ReactElement {
  const { user } = useAuth()
  const { isFeatureEnabled } = useOrganizationFeatures()
  const gamificationEnabled = isFeatureEnabled("gamification_enabled")

  const { data, isLoading } = useQuery({
    queryKey: ["reading", "certificates", "mine"],
    queryFn: () => getMyReadingCertificates(),
    enabled: !!user && gamificationEnabled,
  })

  const certificates = data?.items ?? []

  if (!gamificationEnabled) {
    return (
      <StandardPageLayout title="Reading Certificates" icon={Award}>
        <div className="text-center py-16">
          <Award className="w-12 h-12 text-earth-300 dark:text-earth-600 mx-auto mb-4" aria-hidden="true" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-lg">
            Reading certificates are not currently available.
          </p>
        </div>
      </StandardPageLayout>
    )
  }

  return (
    <StandardPageLayout
      title="Reading Certificates"
      subtitle="Certificates earned from completing reading programs and challenges."
      icon={Award}
      isLoading={isLoading}
      isEmpty={!isLoading && certificates.length === 0}
      emptyMessage="No certificates earned yet. Complete a reading program to earn your first certificate!"
      emptyAction={{ label: "Browse Reading Programs", href: "/programs" }}
    >
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {certificates.map((cert) => (
          <CertificateCard key={cert.id} cert={cert} />
        ))}
      </div>
    </StandardPageLayout>
  )
}
