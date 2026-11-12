/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from "vitest"
import "@testing-library/jest-dom"
import { render, screen } from "@testing-library/react"
import { axe } from "jest-axe"
import RichTextEditor from "../RichTextEditor"

describe("RichTextEditor", () => {
  it("renders an accessible toolbar and labelled editing region", () => {
    render(
      <RichTextEditor defaultValue="<p>Hello world</p>" onChange={vi.fn()} ariaLabel="Lesson content" />,
    )
    // Toolbar controls expose accessible names.
    expect(screen.getByLabelText("Bold")).toBeInTheDocument()
    expect(screen.getByLabelText("Italic")).toBeInTheDocument()
    expect(screen.getByLabelText("Heading 2")).toBeInTheDocument()
    expect(screen.getByLabelText("Bullet list")).toBeInTheDocument()
    expect(screen.getByLabelText("Add link")).toBeInTheDocument()
    expect(screen.getByLabelText("Insert callout")).toBeInTheDocument()
    // The editing surface is a named multiline textbox.
    expect(screen.getByRole("textbox", { name: "Lesson content" })).toBeInTheDocument()
  })

  it("hides the image button when no upload handler is provided", () => {
    const { rerender } = render(<RichTextEditor onChange={vi.fn()} ariaLabel="Body" />)
    expect(screen.queryByLabelText("Upload image")).not.toBeInTheDocument()

    rerender(<RichTextEditor onChange={vi.fn()} ariaLabel="Body" onImageUpload={vi.fn()} />)
    expect(screen.getByLabelText("Upload image")).toBeInTheDocument()
  })

  it("has no axe violations", async () => {
    const { container } = render(
      <RichTextEditor defaultValue="<p>Some content</p>" onChange={vi.fn()} ariaLabel="Content" />,
    )
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
