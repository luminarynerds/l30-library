/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor, userEvent } from "@/__tests__/utils/test-utils"
import ImageAltModal from "../ImageAltModal"

// FocusTrap doesn't play nicely with happy-dom; stub it so the input mounts focusable.
vi.mock("focus-trap-react", () => ({
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

describe("ImageAltModal", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders the alt-text input and decorative toggle when open", () => {
    render(
      <ImageAltModal
        isOpen={true}
        imageUrl="/test.png"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    )
    expect(screen.getByRole("dialog")).toBeInTheDocument()
    expect(screen.getByRole("textbox", { name: /alt text/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/decorative image/i)).toBeInTheDocument()
  })

  it("renders nothing when isOpen is false", () => {
    render(
      <ImageAltModal
        isOpen={false}
        imageUrl="/test.png"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    )
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })

  it("requires alt text when decorative is off -- does not call onConfirm with empty", async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()
    render(
      <ImageAltModal
        isOpen={true}
        imageUrl="/test.png"
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />,
    )
    const submit = screen.getByRole("button", { name: /insert image/i })
    // Button should be disabled while alt is empty and not decorative
    expect(submit).toBeDisabled()
    await user.click(submit)
    expect(onConfirm).not.toHaveBeenCalled()
  })

  it("submits with the alt text when filled in", async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()
    render(
      <ImageAltModal
        isOpen={true}
        imageUrl="/test.png"
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />,
    )
    const input = screen.getByRole("textbox", { name: /alt text/i })
    await user.type(input, "Kids reading at the library")
    const submit = screen.getByRole("button", { name: /insert image/i })
    expect(submit).not.toBeDisabled()
    await user.click(submit)
    expect(onConfirm).toHaveBeenCalledWith({
      alt: "Kids reading at the library",
      decorative: false,
    })
  })

  it("decorative toggle disables alt requirement and emits empty alt with decorative=true", async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()
    render(
      <ImageAltModal
        isOpen={true}
        imageUrl="/test.png"
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />,
    )
    const checkbox = screen.getByLabelText(/decorative image/i)
    await user.click(checkbox)
    // After toggling decorative, alt input should be disabled
    expect(screen.getByRole("textbox", { name: /alt text/i })).toBeDisabled()
    const submit = screen.getByRole("button", { name: /insert image/i })
    expect(submit).not.toBeDisabled()
    await user.click(submit)
    expect(onConfirm).toHaveBeenCalledWith({ alt: "", decorative: true })
  })

  it("calls onCancel when cancel button is clicked", async () => {
    const user = userEvent.setup()
    const onCancel = vi.fn()
    render(
      <ImageAltModal
        isOpen={true}
        imageUrl="/test.png"
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />,
    )
    await user.click(screen.getByRole("button", { name: /cancel/i }))
    expect(onCancel).toHaveBeenCalled()
  })

  it("ESC closes the modal via onCancel", async () => {
    const user = userEvent.setup()
    const onCancel = vi.fn()
    render(
      <ImageAltModal
        isOpen={true}
        imageUrl="/test.png"
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />,
    )
    // Focus the alt input so the synthetic onKeyDown handler in Modal receives the event
    const altInput = screen.getByRole("textbox", { name: /alt text/i })
    altInput.focus()
    await user.keyboard("{Escape}")
    expect(onCancel).toHaveBeenCalled()
  })

  it("pre-fills the alt input with initialAlt", () => {
    render(
      <ImageAltModal
        isOpen={true}
        imageUrl="/test.png"
        initialAlt="Suggested description"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    )
    const input = screen.getByRole("textbox", { name: /alt text/i }) as HTMLInputElement
    expect(input.value).toBe("Suggested description")
  })

  it("focuses the alt input when the modal opens (focus trap entry)", async () => {
    render(
      <ImageAltModal
        isOpen={true}
        imageUrl="/test.png"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    )
    const input = screen.getByRole("textbox", { name: /alt text/i })
    // useEffect-driven focus runs after a short timer
    await waitFor(() => expect(input).toHaveFocus(), { timeout: 200 })
  })

  it("marks the dialog with aria-modal and a labelled title", () => {
    render(
      <ImageAltModal
        isOpen={true}
        imageUrl="/test.png"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    )
    const dialog = screen.getByRole("dialog")
    expect(dialog).toHaveAttribute("aria-modal", "true")
    expect(screen.getByText(/^image alt text$/i)).toBeInTheDocument()
  })
})
