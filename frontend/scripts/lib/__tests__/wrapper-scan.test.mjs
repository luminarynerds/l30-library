import { describe, it, expect } from 'vitest'
import { Project } from 'ts-morph'
import { scanWrappers } from '../wrapper-scan.mjs'

function projectFrom(code) {
  const project = new Project({ useInMemoryFileSystem: true, compilerOptions: { strict: true } })
  project.createSourceFile('api.ts', code)
  return project
}

describe('scanWrappers', () => {
  it('extracts body field set + path + method from an inline-typed wrapper', () => {
    const project = projectFrom(`
      import { fetchApi } from '@/lib/api-client'
      export async function convertSelectionToPO(data: { item_ids: number[]; vendor_id: number }) {
        return await fetchApi('/acquisition/selection-list/convert-to-po', { method: 'POST', body: data })
      }
    `)
    const calls = scanWrappers(project)
    const c = calls.find((x) => x.path === '/acquisition/selection-list/convert-to-po')
    expect(c.method).toBe('POST')
    expect(c.status).toBe('resolved')
    expect(c.bodyFields.map((f) => f.name).sort()).toEqual(['item_ids', 'vendor_id'])
  })

  it('marks template-literal paths resolved with {param}', () => {
    const project = projectFrom(`
      import { fetchApi } from '@/lib/api-client'
      export async function create(id: number, data: { title: string }) {
        return await fetchApi(\`/acquisition/funds/\${id}\`, { method: 'PUT', body: data })
      }
    `)
    const c = scanWrappers(project)[0]
    expect(c.path).toBe('/acquisition/funds/{param}')
    expect(c.status).toBe('resolved')
  })

  it('ignores fetchApi not imported from @/lib/api-client', () => {
    const project = projectFrom(`
      import { fetchApi } from '../fetchApi'
      export async function legacy(body: string) {
        return await fetchApi('/x', { method: 'POST', body })
      }
    `)
    expect(scanWrappers(project)).toHaveLength(0)
  })

  it('marks dynamic-prefix paths unresolved', () => {
    const project = projectFrom(`
      import { fetchApi } from '@/lib/api-client'
      const BASE = '/acquisition'
      export async function dyn(data: { a: number }) {
        return await fetchApi(\`\${BASE}/x\`, { method: 'POST', body: data })
      }
    `)
    expect(scanWrappers(project)[0].status).toBe('unresolved-path')
  })
})
