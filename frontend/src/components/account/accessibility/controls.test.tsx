/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="vitest/globals" />
/// <reference types="@testing-library/jest-dom" />
import { render } from "@testing-library/react";
import { screen, fireEvent } from "@testing-library/dom";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import { SettingToggle } from "./controls";

expect.extend(toHaveNoViolations);

describe("SettingToggle hit area", () => {
  it("toggles when the title text is clicked (not just the pill)", () => {
    const onChange = vi.fn();
    render(
      <SettingToggle
        label="Dyslexia-Friendly Font"
        description="Switches to Atkinson Hyperlegible."
        checked={false}
        onChange={onChange}
      />
    );
    fireEvent.click(screen.getByText("Dyslexia-Friendly Font"));
    expect(onChange).toHaveBeenCalledWith(true);
  });

  it("toggles when the description text is clicked", () => {
    const onChange = vi.fn();
    render(
      <SettingToggle
        label="High Contrast"
        description="Increase the contrast between text and background."
        checked={true}
        onChange={onChange}
      />
    );
    fireEvent.click(
      screen.getByText("Increase the contrast between text and background.")
    );
    expect(onChange).toHaveBeenCalledWith(false);
  });

  it("toggles with keyboard (Space) when focused", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <SettingToggle
        label="Reduce Motion"
        description="Minimize animations."
        checked={false}
        onChange={onChange}
      />
    );
    const sw = screen.getByRole("switch", { name: "Reduce Motion" });
    sw.focus();
    await user.keyboard(" ");
    expect(onChange).toHaveBeenCalledWith(true);
  });

  it("does not toggle when disabled", () => {
    const onChange = vi.fn();
    render(
      <SettingToggle
        label="Focus Mode"
        description="Hide distractions."
        checked={false}
        onChange={onChange}
        disabled
      />
    );
    fireEvent.click(screen.getByText("Focus Mode"));
    expect(onChange).not.toHaveBeenCalled();
  });

  it("exposes a single switch role with the accessible name", () => {
    const onChange = vi.fn();
    render(
      <SettingToggle
        label="Plain Language"
        description="Simplify wording."
        checked={false}
        onChange={onChange}
      />
    );
    const switches = screen.getAllByRole("switch");
    expect(switches).toHaveLength(1);
    expect(switches[0]).toHaveAttribute("aria-checked", "false");
    expect(switches[0]).toHaveAccessibleName("Plain Language");
  });

  it("has no axe violations", async () => {
    const { container } = render(
      <SettingToggle
        label="Muted Colors"
        description="Reduce color intensity."
        checked={false}
        onChange={vi.fn()}
      />
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
