/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { API_BASE } from '@/api/types';
import {
  getMyCheckouts,
  getMyHolds,
  renewCheckout,
  cancelHold,
  login,



  searchCatalog,
  getCatalogItem,
} from "../api/api"

describe("API Service", () => {
  const mockToken = "test-token-123"
  
  beforeEach(() => {
    vi.resetAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe("getMyCheckouts", () => {
    it("should return an array of checkouts", async () => {
      const mockCheckouts = [
        {
          id: 1,
          user_id: 1,
          item_id: 1,
          status: "active",
          checked_out_at: "2024-01-01T00:00:00Z",
          due_date: "2024-01-15T00:00:00Z",
          returned_at: null,
          item_title: "Test Book",
          item_author: "Test Author",
        },
      ]

      // getMyCheckouts unwraps the paginated { data, pagination } envelope.
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            data: mockCheckouts,
            pagination: { page: 1, per_page: 20, total: 1, total_pages: 1, has_next: false, has_previous: false },
          }),
      })

      const result = await getMyCheckouts(mockToken)

      expect(Array.isArray(result)).toBe(true)
      expect(result).toEqual(mockCheckouts)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`${API_BASE}/circulation/checkouts`),
        expect.objectContaining({
          credentials: "include",
          headers: expect.objectContaining({ Authorization: "Bearer test-token-123" }),
        })
      )
    })

    it("should throw error on failed request", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ detail: "Unauthorized" }),
      })

      await expect(getMyCheckouts(mockToken)).rejects.toThrow("Failed to fetch checkouts")
    })
  })

  describe("getMyHolds", () => {
    it("should return an array of holds", async () => {
      const mockHolds = [
        {
          id: 1,
          user_id: 1,
          item_id: 2,
          status: "pending",
          position: 1,
          created_at: "2024-01-01T00:00:00Z",
          notified_at: null,
          expires_at: null,
          item_title: "Reserved Book",
          item_author: "Reserved Author",
        },
      ]

      // getMyHolds unwraps the paginated { data, pagination } envelope.
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            data: mockHolds,
            pagination: { page: 1, per_page: 20, total: 1, total_pages: 1, has_next: false, has_previous: false },
          }),
      })

      const result = await getMyHolds(mockToken)

      expect(Array.isArray(result)).toBe(true)
      expect(result).toEqual(mockHolds)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`${API_BASE}/circulation/holds`),
        expect.objectContaining({
          credentials: "include",
          headers: expect.objectContaining({ Authorization: "Bearer test-token-123" }),
        })
      )
    })

    it("should throw error on failed request", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ detail: "Server error" }),
      })

      await expect(getMyHolds(mockToken)).rejects.toThrow()
    })
  })

  describe("renewCheckout", () => {
    it("should call correct endpoint and return renewed checkout", async () => {
      const checkoutId = 5
      const mockRenewedCheckout = {
        id: checkoutId,
        user_id: 1,
        item_id: 1,
        status: "active",
        checked_out_at: "2024-01-01T00:00:00Z",
        due_date: "2024-01-29T00:00:00Z",
        returned_at: null,
        item_title: "Renewed Book",
        item_author: "Test Author",
      }

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockRenewedCheckout),
      })

      const result = await renewCheckout(mockToken, checkoutId)

      expect(result).toEqual(mockRenewedCheckout)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`${API_BASE}/circulation/renew/5`),
        expect.objectContaining({
          method: "POST",
          credentials: "include",
          headers: expect.objectContaining({ Authorization: "Bearer test-token-123" }),
        })
      )
    })

    it("should throw error with message from API on failure", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ detail: "Maximum renewals reached" }),
      })

      await expect(renewCheckout(mockToken, 5)).rejects.toThrow("Maximum renewals reached")
    })
  })

  describe("cancelHold", () => {
    it("should call correct endpoint with DELETE method", async () => {
      const holdId = 3

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
      })

      await cancelHold(mockToken, holdId)

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`${API_BASE}/circulation/holds/3`),
        expect.objectContaining({
          method: "DELETE",
          credentials: "include",
          headers: expect.objectContaining({ Authorization: "Bearer test-token-123" }),
        })
      )
    })

    it("should throw error on failed request", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: "Hold not found" }),
      })

      await expect(cancelHold(mockToken, 999)).rejects.toThrow("This hold was not found")
    })
  })

  describe("login", () => {
    it("should send credentials and return token response", async () => {
      const mockTokenResponse = {
        access_token: "new-token-xyz",
        token_type: "bearer",
      }

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockTokenResponse),
      })

      const result = await login("test@example.com", "password123")

      expect(result).toEqual(mockTokenResponse)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`${API_BASE}/auth/login`),
        expect.objectContaining({
          method: "POST",
          credentials: "include",
          headers: expect.objectContaining({ "Content-Type": "application/json" }),
        })
      )
    })

    it("should throw error with message on failed login", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ detail: "Invalid credentials" }),
      })

      await expect(login("bad@email.com", "wrong")).rejects.toThrow()
    })
  })

  describe("searchCatalog", () => {
    it("should return catalog search results", async () => {
      const mockResults = {
        items: [{ id: 1, title: "Test Book", author: "Author", item_type: "book", status: "available" }],
        total: 1,
        page: 1,
        per_page: 20,
        pages: 1,
      }

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResults),
      })

      const result = await searchCatalog({ query: "test", page: 1, per_page: 20 })

      expect(result.items).toHaveLength(1)
      expect(result.total).toBe(1)
      expect(global.fetch).toHaveBeenCalledWith(
        // searchCatalog hits /catalog/ (trailing slash) before the query string.
        expect.stringContaining(`${API_BASE}/catalog/?`),
        expect.objectContaining({ credentials: "include" })
      )
    })
  })

  describe("getCatalogItem", () => {
    it("should return a single catalog item", async () => {
      const mockItem = {
        id: 1,
        title: "Test Book",
        author: "Test Author",
        item_type: "book",
        status: "available",
      }

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockItem),
      })

      const result = await getCatalogItem(1)

      expect(result.id).toBe(1)
      expect(result.title).toBe("Test Book")
    })

    it("should throw Item not found on 404", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: "Not found" }),
      })

      await expect(getCatalogItem(999)).rejects.toThrow()
    })
  })
})