/**
 * Pure helpers: turn a fresh OpenAPI spec into a per-endpoint request-body oracle.
 * No I/O — the caller reads openapi.json and passes the parsed object.
 */

/** Collapse `${x}` and `{x}` path params to `{param}` and drop any query string. */
export function normalizePath(p) {
  return p
    .replace(/\$\{[^}]+\}/g, '{param}')
    .replace(/\{[^}]+\}/g, '{param}')
    .replace(/\?.*$/, '')
}

function resolveSchema(spec, schema) {
  if (!schema) return null
  if (schema.$ref) {
    const name = schema.$ref.split('/').pop()
    return { name, schema: spec.components?.schemas?.[name] ?? null }
  }
  return { name: null, schema }
}

/** Merge allOf members defensively (Pydantic v2 usually inlines, but be safe). */
function collectFields(spec, schema) {
  const properties = new Set()
  const required = new Set()
  let strict = false
  const visit = (s) => {
    if (!s) return
    if (Array.isArray(s.allOf)) {
      for (const m of s.allOf) visit(resolveSchema(spec, m)?.schema)
    }
    for (const k of Object.keys(s.properties ?? {})) properties.add(k)
    for (const r of s.required ?? []) required.add(r)
    if (s.additionalProperties === false) strict = true
  }
  visit(schema)
  return { properties, required, strict }
}

/**
 * @returns {Map<string, {schemaName:string|null, properties:Set<string>,
 *   required:Set<string>, strict:boolean, hasJsonBody:boolean}>}
 *   keyed by `"METHOD /normalized/path"`.
 */
export function buildOracle(spec) {
  const oracle = new Map()
  for (const [rawPath, methods] of Object.entries(spec.paths ?? {})) {
    const np = normalizePath(rawPath)
    for (const [method, op] of Object.entries(methods ?? {})) {
      const key = `${method.toUpperCase()} ${np}`
      const jsonSchema = op?.requestBody?.content?.['application/json']?.schema
      if (!jsonSchema) {
        oracle.set(key, { schemaName: null, properties: new Set(), required: new Set(), strict: false, hasJsonBody: false })
        continue
      }
      const resolved = resolveSchema(spec, jsonSchema)
      const { properties, required, strict } = collectFields(spec, resolved?.schema)
      oracle.set(key, { schemaName: resolved?.name ?? null, properties, required, strict, hasJsonBody: true })
    }
  }
  return oracle
}
