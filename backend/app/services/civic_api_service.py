# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import contextlib
from app.core.logging import get_logger
import re
from datetime import datetime, timedelta, timezone

import httpx
import yaml

from ..core.config import get_settings

settings = get_settings()

logger = get_logger(__name__)

# In-memory caches
_address_cache: dict[str, tuple[list, datetime]] = {}
_legislators_cache: dict[str, tuple[list, datetime]] = {}

_CACHE_TTL = timedelta(hours=24)
_LEGISLATORS_CACHE_TTL = timedelta(hours=24)

_CENSUS_GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"
_CENSUS_COORD_URL = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"
_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_LEGISLATORS_URL = (
    "https://raw.githubusercontent.com/unitedstates/congress-legislators/"
    "main/legislators-current.yaml"
)

# FIPS state code -> state abbreviation
_FIPS_TO_STATE: dict[str, str] = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
    "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
    "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
    "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
    "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
    "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
    "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
    "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
    "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
    "56": "WY", "60": "AS", "66": "GU", "69": "MP", "72": "PR",
    "78": "VI",
}


class CivicApiService:

    @staticmethod
    async def lookup_reps(address: str) -> tuple[list[dict], bool]:
        cache_key = address.strip().lower()
        cached = _address_cache.get(cache_key)
        if cached is not None:
            results, cached_at = cached
            if datetime.now(timezone.utc) - cached_at < _CACHE_TTL:
                logger.debug("Rep lookup cache hit")
                return results, False

        # Step 1: geocode address via Census Bureau
        geo_info = await CivicApiService._census_geocode(address)
        if geo_info is None:
            return [], False

        state_abbr = geo_info["state"]
        district = geo_info.get("district")

        # Step 2: fetch federal legislators
        legislators = await CivicApiService._get_legislators()

        results: list[dict] = []

        # Match senators (2 per state)
        for leg in legislators:
            term = leg["terms"][-1]
            if term["type"] == "sen" and term["state"] == state_abbr:
                results.append(CivicApiService._legislator_to_rep(leg, "federal"))

        # Match house representative (by district)
        if district is not None:
            for leg in legislators:
                term = leg["terms"][-1]
                if (
                    term["type"] == "rep"
                    and term["state"] == state_abbr
                    and term.get("district") == district
                ):
                    results.append(CivicApiService._legislator_to_rep(leg, "federal"))

        # At-large districts (district 0 or states with 1 rep)
        if district is None or district == 0:
            for leg in legislators:
                term = leg["terms"][-1]
                if (
                    term["type"] == "rep"
                    and term["state"] == state_abbr
                    and term.get("district", 0) in (0, None)
                ):
                    results.append(CivicApiService._legislator_to_rep(leg, "federal"))

        # Step 3: add state-level info from Census geographies if available
        for slld in geo_info.get("state_upper", []):
            results.append({
                "name": "",
                "office": f"State Senate - {slld}",
                "level": "state",
                "party": "",
                "phones": [],
                "emails": [],
                "urls": [f"https://openstates.org/search/?query=&state={state_abbr.lower()}"],
                "photoUrl": None,
                "channels": [],
            })

        for slld in geo_info.get("state_lower", []):
            results.append({
                "name": "",
                "office": f"State House - {slld}",
                "level": "state",
                "party": "",
                "phones": [],
                "emails": [],
                "urls": [f"https://openstates.org/search/?query=&state={state_abbr.lower()}"],
                "photoUrl": None,
                "channels": [],
            })

        # Cache results (only cache non-empty to allow retries on failures)
        if results:
            _address_cache[cache_key] = (results, datetime.now(timezone.utc))

        logger.info(
            "Rep lookup returned %d representatives for: %s",
            len(results),
            address,
        )
        return results, False

    @staticmethod
    async def _census_geocode(address: str) -> dict | None:
        # Try address geocoder first
        geos = await CivicApiService._census_address_geocode(address)

        # Fallback: Nominatim -> Census coordinate geocoder
        if geos is None:
            logger.info("Address geocoder miss, trying Nominatim fallback")
            geos = await CivicApiService._nominatim_fallback(address)

        if geos is None:
            return None

        return CivicApiService._parse_geographies(geos)

    @staticmethod
    async def _census_address_geocode(address: str) -> dict | None:
        params = {
            "address": address,
            "benchmark": "Public_AR_Current",
            "vintage": "Current_Current",
            "format": "json",
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(_CENSUS_GEOCODER_URL, params=params)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, asyncio.TimeoutError) as exc:
            logger.error("Census address geocoder error: %s", exc)
            return None

        matches = data.get("result", {}).get("addressMatches", [])
        if not matches:
            return None

        return matches[0].get("geographies", {})

    @staticmethod
    async def _nominatim_fallback(address: str) -> dict | None:
        # Determine if input looks like a zip code
        stripped = address.strip()
        is_zip = bool(re.match(r"^\d{5}(-\d{4})?$", stripped))

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Build Nominatim query
                nom_params: dict = {"format": "json", "limit": "1", "countrycodes": "us"}
                if is_zip:
                    nom_params["postalcode"] = stripped
                    nom_params["country"] = "US"
                else:
                    nom_params["q"] = address

                response = await client.get(
                    _NOMINATIM_URL,
                    params=nom_params,
                    headers={"User-Agent": settings.library_user_agent},
                )
                response.raise_for_status()
                results = response.json()
        except (httpx.HTTPError, asyncio.TimeoutError) as exc:
            logger.error("Nominatim error: %s", exc)
            return None

        if not results:
            logger.warning("Nominatim: no results for address lookup")
            return None

        lat = results[0].get("lat")
        lon = results[0].get("lon")
        if not lat or not lon:
            return None

        # Now use Census coordinate geocoder
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    _CENSUS_COORD_URL,
                    params={
                        "x": lon,
                        "y": lat,
                        "benchmark": "Public_AR_Current",
                        "vintage": "Current_Current",
                        "format": "json",
                    },
                )
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, asyncio.TimeoutError) as exc:
            logger.error("Census coordinate geocoder error: %s", exc)
            return None

        return data.get("result", {}).get("geographies")

    @staticmethod
    def _parse_geographies(geos: dict) -> dict | None:
        # Extract state FIPS
        state_fips = None
        for geo_values in geos.values():
            for gv in geo_values:
                if "STATE" in gv and gv["STATE"]:
                    state_fips = gv["STATE"]
                    break
            if state_fips:
                break

        if not state_fips or state_fips not in _FIPS_TO_STATE:
            logger.warning("Census geocoder: unknown state FIPS '%s'", state_fips)
            return None

        state_abbr = _FIPS_TO_STATE[state_fips]

        # Extract congressional district
        district = None
        for key, geo_values in geos.items():
            if "congressional" in key.lower():
                for gv in geo_values:
                    cd = gv.get("CD", gv.get("CONGRESSIONAL DISTRICT", ""))
                    if cd and cd not in ("ZZ", "98"):
                        with contextlib.suppress(ValueError, TypeError):
                            district = int(cd)
                        break
                    # Fallback: parse district number from NAME field
                    if district is None:
                        name = gv.get("NAME", "")
                        m = re.search(r"(\d+)", name)
                        if m:
                            district = int(m.group(1))

        # Extract state legislative districts
        state_upper: list[str] = []
        state_lower: list[str] = []
        for key, geo_values in geos.items():
            key_lower = key.lower()
            if "legislative" in key_lower and "upper" in key_lower:
                for gv in geo_values:
                    name = gv.get("NAME", gv.get("BASENAME", ""))
                    if name:
                        state_upper.append(name)
            elif "legislative" in key_lower and "lower" in key_lower:
                for gv in geo_values:
                    name = gv.get("NAME", gv.get("BASENAME", ""))
                    if name:
                        state_lower.append(name)

        return {
            "state": state_abbr,
            "district": district,
            "state_upper": state_upper,
            "state_lower": state_lower,
        }

    @staticmethod
    async def _get_legislators() -> list[dict]:
        cached = _legislators_cache.get("all")
        if cached is not None:
            data, cached_at = cached
            if datetime.now(timezone.utc) - cached_at < _LEGISLATORS_CACHE_TTL:
                return data

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(_LEGISLATORS_URL)
                response.raise_for_status()
                data = yaml.safe_load(response.text)
        except (httpx.HTTPError, asyncio.TimeoutError, yaml.YAMLError) as exc:
            logger.error("Failed to fetch legislators data: %s", exc)
            # Return stale cache if available
            if cached is not None:
                return cached[0]
            return []

        _legislators_cache["all"] = (data, datetime.now(timezone.utc))
        logger.info("Fetched %d current legislators", len(data))
        return data

    @staticmethod
    def _legislator_to_rep(leg: dict, level: str) -> dict:
        name_info = leg.get("name", {})
        term = leg["terms"][-1]
        bio = leg.get("bio", {})

        official_name = name_info.get("official_full", "")
        if not official_name:
            first = name_info.get("first", "")
            last = name_info.get("last", "")
            official_name = f"{first} {last}".strip()

        # Build office title
        if term["type"] == "sen":
            office = f"U.S. Senator - {term['state']}"
        else:
            dist = term.get("district", 0)
            if dist and dist > 0:
                office = f"U.S. Representative - {term['state']}-{dist}"
            else:
                office = f"U.S. Representative - {term['state']} (At-Large)"

        # Party mapping
        party_map = {
            "Democrat": "Democratic",
            "Republican": "Republican",
            "Independent": "Independent",
        }
        party = party_map.get(term.get("party", ""), term.get("party", ""))

        # Contact info
        phones = [term["phone"]] if term.get("phone") else []
        urls = [term["url"]] if term.get("url") else []
        contact_form = term.get("contact_form")
        if contact_form:
            urls.append(contact_form)

        # Photo from bioguide
        bioguide = leg.get("id", {}).get("bioguide", "")
        photo_url = (
            f"https://bioguide.congress.gov/bioguide/photo/{bioguide[0]}/{bioguide}.jpg"
            if bioguide
            else None
        )

        # Social channels
        channels: list[dict] = []
        socials = leg.get("id", {})
        if socials.get("twitter"):
            channels.append({"type": "Twitter", "id": socials["twitter"]})

        return {
            "name": official_name,
            "office": office,
            "level": level,
            "party": party,
            "phones": phones,
            "emails": [],
            "urls": urls,
            "photoUrl": photo_url,
            "channels": channels,
        }
