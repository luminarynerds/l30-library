import { describe, it, expect } from 'vitest'
import { buildOracle } from '../lib/openapi-oracle.mjs'
import { compareCallsToOracle, errorKey, diffAgainstBaseline } from '../check-api-request-bodies.mjs'

const SPEC = {
  paths: {
    '/api/v1/acquisition/selection-list/convert-to-po': {
      post: { requestBody: { content: { 'application/json': { schema: { $ref: '#/components/schemas/ConvertToPoRequest' } } } } },
    },
    '/api/v1/lax/thing': {
      post: { requestBody: { content: { 'application/json': { schema: { $ref: '#/components/schemas/LaxRequest' } } } } },
    },
  },
  components: {
    schemas: {
      ConvertToPoRequest: {
        type: 'object', additionalProperties: false, required: ['selection_item_ids'],
        properties: { selection_item_ids: {}, vendor_id: {}, fund_id: {} },
      },
      LaxRequest: { type: 'object', properties: { a: {} } },
    },
  },
}
const oracle = buildOracle(SPEC)

const call = (over) => ({
  file: 'src/api/x.ts', line: 1, method: 'POST',
  path: '/acquisition/selection-list/convert-to-po', bodyFields: [], status: 'resolved', ...over,
})

describe('compareCallsToOracle', () => {
  it('ERRORs on an extra field against a strict schema (the #1370 bug)', () => {
    const { errors } = compareCallsToOracle([call({ bodyFields: [{ name: 'item_ids', optional: false }] })], oracle)
    expect(errors.some((e) => e.kind === 'extra-field' && e.field === 'item_ids')).toBe(true)
  })
  it('passes when fields match the strict schema', () => {
    const { errors } = compareCallsToOracle([call({ bodyFields: [{ name: 'selection_item_ids', optional: false }] })], oracle)
    expect(errors).toHaveLength(0)
  })
  it('does NOT error on an extra field against a non-strict schema', () => {
    const { errors } = compareCallsToOracle(
      [call({ path: '/lax/thing', bodyFields: [{ name: 'a', optional: false }, { name: 'b', optional: false }] })], oracle)
    expect(errors).toHaveLength(0)
  })
  it('WARNs on a missing required field', () => {
    const { warnings } = compareCallsToOracle([call({ bodyFields: [{ name: 'vendor_id', optional: false }] })], oracle)
    expect(warnings.some((w) => w.kind === 'missing-required' && w.field === 'selection_item_ids')).toBe(true)
  })
  it('WARNs when the endpoint is not in the spec', () => {
    const { warnings } = compareCallsToOracle([call({ path: '/ghost/route' })], oracle)
    expect(warnings.some((w) => w.kind === 'endpoint-not-in-spec')).toBe(true)
  })
})

describe('diffAgainstBaseline', () => {
  const e = { kind: 'extra-field', schemaName: 'ConvertToPoRequest', field: 'item_ids', method: 'POST', path: '/acquisition/selection-list/convert-to-po', file: 'x', line: 1 }
  it('classifies a baseline-known error as known, not new', () => {
    const { newErrors, knownErrors } = diffAgainstBaseline([e], [errorKey(e)])
    expect(newErrors).toHaveLength(0)
    expect(knownErrors).toHaveLength(1)
  })
  it('classifies an unlisted error as new', () => {
    const { newErrors } = diffAgainstBaseline([e], [])
    expect(newErrors).toHaveLength(1)
  })
  it('reports baseline keys with no current error as stale', () => {
    const { staleKeys } = diffAgainstBaseline([], ['extra-field|Foo|bar|POST|/x'])
    expect(staleKeys).toEqual(['extra-field|Foo|bar|POST|/x'])
  })
})
