import { describe, expect, it, vi, beforeEach } from 'vitest'

vi.mock('@/lib/api-client', () => ({
  fetchApi: vi.fn(),
  isApiError: (e: unknown) => typeof e === 'object' && e !== null && 'detail' in (e as object),
}))
import { fetchApi } from '@/lib/api-client'
import { getFeaturedUpcoming } from '../releases-api'

describe('getFeaturedUpcoming', () => {
  beforeEach(() => vi.clearAllMocks())
  it('calls the featured-upcoming endpoint and returns items', async () => {
    ;(fetchApi as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ items: [{ tracker_book_id: 'a', title: 'X', source: 'libraryreads', library_status: 'new' }], total: 1, page: 1, per_page: 24 })
    const res = await getFeaturedUpcoming()
    expect(fetchApi).toHaveBeenCalledWith('/releases/featured-upcoming')
    expect(res.items[0]?.title).toBe('X')
  })
})
