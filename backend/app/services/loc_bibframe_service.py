# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import json
import re
from datetime import datetime
from typing import Any, Optional
from urllib.parse import quote, urlencode

import httpx

from ..models.bibframe import (
    AuthorityLink,
    AuthoritySource,
    BibframeContributor,
    BibframeInstance,
    BibframeItem,
    BibframeSubject,
    BibframeWork,
    CarrierType,
    ContributorRole,
    InstanceType,
    MediaType,
    WorkType,
)
from ..utils.title_extraction_utils import (
    safe_extract_title,
    extract_subtitle,
    normalize_title_for_sorting,
)
from ..utils.identifier_normalizer import IdentifierNormalizer
from ..core.branding import branding


class LocBibframeService:

    # LC API endpoints
    LC_BASE_URL = "https://id.loc.gov"
    LC_SEARCH_URL = "https://id.loc.gov/search/"
    LC_BIBFRAME_BASE = "https://id.loc.gov/resources/works"
    LC_AUTHORITIES_BASE = "https://id.loc.gov/authorities"

    # SRU search endpoint (more structured search)
    SRU_BASE_URL = "https://lx2.loc.gov/sru/lcdb"

    # Content negotiation headers
    JSONLD_HEADERS = {
        "Accept": "application/ld+json",
        "User-Agent": branding.USER_AGENT,
    }

    # Work type mapping from LC BIBFRAME to our types
    LC_WORK_TYPE_MAP = {
        "Text": WorkType.text,
        "StillImage": WorkType.still_image,
        "MovingImage": WorkType.two_dimensional_moving_image,
        "Audio": WorkType.spoken_word,
        "Dataset": WorkType.computer_dataset,
        "Software": WorkType.computer_program,
        "NotatedMusic": WorkType.notated_music,
        "Cartography": WorkType.cartographic_image,
        "MixedMaterial": WorkType.other,
        "Manuscript": WorkType.text,
    }

    # Instance type mapping
    LC_INSTANCE_TYPE_MAP = {
        "Print": InstanceType.print,
        "Electronic": InstanceType.electronic,
        "Archival": InstanceType.archive,
        "Manuscript": InstanceType.manuscript,
        "Tactile": InstanceType.tactile,
    }

    def __init__(self, timeout: int = 30, max_concurrent_requests: int = 5):
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        # Semaphore to limit concurrent HTTP requests
        # Prevents overwhelming the LC API with too many simultaneous requests
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers=self.JSONLD_HEADERS,
                follow_redirects=True,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # =========================================================================
    # Search Methods
    # =========================================================================

    async def search(
        self,
        query: str,
        search_type: str = "keyword",
        max_results: int = 10,
    ) -> dict[str, Any]:
        client = await self._get_client()

        # Build search query based on type
        if search_type == "isbn":
            # Use ISBN search
            clean_isbn = re.sub(r"[^0-9Xx]", "", query)
            search_query = f"bf:identifiedBy.bf:Isbn.rdf:value:{clean_isbn}"
        elif search_type == "lccn":
            # Use LCCN search
            clean_lccn = re.sub(r"\s+", "", query)
            search_query = f"bf:identifiedBy.bf:Lccn.rdf:value:{clean_lccn}"
        elif search_type == "title":
            search_query = f"bf:title.bf:mainTitle:{query}"
        elif search_type == "author":
            search_query = f"bf:contribution.bf:agent.rdfs:label:{query}"
        elif search_type == "subject":
            search_query = f"bf:subject.rdfs:label:{query}"
        else:
            # General keyword search
            search_query = query

        # Construct search URL
        params = {
            "q": search_query,
            "format": "json",
            "count": max_results,
        }
        url = f"{self.LC_SEARCH_URL}?{urlencode(params)}"

        try:
            response = await client.get(url)
            response.raise_for_status()

            data = response.json()
            results = self._parse_search_results(data, query)
            return results

        except httpx.HTTPStatusError as e:
            return {
                "results": [],
                "total_results": 0,
                "query": query,
                "error": f"HTTP error: {e.response.status_code}",
            }
        except (httpx.HTTPError, asyncio.TimeoutError, json.JSONDecodeError, ValueError) as e:
            return {
                "results": [],
                "total_results": 0,
                "query": query,
                "error": str(e),
            }

    async def search_works(
        self,
        title: Optional[str] = None,
        author: Optional[str] = None,
        subject: Optional[str] = None,
        isbn: Optional[str] = None,
        lccn: Optional[str] = None,
        max_results: int = 10,
    ) -> dict[str, Any]:
        # Build compound query
        query_parts = []

        if isbn:
            return await self.search(isbn, "isbn", max_results)

        if lccn:
            return await self.search(lccn, "lccn", max_results)

        if title:
            query_parts.append(f'title:"{title}"')
        if author:
            query_parts.append(f'contributor:"{author}"')
        if subject:
            query_parts.append(f'subject:"{subject}"')

        query = " AND ".join(query_parts) if query_parts else "*"

        return await self.search(query, "keyword", max_results)

    def _parse_search_results(self, data: dict, query: str) -> dict[str, Any]:
        results = []
        total = 0

        if isinstance(data, list):
            # Array of results
            items = data
            total = len(items)
        elif isinstance(data, dict):
            # Object with results array
            items = data.get("results", data.get("@graph", []))
            total = data.get("totalResults", len(items))
        else:
            items = []

        for item in items:
            if isinstance(item, dict):
                result = {
                    "uri": item.get("@id", item.get("id", "")),
                    "title": self._extract_title_from_result(item),
                    "contributors": self._extract_contributors_from_result(item),
                    "publication_info": self._extract_publication_from_result(item),
                    "identifiers": self._extract_identifiers_from_result(item),
                    "work_type": item.get("@type", "Unknown"),
                }
                if result["uri"]:
                    results.append(result)

        return {
            "results": results,
            "total_results": total,
            "query": query,
        }

    def _extract_title_from_result(self, item: dict) -> str:
        return safe_extract_title(item)

    def _extract_contributors_from_result(self, item: dict) -> list[str]:
        contributors = []

        contrib_data = item.get("contribution", item.get("bf:contribution", []))
        if isinstance(contrib_data, dict):
            contrib_data = [contrib_data]

        for contrib in contrib_data:
            if isinstance(contrib, dict):
                agent = contrib.get("agent", contrib.get("bf:agent", {}))
                if isinstance(agent, dict):
                    name = agent.get("rdfs:label", agent.get("label", ""))
                    if name:
                        contributors.append(name)
                elif isinstance(agent, str):
                    contributors.append(agent)

        return contributors

    def _extract_publication_from_result(self, item: dict) -> Optional[str]:
        prov = item.get("provisionActivity", item.get("bf:provisionActivity", {}))
        if isinstance(prov, list) and prov:
            prov = prov[0]

        if isinstance(prov, dict):
            parts = []
            place = prov.get("place", prov.get("bf:place", {}))
            if isinstance(place, dict):
                place = place.get("rdfs:label", "")
            if place:
                parts.append(str(place))

            agent = prov.get("agent", prov.get("bf:agent", {}))
            if isinstance(agent, dict):
                agent = agent.get("rdfs:label", "")
            if agent:
                parts.append(str(agent))

            date = prov.get("date", prov.get("bf:date", ""))
            if date:
                parts.append(str(date))

            if parts:
                return ", ".join(parts)

        return None

    def _extract_identifiers_from_result(self, item: dict) -> dict[str, str]:
        identifiers = {}

        id_data = item.get("identifiedBy", item.get("bf:identifiedBy", []))
        if isinstance(id_data, dict):
            id_data = [id_data]

        for identifier in id_data:
            if isinstance(identifier, dict):
                id_type = identifier.get("@type", "")
                id_value = identifier.get("rdf:value", identifier.get("value", ""))

                if "Isbn" in id_type:
                    identifiers["isbn"] = str(id_value)
                elif "Lccn" in id_type:
                    identifiers["lccn"] = str(id_value)
                elif "Issn" in id_type:
                    identifiers["issn"] = str(id_value)

        return identifiers

    # =========================================================================
    # Fetch Methods
    # =========================================================================

    async def fetch_work(self, uri: str) -> Optional[dict[str, Any]]:
        client = await self._get_client()

        # Ensure we're requesting JSON-LD
        if not uri.endswith(".jsonld"):
            uri = uri.rstrip("/") + ".jsonld"

        try:
            response = await client.get(uri)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, asyncio.TimeoutError, json.JSONDecodeError, ValueError) as e:
            print(f"Error fetching work {uri}: {e}")
            return None

    async def fetch_instance(self, uri: str) -> Optional[dict[str, Any]]:
        return await self.fetch_work(uri)  # Same fetch mechanism

    async def fetch_authority(self, uri: str) -> Optional[dict[str, Any]]:
        client = await self._get_client()

        if not uri.endswith(".jsonld"):
            uri = uri.rstrip("/") + ".jsonld"

        try:
            response = await client.get(uri)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, asyncio.TimeoutError, json.JSONDecodeError, ValueError) as e:
            print(f"Error fetching authority {uri}: {e}")
            return None

    # =========================================================================
    # Parallel HTTP Fetching
    # =========================================================================

    async def _fetch_with_semaphore(self, uri: str) -> Optional[dict[str, Any]]:
        async with self._semaphore:
            return await self.fetch_work(uri)  # Reuses existing fetch logic

    async def _fetch_instances_parallel(
        self,
        instance_uris: list[str],
        max_instances: int = 5,
    ) -> list[BibframeInstance]:
        instances = []

        # Limit to max_instances
        uris_to_fetch = instance_uris[:max_instances]

        # Create parallel fetch tasks
        fetch_tasks = [
            self._fetch_with_semaphore(uri)
            for uri in uris_to_fetch
        ]

        # Execute all fetches concurrently with semaphore control
        results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        # Process results
        for inst_data in results:
            if isinstance(inst_data, dict):
                instance, _ = self._parse_instance_jsonld(inst_data, inst_data.get("@id", ""))
                if instance:
                    instances.append(instance)
            elif isinstance(inst_data, Exception):
                # Log but continue on individual fetch failures
                pass

        return instances

    # =========================================================================
    # Import Methods
    # =========================================================================

    async def import_work(
        self,
        uri: str,
        create_instances: bool = True,
        link_authorities: bool = True,
    ) -> dict[str, Any]:
        warnings = []

        # Fetch the work data
        work_data = await self.fetch_work(uri)
        if not work_data:
            return {
                "work": None,
                "instances": [],
                "contributors": [],
                "subjects": [],
                "authority_links": [],
                "warnings": ["Could not fetch work data from LC"],
            }

        # Parse the work
        work, work_contribs, work_subjects, work_links = self._parse_work_jsonld(work_data, uri)

        instances = []
        instance_links = []

        # Import instances if requested using parallel fetching for 5-10x speedup
        if create_instances:
            instance_uris = self._extract_instance_uris(work_data)
            if instance_uris:
                # Use parallel fetching with semaphore control instead of sequential
                # This typically reduces 5-10 second sequential fetch to 1-2 seconds
                instances = await self._fetch_instances_parallel(instance_uris, max_instances=5)

                # Extract authority links from instances
                for instance in instances:
                    # Authority links for instance-level identifiers
                    if instance.isbn_13:
                        instance_links.append(AuthorityLink(
                            source=AuthoritySource.ISBN,
                            authority_id=instance.isbn_13,
                            authority_uri=f"urn:isbn:{instance.isbn_13}",
                            link_type="identifier",
                        ))
                    if instance.lccn:
                        instance_links.append(AuthorityLink(
                            source=AuthoritySource.LCCN,
                            authority_id=instance.lccn,
                            authority_uri=f"https://lccn.loc.gov/{instance.lccn}",
                            link_type="identifier",
                        ))

        # Combine all authority links
        all_links = work_links + instance_links if link_authorities else []

        return {
            "work": work,
            "instances": instances,
            "contributors": work_contribs,
            "subjects": work_subjects,
            "authority_links": all_links,
            "warnings": warnings,
        }

    async def import_by_isbn(
        self,
        isbn: str,
        create_instances: bool = True,
    ) -> dict[str, Any]:
        # Search for the ISBN
        results = await self.search(isbn, "isbn", max_results=1)

        if not results["results"]:
            return {
                "work": None,
                "instances": [],
                "contributors": [],
                "subjects": [],
                "authority_links": [],
                "warnings": [f"No results found for ISBN: {isbn}"],
            }

        # Import the first result
        uri = results["results"][0]["uri"]
        return await self.import_work(uri, create_instances)

    async def import_by_lccn(
        self,
        lccn: str,
        create_instances: bool = True,
    ) -> dict[str, Any]:
        results = await self.search(lccn, "lccn", max_results=1)

        if not results["results"]:
            return {
                "work": None,
                "instances": [],
                "contributors": [],
                "subjects": [],
                "authority_links": [],
                "warnings": [f"No results found for LCCN: {lccn}"],
            }

        uri = results["results"][0]["uri"]
        return await self.import_work(uri, create_instances)

    # =========================================================================
    # JSON-LD Parsing
    # =========================================================================

    def _parse_work_jsonld(
        self,
        data: dict,
        uri: str,
    ) -> tuple[BibframeWork, list[BibframeContributor], list[BibframeSubject], list[AuthorityLink]]:
        # Handle @graph structure
        if "@graph" in data:
            # Find the main work resource
            work_data = None
            for item in data["@graph"]:
                if item.get("@id") == uri or item.get("@type") == "bf:Work":
                    work_data = item
                    break
            if not work_data:
                work_data = data["@graph"][0] if data["@graph"] else data
        else:
            work_data = data

        # Extract title
        title = self._extract_title(work_data)
        subtitle = self._extract_subtitle(work_data)

        # Extract work type
        work_type = self._map_work_type(work_data.get("@type", ""))

        # Extract language
        language = self._extract_language(work_data)

        # Extract summary
        summary = self._extract_summary(work_data)

        # Extract classification
        dewey, lc_class = self._extract_classification(work_data)

        # Extract contributors
        contributors, contrib_links = self._extract_contributions(work_data)

        # Extract subjects
        subjects, subject_links = self._extract_subjects(work_data)

        # Create authority link for the work itself
        work_links = [
            AuthorityLink(
                source=AuthoritySource.LCCN,
                authority_id=uri.split("/")[-1],
                authority_uri=uri,
                link_type="sameAs",
            )
        ]
        work_links.extend(contrib_links)
        work_links.extend(subject_links)

        work = BibframeWork(
            uri=uri,
            title=title,
            title_sort=self._generate_sort_title(title),
            subtitle=subtitle,
            work_type=work_type,
            language=language,
            summary=summary,
            dewey_classification=dewey,
            lc_classification=lc_class,
            source="loc",
            source_record_id=uri.split("/")[-1],
        )

        return work, contributors, subjects, work_links

    def _parse_instance_jsonld(
        self,
        data: dict,
        uri: str,
    ) -> tuple[Optional[BibframeInstance], list[AuthorityLink]]:
        # Handle @graph structure
        if "@graph" in data:
            inst_data = None
            for item in data["@graph"]:
                if item.get("@id") == uri or "Instance" in str(item.get("@type", "")):
                    inst_data = item
                    break
            if not inst_data:
                inst_data = data["@graph"][0] if data["@graph"] else data
        else:
            inst_data = data

        # Extract title
        title = self._extract_title(inst_data)

        # Extract identifiers
        isbn_10, isbn_13 = self._extract_isbn(inst_data)
        lccn = self._extract_lccn(inst_data)

        # Extract publication info
        publisher, place, pub_year = self._extract_publication(inst_data)

        # Extract physical description
        extent, dimensions, page_count = self._extract_extent(inst_data)

        # Create authority links
        links = []
        if lccn:
            links.append(AuthorityLink(
                source=AuthoritySource.LCCN,
                authority_id=lccn,
                authority_uri=f"https://lccn.loc.gov/{lccn}",
                link_type="identifier",
            ))
        if isbn_13:
            links.append(AuthorityLink(
                source=AuthoritySource.ISBN,
                authority_id=isbn_13,
                authority_uri=f"urn:isbn:{isbn_13}",
                link_type="identifier",
            ))

        instance = BibframeInstance(
            uri=uri,
            title=title,
            isbn_10=isbn_10,
            isbn_13=isbn_13,
            lccn=lccn,
            publisher=publisher,
            publisher_place=place,
            publication_year=pub_year,
            extent=extent,
            dimensions=dimensions,
            page_count=page_count,
            source="loc",
            source_record_id=uri.split("/")[-1],
        )

        return instance, links

    def _extract_title(self, data: dict) -> str:
        return safe_extract_title(data)

    def _extract_subtitle(self, data: dict) -> Optional[str]:
        return extract_subtitle(data)

    def _map_work_type(self, lc_type: Any) -> WorkType:
        if isinstance(lc_type, list):
            lc_type = lc_type[0] if lc_type else ""

        lc_type = str(lc_type)

        for key, value in self.LC_WORK_TYPE_MAP.items():
            if key.lower() in lc_type.lower():
                return value

        return WorkType.text

    def _extract_language(self, data: dict) -> str:
        lang_data = data.get("bf:language", data.get("language", []))
        if isinstance(lang_data, list) and lang_data:
            lang_data = lang_data[0]

        if isinstance(lang_data, dict):
            uri = lang_data.get("@id", "")
            # Extract language code from URI like http://id.loc.gov/vocabulary/languages/eng
            if "/languages/" in uri:
                return uri.split("/")[-1][:3]

        return "eng"

    def _extract_summary(self, data: dict) -> Optional[str]:
        summary_data = data.get("bf:summary", data.get("summary", []))
        if isinstance(summary_data, list) and summary_data:
            summary_data = summary_data[0]

        if isinstance(summary_data, dict):
            return summary_data.get("rdfs:label", summary_data.get("label"))
        elif isinstance(summary_data, str):
            return summary_data

        return None

    def _extract_classification(self, data: dict) -> tuple[Optional[str], Optional[str]]:
        dewey = None
        lc_class = None

        class_data = data.get("bf:classification", data.get("classification", []))
        if isinstance(class_data, dict):
            class_data = [class_data]

        for cls in class_data:
            if isinstance(cls, dict):
                cls_type = cls.get("@type", "")
                cls_portion = cls.get("bf:classificationPortion", cls.get("classificationPortion", ""))

                if "Ddc" in cls_type or "dewey" in cls_type.lower():
                    dewey = cls_portion
                elif "Lcc" in cls_type or "lcc" in cls_type.lower():
                    lc_class = cls_portion

        return dewey, lc_class

    def _extract_contributions(
        self, data: dict
    ) -> tuple[list[BibframeContributor], list[AuthorityLink]]:
        contributors = []
        links = []

        contrib_data = data.get("bf:contribution", data.get("contribution", []))
        if isinstance(contrib_data, dict):
            contrib_data = [contrib_data]

        for contrib in contrib_data:
            if isinstance(contrib, dict):
                agent = contrib.get("bf:agent", contrib.get("agent", {}))
                if isinstance(agent, dict):
                    name = agent.get("rdfs:label", agent.get("label", ""))
                    agent_uri = agent.get("@id", "")

                    if name:
                        contributor = BibframeContributor(
                            name=name,
                            contributor_type="person",
                            name_inverted=name if "," in name else None,
                        )

                        # Create authority link if we have a URI
                        if agent_uri and "id.loc.gov/authorities/names/" in agent_uri:
                            lcnaf_id = agent_uri.split("/")[-1]
                            contributor.lcnaf_id = lcnaf_id
                            links.append(AuthorityLink(
                                source=AuthoritySource.LCNAF,
                                authority_id=lcnaf_id,
                                authority_uri=agent_uri,
                                link_type="sameAs",
                            ))

                        contributors.append(contributor)

        return contributors, links

    def _extract_subjects(
        self, data: dict
    ) -> tuple[list[BibframeSubject], list[AuthorityLink]]:
        subjects = []
        links = []

        subj_data = data.get("bf:subject", data.get("subject", []))
        if isinstance(subj_data, dict):
            subj_data = [subj_data]

        for subj in subj_data:
            if isinstance(subj, dict):
                label = subj.get("rdfs:label", subj.get("label", ""))
                subj_uri = subj.get("@id", "")
                subj_type = subj.get("@type", "Topic")

                if label:
                    # Determine subject type
                    subject_type = "topic"
                    if "Place" in str(subj_type):
                        subject_type = "place"
                    elif "Temporal" in str(subj_type):
                        subject_type = "temporal"
                    elif "Person" in str(subj_type):
                        subject_type = "person"
                    elif "Organization" in str(subj_type):
                        subject_type = "organization"

                    subject = BibframeSubject(
                        label=label,
                        label_normalized=label.lower(),
                        subject_type=subject_type,
                    )

                    # Create authority link if we have a URI
                    if subj_uri and "id.loc.gov/authorities/subjects/" in subj_uri:
                        lcsh_id = subj_uri.split("/")[-1]
                        subject.lcsh_id = lcsh_id
                        subject.source = AuthoritySource.LCSH
                        links.append(AuthorityLink(
                            source=AuthoritySource.LCSH,
                            authority_id=lcsh_id,
                            authority_uri=subj_uri,
                            link_type="sameAs",
                        ))

                    subjects.append(subject)

        return subjects, links

    def _extract_instance_uris(self, data: dict) -> list[str]:
        uris = []

        instances = data.get("bf:hasInstance", data.get("hasInstance", []))
        if isinstance(instances, dict):
            instances = [instances]

        for inst in instances:
            if isinstance(inst, dict):
                uri = inst.get("@id", "")
                if uri:
                    uris.append(uri)
            elif isinstance(inst, str):
                uris.append(inst)

        return uris

    def _extract_isbn(self, data: dict) -> tuple[Optional[str], Optional[str]]:
        id_data = data.get("bf:identifiedBy", data.get("identifiedBy", []))
        if isinstance(id_data, dict):
            id_data = [id_data]

        for identifier in id_data:
            if isinstance(identifier, dict):
                id_type = identifier.get("@type", "")
                if "Isbn" in id_type:
                    value = identifier.get("rdf:value", identifier.get("value", ""))
                    if value:
                        isbn_10, isbn_13 = IdentifierNormalizer.normalize_isbn(str(value))
                        if isbn_10 or isbn_13:
                            return isbn_10, isbn_13

        return None, None

    def _extract_lccn(self, data: dict) -> Optional[str]:
        id_data = data.get("bf:identifiedBy", data.get("identifiedBy", []))
        if isinstance(id_data, dict):
            id_data = [id_data]

        for identifier in id_data:
            if isinstance(identifier, dict):
                id_type = identifier.get("@type", "")
                if "Lccn" in id_type:
                    value = identifier.get("rdf:value", identifier.get("value", ""))
                    if value:
                        return IdentifierNormalizer.normalize_lccn(str(value))

        return None

    def _extract_publication(self, data: dict) -> tuple[Optional[str], Optional[str], Optional[int]]:
        publisher = None
        place = None
        year = None

        prov_data = data.get("bf:provisionActivity", data.get("provisionActivity", []))
        if isinstance(prov_data, dict):
            prov_data = [prov_data]

        for prov in prov_data:
            if isinstance(prov, dict):
                prov_type = prov.get("@type", "")
                if "Publication" in str(prov_type):
                    # Agent (publisher)
                    agent = prov.get("bf:agent", prov.get("agent", {}))
                    if isinstance(agent, dict):
                        publisher = agent.get("rdfs:label", agent.get("label"))

                    # Place
                    place_data = prov.get("bf:place", prov.get("place", {}))
                    if isinstance(place_data, dict):
                        place = place_data.get("rdfs:label", place_data.get("label"))

                    # Date
                    date = prov.get("bf:date", prov.get("date", ""))
                    if date:
                        year_match = re.search(r"(\d{4})", str(date))
                        if year_match:
                            year = int(year_match.group(1))

        return publisher, place, year

    def _extract_extent(self, data: dict) -> tuple[Optional[str], Optional[str], Optional[int]]:
        extent = None
        dimensions = None
        page_count = None

        extent_data = data.get("bf:extent", data.get("extent", {}))
        if isinstance(extent_data, dict):
            extent = extent_data.get("rdfs:label", extent_data.get("label"))
        elif isinstance(extent_data, str):
            extent = extent_data

        dimensions_data = data.get("bf:dimensions", data.get("dimensions"))
        if dimensions_data:
            dimensions = str(dimensions_data)

        # Try to extract page count
        if extent:
            page_match = re.search(r"(\d+)\s*(?:p\.|pages)", str(extent), re.I)
            if page_match:
                page_count = int(page_match.group(1))

        return extent, dimensions, page_count

    def _generate_sort_title(self, title: str) -> str:
        return normalize_title_for_sorting(title)


# Singleton instance
loc_bibframe_service = LocBibframeService()
