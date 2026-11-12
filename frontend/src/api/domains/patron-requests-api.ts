/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

export interface LibrarySearchResult {
  id: number;
  name: string;
  city: string | null;
  state: string | null;
  is_connected: boolean;
}

export interface PatronRequestResponse {
  success: boolean;
  message: string;
  library_name: string;
  is_connected: boolean;
}

export interface LibraryAddResponse {
  id: number;
  name: string;
  message: string;
}

export const patronRequestsApi = {
  searchLibraries: async (query: string): Promise<LibrarySearchResult[]> => {
    const res = await fetch(`${API_BASE}/patron-requests/libraries/search?q=${encodeURIComponent(query)}`);
    if (!res.ok) throw new Error('Search failed');
    return res.json();
  },

  submitRequest: async (data: {
    ebook_id: number;
    library_directory_id: number;
    patron_email?: string;
    patron_name?: string;
    source?: string;
  }): Promise<PatronRequestResponse> => {
    const res = await fetch(`${API_BASE}/patron-requests/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Request failed');
    return res.json();
  },

  addLibrary: async (data: {
    name: string;
    city?: string;
    state?: string;
  }): Promise<LibraryAddResponse> => {
    const res = await fetch(`${API_BASE}/patron-requests/libraries/add`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to add library' }));
      throw new Error(err.detail || 'Failed to add library');
    }
    return res.json();
  },
};
