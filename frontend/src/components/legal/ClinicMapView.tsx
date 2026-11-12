/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import { Icon } from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { LegalClinicSummary } from '@/api/legal-api'
import { getCurrentLocale, useTranslation } from '@/i18n'

const MARKER_CDN = 'https://unpkg.com/leaflet@1.9.4/dist/images'

const defaultIcon = new Icon({
  iconUrl: `${MARKER_CDN}/marker-icon.png`,
  iconRetinaUrl: `${MARKER_CDN}/marker-icon-2x.png`,
  shadowUrl: `${MARKER_CDN}/marker-shadow.png`,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
})

interface ClinicMapViewProps {
  clinics: LegalClinicSummary[]
}

const ZANESVILLE_CENTER: [number, number] = [39.9403, -82.0132]
const DEFAULT_ZOOM = 11

const formatDate = (dateStr: string): string =>
  new Date(dateStr).toLocaleDateString(getCurrentLocale(), {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })

export default function ClinicMapView({ clinics }: ClinicMapViewProps): React.ReactElement {
  const { t } = useTranslation()
  const mappable = clinics.filter((c) => c.latitude != null && c.longitude != null)

  return (
    <div className="rounded-xl overflow-hidden border border-lsc-border dark:border-earth-700">
      <MapContainer
        center={ZANESVILLE_CENTER}
        zoom={DEFAULT_ZOOM}
        style={{ height: '400px', width: '100%' }}
        scrollWheelZoom={false}
      >
        <TileLayer
          attribution={'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {mappable.map((clinic) => (
          <Marker
            key={clinic.id}
            position={[clinic.latitude!, clinic.longitude!]}
            icon={defaultIcon}
          >
            <Popup>
              <div className="text-sm">
                <p className="font-semibold">{clinic.title}</p>
                <p className="text-earth-600">{formatDate(clinic.date)}</p>
                <p className={clinic.spots_available > 0 ? 'text-status-success-700' : 'text-status-danger-700'}>
                  {clinic.spots_available > 0
                    ? t('components.legal.clinicsTab.spotsAvailable', { count: clinic.spots_available })
                    : t('components.legal.clinicsTab.full', 'Full')}
                </p>
                {clinic.topic_name && (
                  <p className="text-lsc-rose text-xs mt-1">{clinic.topic_name}</p>
                )}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
      {mappable.length === 0 && (
        <p className="text-center text-sm text-lsc-dark/50 dark:text-lsc-cream/50 py-2">
          {t('components.legal.clinicMapView.noClinicLocationsMapped', 'No clinic locations mapped yet.')}
        </p>
      )}
    </div>
  )
}
