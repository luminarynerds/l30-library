/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { beforeAll, describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { loadLanguage, getTranslation } from "@/i18n/translations"

// Mock the i18n hook so the component resolves real en.json keys.
vi.mock("@/i18n", async () => {
  const actual = await vi.importActual<typeof import("@/i18n")>("@/i18n")
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string, params?: Record<string, unknown> | string) =>
        typeof params === "string"
          ? getTranslation(key, "en", undefined, params)
          : getTranslation(key, "en", params),
      language: "en",
      isRTL: false,
    }),
  }
})

// Mock the API module.
const importBookClubMembers = vi.fn()
vi.mock("@/api/domains/content/book-clubs-api", () => ({
  importBookClubMembers: (...args: unknown[]) =>
    importBookClubMembers(...args),
}))

import { ImportMembersModal } from "./ImportMembersModal"

beforeAll(async () => {
  await loadLanguage("en")
})

beforeEach(() => {
  importBookClubMembers.mockReset()
})

function renderModal(props?: Partial<Parameters<typeof ImportMembersModal>[0]>) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  const onClose = vi.fn()
  const onImported = vi.fn()
  render(
    <QueryClientProvider client={qc}>
      <ImportMembersModal
        clubId={7}
        onClose={onClose}
        onImported={onImported}
        {...props}
      />
    </QueryClientProvider>,
  )
  return { onClose, onImported }
}

function makeCsvFile(rowCount: number): File {
  const rows = ["email,patron_id,role"]
  for (let i = 0; i < rowCount; i++) rows.push(`p${i}@x.local,,member`)
  return new File([rows.join("\n")], "members.csv", { type: "text/csv" })
}

describe("ImportMembersModal", () => {
  it("renders the upload step with the localized title", () => {
    renderModal()
    expect(
      screen.getByText("Import Members from CSV"),
    ).toBeInTheDocument()
    expect(
      screen.getByText("Drop a CSV file here or click to browse"),
    ).toBeInTheDocument()
  })

  it("shows a client-side row count after picking a file", async () => {
    const user = userEvent.setup()
    renderModal()
    const input = screen.getByLabelText(
      "Drop a CSV file here or click to browse",
    ) as HTMLInputElement
    await user.upload(input, makeCsvFile(3))
    await waitFor(() =>
      expect(screen.getByText("3 data rows detected")).toBeInTheDocument(),
    )
  })

  it("warns and blocks Next when the file exceeds 500 rows", async () => {
    const user = userEvent.setup()
    renderModal()
    const input = screen.getByLabelText(
      "Drop a CSV file here or click to browse",
    ) as HTMLInputElement
    await user.upload(input, makeCsvFile(501))
    await waitFor(() =>
      expect(
        screen.getByText(
          "This file has more than 500 rows. Trim it before importing.",
        ),
      ).toBeInTheDocument(),
    )
    const next = screen.getByRole("button", { name: "Next" })
    expect(next).toBeDisabled()
  })

  it("runs a dry-run preview and renders status badges", async () => {
    const user = userEvent.setup()
    importBookClubMembers.mockResolvedValueOnce({
      import_id: null,
      dry_run: true,
      total_rows: 2,
      success_count: 1,
      skipped_count: 1,
      error_count: 0,
      rows: [
        {
          row: 1,
          email: "a@x.local",
          patron_id: null,
          role: "member",
          status: "success",
          user_id: 10,
          message: null,
        },
        {
          row: 2,
          email: "dup@x.local",
          patron_id: null,
          role: "member",
          status: "duplicate",
          user_id: 11,
          message: "Already a member of this club.",
        },
      ],
    })
    renderModal()
    const input = screen.getByLabelText(
      "Drop a CSV file here or click to browse",
    ) as HTMLInputElement
    await user.upload(input, makeCsvFile(2))
    await user.click(screen.getByRole("button", { name: "Next" }))
    await user.click(
      screen.getByRole("button", { name: "Preview Import" }),
    )
    await waitFor(() =>
      expect(screen.getByText("Preview - 2 rows")).toBeInTheDocument(),
    )
    expect(screen.getByText("Added")).toBeInTheDocument()
    expect(screen.getByText("Already a member")).toBeInTheDocument()
    expect(importBookClubMembers).toHaveBeenCalledWith(
      7,
      expect.any(File),
      "member",
      true,
    )
  })

  it("confirms a real import and offers an error-row download", async () => {
    const user = userEvent.setup()
    importBookClubMembers
      .mockResolvedValueOnce({
        import_id: null,
        dry_run: true,
        total_rows: 1,
        success_count: 0,
        skipped_count: 0,
        error_count: 1,
        rows: [
          {
            row: 1,
            email: "bad",
            patron_id: null,
            role: "member",
            status: "invalid_email",
            user_id: null,
            message: "Email does not look valid",
          },
        ],
      })
      .mockResolvedValueOnce({
        import_id: "abc-123",
        dry_run: false,
        total_rows: 1,
        success_count: 0,
        skipped_count: 0,
        error_count: 1,
        rows: [
          {
            row: 1,
            email: "bad",
            patron_id: null,
            role: "member",
            status: "invalid_email",
            user_id: null,
            message: "Email does not look valid",
          },
        ],
      })
    const { onImported } = renderModal()
    const input = screen.getByLabelText(
      "Drop a CSV file here or click to browse",
    ) as HTMLInputElement
    await user.upload(input, makeCsvFile(1))
    await user.click(screen.getByRole("button", { name: "Next" }))
    await user.click(
      screen.getByRole("button", { name: "Preview Import" }),
    )
    await waitFor(() =>
      expect(screen.getByText("Preview - 1 rows")).toBeInTheDocument(),
    )
    // Confirm (real import)
    await user.click(
      screen.getByRole("button", { name: /Import 0 members/ }),
    )
    await waitFor(() =>
      expect(screen.getByText("Import complete")).toBeInTheDocument(),
    )
    expect(
      screen.getByRole("button", { name: "Download error rows as CSV" }),
    ).toBeInTheDocument()
    // Closing after a real import triggers parent refetch.
    await user.click(screen.getByRole("button", { name: "Close" }))
    expect(onImported).toHaveBeenCalledTimes(1)
  })
})
