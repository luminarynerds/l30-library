const LEXILE_RE = /^(AD|HL|BR|NC|IG)?(\d{1,4})L$/i

export interface ParsedLexile { canonical: string | null; numeric: number | null }

export function parseLexileClient(raw: string | null | undefined): ParsedLexile {
  if (raw == null) return { canonical: null, numeric: null }
  const s = raw.trim().toUpperCase()
  if (s === '') return { canonical: null, numeric: null }
  if (s === 'NP') return { canonical: 'NP', numeric: null }
  if (s === 'BR') return { canonical: 'BR', numeric: 0 }
  const m = LEXILE_RE.exec(s)
  if (!m) throw new Error('invalid')
  const prefix = m[1] ?? ''
  const digits = m[2]
  if (!digits) throw new Error('invalid')
  let numeric = parseInt(digits, 10)
  if (prefix === 'BR') {
    if (numeric === 0 || numeric > 400) throw new Error('invalid')
    numeric = -numeric
  }
  if (numeric < -400 || numeric > 2000) throw new Error('invalid')
  return { canonical: `${prefix}${digits}L`, numeric }
}
