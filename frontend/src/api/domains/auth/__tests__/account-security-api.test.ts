import { describe, it, expect, vi, beforeEach } from 'vitest'
import { verify2FARecovery } from '../account-security-api'

const fetchApi = vi.hoisted(() => vi.fn())
vi.mock('@/lib/api-client', () => ({ fetchApi }))

describe('verify2FARecovery', () => {
  beforeEach(() => fetchApi.mockReset())

  it('places turnstile_token in the request body when provided', async () => {
    fetchApi.mockResolvedValueOnce({ access_token: 'tok', recovery_codes_remaining: 7 })
    await verify2FARecovery('pending-abc', 'RECO-CODE', 'cf-turnstile-xyz')
    expect(fetchApi).toHaveBeenCalledTimes(1)
    const [, options] = fetchApi.mock.calls[0]!
    const body = JSON.parse(options.body)
    expect(body.turnstile_token).toBe('cf-turnstile-xyz')
    expect(body.pending_token).toBe('pending-abc')
    expect(body.recovery_code).toBe('RECO-CODE')
  })
})
