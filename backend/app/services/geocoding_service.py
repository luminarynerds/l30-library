# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import math
import re
from typing import Optional

import httpx

from ..core.config import get_settings


class GeocodingService:

    # In-memory cache for geocoded addresses (production would use Redis)
    _geocode_cache: dict[str, tuple[float, float]] = {}

    # Earth's radius in miles
    EARTH_RADIUS_MILES = 3958.8

    @staticmethod
    def haversine_distance(
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        # Haversine formula
        a = (
            math.sin(delta_lat / 2) ** 2 +
            math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return GeocodingService.EARTH_RADIUS_MILES * c

    @staticmethod
    async def geocode_address(address: str) -> Optional[tuple[float, float]]:
        if not address:
            return None

        # Check cache first
        cache_key = address.lower().strip()
        if cache_key in GeocodingService._geocode_cache:
            return GeocodingService._geocode_cache[cache_key]

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={
                        "q": address,
                        "format": "json",
                        "limit": 1
                    },
                    headers={
                        # Nominatim requires a User-Agent
                        "User-Agent": branding.USER_AGENT
                    }
                )
                response.raise_for_status()
                data = response.json()

                if data:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    # Cache the result
                    GeocodingService._geocode_cache[cache_key] = (lat, lon)
                    return (lat, lon)

        except (httpx.HTTPError, ValueError, KeyError, IndexError):
            # Log error in production, but don't fail the operation
            pass

        return None

    @staticmethod
    def extract_zip_code(address: str) -> Optional[str]:
        if not address:
            return None
        # Match 5-digit or 5+4 digit ZIP codes
        match = re.search(r'\b(\d{5})(?:-\d{4})?\b', address)
        return match.group(1) if match else None

    @staticmethod
    async def optimize_route_by_distance(
        stops: list[dict],
        start_coords: Optional[tuple[float, float]] = None
    ) -> tuple[list[dict], float, float]:
        if len(stops) < 2:
            return stops, 0.0, len(stops) * 15.0

        # Geocode any stops missing coordinates
        geocoded_stops = []
        for stop in stops:
            lat = stop.get("lat")
            lon = stop.get("lon")

            if lat is None or lon is None:
                coords = await GeocodingService.geocode_address(stop.get("address", ""))
                if coords:
                    lat, lon = coords

            geocoded_stops.append({
                **stop,
                "lat": lat,
                "lon": lon
            })

        # Filter stops with valid coordinates
        valid_stops = [s for s in geocoded_stops if s["lat"] is not None and s["lon"] is not None]
        invalid_stops = [s for s in geocoded_stops if s["lat"] is None or s["lon"] is None]

        if len(valid_stops) < 2:
            # Not enough geocoded stops, return original order
            total_time = len(stops) * 15.0  # 15 mins per stop estimate
            return stops, len(stops) * 2.0, total_time

        # Nearest-neighbor algorithm
        optimized = []
        remaining = valid_stops.copy()

        # Start from provided coordinates or first stop
        if start_coords:
            current_lat, current_lon = start_coords
        else:
            first = remaining.pop(0)
            optimized.append(first)
            current_lat, current_lon = first["lat"], first["lon"]

        total_distance = 0.0

        while remaining:
            # Find nearest unvisited stop
            nearest_idx = 0
            nearest_distance = float('inf')

            for i, stop in enumerate(remaining):
                dist = GeocodingService.haversine_distance(
                    current_lat, current_lon,
                    stop["lat"], stop["lon"]
                )
                if dist < nearest_distance:
                    nearest_distance = dist
                    nearest_idx = i

            # Move to nearest stop
            nearest = remaining.pop(nearest_idx)
            optimized.append(nearest)
            total_distance += nearest_distance
            current_lat, current_lon = nearest["lat"], nearest["lon"]

        # Add any stops that couldn't be geocoded at the end
        optimized.extend(invalid_stops)

        # Estimate duration: average 25 mph driving + 15 mins per stop
        driving_time = (total_distance / 25) * 60  # Convert hours to minutes
        stop_time = len(optimized) * 15  # 15 mins per delivery
        estimated_duration = driving_time + stop_time

        return optimized, total_distance, estimated_duration

    @staticmethod
    def calculate_route_distance(
        stops: list[tuple[float, float]]
    ) -> float:
        if len(stops) < 2:
            return 0.0

        total = 0.0
        for i in range(len(stops) - 1):
            total += GeocodingService.haversine_distance(
                stops[i][0], stops[i][1],
                stops[i + 1][0], stops[i + 1][1]
            )

        return total
