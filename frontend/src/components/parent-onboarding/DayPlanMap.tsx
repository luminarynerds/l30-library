/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Interactive day-plan map (Leaflet + OpenStreetMap raster tiles).
 *
 * Loaded behind a React.lazy() boundary so neither Leaflet nor its CSS
 * land in the route-level entry chunk. See feedback_l30_perf_entry_chunk_audit
 * and feedback_l30_vite_central_chunk_inlining for why this matters: the
 * staff bundle is already large and we don't want a passive route to add
 * ~140kB gzipped to first-paint.
 *
 * Tiles: OpenStreetMap raster (https://tile.openstreetmap.org/). No API
 * key required; per OSM policy: include a User-Agent (handled via the
 * referrer header automatically) and don't deep-link tile URLs into a
 * mass-deployed app. Staff page = acceptable volume.
 *
 * A11y: this component sits *behind* a sr-only ordered list in the
 * parent page, so a screen-reader user gets the full stop sequence
 * without depending on the map. The map itself is given a role and
 * aria-label so it's announced as one element.
 */
import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

import type { DayPlanStop } from '@/api/parent-onboarding-api'

// Leaflet's default marker icons reference image assets via URLs that
// break under Vite's bundler (the URL is computed at runtime by Leaflet,
// not declared in source). Override the icon paths with the bundled
// assets so pins actually render in production.
//
// This re-binding is intentional and one-time; calling it inside
// useEffect would be wasteful but harmless. We do it at module-eval
// because Leaflet caches the icon options on its prototype.
delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: new URL(
    'leaflet/dist/images/marker-icon-2x.png',
    import.meta.url,
  ).href,
  iconUrl: new URL('leaflet/dist/images/marker-icon.png', import.meta.url).href,
  shadowUrl: new URL('leaflet/dist/images/marker-shadow.png', import.meta.url).href,
})

interface Props {
  stops: Array<DayPlanStop & { lat: number; lng: number }>
}

export default function DayPlanMap({ stops }: Props) {
  const mapEl = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<L.Map | null>(null)

  useEffect(() => {
    if (!mapEl.current) return
    if (mapRef.current) return // already initialized

    const map = L.map(mapEl.current, {
      // Keyboard support is on by default in Leaflet; we don't need to
      // re-enable. We do disable scroll-zoom to avoid hijacking the
      // page scroll on touch devices.
      scrollWheelZoom: false,
    })
    mapRef.current = map

    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map)

    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  // Re-fit bounds + re-render markers whenever stops change.
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    // Drop all existing layers except the tile layer.
    map.eachLayer((layer) => {
      if (layer instanceof L.Marker || layer instanceof L.Polyline) {
        map.removeLayer(layer)
      }
    })

    if (stops.length === 0) {
      map.setView([0, 0], 2)
      return
    }

    const latlngs: L.LatLng[] = stops.map((s) => L.latLng(s.lat, s.lng))
    stops.forEach((stop, idx) => {
      const here = latlngs[idx]
      if (!here) return
      const marker = L.marker(here, {
        title: `Stop ${idx + 1}: ${stop.patron_name ?? stop.address ?? ''}`,
        alt: `Stop ${idx + 1}, ${stop.scheduled_time ?? ''}, ${stop.patron_name ?? ''}, ${stop.address ?? ''}`,
      })
      marker.bindPopup(
        `<strong>Stop ${idx + 1}</strong><br>${stop.scheduled_time ?? ''}<br>${stop.patron_name ?? ''}<br>${stop.address ?? ''}`,
      )
      marker.addTo(map)
    })

    if (latlngs.length > 1) {
      // Connect stops with a polyline so the route is visible. We don't
      // ask OSRM for the actual road geometry here -- the leg ETAs in
      // the address list are the source of truth.
      L.polyline(latlngs, { weight: 3, opacity: 0.6 }).addTo(map)
    }

    const first = latlngs[0]
    if (latlngs.length === 1 && first) {
      map.setView(first, 14)
    } else if (latlngs.length > 0) {
      map.fitBounds(L.latLngBounds(latlngs).pad(0.2))
    }
  }, [stops])

  return (
    <div
      ref={mapEl}
      role="region"
      aria-label="Day plan map"
      data-testid="day-plan-map"
      className="h-64 rounded-xl border border-lsc-dark/10 dark:border-lsc-cream/10 print:hidden"
    />
  )
}
