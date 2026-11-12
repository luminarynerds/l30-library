/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Tests for LinkFamilyAccountForm component
 */

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event';
import { LinkFamilyAccountForm } from '../LinkFamilyAccountForm';
import { API_BASE } from '@/api/types'

// LinkFamilyAccountForm calls useTranslation() from the '@/i18n' barrel,
// which now requires I18nProvider (and I18nProvider itself requires
// BrandingProvider). Rather than wrap with the real providers -- which
// themselves call fetchApi (src/lib/api-client.ts, backed by the same
// global.fetch this file mocks raw) and would silently steal queued
// mockResolvedValueOnce() values meant for the component's own submit
// call -- mock the barrel directly, matching this file's existing
// "mock raw fetch" style.
vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: string) => fallback ?? key,
    language: 'en',
    setLanguage: vi.fn(),
    isRTL: false,
  }),
}))

// Mock fetch
global.fetch = vi.fn();

// Minimal fake Response -- these tests only ever read `.ok` and `.json()`.
// vi.mocked(global.fetch) types its resolved value as a real `Response`,
// which the plain `{ ok, json }` object literals don't satisfy structurally.
function fakeResponse<T>(ok: boolean, data: T): Response {
  return { ok, json: async () => data } as Response
}

describe('LinkFamilyAccountForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders form fields', () => {
    render(<LinkFamilyAccountForm />);

    expect(screen.getByLabelText(/Parent Email Address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Message/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Send Link Request/i })).toBeInTheDocument();
  });

  it('requires parent email', () => {
    render(<LinkFamilyAccountForm />);

    const submitButton = screen.getByRole('button', { name: /Send Link Request/i });
    expect(submitButton).toBeDisabled();
  });

  it('enables submit button when email is provided', async () => {
    const user = userEvent.setup();
    render(<LinkFamilyAccountForm />);

    const emailInput = screen.getByLabelText(/Parent Email Address/i);
    await user.type(emailInput, 'parent@example.com');

    const submitButton = screen.getByRole('button', { name: /Send Link Request/i });
    expect(submitButton).not.toBeDisabled();
  });

  it('submits form with email and optional message', async () => {
    const user = userEvent.setup();
    vi.mocked(global.fetch).mockResolvedValueOnce(fakeResponse(true, { id: 1, status: 'pending' }));

    render(<LinkFamilyAccountForm />);

    const emailInput = screen.getByLabelText(/Parent Email Address/i);
    const messageInput = screen.getByLabelText(/Message/i);
    const submitButton = screen.getByRole('button', { name: /Send Link Request/i });

    await user.type(emailInput, 'parent@example.com');
    await user.type(messageInput, 'Please link me');
    await user.click(submitButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        `${API_BASE}/households/link-request`,
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            parent_email: 'parent@example.com',
            message: 'Please link me',
          }),
        })
      );
    });
  });

  it('displays success message after successful submission', async () => {
    const user = userEvent.setup();
    vi.mocked(global.fetch).mockResolvedValueOnce(fakeResponse(true, { id: 1, status: 'pending' }));

    render(<LinkFamilyAccountForm />);

    const emailInput = screen.getByLabelText(/Parent Email Address/i);
    const submitButton = screen.getByRole('button', { name: /Send Link Request/i });

    await user.type(emailInput, 'parent@example.com');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Link Request Sent/i)).toBeInTheDocument();
    });
  });

  it('displays error message on submission failure', async () => {
    const user = userEvent.setup();
    vi.mocked(global.fetch).mockResolvedValueOnce(fakeResponse(false, { detail: 'Parent not found' }));

    render(<LinkFamilyAccountForm />);

    const emailInput = screen.getByLabelText(/Parent Email Address/i);
    const submitButton = screen.getByRole('button', { name: /Send Link Request/i });

    await user.type(emailInput, 'nonexistent@example.com');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Parent not found/i)).toBeInTheDocument();
    });
  });

  it('calls onSuccess callback after successful submission', async () => {
    const user = userEvent.setup();
    const onSuccess = vi.fn();

    vi.mocked(global.fetch).mockResolvedValueOnce(fakeResponse(true, { id: 1, status: 'pending' }));

    render(<LinkFamilyAccountForm onSuccess={onSuccess} />);

    const emailInput = screen.getByLabelText(/Parent Email Address/i);
    const submitButton = screen.getByRole('button', { name: /Send Link Request/i });

    await user.type(emailInput, 'parent@example.com');
    await user.click(submitButton);

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled();
    }, { timeout: 2000 });
  });

  it('calls onCancel callback when cancel button is clicked', async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();

    render(<LinkFamilyAccountForm onCancel={onCancel} />);

    const cancelButton = screen.getByRole('button', { name: /Cancel/i });
    await user.click(cancelButton);

    expect(onCancel).toHaveBeenCalled();
  });

  it('shows character count for message field', async () => {
    const user = userEvent.setup();
    render(<LinkFamilyAccountForm />);

    const messageInput = screen.getByLabelText(/Message/i);
    await user.type(messageInput, 'Test message');

    expect(screen.getByText(/12\/500 characters/)).toBeInTheDocument();
  });

  it('disables form during submission', async () => {
    const user = userEvent.setup();
    vi.mocked(global.fetch).mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 100))
    );

    render(<LinkFamilyAccountForm />);

    const emailInput = screen.getByLabelText(/Parent Email Address/i);
    const messageInput = screen.getByLabelText(/Message/i);
    const submitButton = screen.getByRole('button', { name: /Send Link Request/i });

    await user.type(emailInput, 'parent@example.com');
    await user.click(submitButton);

    expect(screen.getByText(/Sending/i)).toBeInTheDocument();
    expect(emailInput).toBeDisabled();
    expect(messageInput).toBeDisabled();
  });
});