/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export interface EmbeddingProgress {
  entity_type: string;
  status: 'not_started' | 'running' | 'completed' | 'failed';
  progress: {
    total_count: number;
    embedded_count: number;
    failed_count: number;
    progress_percent: number;
    started_at: string | null;
    completed_at: string | null;
  } | null;
}

export interface GenerationRequest {
  entity_types: string[];
  batch_size: number;
  skip_existing: boolean;
}

export interface LibraryDocumentSummary {
  id: number;
  title: string;
  document_type: string;
  description: string | null;
  publish_date: string | null;
  tags: string[];
  filename: string | null;
  file_size_bytes: number | null;
  page_count: number | null;
  chunk_count: number;
  created_at: string;
}

export interface DocumentListResponse {
  documents: LibraryDocumentSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface DocumentStatsResponse {
  total_documents: number;
  total_chunks: number;
  by_type: Record<string, number>;
}
