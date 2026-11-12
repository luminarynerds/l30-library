-- Migration: Add library document ingestion tables
-- Date: 2026-02-28
-- Description: Creates tables for uploading newsletters, reports, and other library
--   content for semantic search. Documents are chunked for embedding generation.

-- 1. Create library_documents table
CREATE TABLE IF NOT EXISTS library_documents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    document_type VARCHAR(30) NOT NULL,
    description TEXT,
    publish_date TIMESTAMPTZ,
    tags TEXT[] DEFAULT '{}',
    filename VARCHAR(500),
    file_path VARCHAR(1000),
    file_size_bytes INTEGER,
    mime_type VARCHAR(100),
    full_text TEXT NOT NULL,
    page_count INTEGER,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    uploaded_by_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_library_documents_document_type ON library_documents(document_type);
CREATE INDEX IF NOT EXISTS ix_library_documents_type_date ON library_documents(document_type, publish_date);

-- 2. Create library_document_chunks table
CREATE TABLE IF NOT EXISTS library_document_chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES library_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    section_title VARCHAR(500),
    page_number INTEGER,
    chunk_text TEXT NOT NULL,
    word_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_doc_chunks_document_id ON library_document_chunks(document_id);
CREATE INDEX IF NOT EXISTS ix_doc_chunks_doc_index ON library_document_chunks(document_id, chunk_index);
