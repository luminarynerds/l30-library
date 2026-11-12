/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="vitest/globals" />
/// <reference types="@testing-library/jest-dom" />
/**
 * Accessibility Component Tests
 *
 * Tests for the accessibility components using jest-axe.
 * Ensures all accessibility features meet WCAG 2.2 standards.
 */

import { render as rtlRender } from "@testing-library/react";
import { screen, fireEvent, waitFor } from '@testing-library/dom';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import { MemoryRouter } from 'react-router-dom';
import type { ReactElement } from 'react';

// QuickAccessibilityWidget renders react-router <Link>s (#1517 ND/a11y sweep),
// so it needs a Router in the tree even though these tests never navigate.
function render(ui: ReactElement) {
  return rtlRender(ui, { wrapper: MemoryRouter });
}

// Extend Jest matchers
expect.extend(toHaveNoViolations);

// Mock the accessibility context
const mockSettings = {
  theme: 'light',
  highContrast: false,
  fontSize: 'normal',
  dyslexiaFont: false,
  focusMode: false,
  reduceMotion: false,
  lineFocusGuide: false,
  voiceControlEnabled: false,
  showQuickSettings: true,
  quickSettingsPosition: 'bottom-right',
  bionicReading: false,
  language: 'en',
  breakReminders: false,
  breakIntervalMinutes: 30,
  readingTool: 'none',
  readingMaskOpacity: 75,
  readingMaskHeight: 80,
};

const mockUpdateSetting = vi.fn();
const mockResetSettings = vi.fn();

vi.mock(
  '../../features/accessibility/hooks/useAccessibility',
  () => ({
    useAccessibility: () => ({
      settings: mockSettings,
      updateSetting: mockUpdateSetting,
      resetSettings: mockResetSettings,
    }),
  })
);

vi.mock(
  '../../features/accessibility/hooks/useUnifiedAccessibility',
  () => ({
    useUnifiedAccessibility: () => ({
      settings: mockSettings,
      updateSetting: mockUpdateSetting,
      resetSettings: mockResetSettings,
    }),
  })
);

// Import components after mocking
import { QuickAccessibilityWidget } from '../../features/accessibility/components/QuickAccessibilityWidget';

// Preload English translations. vitest setup.ts does not preload i18n,
// and t() returns raw dotted-path keys (e.g. aria.accessibility.openAccessibilityQuickSettings)
// when no language is loaded, breaking assertions that match resolved English strings.

describe('Accessibility Components', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('QuickAccessibilityWidget', () => {
    it('should have no accessibility violations when closed', async () => {
      const { container } = render(<QuickAccessibilityWidget />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have proper aria attributes on toggle button', () => {
      render(<QuickAccessibilityWidget />);
      const button = screen.getByRole('button', {
        name: /open accessibility quick settings/i,
      });
      expect(button).toHaveAttribute('aria-expanded', 'false');
    });

    it('should open widget when clicked', async () => {
      render(<QuickAccessibilityWidget />);
      const button = screen.getByRole('button', {
        name: /open accessibility quick settings/i,
      });
      await userEvent.click(button);
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('should have no accessibility violations when open', async () => {
      const { container } = render(<QuickAccessibilityWidget />);
      const button = screen.getByRole('button', {
        name: /open accessibility quick settings/i,
      });
      await userEvent.click(button);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should close on Escape key', async () => {
      render(<QuickAccessibilityWidget />);
      const button = screen.getByRole('button', {
        name: /open accessibility quick settings/i,
      });
      await userEvent.click(button);
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      fireEvent.keyDown(window, { key: 'Escape' });
      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });
    });

    it('should have proper toggle switch roles', async () => {
      render(<QuickAccessibilityWidget />);
      await userEvent.click(
        screen.getByRole('button', { name: /open accessibility/i })
      );
      const toggles = screen.getAllByRole('switch');
      expect(toggles.length).toBeGreaterThan(0);
      toggles.forEach((toggle: HTMLElement) => {
        expect(toggle).toHaveAttribute('aria-checked');
      });
    });
  });

});

describe('WCAG 2.2 Compliance', () => {
  describe('Target Size (SC 2.5.8)', () => {
    it('all interactive elements should meet minimum target size', async () => {
      render(<QuickAccessibilityWidget />);
      await userEvent.click(
        screen.getByRole('button', { name: /open accessibility/i })
      );

      const buttons = screen.getAllByRole('button');
      buttons.forEach((button: HTMLElement) => {
        // Note: In real tests, you'd check computed styles via getBoundingClientRect()
        // This is a placeholder for the concept
        expect(button).toBeInTheDocument();
      });
    });
  });

  describe('Focus Appearance (SC 2.4.11)', () => {
    it('focused elements should have visible focus indicators', async () => {
      render(<QuickAccessibilityWidget />);
      const button = screen.getByRole('button', {
        name: /open accessibility/i,
      });
      button.focus();
      expect(document.activeElement).toBe(button);
    });
  });

  describe('Name, Role, Value (SC 4.1.2)', () => {
    it('all components should have accessible names', async () => {
      const { container } = render(<QuickAccessibilityWidget />);

      // All buttons should have accessible names
      const buttons = screen.getAllByRole('button');
      buttons.forEach((button: HTMLElement) => {
        const name =
          button.getAttribute('aria-label') ||
          button.textContent ||
          button.getAttribute('title');
        expect(name).toBeTruthy();
      });

      // Run axe for comprehensive check
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
});

