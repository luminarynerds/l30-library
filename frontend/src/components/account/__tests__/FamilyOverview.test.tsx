/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Tests for FamilyOverview component
 */

import { render as rtlRender, screen, waitFor, fireEvent, type RenderOptions } from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';
import { I18nProvider } from '@/i18n/I18nContext';
import { BrandingProvider } from '@/contexts/BrandingContext';
import { FamilyOverview } from '../FamilyOverview';

// FamilyOverview calls useTranslation(), which now requires I18nProvider
// (and I18nProvider itself requires BrandingProvider).
function render(ui: ReactElement, options?: RenderOptions) {
  return rtlRender(ui, {
    wrapper: ({ children }: { children: ReactNode }) => (
      <BrandingProvider>
        <I18nProvider>{children}</I18nProvider>
      </BrandingProvider>
    ),
    ...options,
  });
}

// Mock fetch
global.fetch = vi.fn();

// Minimal fake Response -- these tests only ever read `.ok` and `.json()`.
// vi.mocked(global.fetch) types its resolved value as a real `Response`,
// which the plain `{ ok, json }` object literals don't satisfy structurally.
function fakeResponse<T>(ok: boolean, data: T): Response {
  return { ok, json: async () => data } as Response
}

describe('FamilyOverview', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    vi.mocked(global.fetch).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(<FamilyOverview />);
    expect(screen.getByText(/loading family information/i)).toBeInTheDocument();
  });

  it('renders household data when loaded', async () => {
    const mockData = {
      viewing_as_user_id: 1,
      viewing_as_name: 'John Doe',
      relationship: 'parent',
      household_id: 1,
      household_members: [
        {
          id: 1,
          first_name: 'John',
          last_name: 'Doe',
          email: 'john@example.com',
          relationship: 'parent',
          link_status: 'approved',
          linked_at: '2024-01-01',
        },
        {
          id: 2,
          first_name: 'Jane',
          last_name: 'Doe',
          email: 'jane@example.com',
          relationship: 'child',
          link_status: 'approved',
          linked_at: '2024-01-02',
        },
      ],
      pending_requests: [],
      holds: [],
      checkouts: [],
      fines: [],
      total_holds: 0,
      total_checkouts: 0,
      total_fines_amount: 0,
    };

    vi.mocked(global.fetch).mockResolvedValueOnce(fakeResponse(true, mockData));

    render(<FamilyOverview />);

    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText('Jane Doe')).toBeInTheDocument();
    });
  });

  it('renders error state on fetch failure', async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(fakeResponse(false, { detail: 'Error loading data' }));

    render(<FamilyOverview />);

    await waitFor(() => {
      expect(screen.getByText(/failed to load household data/i)).toBeInTheDocument();
    });
  });

  it('shows link request form for children', async () => {
    const mockData = {
      viewing_as_user_id: 2,
      viewing_as_name: 'Jane Doe',
      relationship: 'self',
      household_id: null,
      household_members: [],
      pending_requests: [],
      holds: [],
      checkouts: [],
      fines: [],
      total_holds: 0,
      total_checkouts: 0,
      total_fines_amount: 0,
    };

    vi.mocked(global.fetch).mockResolvedValueOnce(fakeResponse(true, mockData));

    render(<FamilyOverview />);

    await waitFor(() => {
      expect(screen.getByText(/Get Started with Family Linking/i)).toBeInTheDocument();
      expect(screen.getByText(/Request Family Link/i)).toBeInTheDocument();
    });
  });

  it('displays aggregated household stats when linked', async () => {
    const mockData = {
      viewing_as_user_id: 1,
      viewing_as_name: 'John Doe',
      relationship: 'parent',
      household_id: 1,
      household_members: [
        {
          id: 1,
          first_name: 'John',
          last_name: 'Doe',
          email: 'john@example.com',
          relationship: 'parent',
          link_status: 'approved',
        },
        {
          id: 2,
          first_name: 'Jane',
          last_name: 'Doe',
          email: 'jane@example.com',
          relationship: 'child',
          link_status: 'approved',
        },
      ],
      pending_requests: [],
      holds: [],
      checkouts: [],
      fines: [],
      total_holds: 3,
      total_checkouts: 5,
      total_fines_amount: 12.5,
    };

    vi.mocked(global.fetch).mockResolvedValueOnce(fakeResponse(true, mockData));

    render(<FamilyOverview />);

    await waitFor(() => {
      expect(screen.getByText('3')).toBeInTheDocument(); // total holds
      expect(screen.getByText('5')).toBeInTheDocument(); // total checkouts
      expect(screen.getByText(/\$12\.50/)).toBeInTheDocument(); // total fines
    });
  });

  it('displays pending requests for parents', async () => {
    const mockData = {
      viewing_as_user_id: 1,
      viewing_as_name: 'John Doe',
      relationship: 'parent',
      household_id: 1,
      household_members: [],
      pending_requests: [
        {
          id: 1,
          requester_name: 'Jane Doe',
          message: 'Please link me',
          created_at: '2024-01-01T00:00:00Z',
          status: 'pending',
        },
      ],
      holds: [],
      checkouts: [],
      fines: [],
      total_holds: 0,
      total_checkouts: 0,
      total_fines_amount: 0,
    };

    vi.mocked(global.fetch).mockResolvedValueOnce(fakeResponse(true, mockData));

    render(<FamilyOverview />);

    await waitFor(() => {
      expect(screen.getByText(/Pending Link Requests/i)).toBeInTheDocument();
    });
  });

  it('calls onClose when close button is clicked', async () => {
    const mockData = {
      viewing_as_user_id: 1,
      viewing_as_name: 'John Doe',
      relationship: 'parent',
      household_id: 1,
      household_members: [],
      pending_requests: [],
      holds: [],
      checkouts: [],
      fines: [],
      total_holds: 0,
      total_checkouts: 0,
      total_fines_amount: 0,
    };

    vi.mocked(global.fetch).mockResolvedValueOnce(fakeResponse(true, mockData));

    const onClose = vi.fn();
    render(<FamilyOverview onClose={onClose} />);

    await waitFor(() => {
      fireEvent.click(screen.getByText('Close'));
      expect(onClose).toHaveBeenCalled();
    });
  });
});
