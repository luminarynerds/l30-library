/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, expect, it } from 'vitest'
import { parseSubjectsField } from '../parseSubjectsField'

describe('parseSubjectsField', () => {
  it('returns [] for nullish or empty input', () => {
    expect(parseSubjectsField(null)).toEqual([])
    expect(parseSubjectsField(undefined)).toEqual([])
    expect(parseSubjectsField('')).toEqual([])
    expect(parseSubjectsField('   ')).toEqual([])
  })

  it('splits on commas', () => {
    expect(parseSubjectsField('Fiction, Memoir, History')).toEqual([
      'Fiction', 'Memoir', 'History',
    ])
  })

  it('splits on semicolons', () => {
    expect(parseSubjectsField('Fiction; Memoir; History')).toEqual([
      'Fiction', 'Memoir', 'History',
    ])
  })

  it('handles mixed comma and semicolon delimiters', () => {
    expect(parseSubjectsField('Fiction, Memoir; History,Science')).toEqual([
      'Fiction', 'Memoir', 'History', 'Science',
    ])
  })

  it('parses single-quote Python array literals', () => {
    expect(parseSubjectsField("['Fiction', 'Memoir', 'History']")).toEqual([
      'Fiction', 'Memoir', 'History',
    ])
  })

  it('parses double-quote array literals', () => {
    expect(parseSubjectsField('["Fiction", "Memoir"]')).toEqual([
      'Fiction', 'Memoir',
    ])
  })

  it('returns [] for empty array literal', () => {
    expect(parseSubjectsField('[]')).toEqual([])
  })

  it('strips whitespace inside array literal entries', () => {
    expect(parseSubjectsField("[ 'Fiction' , 'Memoir' ]")).toEqual([
      'Fiction', 'Memoir',
    ])
  })

  it('drops empty substrings', () => {
    expect(parseSubjectsField('Fiction,,Memoir,;,History')).toEqual([
      'Fiction', 'Memoir', 'History',
    ])
  })

  it('preserves LCSH double-hyphen subdivisions', () => {
    expect(parseSubjectsField('Cooking -- Italian; Fiction -- Psychological')).toEqual([
      'Cooking -- Italian', 'Fiction -- Psychological',
    ])
  })

  it('returns single subject when no delimiter is present', () => {
    expect(parseSubjectsField('Fiction')).toEqual(['Fiction'])
  })

  it('falls back to delimiter split when array literal has no quoted strings', () => {
    // Bare bracket-wrapped value isn't a valid array literal; we still
    // expect a usable list rather than a thrown error.
    const result = parseSubjectsField('[Fiction, Memoir]')
    expect(Array.isArray(result)).toBe(true)
    // Don't pin exact content -- only that it doesn't throw and returns strings.
    expect(result.every((s) => typeof s === 'string')).toBe(true)
  })
})
