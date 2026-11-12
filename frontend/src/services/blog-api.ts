/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { API_BASE } from "@/api/types"

const BLOG_BASE = `${API_BASE}/blog`

// ==================== Types ====================

export interface BlogTag {
  id: number
  name: string
  slug: string
  post_count?: number
}

export interface BlogPostListItem {
  id: number
  title: string
  slug: string
  tldr: string | null
  meta_description: string | null
  featured_image: string | null
  author_name: string
  author_role: string | null
  status: string
  published_at: string | null
  scheduled_at: string | null
  series_name: string | null
  read_time_minutes: number
  view_count: number
  created_at: string
  deleted_at?: string | null
  tags: BlogTag[]
}

export interface BlogPost extends BlogPostListItem {
  body: string
  series_order: number | null
  updated_at: string | null
}

export interface BlogPostListResponse {
  items: BlogPostListItem[]
  total: number
  page: number
  per_page: number
  draft_count?: number
  published_count?: number
  scheduled_count?: number
}

export interface BlogPostFormData {
  title: string
  slug?: string
  body: string
  tldr?: string
  meta_description?: string
  author_name: string
  author_role?: string
  featured_image?: string
  status: string
  scheduled_at?: string
  series_name?: string
  series_order?: number
  tags: string[]
}

export interface BlogAnalytics {
  total_views: number
  total_posts: number
  published_posts: number
  views_last_7_days: number
  views_last_30_days: number
  top_posts: { id: number; title: string; slug: string; view_count: number }[]
  views_by_day: { date: string; count: number }[]
}

// ==================== Version Types ====================

export interface BlogPostVersionListItem {
  id: number
  version_number: number
  title: string
  created_at: string
  created_by: string | null
}

export interface BlogPostVersionResponse {
  id: number
  version_number: number
  title: string
  body: string
  tldr: string | null
  created_at: string
  created_by: string | null
}

// ==================== Helpers ====================

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  // eslint-disable-next-line no-restricted-syntax -- custom Pydantic array-detail error parsing below; fetchApi only handles string detail
  const res = await fetch(`${BLOG_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }))
    let message: string
    if (Array.isArray(err.detail)) {
      message = err.detail
        .map((e: { msg?: string; loc?: (string | number)[] }) => {
          const field = Array.isArray(e.loc) ? e.loc.slice(1).join(".") : ""
          return field ? `${field}: ${e.msg ?? ""}` : (e.msg ?? "")
        })
        .filter(Boolean)
        .join("; ")
    } else if (typeof err.detail === "string") {
      message = err.detail
    } else {
      message = `Request failed: ${res.status}`
    }
    throw new Error(message || `Request failed: ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` }
}

// ==================== Public ====================

export async function getBlogPosts(params?: {
  tag?: string
  q?: string
  page?: number
  per_page?: number
}): Promise<BlogPostListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.tag) searchParams.set("tag", params.tag)
  if (params?.q) searchParams.set("q", params.q)
  if (params?.page) searchParams.set("page", params.page.toString())
  if (params?.per_page) searchParams.set("per_page", params.per_page.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ""
  return apiFetch(`/posts${query}`)
}

export async function getBlogPost(slug: string): Promise<BlogPost> {
  return apiFetch(`/posts/${slug}`)
}

export async function getRelatedPosts(slug: string): Promise<BlogPostListItem[]> {
  return apiFetch(`/posts/${slug}/related`)
}

export async function getBlogTags(): Promise<BlogTag[]> {
  return apiFetch("/tags")
}

export async function getBlogSeries(seriesName: string): Promise<BlogPostListItem[]> {
  return apiFetch(`/series/${encodeURIComponent(seriesName)}`)
}

// ==================== Staff/Admin ====================

export async function getAdminPosts(
  token: string,
  params?: { status?: string; q?: string; page?: number; per_page?: number }
): Promise<BlogPostListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set("status", params.status)
  if (params?.q) searchParams.set("q", params.q)
  if (params?.page) searchParams.set("page", params.page.toString())
  if (params?.per_page) searchParams.set("per_page", params.per_page.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ""
  return apiFetch(`/posts/admin${query}`, { headers: authHeaders(token) })
}

export async function getBlogAnalytics(token: string, days?: number): Promise<BlogAnalytics> {
  const query = days ? `?days=${days}` : ""
  return apiFetch(`/analytics${query}`, { headers: authHeaders(token) })
}

export async function createBlogPost(token: string, data: BlogPostFormData): Promise<BlogPost> {
  return apiFetch("/posts", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(data),
  })
}

export async function updateBlogPost(token: string, id: number, data: Partial<BlogPostFormData>): Promise<BlogPost> {
  return apiFetch(`/posts/${id}`, {
    method: "PUT",
    headers: authHeaders(token),
    body: JSON.stringify(data),
  })
}

export async function deleteBlogPost(token: string, id: number): Promise<void> {
  return apiFetch(`/posts/${id}`, {
    method: "DELETE",
    headers: authHeaders(token),
  })
}

export async function restoreBlogPost(token: string, id: number): Promise<void> {
  await apiFetch(`/posts/${id}/restore`, {
    method: "POST",
    headers: authHeaders(token),
  })
}

export async function publishBlogPost(token: string, id: number): Promise<BlogPost> {
  return apiFetch(`/posts/${id}/publish`, {
    method: "PUT",
    headers: authHeaders(token),
  })
}

export async function unpublishBlogPost(token: string, id: number): Promise<BlogPost> {
  return apiFetch(`/posts/${id}/unpublish`, {
    method: "PUT",
    headers: authHeaders(token),
  })
}


export async function scheduleBlogPost(token: string, id: number, scheduledAt: string): Promise<BlogPost> {
  const params = new URLSearchParams({ scheduled_at: scheduledAt })
  return apiFetch(`/posts/${id}/schedule?${params}`, {
    method: "PUT",
    headers: authHeaders(token),
  })
}

// ==================== Admin Post by ID ====================

export async function getAdminPost(token: string, postId: number): Promise<BlogPost> {
  return apiFetch(`/posts/admin/${postId}`, { headers: authHeaders(token) })
}

// ==================== Media Upload ====================

export async function uploadBlogMedia(token: string, file: File): Promise<{ url: string }> {
  const formData = new FormData()
  formData.append("file", file)
  // eslint-disable-next-line no-restricted-syntax -- multipart FormData upload; fetchApi forces Content-Type: application/json which breaks boundary
  const res = await fetch(`${BLOG_BASE}/media`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }))
    throw new Error(err.detail || "Upload failed")
  }
  return res.json()
}

// ==================== Media Library ====================

export async function listBlogMedia(token: string): Promise<{ filename: string; url: string; size: number; uploaded_at: number }[]> {
  return apiFetch("/media", { headers: authHeaders(token) })
}

export async function deleteBlogMedia(token: string, filename: string): Promise<void> {
  return apiFetch(`/media/${encodeURIComponent(filename)}`, {
    method: "DELETE",
    headers: authHeaders(token),
  })
}

// ==================== Bulk Operations ====================

export async function bulkPublishPosts(token: string, postIds: number[]): Promise<{ published: number }> {
  return apiFetch("/posts/bulk/publish", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(postIds),
  })
}

export async function bulkDeletePosts(token: string, postIds: number[]): Promise<{ deleted: number }> {
  return apiFetch("/posts/bulk/delete", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(postIds),
  })
}

// ==================== Version History ====================

export async function getPostVersions(token: string, postId: number): Promise<BlogPostVersionListItem[]> {
  return apiFetch(`/posts/${postId}/versions`, { headers: authHeaders(token) })
}

export async function getPostVersion(token: string, postId: number, versionId: number): Promise<BlogPostVersionResponse> {
  return apiFetch(`/posts/${postId}/versions/${versionId}`, { headers: authHeaders(token) })
}

export async function restorePostVersion(token: string, postId: number, versionId: number): Promise<BlogPost> {
  return apiFetch(`/posts/${postId}/versions/${versionId}/restore`, {
    method: "PUT",
    headers: authHeaders(token),
  })
}
