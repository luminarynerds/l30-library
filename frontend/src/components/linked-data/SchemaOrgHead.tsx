/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-hooks/exhaustive-deps */
/* eslint-disable react-refresh/only-export-components */
import * as Sentry from "@/lib/sentry-lazy"
/**
 * SchemaOrgHead Component
 *
 * Injects Schema.org JSON-LD structured data into the page head
 * for SEO and rich snippets in search results.
 */

import { useEffect, useState } from 'react'
import {
  getWorkSchemaOrg,
  getInstanceSchemaOrg,
  getCatalogItemSchemaOrg,
  getLibrarySchemaOrg,
  type SchemaOrgMarkup,
} from '@/api/linked-data-api'

interface SchemaOrgHeadProps {
  /** Type of entity to get Schema.org markup for */
  type: 'work' | 'instance' | 'catalog-item' | 'library'
  /** Entity ID (not needed for 'library' type) */
  id?: number
}

export default function SchemaOrgHead({ type, id }: SchemaOrgHeadProps): null {
  const [markup, setMarkup] = useState<SchemaOrgMarkup | null>(null)

  const loadSchemaOrg = async () => {
    try {
      let data: SchemaOrgMarkup

      switch (type) {
        case 'work':
          if (!id) throw new Error('Work ID is required')
          data = await getWorkSchemaOrg(id)
          break
        case 'instance':
          if (!id) throw new Error('Instance ID is required')
          data = await getInstanceSchemaOrg(id)
          break
        case 'catalog-item':
          if (!id) throw new Error('Catalog item ID is required')
          data = await getCatalogItemSchemaOrg(id)
          break
        case 'library':
          data = await getLibrarySchemaOrg()
          break
        default:
          throw new Error(`Unknown type: ${type}`)
      }

      setMarkup(data)
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)))
    }
  }


  useEffect(() => {


    loadSchemaOrg()

  }, [type, id])

  useEffect(() => {
    if (!markup) return

    // Create or update the JSON-LD script tag
    const scriptId = `schema-org-${type}-${id || 'main'}`
    let script = document.getElementById(scriptId) as HTMLScriptElement | null

    if (!script) {
      script = document.createElement('script')
      script.id = scriptId
      script.type = 'application/ld+json'
      document.head.appendChild(script)
    }

    script.textContent = JSON.stringify(markup)

    // Cleanup on unmount
    return () => {
      const existingScript = document.getElementById(scriptId)
      if (existingScript) {
        existingScript.remove()
      }
    }
  }, [markup, type, id])

  // This component doesn't render anything visible
  return null
}

export function useSchemaOrg(markup: SchemaOrgMarkup | null, id: string): void {
  useEffect(() => {
    if (!markup) return

    const scriptId = `schema-org-custom-${id}`
    let script = document.getElementById(scriptId) as HTMLScriptElement | null

    if (!script) {
      script = document.createElement('script')
      script.id = scriptId
      script.type = 'application/ld+json'
      document.head.appendChild(script)
    }

    script.textContent = JSON.stringify(markup)

    return () => {
      const existingScript = document.getElementById(scriptId)
      if (existingScript) {
        existingScript.remove()
      }
    }
  }, [markup, id])
}

export function createBookSchema(options: {
  name: string
  author?: string | string[]
  isbn?: string
  publisher?: string
  datePublished?: string
  description?: string
  image?: string
  url?: string
}): SchemaOrgMarkup {
  const schema: SchemaOrgMarkup = {
    '@context': 'https://schema.org',
    '@type': 'Book',
    '@id': options.url || '',
    name: options.name,
  }

  if (options.author) {
    const authors = Array.isArray(options.author) ? options.author : [options.author]
    schema.author = authors.map((name) => ({
      '@type': 'Person',
      name,
    }))
  }

  if (options.isbn) {
    schema.isbn = options.isbn
  }

  if (options.publisher) {
    schema.publisher = {
      '@type': 'Organization',
      name: options.publisher,
    }
  }

  if (options.datePublished) {
    schema.datePublished = options.datePublished
  }

  if (options.description) {
    schema.description = options.description
  }

  if (options.image) {
    schema.image = options.image
  }

  if (options.url) {
    schema.url = options.url
  }

  return schema
}

export function createLibrarySchema(options: {
  name: string
  url?: string
  logo?: string
  address?: {
    streetAddress: string
    city: string
    state: string
    postalCode: string
    country?: string
  }
  telephone?: string
  email?: string
  openingHours?: string[]
}): SchemaOrgMarkup {
  const schema: SchemaOrgMarkup = {
    '@context': 'https://schema.org',
    '@type': 'Library',
    '@id': options.url || '',
    name: options.name,
  }

  if (options.url) {
    schema.url = options.url
  }

  if (options.logo) {
    schema.logo = options.logo
  }

  if (options.address) {
    schema.address = {
      '@type': 'PostalAddress',
      streetAddress: options.address.streetAddress,
      addressLocality: options.address.city,
      addressRegion: options.address.state,
      postalCode: options.address.postalCode,
      addressCountry: options.address.country || 'US',
    }
  }

  if (options.telephone) {
    schema.telephone = options.telephone
  }

  if (options.email) {
    schema.email = options.email
  }

  if (options.openingHours) {
    schema.openingHoursSpecification = options.openingHours.map((hours) => {
      const [days, times] = hours.split(' ')
      const [opens, closes] = times?.split('-') || []
      return {
        '@type': 'OpeningHoursSpecification',
        dayOfWeek: days,
        opens,
        closes,
      }
    })
  }

  return schema
}
