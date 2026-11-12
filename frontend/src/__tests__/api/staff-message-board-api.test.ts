/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { API_BASE } from '@/api/types';
import {
  listPosts, getPost, createPost, updatePost, deletePost,
  createReply, updateReply, deleteReply, getCategories,
} from '../../api/staff-message-board-api'

const mockFetch = vi.fn()
global.fetch = mockFetch

// apiClient (shared api-client.ts) sends credentials + a Content-Type header
// on every request, regardless of method.
const baseHeaders = { 'Content-Type': 'application/json' }

beforeEach(() => {
  mockFetch.mockReset()
})

describe('staff-message-board-api', () => {
  describe('getCategories', () => {
    it('fetches categories from the correct endpoint', async () => {
      const categories = [
        { value: 'memo', label: 'Memos' },
        { value: 'general', label: 'General Discussion' },
      ]
      mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(categories) })

      const result = await getCategories()

      expect(mockFetch).toHaveBeenCalledWith(`${API_BASE}/staff/message-board/categories`, {
        method: 'GET',
        credentials: 'include',
        headers: baseHeaders,
      })
      expect(result).toEqual(categories)
    })
  })

  describe('listPosts', () => {
    it('fetches posts with default pagination', async () => {
      const response = { posts: [], total: 0, page: 1, per_page: 20, pages: 1 }
      mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(response) })

      const result = await listPosts()

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(`${API_BASE}/staff/message-board?`),
        expect.objectContaining({ method: 'GET', credentials: 'include' }),
      )
      const url = mockFetch.mock.calls[0]?.[0] as string
      expect(url).toContain('page=1')
      expect(url).toContain('per_page=20')
      expect(result.total).toBe(0)
    })

    it('includes category filter when provided', async () => {
      const response = { posts: [], total: 0, page: 1, per_page: 20, pages: 1 }
      mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(response) })

      await listPosts(1, 20, 'memo')

      const url = mockFetch.mock.calls[0]?.[0] as string
      expect(url).toContain('category=memo')
    })

    it('includes search term when provided', async () => {
      const response = { posts: [], total: 0, page: 1, per_page: 20, pages: 1 }
      mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(response) })

      await listPosts(1, 20, undefined, false, false, 'test search')

      const url = mockFetch.mock.calls[0]?.[0] as string
      expect(url).toContain('search=test+search')
    })

    it('throws on API error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: () => Promise.resolve({}),
      })

      await expect(listPosts()).rejects.toThrow('Forbidden')
    })
  })

  describe('getPost', () => {
    it('fetches a single post by ID', async () => {
      const post = { id: 1, title: 'Test', content: 'Content', replies: [] }
      mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(post) })

      const result = await getPost(1)

      expect(mockFetch).toHaveBeenCalledWith(`${API_BASE}/staff/message-board/1`, {
        method: 'GET',
        credentials: 'include',
        headers: baseHeaders,
      })
      expect(result.title).toBe('Test')
    })
  })

  describe('createPost', () => {
    it('sends POST request with correct payload', async () => {
      const newPost = { title: 'New Post', content: 'Body', category: 'memo' }
      const created = { ...newPost, id: 1, replies: [] }
      mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(created) })

      const result = await createPost(newPost)

      expect(mockFetch).toHaveBeenCalledWith(`${API_BASE}/staff/message-board`, {
        method: 'POST',
        credentials: 'include',
        headers: baseHeaders,
        body: JSON.stringify(newPost),
      })
      expect(result.id).toBe(1)
    })
  })

  describe('updatePost', () => {
    it('sends PUT request with partial update data', async () => {
      const updates = { title: 'Updated Title' }
      const updated = { id: 1, title: 'Updated Title', content: 'Body', replies: [] }
      mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(updated) })

      const result = await updatePost(1, updates)

      expect(mockFetch).toHaveBeenCalledWith(`${API_BASE}/staff/message-board/1`, {
        method: 'PUT',
        credentials: 'include',
        headers: baseHeaders,
        body: JSON.stringify(updates),
      })
      expect(result.title).toBe('Updated Title')
    })
  })

  describe('deletePost', () => {
    it('sends DELETE request', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, status: 204 })

      await deletePost(5)

      expect(mockFetch).toHaveBeenCalledWith(`${API_BASE}/staff/message-board/5`, {
        method: 'DELETE',
        credentials: 'include',
        headers: baseHeaders,
      })
    })

    it('throws on API error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: () => Promise.resolve({}),
      })

      await expect(deletePost(999)).rejects.toThrow('Not Found')
    })
  })

  describe('createReply', () => {
    it('sends POST request to the reply endpoint', async () => {
      const reply = { id: 10, content: 'A reply', author: null, created_at: '', updated_at: '' }
      mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(reply) })

      const result = await createReply(1, 'A reply')

      expect(mockFetch).toHaveBeenCalledWith(`${API_BASE}/staff/message-board/1/replies`, {
        method: 'POST',
        credentials: 'include',
        headers: baseHeaders,
        body: JSON.stringify({ content: 'A reply' }),
      })
      expect(result.content).toBe('A reply')
    })
  })

  describe('updateReply', () => {
    it('sends PUT request to the correct reply endpoint', async () => {
      const reply = { id: 10, content: 'Updated', author: null, created_at: '', updated_at: '' }
      mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(reply) })

      const result = await updateReply(1, 10, 'Updated')

      expect(mockFetch).toHaveBeenCalledWith(`${API_BASE}/staff/message-board/1/replies/10`, {
        method: 'PUT',
        credentials: 'include',
        headers: baseHeaders,
        body: JSON.stringify({ content: 'Updated' }),
      })
      expect(result.content).toBe('Updated')
    })
  })

  describe('deleteReply', () => {
    it('sends DELETE request to the correct reply endpoint', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true, status: 204 })

      await deleteReply(1, 10)

      expect(mockFetch).toHaveBeenCalledWith(`${API_BASE}/staff/message-board/1/replies/10`, {
        method: 'DELETE',
        credentials: 'include',
        headers: baseHeaders,
      })
    })
  })
})
