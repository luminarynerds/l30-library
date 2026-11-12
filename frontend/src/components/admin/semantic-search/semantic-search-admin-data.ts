/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export const ENTITY_TYPES = [
  {
    id: 'catalog_item_combined',
    label: 'Combined Item Embedding',
    description: 'Title + author + description + subjects — best for semantic search',
    recommended: true,
  },
  {
    id: 'catalog_item_title',
    label: 'Title-Only Embedding',
    description: 'Faster to generate, used for autocomplete',
    recommended: false,
  },
  {
    id: 'gutenberg_combined',
    label: 'Gutenberg Combined',
    description: 'Embeddings for Project Gutenberg public domain books',
    recommended: true,
  },
  {
    id: 'library_document',
    label: 'Library Documents',
    description: 'Newsletters, reports, and other uploaded document chunks',
    recommended: true,
  },
];

export const DOCUMENT_TYPES = [
  { value: 'newsletter', label: 'Newsletter' },
  { value: 'annual_report', label: 'Annual Report' },
  { value: 'board_report', label: 'Board Report' },
  { value: 'flyer', label: 'Flyer' },
  { value: 'program_guide', label: 'Program Guide' },
  { value: 'policy_document', label: 'Policy Document' },
  { value: 'press_release', label: 'Press Release' },
  { value: 'other', label: 'Other' },
];
