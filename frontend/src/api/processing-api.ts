/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { API_BASE as API_ROOT } from '@/api/types'
const API_BASE = `${API_ROOT}/processing`;

async function apiFetch<T>(path: string, token: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export interface ProcessingQueueItem {
  copy_id: number;
  item_id: number;
  title: string;
  author: string | null;
  barcode: string | null;
  call_number: string | null;
  current_step: string;
  assigned_staff_id: number | null;
  assigned_staff_name: string | null;
  received_at: string | null;
  time_in_step: string | null;
}

export interface QueueResponse {
  received: ProcessingQueueItem[];
  labeling: ProcessingQueueItem[];
  rfid_tagging: ProcessingQueueItem[];
  ready_to_shelve: ProcessingQueueItem[];
  totals: Record<string, number>;
}

export interface QueueStats {
  total_in_processing: number;
}

export async function getProcessingQueue(token: string, branchId?: number): Promise<QueueResponse> {
  const params = branchId ? `?branch_id=${branchId}` : '';
  return apiFetch<QueueResponse>(`/queue${params}`, token);
}

export async function advanceItem(token: string, copyId: number): Promise<{ status: string; message: string }> {
  return apiFetch(`/queue/${copyId}/advance`, token, { method: 'POST' });
}

export async function bulkAdvance(token: string, copyIds: number[]): Promise<{ results: Array<{ copy_id: number; status?: string; error?: string }> }> {
  return apiFetch(`/queue/bulk-advance`, token, { method: 'POST', body: JSON.stringify({ copy_ids: copyIds }) });
}

export async function getQueueStats(token: string): Promise<QueueStats> {
  return apiFetch<QueueStats>(`/queue/stats`, token);
}