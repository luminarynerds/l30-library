// SPDX-License-Identifier: AGPL-3.0-or-later
/// <reference types="vite/client" />
/// <reference types="@testing-library/jest-dom/vitest" />
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach, beforeAll, afterAll } from 'vitest';
import AdminGettingStartedChecklist from '../AdminGettingStartedChecklist';
import type { SetupProgress } from '@/hooks/useSetupProgress';

// Install a Map-backed localStorage shim so setItem/getItem round-trips work.
// The global setup.ts replaces window.localStorage with bare vi.fn() stubs that
// don't store anything; tests that need real persistence must install their own shim.
let originalLocalStorage: Storage;
let storage: Map<string, string>;

beforeAll(() => {
  originalLocalStorage = window.localStorage;
  storage = new Map<string, string>();
  const shim: Storage = {
    get length() { return storage.size; },
    clear: () => storage.clear(),
    getItem: (key: string) => (storage.has(key) ? storage.get(key)! : null),
    setItem: (key: string, value: string) => { storage.set(key, String(value)); },
    removeItem: (key: string) => { storage.delete(key); },
    key: (index: number) => Array.from(storage.keys())[index] ?? null,
  };
  Object.defineProperty(window, 'localStorage', { value: shim, configurable: true });
});

afterAll(() => {
  Object.defineProperty(window, 'localStorage', { value: originalLocalStorage, configurable: true });
});

const mockUse = vi.fn();
vi.mock('@/hooks/useSetupProgress', () => ({
  useSetupProgress: () => mockUse(),
}));

const progress = (over: Partial<SetupProgress> = {}): SetupProgress => ({
  library_system_id: 7,
  completed_count: 2,
  total: 6,
  all_complete: false,
  steps: [
    { id: 'add_team', title: 'Add your team', description: '', action: '/staff/admin/users', icon: 'users', completed: true, count: 3 },
    { id: 'set_policies', title: 'Set circulation policies', description: '', action: '/x', icon: 'scale', completed: true },
    { id: 'build_catalog', title: 'Build your catalog', description: '', action: '/x', icon: 'book', completed: false },
    { id: 'add_holdings', title: 'Add copies / holdings', description: '', action: '/x', icon: 'layers', completed: false },
    { id: 'add_patrons', title: 'Add patrons', description: '', action: '/x', icon: 'user-plus', completed: false },
    { id: 'first_checkout', title: 'Record your first checkout', description: '', action: '/x', icon: 'check-circle', completed: false },
  ],
  ...over,
});

const renderIt = () =>
  render(
    <MemoryRouter>
      <AdminGettingStartedChecklist />
    </MemoryRouter>,
  );

beforeEach(() => {
  storage.clear();
  mockUse.mockReset();
});

describe('AdminGettingStartedChecklist', () => {
  it('renders all six steps with a progress count', () => {
    mockUse.mockReturnValue({ data: progress(), loading: false });
    renderIt();
    expect(screen.getByText('Add your team')).toBeInTheDocument();
    expect(screen.getByText('Record your first checkout')).toBeInTheDocument();
    expect(screen.getByText(/2 of 6/i)).toBeInTheDocument();
  });

  it('renders nothing when all steps are complete', () => {
    mockUse.mockReturnValue({ data: progress({ all_complete: true, completed_count: 6 }), loading: false });
    const { container } = renderIt();
    expect(container).toBeEmptyDOMElement();
  });

  it('dismiss hides the checklist and persists per library_system_id', () => {
    mockUse.mockReturnValue({ data: progress(), loading: false });
    const { rerender } = renderIt();
    fireEvent.click(screen.getByRole('button', { name: /hide/i }));
    expect(localStorage.getItem('l30.adminSetupChecklist.dismissed.7')).toBe('1');
    rerender(
      <MemoryRouter>
        <AdminGettingStartedChecklist />
      </MemoryRouter>,
    );
    expect(screen.queryByText('Add your team')).not.toBeInTheDocument();
    expect(screen.getByText(/show setup checklist/i)).toBeInTheDocument();
  });

  it('renders nothing while loading', () => {
    mockUse.mockReturnValue({ data: null, loading: true });
    const { container } = renderIt();
    expect(container).toBeEmptyDOMElement();
  });
});
