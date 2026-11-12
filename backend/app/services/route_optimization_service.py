# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
import math
from dataclasses import dataclass
from datetime import date, time
from enum import StrEnum
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.config import get_settings
from ..models.home_delivery import Delivery, DeliveryRoute, DeliveryVolunteer

logger = get_logger(__name__)


class MappingProvider(StrEnum):
    NONE = "none"  # Use basic estimation
    GOOGLE_MAPS = "google_maps"
    OPENSTREETMAP = "openstreetmap"
    MAPBOX = "mapbox"


@dataclass
class GeoCoordinate:
    latitude: float
    longitude: float
    address: str


@dataclass
class RouteStop:
    delivery_id: int
    address: str
    coordinates: Optional[GeoCoordinate]
    time_window_start: Optional[str]
    time_window_end: Optional[str]
    estimated_service_time_minutes: int = 10
    priority: int = 1  # 1 = normal, 2 = high, 3 = critical


@dataclass
class OptimizedRoute:
    stops: list[RouteStop]
    total_distance_miles: float
    total_duration_minutes: int
    route_geometry: Optional[dict]  # GeoJSON
    warnings: list[str]


@dataclass
class RouteOptimizationConfig:
    provider: MappingProvider = MappingProvider.NONE
    api_key: Optional[str] = None
    start_location: Optional[str] = None
    end_location: Optional[str] = None  # If different from start
    return_to_start: bool = True
    optimize_for: str = "distance"  # "distance" or "time"
    avoid_highways: bool = False
    avoid_tolls: bool = False
    max_stops_per_route: int = 20
    service_time_per_stop_minutes: int = 10
    travel_speed_mph: float = 25.0  # Average urban speed


class RouteOptimizationService:

    def __init__(self, config: Optional[RouteOptimizationConfig] = None):
        self.config = config or RouteOptimizationConfig()

    async def optimize_route(
        self,
        db: AsyncSession,
        route_id: int,
        start_location: Optional[str] = None
    ) -> OptimizedRoute:
        # Get route with deliveries
        result = await db.execute(
            select(DeliveryRoute)
            .options(selectinload(DeliveryRoute.deliveries))
            .where(DeliveryRoute.id == route_id)
        )
        route = result.scalar_one_or_none()
        if not route:
            raise ValueError("Route not found")

        deliveries = list(route.deliveries)
        if len(deliveries) < 2:
            return OptimizedRoute(
                stops=[self._delivery_to_stop(d) for d in deliveries],
                total_distance_miles=0,
                total_duration_minutes=self.config.service_time_per_stop_minutes * len(deliveries),
                route_geometry=None,
                warnings=[]
            )

        # Convert deliveries to route stops
        stops = [self._delivery_to_stop(d) for d in deliveries]

        # Geocode addresses if we have a mapping provider
        if self.config.provider != MappingProvider.NONE:
            stops = await self._geocode_stops(stops)

        # Optimize route order
        if self.config.provider == MappingProvider.GOOGLE_MAPS:
            optimized = await self._optimize_with_google_maps(stops, start_location)
        elif self.config.provider == MappingProvider.OPENSTREETMAP:
            optimized = await self._optimize_with_osrm(stops, start_location)
        elif self.config.provider == MappingProvider.MAPBOX:
            optimized = await self._optimize_with_mapbox(stops, start_location)
        else:
            optimized = self._optimize_with_basic_algorithm(stops, start_location)

        # Update delivery order in database
        for i, stop in enumerate(optimized.stops):
            for delivery in deliveries:
                if delivery.id == stop.delivery_id:
                    delivery.route_order = i + 1
                    break

        # Update route statistics
        route.optimized_order = [stop.delivery_id for stop in optimized.stops]
        route.estimated_distance_miles = optimized.total_distance_miles
        route.estimated_duration_minutes = optimized.total_duration_minutes
        if optimized.route_geometry:
            route.route_geometry = optimized.route_geometry

        await db.commit()

        return optimized

    def _delivery_to_stop(self, delivery: Delivery) -> RouteStop:
        return RouteStop(
            delivery_id=delivery.id,
            address=delivery.delivery_address or "",
            coordinates=None,
            time_window_start=delivery.scheduled_time_start,
            time_window_end=delivery.scheduled_time_end,
            estimated_service_time_minutes=self.config.service_time_per_stop_minutes
        )

    async def _geocode_stops(self, stops: list[RouteStop]) -> list[RouteStop]:
        # Placeholder for geocoding integration
        # In production, this would call the mapping API
        for stop in stops:
            coords = self._estimate_coordinates_from_address(stop.address)
            if coords:
                stop.coordinates = coords
        return stops

    def _estimate_coordinates_from_address(self, address: str) -> Optional[GeoCoordinate]:
        # For now, return None - actual geocoding would be implemented
        # with the mapping provider
        return None

    def _optimize_with_basic_algorithm(
        self,
        stops: list[RouteStop],
        start_location: Optional[str] = None
    ) -> OptimizedRoute:
        if not stops:
            return OptimizedRoute(
                stops=[],
                total_distance_miles=0,
                total_duration_minutes=0,
                route_geometry=None,
                warnings=[]
            )

        warnings = []

        # If we have coordinates, use nearest-neighbor
        stops_with_coords = [s for s in stops if s.coordinates]
        if len(stops_with_coords) == len(stops) and len(stops) > 1:
            optimized_stops = self._nearest_neighbor_optimization(stops)
        else:
            # Fall back to sorting by address (ZIP code/street grouping)
            optimized_stops = self._sort_by_address_grouping(stops)
            if len(stops_with_coords) < len(stops):
                warnings.append(
                    f"Could not geocode {len(stops) - len(stops_with_coords)} addresses. "
                    "Route order is estimated based on address similarity."
                )

        # Estimate distance and duration
        total_distance = self._estimate_total_distance(optimized_stops)
        total_duration = self._estimate_total_duration(optimized_stops, total_distance)

        return OptimizedRoute(
            stops=optimized_stops,
            total_distance_miles=round(total_distance, 1),
            total_duration_minutes=total_duration,
            route_geometry=None,
            warnings=warnings
        )

    def _nearest_neighbor_optimization(self, stops: list[RouteStop]) -> list[RouteStop]:
        if len(stops) <= 1:
            return stops

        remaining = stops.copy()
        optimized = [remaining.pop(0)]  # Start with first stop

        while remaining:
            current = optimized[-1]
            nearest = min(
                remaining,
                key=lambda s: self._haversine_distance(
                    current.coordinates, s.coordinates
                ) if current.coordinates and s.coordinates else float('inf')
            )
            optimized.append(nearest)
            remaining.remove(nearest)

        return optimized

    def _sort_by_address_grouping(self, stops: list[RouteStop]) -> list[RouteStop]:
        def address_sort_key(stop: RouteStop) -> tuple:
            addr = stop.address.upper()
            # Extract ZIP code if present (assumes US format)
            zip_code = ""
            parts = addr.split()
            for part in parts:
                if len(part) == 5 and part.isdigit():
                    zip_code = part
                    break
            # Use first part of street for grouping
            street = parts[0] if parts else ""
            return (zip_code, street, addr)

        return sorted(stops, key=address_sort_key)

    def _haversine_distance(
        self,
        coord1: Optional[GeoCoordinate],
        coord2: Optional[GeoCoordinate]
    ) -> float:
        if not coord1 or not coord2:
            return float('inf')

        R = 3959  # Earth's radius in miles

        lat1, lon1 = math.radians(coord1.latitude), math.radians(coord1.longitude)
        lat2, lon2 = math.radians(coord2.latitude), math.radians(coord2.longitude)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    def _estimate_total_distance(self, stops: list[RouteStop]) -> float:
        if len(stops) < 2:
            return 0

        # If we have coordinates, calculate actual distances
        total = 0
        for i in range(len(stops) - 1):
            if stops[i].coordinates and stops[i+1].coordinates:
                total += self._haversine_distance(
                    stops[i].coordinates,
                    stops[i+1].coordinates
                )
            else:
                # Estimate 2-3 miles between stops for urban area
                total += 2.5

        return total

    def _estimate_total_duration(self, stops: list[RouteStop], distance_miles: float) -> int:
        # Travel time
        travel_time = (distance_miles / self.config.travel_speed_mph) * 60

        # Service time at each stop
        service_time = sum(s.estimated_service_time_minutes for s in stops)

        return int(travel_time + service_time)

    async def _optimize_with_google_maps(
        self,
        stops: list[RouteStop],
        start_location: Optional[str] = None
    ) -> OptimizedRoute:
        settings = get_settings()
        api_key = settings.google_maps_api_key

        if not api_key:
            logger.warning("Google Maps API key not configured")
            return self._optimize_with_basic_algorithm(stops, start_location)

        stops_with_coords = [s for s in stops if s.coordinates]
        if len(stops_with_coords) < 2:
            logger.warning("Not enough geocoded stops for Google Maps optimization")
            return self._optimize_with_basic_algorithm(stops, start_location)

        try:
            # Build waypoints (intermediate stops)
            origin = f"{stops_with_coords[0].coordinates.latitude},{stops_with_coords[0].coordinates.longitude}"
            destination = origin if self.config.return_to_start else f"{stops_with_coords[-1].coordinates.latitude},{stops_with_coords[-1].coordinates.longitude}"

            waypoints = "|".join(
                f"{s.coordinates.latitude},{s.coordinates.longitude}"
                for s in stops_with_coords[1:-1] if s.coordinates
            )

            # Call Google Maps Directions API
            url = "https://maps.googleapis.com/maps/api/directions/json"
            params = {
                "origin": origin,
                "destination": destination,
                "waypoints": f"optimize:true|{waypoints}" if waypoints else None,
                "key": api_key,
                "mode": "driving"
            }
            params = {k: v for k, v in params.items() if v is not None}

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            if data.get("status") != "OK":
                logger.error(f"Google Maps error: {data.get('status')}")
                return self._optimize_with_basic_algorithm(stops, start_location)

            routes = data.get("routes", [])
            if not routes:
                return self._optimize_with_basic_algorithm(stops, start_location)

            route = routes[0]
            waypoint_order = route.get("waypoint_order", [])

            # Reorder stops based on optimized waypoint order
            optimized_stops = [stops_with_coords[0]]  # Start with origin
            for idx in waypoint_order:
                # waypoint_order indices refer to intermediate waypoints (1 to n-2)
                if idx + 1 < len(stops_with_coords) - 1:
                    optimized_stops.append(stops_with_coords[idx + 1])
            if not self.config.return_to_start:
                optimized_stops.append(stops_with_coords[-1])  # Add destination

            # Add stops without coordinates at the end
            for s in stops:
                if s not in optimized_stops:
                    optimized_stops.append(s)

            # Calculate totals from legs
            legs = route.get("legs", [])
            total_distance_meters = sum(leg.get("distance", {}).get("value", 0) for leg in legs)
            total_duration_seconds = sum(leg.get("duration", {}).get("value", 0) for leg in legs)

            return OptimizedRoute(
                stops=optimized_stops,
                total_distance_miles=round(total_distance_meters / 1609.34, 1),
                total_duration_minutes=int(total_duration_seconds / 60) + (len(stops) * self.config.service_time_per_stop_minutes),
                route_geometry=route.get("overview_polyline", {}).get("points"),
                warnings=[]
            )

        except httpx.HTTPError as e:
            logger.error(f"Google Maps HTTP error: {e}")
            return self._optimize_with_basic_algorithm(stops, start_location)
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Google Maps optimization failed: {e}")
            return self._optimize_with_basic_algorithm(stops, start_location)

    async def _optimize_with_osrm(
        self,
        stops: list[RouteStop],
        start_location: Optional[str] = None
    ) -> OptimizedRoute:
        settings = get_settings()
        osrm_url = settings.osrm_server_url

        # Filter stops with coordinates
        stops_with_coords = [s for s in stops if s.coordinates]
        if len(stops_with_coords) < 2:
            logger.warning("Not enough geocoded stops for OSRM optimization")
            return self._optimize_with_basic_algorithm(stops, start_location)

        try:
            # Build coordinates string for OSRM
            coords = ";".join(
                f"{s.coordinates.longitude},{s.coordinates.latitude}"
                for s in stops_with_coords
            )

            # Call OSRM trip endpoint for TSP optimization
            url = f"{osrm_url}/trip/v1/driving/{coords}"
            params = {
                "roundtrip": "true" if self.config.return_to_start else "false",
                "source": "first",
                "geometries": "geojson",
                "overview": "full",
                "annotations": "duration,distance"
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            if data.get("code") != "Ok":
                logger.error(f"OSRM error: {data.get('message', 'Unknown error')}")
                return self._optimize_with_basic_algorithm(stops, start_location)

            # Parse optimized order from waypoints
            trips = data.get("trips", [])
            if not trips:
                return self._optimize_with_basic_algorithm(stops, start_location)

            trip = trips[0]
            waypoints = data.get("waypoints", [])

            # Reorder stops based on OSRM optimization
            optimized_stops = []
            for wp in sorted(waypoints, key=lambda w: w.get("waypoint_index", 0)):
                original_idx = wp.get("waypoint_index", 0)
                if original_idx < len(stops_with_coords):
                    optimized_stops.append(stops_with_coords[original_idx])

            # Add stops without coordinates at the end
            for s in stops:
                if s not in optimized_stops:
                    optimized_stops.append(s)

            # Extract distance and duration
            total_distance_meters = trip.get("distance", 0)
            total_duration_seconds = trip.get("duration", 0)

            return OptimizedRoute(
                stops=optimized_stops,
                total_distance_miles=round(total_distance_meters / 1609.34, 1),
                total_duration_minutes=int(total_duration_seconds / 60) + (len(stops) * self.config.service_time_per_stop_minutes),
                route_geometry=trip.get("geometry"),
                warnings=[]
            )

        except httpx.HTTPError as e:
            logger.error(f"OSRM HTTP error: {e}")
            return self._optimize_with_basic_algorithm(stops, start_location)
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"OSRM optimization failed: {e}")
            return self._optimize_with_basic_algorithm(stops, start_location)

    async def _optimize_with_mapbox(
        self,
        stops: list[RouteStop],
        start_location: Optional[str] = None
    ) -> OptimizedRoute:
        settings = get_settings()
        api_key = settings.mapbox_api_key

        if not api_key:
            logger.warning("Mapbox API key not configured")
            return self._optimize_with_basic_algorithm(stops, start_location)

        stops_with_coords = [s for s in stops if s.coordinates]
        if len(stops_with_coords) < 2:
            logger.warning("Not enough geocoded stops for Mapbox optimization")
            return self._optimize_with_basic_algorithm(stops, start_location)

        try:
            # Build coordinates string
            coords = ";".join(
                f"{s.coordinates.longitude},{s.coordinates.latitude}"
                for s in stops_with_coords
            )

            # Call Mapbox Optimization API
            url = f"https://api.mapbox.com/optimized-trips/v1/mapbox/driving/{coords}"
            params = {
                "access_token": api_key,
                "roundtrip": "true" if self.config.return_to_start else "false",
                "source": "first",
                "geometries": "geojson",
                "overview": "full"
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            if data.get("code") != "Ok":
                logger.error(f"Mapbox error: {data.get('message', 'Unknown error')}")
                return self._optimize_with_basic_algorithm(stops, start_location)

            trips = data.get("trips", [])
            if not trips:
                return self._optimize_with_basic_algorithm(stops, start_location)

            trip = trips[0]
            waypoints = data.get("waypoints", [])

            # Reorder stops
            optimized_stops = []
            for wp in sorted(waypoints, key=lambda w: w.get("waypoint_index", 0)):
                original_idx = wp.get("waypoint_index", 0)
                if original_idx < len(stops_with_coords):
                    optimized_stops.append(stops_with_coords[original_idx])

            for s in stops:
                if s not in optimized_stops:
                    optimized_stops.append(s)

            total_distance_meters = trip.get("distance", 0)
            total_duration_seconds = trip.get("duration", 0)

            return OptimizedRoute(
                stops=optimized_stops,
                total_distance_miles=round(total_distance_meters / 1609.34, 1),
                total_duration_minutes=int(total_duration_seconds / 60) + (len(stops) * self.config.service_time_per_stop_minutes),
                route_geometry=trip.get("geometry"),
                warnings=[]
            )

        except httpx.HTTPError as e:
            logger.error(f"Mapbox HTTP error: {e}")
            return self._optimize_with_basic_algorithm(stops, start_location)
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Mapbox optimization failed: {e}")
            return self._optimize_with_basic_algorithm(stops, start_location)

    async def get_distance_matrix(
        self,
        addresses: list[str]
    ) -> list[list[float]]:
        n = len(addresses)
        matrix = [[0.0] * n for _ in range(n)]

        if self.config.provider == MappingProvider.NONE:
            # Estimate distances as 2-3 miles between unique addresses
            for i in range(n):
                for j in range(n):
                    if i != j:
                        matrix[i][j] = 2.5
        else:
            # Would call mapping API for actual distances
            # Placeholder returns estimated distances
            for i in range(n):
                for j in range(n):
                    if i != j:
                        matrix[i][j] = 2.5

        return matrix

    async def estimate_arrival_times(
        self,
        route_id: int,
        db: AsyncSession,
        start_time: time
    ) -> list[dict]:
        result = await db.execute(
            select(DeliveryRoute)
            .options(selectinload(DeliveryRoute.deliveries))
            .where(DeliveryRoute.id == route_id)
        )
        route = result.scalar_one_or_none()
        if not route:
            return []

        # Sort deliveries by route order
        deliveries = sorted(
            route.deliveries,
            key=lambda d: d.route_order or 0
        )

        arrivals = []
        current_minutes = start_time.hour * 60 + start_time.minute

        for i, delivery in enumerate(deliveries):
            if i > 0:
                # Add travel time (estimated 6-8 minutes between stops)
                current_minutes += 7

            arrival_hour = current_minutes // 60
            arrival_minute = current_minutes % 60

            arrivals.append({
                "delivery_id": delivery.id,
                "stop_number": i + 1,
                "estimated_arrival": f"{arrival_hour:02d}:{arrival_minute:02d}",
                "address": delivery.delivery_address
            })

            # Add service time
            current_minutes += self.config.service_time_per_stop_minutes

        return arrivals


class ClusteringService:

    @staticmethod
    async def cluster_deliveries_by_area(
        db: AsyncSession,
        delivery_ids: list[int],
        max_deliveries_per_cluster: int = 10
    ) -> list[list[int]]:
        result = await db.execute(
            select(Delivery).where(Delivery.id.in_(delivery_ids))
        )
        deliveries = result.scalars().all()

        # Group by ZIP code (simple clustering)
        zip_groups: dict[str, list[int]] = {}
        for delivery in deliveries:
            zip_code = ClusteringService._extract_zip(delivery.delivery_address)
            if zip_code not in zip_groups:
                zip_groups[zip_code] = []
            zip_groups[zip_code].append(delivery.id)

        # Split large groups and merge small ones
        clusters = []
        current_cluster = []

        for zip_code, ids in sorted(zip_groups.items()):
            for id in ids:
                current_cluster.append(id)
                if len(current_cluster) >= max_deliveries_per_cluster:
                    clusters.append(current_cluster)
                    current_cluster = []

        if current_cluster:
            clusters.append(current_cluster)

        return clusters

    @staticmethod
    def _extract_zip(address: str) -> str:
        if not address:
            return "00000"

        parts = address.split()
        for part in parts:
            # US ZIP code (5 digits or 5+4)
            clean = part.replace("-", "")
            if len(clean) >= 5 and clean[:5].isdigit():
                return clean[:5]

        return "00000"

    @staticmethod
    async def suggest_routes_for_date(
        db: AsyncSession,
        target_date: date,
        max_routes: int = 5
    ) -> list[dict]:
        from ..models.home_delivery import DeliveryStatus

        # Get all scheduled deliveries for the date
        result = await db.execute(
            select(Delivery)
            .where(
                Delivery.scheduled_date == target_date,
                Delivery.status == DeliveryStatus.scheduled,
                Delivery.route_id.is_(None)
            )
        )
        deliveries = result.scalars().all()

        if not deliveries:
            return []

        delivery_ids = [d.id for d in deliveries]
        clusters = await ClusteringService.cluster_deliveries_by_area(
            db, delivery_ids
        )

        suggestions = []
        for i, cluster in enumerate(clusters[:max_routes]):
            cluster_deliveries = [d for d in deliveries if d.id in cluster]
            suggestions.append({
                "suggested_name": f"Route {target_date.strftime('%m/%d')} - Area {i + 1}",
                "delivery_ids": cluster,
                "delivery_count": len(cluster),
                "addresses": [d.delivery_address for d in cluster_deliveries]
            })

        return suggestions
