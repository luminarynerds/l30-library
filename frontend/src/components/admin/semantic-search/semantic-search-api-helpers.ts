/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client';
import { EmbeddingProgress, GenerationRequest, DocumentListResponse, DocumentStatsResponse, LibraryDocumentSummary } from './types';

export async function getEmbeddingProgress(entityType: string): Promise<EmbeddingProgress> {
  return fetchApi<EmbeddingProgress>(`/search/embeddings/progress/${encodeURIComponent(entityType)}`);
}

export async function triggerEmbeddingGeneration(request: GenerationRequest): Promise<{ message: string; entity_types: string[]; status: string }> {
  return fetchApi('/search/embeddings/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    timeoutMs: 60000,
  });
}

export async function triggerGemRecalculation(params: { source_collection?: string; batch_size?: number }): Promise<{ message: string; status: string }> {
  return fetchApi('/search/hidden-gems/recalculate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
    timeoutMs: 60000,
  });
}

export async function triggerAuthorEmbeddingRebuild(params: { batch_size?: number }): Promise<{ message: string; status: string }> {
  return fetchApi('/search/author-embeddings/rebuild', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
    timeoutMs: 60000,
  });
}

export async function getDocumentList(documentType?: string): Promise<DocumentListResponse> {
  const params = new URLSearchParams({ limit: '100' });
  if (documentType) params.set('document_type', documentType);
  return fetchApi<DocumentListResponse>(`/library-documents?${params.toString()}`);
}

export async function getDocumentStats(): Promise<DocumentStatsResponse> {
  return fetchApi<DocumentStatsResponse>('/library-documents/stats');
}

export async function deleteDocument(id: number): Promise<{ message: string }> {
  return fetchApi<{ message: string }>(`/library-documents/${id}`, { method: 'DELETE' });
}

export async function uploadPdfDocument(formData: FormData): Promise<LibraryDocumentSummary> {
  return fetchApi<LibraryDocumentSummary>('/library-documents/upload/pdf', {
    method: 'POST',
    body: formData,
    timeoutMs: 120000,
  });
}

export async function uploadTextDocument(formData: FormData): Promise<LibraryDocumentSummary> {
  return fetchApi<LibraryDocumentSummary>('/library-documents/upload/text', {
    method: 'POST',
    body: formData,
    timeoutMs: 60000,
  });
}
