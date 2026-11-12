/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * SPARQL Endpoint API Service
 *
 * Provides access to the SPARQL endpoint for querying BIBFRAME data
 * using the SPARQL query language.
 *
 * The endpoint follows the SPARQL 1.1 Protocol specification:
 * https://www.w3.org/TR/sparql11-protocol/
 *
 * Supported features:
 * - SELECT queries with basic graph patterns
 * - FILTER expressions
 * - LIMIT, OFFSET, ORDER BY
 * - Content negotiation (JSON, XML, CSV results)
 */

import { fetchApi } from '@/lib/api-client'
import { API_BASE } from '@/api/types'

// ==================== Types ====================

export type SparqlResultFormat = 'json' | 'xml' | 'csv'

export interface SparqlBinding {
  /** Binding type: uri, literal, or blank node */
  type: 'uri' | 'literal' | 'bnode'
  /** The actual value */
  value: string
  /** Datatype URI for typed literals (e.g., xsd:integer) */
  datatype?: string
  /** Language tag for language-tagged literals */
  'xml:lang'?: string
}

export interface SparqlResults {
  /** Result head containing variable names */
  head: {
    /** List of variable names in the result set */
    vars: string[]
  }
  /** Query results */
  results: {
    /** Array of result bindings, each mapping variable names to values */
    bindings: Array<Record<string, SparqlBinding>>
  }
  /** Error message if query failed */
  error?: string
}

export interface SparqlQueryRequest {
  /** SPARQL query string (max 10000 characters) */
  query: string
  /** Default graph URI (not yet supported) */
  default_graph_uri?: string
  /** Named graph URIs (not yet supported) */
  named_graph_uri?: string[]
}

export interface SparqlServiceDescription {
  '@context': {
    sd: string
    bf: string
  }
  '@type': string
  'sd:endpoint': string
  'sd:supportedLanguage': string
  'sd:resultFormat': string[]
}

export interface SparqlPrefixes {
  /** Map of prefix to namespace URI */
  prefixes: Record<string, string>
  /** Example query using the prefixes */
  example_query: string
}

export interface SparqlExample {
  /** Name of the example */
  name: string
  /** Description of what the query does */
  description: string
  /** The SPARQL query string */
  query: string
}

export interface SparqlExamplesResponse {
  /** List of example queries */
  examples: SparqlExample[]
}

// ==================== Constants ====================

const BASE_PATH = '/sparql'

// ==================== Query Execution Functions ====================

export async function executeQueryGet(
  query: string,
  options: {
    format?: SparqlResultFormat
    defaultGraphUri?: string
  } = {}
): Promise<SparqlResults> {
  const params = new URLSearchParams()
  params.set('query', query)
  if (options.format) {
    params.set('format', options.format)
  }
  if (options.defaultGraphUri) {
    params.set('default-graph-uri', options.defaultGraphUri)
  }

  return fetchApi<SparqlResults>(`${BASE_PATH}/query?${params}`)
}

export async function executeQueryPost(
  query: string,
  options: {
    format?: SparqlResultFormat
    defaultGraphUri?: string
    namedGraphUri?: string[]
  } = {}
): Promise<SparqlResults> {
  const params = new URLSearchParams()
  if (options.format) {
    params.set('format', options.format)
  }
  const queryString = params.toString() ? `?${params}` : ''

  const body: SparqlQueryRequest = {
    query,
    ...(options.defaultGraphUri !== undefined ? { default_graph_uri: options.defaultGraphUri } : {}),
    ...(options.namedGraphUri !== undefined ? { named_graph_uri: options.namedGraphUri } : {}),
  }

  return fetchApi<SparqlResults>(`${BASE_PATH}/query${queryString}`, {
    method: 'POST',
    body,
  })
}

export async function executeQueryDirect(
  query: string,
  format: SparqlResultFormat = 'json'
): Promise<SparqlResults> {
  const params = new URLSearchParams()
  params.set('format', format)

  const response = await fetch(`${API_BASE}${BASE_PATH}/query?${params}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/sparql-query',
    },
    body: query,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Query failed' }))
    throw new Error(error.detail || 'SPARQL query failed')
  }

  return response.json()
}

export async function executeQueryCsv(query: string): Promise<string> {
  const params = new URLSearchParams()
  params.set('query', query)
  params.set('format', 'csv')

  const response = await fetch(`${API_BASE}${BASE_PATH}/query?${params}`)

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Query failed' }))
    throw new Error(error.detail || 'SPARQL query failed')
  }

  return response.text()
}

export async function executeQueryXml(query: string): Promise<string> {
  const params = new URLSearchParams()
  params.set('query', query)
  params.set('format', 'xml')

  const response = await fetch(`${API_BASE}${BASE_PATH}/query?${params}`)

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Query failed' }))
    throw new Error(error.detail || 'SPARQL query failed')
  }

  return response.text()
}

// ==================== Service Description Functions ====================

export async function getServiceDescriptionTurtle(): Promise<string> {
  const response = await fetch(`${API_BASE}${BASE_PATH}`, {
    headers: {
      Accept: 'text/turtle',
    },
  })

  if (!response.ok) {
    throw new Error('Failed to fetch service description')
  }

  return response.text()
}

export async function getServiceDescriptionJsonLd(): Promise<SparqlServiceDescription> {
  const response = await fetch(`${API_BASE}${BASE_PATH}`, {
    headers: {
      Accept: 'application/ld+json',
    },
  })

  if (!response.ok) {
    throw new Error('Failed to fetch service description')
  }

  return response.json()
}

// ==================== Prefix and Example Functions ====================

export async function getPrefixes(): Promise<SparqlPrefixes> {
  return fetchApi<SparqlPrefixes>(`${BASE_PATH}/prefixes`)
}

export async function getExamples(): Promise<SparqlExamplesResponse> {
  return fetchApi<SparqlExamplesResponse>(`${BASE_PATH}/examples`)
}

// ==================== Utility Functions ====================

export function extractValues(
  results: SparqlResults
): Array<Record<string, string>> {
  return results.results.bindings.map((binding) => {
    const row: Record<string, string> = {}
    for (const [key, value] of Object.entries(binding)) {
      row[key] = value.value
    }
    return row
  })
}

export function buildQueryWithPrefixes(
  queryBody: string,
  prefixes: Record<string, string>
): string {
  const prefixDeclarations = Object.entries(prefixes)
    .map(([prefix, uri]) => `PREFIX ${prefix}: <${uri}>`)
    .join('\n')
  return `${prefixDeclarations}\\${queryBody}`
}

export function isUri(binding: SparqlBinding): boolean {
  return binding.type === 'uri'
}

export function isLiteral(binding: SparqlBinding): boolean {
  return binding.type === 'literal'
}

export function isBlankNode(binding: SparqlBinding): boolean {
  return binding.type === 'bnode'
}

export function getLanguageTag(binding: SparqlBinding): string | undefined {
  return binding['xml:lang']
}

export function getDatatype(binding: SparqlBinding): string | undefined {
  return binding.datatype
}