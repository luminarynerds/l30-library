/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Staff Message Board API Client
 * Internal forum / virtual break room for library staff
 */

import { api } from '@/lib/api-client'
import { API_BASE as API_ROOT } from '@/api/types'

export interface Author {
  id: number
  full_name?: string
}

export interface BoardReply {
  id: number
  content: string
  author?: Author
  created_at: string
  updated_at: string
}

export interface BoardPost {
  id: number
  title: string
  content: string
  category: string
  pinned: boolean
  archived: boolean
  author?: Author
  reply_count: number
  created_at: string
  updated_at: string
}

export interface BoardPostDetail extends BoardPost {
  replies: BoardReply[]
}

export interface PostListResponse {
  posts: BoardPost[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface CategoryOption {
  value: string
  label: string
}

const API_BASE = `${API_ROOT}/staff/message-board`

export async function getCategories(): Promise<CategoryOption[]> {
  return api.get(`${API_BASE}/categories`)
}

export async function listPosts(
  page: number = 1,
  perPage: number = 20,
  category?: string,
  pinnedOnly?: boolean,
  includeArchived?: boolean,
  search?: string,
): Promise<PostListResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    per_page: perPage.toString(),
  })
  if (category) params.append('category', category)
  if (pinnedOnly) params.append('pinned_only', 'true')
  if (includeArchived) params.append('include_archived', 'true')
  if (search) params.append('search', search)

  return api.get(`${API_BASE}?${params}`)
}

export async function getPost(postId: number): Promise<BoardPostDetail> {
  return api.get(`${API_BASE}/${postId}`)
}

export async function createPost(data: {
  title: string
  content: string
  category: string
  pinned?: boolean
}): Promise<BoardPostDetail> {
  return api.post(`${API_BASE}`, data)
}

export async function updatePost(
  postId: number,
  data: {
    title?: string
    content?: string
    category?: string
    pinned?: boolean
    archived?: boolean
  },
): Promise<BoardPostDetail> {
  return api.put(`${API_BASE}/${postId}`, data)
}

export async function deletePost(postId: number): Promise<void> {
  await api.delete(`${API_BASE}/${postId}`)
}

export async function createReply(
  postId: number,
  content: string,
): Promise<BoardReply> {
  return api.post(`${API_BASE}/${postId}/replies`, { content })
}

export async function updateReply(
  postId: number,
  replyId: number,
  content: string,
): Promise<BoardReply> {
  return api.put(`${API_BASE}/${postId}/replies/${replyId}`, { content })
}

export async function deleteReply(postId: number, replyId: number): Promise<void> {
  await api.delete(`${API_BASE}/${postId}/replies/${replyId}`)
}