/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable @typescript-eslint/no-explicit-any -- Legacy fetch wrapper */
import { getAccessToken } from '../utils/tokenStore';
import { API_BASE } from '@/api/types'

 
export async function fetchApi(path: string, init?: RequestInit): Promise<any> {
  const token = getAccessToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(init?.headers as Record<string, string> || {}),
  };

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    // Backend wraps HTTPException as {error: {message}}; bare FastAPI uses {detail}.
    const message =
      err?.error?.message ||
      (typeof err?.detail === 'string' ? err.detail : undefined) ||
      'Request failed';
    throw { status: res.status, message };
  }
  return res.json();
}