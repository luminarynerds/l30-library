/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Book, Disc, Headphones, Newspaper, Film, Gamepad2, Package, Wrench } from "lucide-react"
import type { LucideIcon } from "lucide-react"

export const CATALOGING_DRAFT_KEY = 'lsc_cataloging_draft'

export interface ItemTypeOption {
  value: string
  label: string
  icon: LucideIcon
}

export const ITEM_TYPES: ItemTypeOption[] = [
  { value: "book", label: "Book", icon: Book },
  { value: "audiobook", label: "Audiobook", icon: Headphones },
  { value: "ebook", label: "E-Book", icon: Book },
  { value: "dvd", label: "DVD", icon: Film },
  { value: "bluray", label: "Blu-ray", icon: Film },
  { value: "cd", label: "CD", icon: Disc },
  { value: "vinyl", label: "Vinyl", icon: Disc },
  { value: "magazine", label: "Magazine", icon: Newspaper },
  { value: "game", label: "Video Game", icon: Gamepad2 },
  { value: "equipment", label: "Equipment", icon: Package },
  { value: "kit", label: "Kit", icon: Package },
  { value: "tool", label: "Tool", icon: Wrench },
  { value: "other", label: "Other", icon: Package },
]

export interface ItemStatusOption {
  value: string
  label: string
  group: string
}

// All 12 item statuses grouped by category
export const ITEM_STATUSES: ItemStatusOption[] = [
  // Available
  { value: "available", label: "Available", group: "Available" },
  // Circulation
  { value: "checked_out", label: "Checked Out", group: "Circulation" },
  { value: "on_hold", label: "On Hold", group: "Circulation" },
  { value: "in_transit", label: "In Transit", group: "Circulation" },
  // Acquisitions
  { value: "on_order", label: "On Order", group: "Acquisitions" },
  { value: "in_processing", label: "In Processing", group: "Acquisitions" },
  // Lost
  { value: "missing", label: "Missing", group: "Lost" },
  { value: "lost", label: "Lost", group: "Lost" },
  { value: "lost_by_patron", label: "Lost by Patron", group: "Lost" },
  { value: "lost_in_transit", label: "Lost in Transit", group: "Lost" },
  { value: "claims_returned", label: "Claims Returned", group: "Lost" },
  // Damaged
  { value: "damaged", label: "Damaged", group: "Damaged" },
  { value: "damaged_repairable", label: "Damaged - Repairable", group: "Damaged" },
  { value: "damaged_withdrawn", label: "Damaged - Withdrawn", group: "Damaged" },
  { value: "in_mending", label: "In Mending", group: "Damaged" },
  // Collection
  { value: "withdrawn", label: "Withdrawn", group: "Collection" },
  { value: "reference", label: "Reference", group: "Collection" },
  { value: "restricted", label: "Restricted", group: "Collection" },
]

export interface FormData {
  title: string; author: string; isbn: string; item_type: string; publication_year: string; publisher: string;
  description: string; subjects: string; location: string; barcode: string; status: string; cover_url: string;
  edition: string; page_count: string; series_name: string; series_number: string; is_large_print: boolean;
  director: string; actors: string; runtime_minutes: string; media_format: string; content_rating: string;
  disc_count: string; studio: string;
  artist: string; track_count: string; music_genre: string;
  platform: string; player_count: string; game_genre: string;
  brand: string; model_number: string; dimensions: string; material: string; kit_contents: string;
  safety_certification_required: boolean; certification_name: string; power_source: string; voltage: string; weight_lbs: string; safety_category: string; accessories_included: string; consumables_needed: string; condition_notes: string; replacement_cost: string;
  lexile_measure?: string;
  cataloging_status?: string;
}

export const emptyForm: FormData = {
  title: "", author: "", isbn: "", item_type: "book", publication_year: "", publisher: "",
  description: "", subjects: "", location: "", barcode: "", status: "available", cover_url: "",
  edition: "", page_count: "", series_name: "", series_number: "", is_large_print: false,
  director: "", actors: "", runtime_minutes: "", media_format: "", content_rating: "",
  disc_count: "", studio: "",
  artist: "", track_count: "", music_genre: "",
  platform: "", player_count: "", game_genre: "",
  brand: "", model_number: "", dimensions: "", material: "", kit_contents: "",
  safety_certification_required: false, certification_name: "", power_source: "", voltage: "", weight_lbs: "", safety_category: "", accessories_included: "", consumables_needed: "", condition_notes: "", replacement_cost: "",
  lexile_measure: "",
  cataloging_status: "",
}
