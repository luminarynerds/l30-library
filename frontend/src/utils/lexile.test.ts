import { describe, expect, it } from 'vitest'
import { parseLexileClient } from './lexile'

describe('parseLexileClient', () => {
  it.each([
    ['750L', { canonical: '750L', numeric: 750 }],
    ['ad650l', { canonical: 'AD650L', numeric: 650 }],
    ['HL400L', { canonical: 'HL400L', numeric: 400 }],
    ['BR200L', { canonical: 'BR200L', numeric: -200 }],
    ['NP', { canonical: 'NP', numeric: null }],
    ['', { canonical: null, numeric: null }],
  ])('parses %s', (raw, expected) => {
    expect(parseLexileClient(raw)).toEqual(expected)
  })

  it.each(['L750', '750LL', 'BR500L', '2500L', 'xyz', '750'])('rejects %s', (raw) => {
    expect(() => parseLexileClient(raw)).toThrow()
  })
})
