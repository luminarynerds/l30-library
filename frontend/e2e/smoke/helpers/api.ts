/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import fs from "fs"
import { API_BASE, API_PREFIX, testPrefix } from "../smoke.config"

const BASE = `${API_BASE}${API_PREFIX}`

export interface CatalogItem {
  id: number
  title: string
  barcode: string | null
  status: string
}

export interface Checkout {
  id: number
  user_id: number
  item_id: number
  status: string
}

export interface Hold {
  id: number
  item_id: number
  status: string
}

export interface ReviewRecord {
  id: number
  catalog_item_id: number
  title: string | null
}

export interface EventRecord {
  id: number
  title: string
}

export interface EventRegistration {
  id: number
  event_id: number
  status: string
}

export interface IndieAuthor {
  id: number
  pen_name: string
  user_id: number
}

export interface IndieEbook {
  id: number
  title: string
  submission_status: string
}

async function apiCall<T>(
  method: string,
  path: string,
  token: string,
  body?: unknown,
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${method} ${path} returned ${res.status}: ${text}`)
  }
  if (res.status === 204) return {} as T
  return res.json()
}

export class SmokeApiClient {
  constructor(private token: string) {}

  // --- Catalog ---

  async createCatalogItem(suffix: string): Promise<CatalogItem> {
    return apiCall<CatalogItem>("POST", "/staff/catalog", this.token, {
      title: `${testPrefix()} ${suffix}`,
      author: "Smoke Test Author",
      item_type: "book",
    })
  }

  // --- Circulation ---

  /** Self-checkout: current user checks out the item to themselves. */
  async checkout(itemId: number): Promise<Checkout> {
    return apiCall<Checkout>("POST", "/circulation/checkout", this.token, {
      item_id: itemId,
    })
  }

  /** Staff: view a patron's checkouts. */
  async getPatronCheckouts(patronId: number): Promise<Checkout[]> {
    return apiCall<Checkout[]>("GET", `/staff/patrons/${patronId}/checkouts`, this.token)
  }

  /** Return / check in an item. */
  async checkin(checkoutId: number): Promise<Checkout> {
    return apiCall<Checkout>(
      "POST",
      `/circulation/checkin?checkout_id=${checkoutId}`,
      this.token,
    )
  }

  // --- Holds ---

  async placeHold(itemId: number): Promise<Hold> {
    return apiCall<Hold>("POST", "/circulation/holds", this.token, { item_id: itemId })
  }

  async cancelHold(holdId: number): Promise<void> {
    await apiCall<void>("DELETE", `/circulation/holds/${holdId}`, this.token)
  }

  // --- Reviews ---

  async writeReview(
    catalogItemId: number,
    title: string,
    body: string,
  ): Promise<ReviewRecord> {
    return apiCall<ReviewRecord>("PUT", `/reviews/${catalogItemId}`, this.token, {
      rating: 4,
      title,
      body,
    })
  }

  // --- Events ---

  async createEvent(suffix: string): Promise<EventRecord> {
    const start = new Date()
    start.setDate(start.getDate() + 7) // 1 week from now
    return apiCall<EventRecord>("POST", "/events", this.token, {
      title: `${testPrefix()} ${suffix}`,
      description: "Smoke test event",
      start_time: start.toISOString(),
      location: "Test Room",
      registration_required: true,
      max_attendees: 50,
    })
  }

  async registerForEvent(
    eventId: number,
    name: string,
    email: string,
  ): Promise<EventRegistration> {
    return apiCall<EventRegistration>(
      "POST",
      `/events/${eventId}/register`,
      this.token,
      { patron_name: name, patron_email: email },
    )
  }

  // --- Indie ---

  async registerIndieAuthor(suffix: string): Promise<IndieAuthor> {
    return apiCall<IndieAuthor>("POST", "/indie/authors/register", this.token, {
      pen_name: `${testPrefix()} ${suffix}`,
      bio: "Smoke test author",
      agreement_accepted: true,
    })
  }

  async createIndieEbook(suffix: string): Promise<IndieEbook> {
    return apiCall<IndieEbook>("POST", "/indie/ebooks", this.token, {
      title: `${testPrefix()} ${suffix}`,
      description: "Smoke test ebook",
      genre: "Fiction",
    })
  }

  async submitIndieEbook(ebookId: number): Promise<IndieEbook> {
    return apiCall<IndieEbook>(
      "POST",
      `/indie/ebooks/mine/${ebookId}/submit`,
      this.token,
    )
  }

  // --- User lookup ---

  async getMe(): Promise<{ id: number; email: string; role: string }> {
    return apiCall("GET", "/auth/me", this.token)
  }

  // --- Cleanup ---

  async cleanup(runId: string): Promise<void> {
    try {
      await apiCall<void>("DELETE", "/test/cleanup", this.token, { run_id: runId })
    } catch (err) {
      console.warn(`Cleanup warning: ${err}`)
    }
  }
}

/** Create a client by logging in with the given credentials. */
export async function createClient(
  email: string,
  password: string,
): Promise<SmokeApiClient> {
  const res = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) throw new Error(`Login failed for ${email}: ${res.status}`)
  const data = await res.json()
  return new SmokeApiClient(data.access_token)
}

/** Create a client from a saved storage state file (avoids extra login calls). */
export function createClientFromStorageState(storagePath: string): SmokeApiClient {
  const raw = JSON.parse(fs.readFileSync(storagePath, "utf-8"))
  const tokenEntry = raw.origins?.[0]?.localStorage?.find(
    (e: { name: string }) => e.name === "access_token",
  )
  if (!tokenEntry?.value) throw new Error(`No access_token in ${storagePath}`)
  return new SmokeApiClient(tokenEntry.value)
}
