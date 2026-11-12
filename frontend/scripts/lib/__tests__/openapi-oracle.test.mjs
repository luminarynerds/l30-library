import { describe, it, expect } from 'vitest'
import { normalizePath, buildOracle } from '../openapi-oracle.mjs'

const SPEC = {
  paths: {
    '/api/v1/acquisition/selection-list/convert-to-po': {
      post: {
        requestBody: {
          content: { 'application/json': { schema: { $ref: '#/components/schemas/ConvertToPoRequest' } } },
        },
      },
    },
    '/api/v1/catalog/{item_id}/images': {
      post: { requestBody: { content: { 'multipart/form-data': { schema: {} } } } },
    },
  },
  components: {
    schemas: {
      ConvertToPoRequest: {
        type: 'object',
        additionalProperties: false,
        required: ['selection_item_ids'],
        properties: {
          selection_item_ids: { type: 'array', items: { type: 'integer' } },
          vendor_id: { anyOf: [{ type: 'integer' }, { type: 'null' }] },
          fund_id: { anyOf: [{ type: 'integer' }, { type: 'null' }] },
        },
      },
    },
  },
}

describe('normalizePath', () => {
  it('collapses template and openapi params and strips query', () => {
    expect(normalizePath('/acquisition/funds/${id}')).toBe('/acquisition/funds/{param}')
    expect(normalizePath('/api/v1/catalog/{item_id}/images')).toBe('/api/v1/catalog/{param}/images')
    expect(normalizePath('/acquisition/funds?x=1')).toBe('/acquisition/funds')
  })
})

describe('buildOracle', () => {
  const oracle = buildOracle(SPEC)
  it('resolves a strict $ref schema into fields + strictness', () => {
    const e = oracle.get('POST /api/v1/acquisition/selection-list/convert-to-po')
    expect(e.schemaName).toBe('ConvertToPoRequest')
    expect(e.strict).toBe(true)
    expect([...e.properties].sort()).toEqual(['fund_id', 'selection_item_ids', 'vendor_id'])
    expect([...e.required]).toEqual(['selection_item_ids'])
    expect(e.hasJsonBody).toBe(true)
  })
  it('marks multipart endpoints as no-json-body', () => {
    const e = oracle.get('POST /api/v1/catalog/{param}/images')
    expect(e.hasJsonBody).toBe(false)
  })
})
