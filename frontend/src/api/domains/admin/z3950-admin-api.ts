/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable @typescript-eslint/no-empty-object-type */
 
/**
 * Z39.50 Admin Settings API service
 */
import api from '@/lib/api-client';
import { API_BASE } from '@/api/types'

export interface Z3950Source {
  id: number;
  name: string;
  host: string;
  port: number;
  database_name: string;
  syntax: string;
  encoding: string;
  sru_url: string | null;
  requires_auth: boolean;
  username: string | null;
  password_set: boolean;
  is_enabled: boolean;
  display_order: number;
  last_tested_at: string | null;
  last_test_success: boolean | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface Z3950SourceCreate {
  name: string;
  host: string;
  port: number;
  database_name: string;
  syntax?: string;
  encoding?: string;
  sru_url?: string | null;
  requires_auth?: boolean;
  username?: string | null;
  password?: string | null;
  is_enabled?: boolean;
  display_order?: number;
  notes?: string | null;
}

export interface Z3950SourceUpdate extends Partial<Z3950SourceCreate> {}

export interface TestResult {
  success: boolean;
  message: string;
  response_time_ms: number | null;
}

const BASE = `${API_BASE}/admin/z3950-sources`;

export const z3950AdminApi = {
  list: () => api.get<Z3950Source[]>(BASE),
  create: (data: Z3950SourceCreate) => api.post<Z3950Source>(BASE, data),
  update: (id: number, data: Z3950SourceUpdate) => api.put<Z3950Source>(`${BASE}/${id}`, data),
  delete: (id: number) => api.delete(`${BASE}/${id}`),
  test: (id: number) => api.post<TestResult>(`${BASE}/${id}/test`),
  seed: () => api.post<Z3950Source[]>(`${BASE}/seed`),
};

export default z3950AdminApi;