/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { SearchBar } from "./SearchBar"

describe("hold-shelf SearchBar a11y", () => {
  it("labels the search input", () => {
    render(<SearchBar value="" onChange={() => {}} />)
    expect(
      screen.getByRole("textbox", { name: /search hold shelf/i })
    ).toBeInTheDocument()
  })

  it("labels the clear button when there is a value", () => {
    render(<SearchBar value="dunces" onChange={() => {}} />)
    expect(
      screen.getByRole("button", { name: /clear search/i })
    ).toBeInTheDocument()
  })
})
