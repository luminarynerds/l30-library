/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo, useRef, useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { Upload, X, FileText, AlertTriangle, Loader2 } from "lucide-react"
import { Modal } from "../ui/Modal"
import { useTranslation } from "@/i18n"
import {
  importBookClubMembers,
  type MemberImportResponse,
  type MemberImportRowResult,
  type MemberImportRowStatus,
} from "@/api/domains/content/book-clubs-api"

const MAX_ROWS = 500

type Step = "upload" | "configure" | "preview" | "confirm"

interface Props {
  clubId: number
  onClose: () => void
  /** Called after a real (non-dry-run) import so the parent can refetch. */
  onImported: () => void
}

const STATUS_BADGE: Record<MemberImportRowStatus, string> = {
  success:
    "bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300",
  duplicate:
    "bg-earth-100 text-earth-600 dark:bg-earth-800 dark:text-earth-400",
  not_found:
    "bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300",
  invalid_email:
    "bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300",
  invalid_role:
    "bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300",
  deactivated:
    "bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300",
  parse_error:
    "bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300",
}

function countCsvRows(text: string): number {
  const lines = text
    .split(/\r\n|\r|\n/)
    .filter((l) => l.trim().length > 0)
  return Math.max(0, lines.length - 1)
}

function ResultTable({
  rows,
  t,
}: {
  rows: MemberImportRowResult[]
  t: (k: string, p?: Record<string, unknown> | string) => string
}) {
  return (
    <div className="max-h-72 overflow-y-auto border border-lsc-border dark:border-earth-700 rounded-lg">
      <table className="w-full text-left text-sm">
        <thead className="bg-earth-50 dark:bg-earth-900 sticky top-0">
          <tr>
            <th className="px-3 py-2 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">
              {t("bookClubs.import.rowColumn")}
            </th>
            <th className="px-3 py-2 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">
              {t("bookClubs.import.emailColumn")}
            </th>
            <th className="px-3 py-2 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">
              {t("bookClubs.import.roleColumn")}
            </th>
            <th className="px-3 py-2 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">
              {t("bookClubs.import.statusColumn")}
            </th>
            <th className="px-3 py-2 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">
              {t("bookClubs.import.messageColumn")}
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr
              key={r.row}
              className="border-t border-earth-100 dark:border-earth-700"
            >
              <td className="px-3 py-2 text-earth-700 dark:text-earth-300">
                {r.row}
              </td>
              <td className="px-3 py-2 text-earth-700 dark:text-earth-300">
                {r.email ?? (r.patron_id != null ? `#${r.patron_id}` : "--")}
              </td>
              <td className="px-3 py-2 text-earth-700 dark:text-earth-300">
                {r.role ?? "--"}
              </td>
              <td className="px-3 py-2">
                <span
                  className={`text-xs font-medium px-2 py-1 rounded-full ${STATUS_BADGE[r.status]}`}
                >
                  {t(`bookClubs.import.status.${r.status}`)}
                </span>
              </td>
              <td className="px-3 py-2 text-earth-600 dark:text-earth-400">
                {r.message ?? "--"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function ImportMembersModal({ clubId, onClose, onImported }: Props) {
  const { t } = useTranslation()
  const [step, setStep] = useState<Step>("upload")
  const [file, setFile] = useState<File | null>(null)
  const [clientRowCount, setClientRowCount] = useState<number | null>(null)
  const [defaultRole, setDefaultRole] = useState("member")
  const [dryRun, setDryRun] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<MemberImportResponse | null>(null)
  const [didRealImport, setDidRealImport] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const overLimit =
    clientRowCount != null && clientRowCount > MAX_ROWS

  const mutation = useMutation({
    mutationFn: (vars: { dry: boolean }) =>
      importBookClubMembers(clubId, file as File, defaultRole, vars.dry),
    onSuccess: (data, vars) => {
      setResult(data)
      if (vars.dry) {
        setStep("preview")
      } else {
        setDidRealImport(true)
        setStep("confirm")
      }
    },
    onError: (err: unknown) => {
      setError(
        err instanceof Error
          ? err.message
          : t("bookClubs.import.genericError"),
      )
    },
  })

  async function handleFile(f: File | null) {
    setError(null)
    setResult(null)
    setFile(f)
    if (!f) {
      setClientRowCount(null)
      return
    }
    try {
      const text = await f.text()
      setClientRowCount(countCsvRows(text))
    } catch {
      setClientRowCount(null)
    }
  }

  function downloadErrorRows() {
    if (!result) return
    const bad = result.rows.filter((r) => r.status !== "success")
    const header = "row,email,patron_id,role,status,message"
    const lines = bad.map((r) =>
      [
        r.row,
        r.email ?? "",
        r.patron_id ?? "",
        r.role ?? "",
        r.status,
        (r.message ?? "").replace(/"/g, '""'),
      ]
        .map((v) => `"${String(v)}"`)
        .join(","),
    )
    const blob = new Blob([[header, ...lines].join("\n")], {
      type: "text/csv;charset=utf-8",
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `book-club-${clubId}-import-errors.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  function handleClose() {
    if (didRealImport) onImported()
    onClose()
  }

  const summary = useMemo(() => {
    if (!result) return null
    return t("bookClubs.import.resultSummary", {
      success: result.success_count,
      skipped: result.skipped_count,
      errors: result.error_count,
    })
  }, [result, t])

  return (
    <Modal
      isOpen={true}
      onClose={handleClose}
      title={t("bookClubs.import.title")}
      size="2xl"
    >
      <div className="space-y-4">
        {error && (
          <div
            role="alert"
            className="p-3 text-sm bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-700 dark:text-status-danger-300 rounded-lg"
          >
            {error}
          </div>
        )}

        {step === "upload" && (
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="w-full border-2 border-dashed border-lsc-border dark:border-earth-600 rounded-xl py-10 flex flex-col items-center gap-2 text-earth-600 dark:text-earth-400 hover:border-lsc-rose focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            >
              <Upload className="w-8 h-8" aria-hidden="true" />
              <span className="text-sm">{t("bookClubs.import.dropzone")}</span>
              <span className="text-xs">
                {t("bookClubs.import.dropzoneHint")}
              </span>
            </button>
            <input
              ref={fileInputRef}
              id="book-club-import-file"
              type="file"
              accept=".csv,text/csv"
              className="sr-only"
              aria-label={t("bookClubs.import.dropzone")}
              onChange={(e) =>
                handleFile(e.target.files?.[0] ?? null)
              }
            />

            {file && (
              <div className="flex items-center justify-between p-3 bg-earth-50 dark:bg-earth-900 rounded-lg">
                <span className="flex items-center gap-2 text-sm text-earth-700 dark:text-earth-300">
                  <FileText className="w-4 h-4" aria-hidden="true" />
                  {file.name}
                </span>
                <button
                  type="button"
                  onClick={() => handleFile(null)}
                  aria-label={t("bookClubs.import.removeFile")}
                  className="p-1 text-earth-600 hover:text-status-danger-600 focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}

            {clientRowCount != null && (
              <p
                className={`text-sm ${overLimit ? "text-status-danger-600 dark:text-status-danger-300" : "text-earth-600 dark:text-earth-400"}`}
              >
                {overLimit
                  ? t("bookClubs.import.clientRowWarn")
                  : t("bookClubs.import.clientRowCount", {
                      count: clientRowCount,
                    })}
              </p>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={handleClose}
                className="px-4 py-2 text-sm text-earth-600 dark:text-earth-400 hover:bg-earth-50 dark:hover:bg-earth-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              >
                {t("bookClubs.import.cancelButton")}
              </button>
              <button
                type="button"
                disabled={!file || overLimit}
                onClick={() => setStep("configure")}
                className="px-4 py-2 text-sm bg-lsc-rose text-white rounded-lg disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2"
              >
                {t("bookClubs.import.nextButton")}
              </button>
            </div>
          </div>
        )}

        {step === "configure" && (
          <div className="space-y-4">
            <div>
              <label
                htmlFor="book-club-import-role"
                className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"
              >
                {t("bookClubs.import.defaultRole")}
              </label>
              <select
                id="book-club-import-role"
                value={defaultRole}
                onChange={(e) => setDefaultRole(e.target.value)}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              >
                <option value="member">
                  {t("bookClubs.import.roleMember")}
                </option>
                <option value="facilitator">
                  {t("bookClubs.import.roleFacilitator")}
                </option>
                <option value="admin">
                  {t("bookClubs.import.roleAdmin")}
                </option>
              </select>
            </div>

            <label className="flex items-center gap-2 text-sm text-earth-700 dark:text-earth-300">
              <input
                type="checkbox"
                checked={dryRun}
                onChange={(e) => setDryRun(e.target.checked)}
                className="rounded border-lsc-border focus:ring-2 focus:ring-lsc-rose"
              />
              {t("bookClubs.import.dryRunToggle")}
            </label>

            <div className="flex justify-between gap-2 pt-2">
              <button
                type="button"
                onClick={() => setStep("upload")}
                className="px-4 py-2 text-sm text-earth-600 dark:text-earth-400 hover:bg-earth-50 dark:hover:bg-earth-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              >
                {t("bookClubs.import.backButton")}
              </button>
              <button
                type="button"
                disabled={mutation.isPending}
                onClick={() => mutation.mutate({ dry: dryRun })}
                className="px-4 py-2 text-sm bg-lsc-rose text-white rounded-lg disabled:opacity-50 inline-flex items-center gap-2 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2"
              >
                {mutation.isPending && (
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                )}
                {dryRun
                  ? t("bookClubs.import.submitDryRun")
                  : t("bookClubs.import.submitButton", {
                      count: clientRowCount ?? 0,
                    })}
              </button>
            </div>
          </div>
        )}

        {step === "preview" && result && (
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              {t("bookClubs.import.previewHeading", {
                count: result.total_rows,
              })}
            </h3>
            <p className="text-sm text-earth-600 dark:text-earth-400">
              {summary}
            </p>
            <ResultTable rows={result.rows} t={t} />
            <div className="flex justify-between gap-2 pt-2">
              <button
                type="button"
                onClick={() => setStep("configure")}
                className="px-4 py-2 text-sm text-earth-600 dark:text-earth-400 hover:bg-earth-50 dark:hover:bg-earth-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              >
                {t("bookClubs.import.backButton")}
              </button>
              <button
                type="button"
                disabled={mutation.isPending}
                onClick={() => mutation.mutate({ dry: false })}
                className="px-4 py-2 text-sm bg-lsc-rose text-white rounded-lg disabled:opacity-50 inline-flex items-center gap-2 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2"
              >
                {mutation.isPending && (
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                )}
                {t("bookClubs.import.submitButton", {
                  count: result.success_count,
                })}
              </button>
            </div>
          </div>
        )}

        {step === "confirm" && result && (
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              {t("bookClubs.import.resultHeading")}
            </h3>
            <p className="text-sm text-earth-600 dark:text-earth-400">
              {summary}
            </p>
            <ResultTable rows={result.rows} t={t} />
            <div className="flex justify-between gap-2 pt-2">
              {result.error_count > 0 ? (
                <button
                  type="button"
                  onClick={downloadErrorRows}
                  className="px-4 py-2 text-sm inline-flex items-center gap-2 text-status-warning-700 dark:text-status-warning-300 hover:bg-status-warning-50 dark:hover:bg-status-warning-900/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                >
                  <AlertTriangle className="w-4 h-4" aria-hidden="true" />
                  {t("bookClubs.import.downloadErrors")}
                </button>
              ) : (
                <span />
              )}
              <button
                type="button"
                onClick={handleClose}
                className="px-4 py-2 text-sm bg-lsc-rose text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2"
              >
                {t("bookClubs.import.closeButton")}
              </button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  )
}
