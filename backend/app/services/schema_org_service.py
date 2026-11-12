# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from app.core.logging import get_logger
import os
from datetime import datetime
from typing import Any, Optional

logger = get_logger(__name__)

_LIBRARY_NAME = os.environ.get("LIBRARY_NAME", "My Library")

from ..core.config import get_settings

settings = get_settings()

from ..models.bibframe import (
    BibframeContributor,
    BibframeInstance,
    BibframeItem,
    BibframeSubject,
    BibframeWork,
    CarrierType,
    InstanceType,
    MediaType,
    WorkType,
)
from ..models.catalog import CatalogItem, ItemType


class SchemaOrgService:

    # Base URL for the library
    BASE_URL = settings.schema_org_base_url

    # Library organization info
    LIBRARY_INFO = {
        "@type": "Library",
        "@id": f"{BASE_URL}/#library",
        "name": _LIBRARY_NAME,
        "url": BASE_URL,
        "address": {
            "@type": "PostalAddress",
            "addressLocality": os.environ.get("LIBRARY_CITY", ""),
            "addressRegion": "State",
            "addressCountry": "US",
        },
        "openingHours": "Mo-Fr 09:00-20:00, Sa 10:00-17:00",
    }

    # Work type to Schema.org type mapping
    WORK_TYPE_TO_SCHEMA = {
        WorkType.text: "Book",
        WorkType.spoken_word: "Audiobook",
        WorkType.performed_music: "MusicAlbum",
        WorkType.notated_music: "MusicComposition",
        WorkType.two_dimensional_moving_image: "Movie",
        WorkType.three_dimensional_moving_image: "Movie",
        WorkType.still_image: "Photograph",
        WorkType.cartographic_image: "Map",
        WorkType.computer_program: "SoftwareApplication",
        WorkType.computer_dataset: "Dataset",
        WorkType.three_dimensional_form: "Sculpture",
        WorkType.other: "CreativeWork",
    }

    # CatalogItem type to Schema.org type mapping
    ITEM_TYPE_TO_SCHEMA = {
        ItemType.book: "Book",
        ItemType.ebook: "Book",
        ItemType.audiobook: "Audiobook",
        ItemType.dvd: "Movie",
        ItemType.cd: "MusicAlbum",
        ItemType.magazine: "Periodical",
        ItemType.game: "VideoGame",
        ItemType.other: "CreativeWork",
    }

    # Instance type to Schema.org bookFormat
    INSTANCE_TYPE_TO_FORMAT = {
        InstanceType.print: "Hardcover",  # or Paperback
        InstanceType.electronic: "EBook",
        InstanceType.audio: "AudiobookFormat",
        InstanceType.audiovisual: None,  # Use Movie type instead
    }

    def __init__(self, base_url: Optional[str] = None):
        if base_url:
            self.BASE_URL = base_url
            self.LIBRARY_INFO["@id"] = f"{base_url}/#library"
            self.LIBRARY_INFO["url"] = base_url

    # =========================================================================
    # BIBFRAME to Schema.org
    # =========================================================================

    def work_to_schema_org(
        self,
        work: BibframeWork,
        instances: Optional[list[BibframeInstance]] = None,
        contributors: Optional[list[BibframeContributor]] = None,
        subjects: Optional[list[BibframeSubject]] = None,
        include_library: bool = True,
    ) -> dict[str, Any]:
        # Determine Schema.org type
        schema_type = self.WORK_TYPE_TO_SCHEMA.get(work.work_type, "Book")

        schema = {
            "@context": "https://schema.org",
            "@type": schema_type,
            "@id": f"{self.BASE_URL}/works/{work.id}",
            "name": work.title,
            "url": f"{self.BASE_URL}/catalog/work/{work.id}",
        }

        # Add subtitle
        if work.subtitle:
            schema["alternateName"] = work.subtitle

        # Add description
        if work.summary:
            schema["description"] = work.summary[:500]  # Limit length
            schema["abstract"] = work.summary

        # Add language
        if work.language:
            schema["inLanguage"] = self._language_code_to_schema(work.language)

        # Add genre
        if work.genre_form:
            try:
                genres = json.loads(work.genre_form) if isinstance(work.genre_form, str) else work.genre_form
                if genres:
                    schema["genre"] = genres
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("Failed to parse genre_form JSON for schema.org markup: %s", e)

        # Add classification
        if work.dewey_classification:
            schema["deweyNumber"] = work.dewey_classification

        # Add series info
        if work.series_title:
            schema["isPartOf"] = {
                "@type": "BookSeries",
                "name": work.series_title,
            }
            if work.series_number:
                schema["position"] = work.series_number

        # Add intended audience
        if work.intended_audience:
            schema["audience"] = {
                "@type": "Audience",
                "audienceType": work.intended_audience,
            }

        # Add table of contents
        if work.table_of_contents:
            schema["hasPart"] = {
                "@type": "TableOfContents",
                "description": work.table_of_contents[:1000],
            }

        # Add contributors
        if contributors:
            authors = []
            other_contribs = []

            for contrib in contributors:
                person = self._contributor_to_schema_org(contrib)
                # Check if primary author (simplified - first person is author)
                if contrib.contributor_type == "person" and not authors:
                    authors.append(person)
                else:
                    other_contribs.append(person)

            if authors:
                schema["author"] = authors if len(authors) > 1 else authors[0]
            if other_contribs:
                schema["contributor"] = other_contribs

        elif work.contributors:
            # Use work's contributor relationship
            authors = [self._contributor_to_schema_org(c) for c in work.contributors[:5]]
            if authors:
                schema["author"] = authors if len(authors) > 1 else authors[0]

        # Add subjects as keywords
        if subjects:
            schema["keywords"] = [s.label for s in subjects[:10]]
        elif work.subjects:
            schema["keywords"] = [s.label for s in work.subjects[:10]]

        # Add work examples (instances)
        if instances:
            schema["workExample"] = [
                self._instance_to_work_example(inst) for inst in instances[:5]
            ]

        # Add library as provider
        if include_library:
            schema["provider"] = self.LIBRARY_INFO

        # Add dateCreated from origin_date
        if work.origin_date:
            schema["dateCreated"] = work.origin_date

        # Add same as links from authority links
        same_as = []
        if work.authority_links:
            for link in work.authority_links:
                if link.authority_uri:
                    same_as.append(link.authority_uri)
        if same_as:
            schema["sameAs"] = same_as

        return schema

    def instance_to_schema_org(
        self,
        instance: BibframeInstance,
        work: Optional[BibframeWork] = None,
        items: Optional[list[BibframeItem]] = None,
        include_library: bool = True,
    ) -> dict[str, Any]:
        # Determine type based on instance type
        schema_type = "Book"  # Default
        if work:
            schema_type = self.WORK_TYPE_TO_SCHEMA.get(work.work_type, "Book")

        if instance.instance_type == InstanceType.audio:
            schema_type = "Audiobook"
        elif instance.instance_type == InstanceType.audiovisual:
            schema_type = "Movie"

        schema = {
            "@context": "https://schema.org",
            "@type": schema_type,
            "@id": f"{self.BASE_URL}/instances/{instance.id}",
            "name": instance.title,
            "url": f"{self.BASE_URL}/catalog/instance/{instance.id}",
        }

        # Add ISBN
        if instance.isbn_13:
            schema["isbn"] = instance.isbn_13
        elif instance.isbn_10:
            schema["isbn"] = instance.isbn_10

        # Add book format
        book_format = self.INSTANCE_TYPE_TO_FORMAT.get(instance.instance_type)
        if book_format and schema_type == "Book":
            schema["bookFormat"] = f"https://schema.org/{book_format}"

        # Add publisher
        if instance.publisher:
            schema["publisher"] = {
                "@type": "Organization",
                "name": instance.publisher,
            }
            if instance.publisher_place:
                schema["publisher"]["address"] = {
                    "@type": "PostalAddress",
                    "addressLocality": instance.publisher_place,
                }

        # Add publication date
        if instance.publication_year:
            schema["datePublished"] = str(instance.publication_year)
        elif instance.publication_date:
            schema["datePublished"] = instance.publication_date

        # Add edition
        if instance.edition:
            schema["bookEdition"] = instance.edition

        # Add page count
        if instance.page_count:
            schema["numberOfPages"] = instance.page_count

        # Add dimensions (as text for now)
        if instance.dimensions:
            schema["size"] = instance.dimensions

        # Add cover image
        if instance.cover_url:
            schema["image"] = instance.cover_url

        # Add thumbnail
        if instance.thumbnail_url:
            schema["thumbnailUrl"] = instance.thumbnail_url

        # Add electronic access
        if instance.access_url:
            schema["url"] = instance.access_url

        # Link to parent work
        if work:
            schema["exampleOfWork"] = {
                "@type": "CreativeWork",
                "@id": f"{self.BASE_URL}/works/{work.id}",
                "name": work.title,
            }

            # Inherit author from work
            if work.contributors:
                authors = [self._contributor_to_schema_org(c) for c in work.contributors[:3]]
                if authors:
                    schema["author"] = authors if len(authors) > 1 else authors[0]

        # Add library holdings (offers)
        if items:
            offers = []
            for item in items:
                offer = self._item_to_offer(item)
                offers.append(offer)
            if offers:
                schema["offers"] = offers

        # Add library as provider
        if include_library:
            schema["provider"] = self.LIBRARY_INFO

        return schema

    def item_to_schema_org(
        self,
        item: BibframeItem,
        instance: Optional[BibframeInstance] = None,
        include_library: bool = True,
    ) -> dict[str, Any]:
        schema = {
            "@context": "https://schema.org",
            "@type": "IndividualProduct",  # Specific copy of a product
            "@id": f"{self.BASE_URL}/items/{item.id}",
            "productID": item.barcode or f"ITEM-{item.id}",
        }

        # Add location
        if item.shelving_location or item.library_branch:
            location = {
                "@type": "Place",
                "name": item.library_branch or "Main Library",
            }
            if item.shelving_location:
                location["containedInPlace"] = {
                    "@type": "Place",
                    "name": item.shelving_location,
                }
            schema["itemLocation"] = location

        # Add condition
        if item.condition:
            condition_map = {
                "new": "NewCondition",
                "excellent": "NewCondition",
                "good": "UsedCondition",
                "fair": "UsedCondition",
                "poor": "DamagedCondition",
            }
            schema["itemCondition"] = f"https://schema.org/{condition_map.get(item.condition, 'UsedCondition')}"

        # Add availability as Offer
        offer = self._item_to_offer(item)
        schema["offers"] = offer

        # Link to instance
        if instance:
            schema["isVariantOf"] = {
                "@type": "Book",
                "@id": f"{self.BASE_URL}/instances/{instance.id}",
                "name": instance.title,
            }

        # Add library as seller
        if include_library:
            schema["seller"] = self.LIBRARY_INFO

        return schema

    def _item_to_offer(self, item: BibframeItem) -> dict[str, Any]:
        # Map circulation status to availability
        availability_map = {
            "available": "InStock",
            "checked_out": "OutOfStock",
            "on_hold": "PreOrder",
            "in_transit": "BackOrder",
            "lost": "Discontinued",
            "damaged": "OutOfStock",
            "missing": "OutOfStock",
        }

        availability = availability_map.get(item.circulation_status, "InStock")

        offer = {
            "@type": "Offer",
            "availability": f"https://schema.org/{availability}",
            "price": "0",
            "priceCurrency": "USD",
            "category": "Library Lending",
            "seller": self.LIBRARY_INFO,
        }

        # Add item location
        if item.library_branch:
            offer["areaServed"] = {
                "@type": "Place",
                "name": item.library_branch,
            }

        # Add inventory level (always 1 for individual items)
        offer["inventoryLevel"] = {
            "@type": "QuantitativeValue",
            "value": 1 if item.circulation_status == "available" else 0,
        }

        return offer

    def _instance_to_work_example(self, instance: BibframeInstance) -> dict[str, Any]:
        example = {
            "@type": "Book",
            "@id": f"{self.BASE_URL}/instances/{instance.id}",
            "name": instance.title,
            "url": f"{self.BASE_URL}/catalog/instance/{instance.id}",
        }

        if instance.isbn_13:
            example["isbn"] = instance.isbn_13

        book_format = self.INSTANCE_TYPE_TO_FORMAT.get(instance.instance_type)
        if book_format:
            example["bookFormat"] = f"https://schema.org/{book_format}"

        if instance.publication_year:
            example["datePublished"] = str(instance.publication_year)

        return example

    # =========================================================================
    # CatalogItem to Schema.org (for backward compatibility)
    # =========================================================================

    def catalog_item_to_schema_org(
        self,
        item: CatalogItem,
        include_library: bool = True,
    ) -> dict[str, Any]:
        # Determine Schema.org type
        schema_type = self.ITEM_TYPE_TO_SCHEMA.get(item.item_type, "Book")

        schema = {
            "@context": "https://schema.org",
            "@type": schema_type,
            "@id": f"{self.BASE_URL}/catalog/{item.id}",
            "name": item.title,
            "url": f"{self.BASE_URL}/catalog/{item.id}",
        }

        # Add author
        if item.author:
            schema["author"] = {
                "@type": "Person",
                "name": item.author,
            }

        # Add ISBN
        if item.isbn:
            schema["isbn"] = item.isbn

        # Add publisher
        if item.publisher:
            schema["publisher"] = {
                "@type": "Organization",
                "name": item.publisher,
            }

        # Add publication year
        if item.publication_year:
            schema["datePublished"] = str(item.publication_year)

        # Add description
        if item.description:
            schema["description"] = item.description[:500]

        # Add subjects as keywords
        if item.subjects:
            keywords = [s.strip() for s in item.subjects.split(",") if s.strip()]
            if keywords:
                schema["keywords"] = keywords[:10]

        # Add cover image
        if item.cover_url:
            schema["image"] = item.cover_url

        # Add page count
        if item.page_count:
            schema["numberOfPages"] = item.page_count

        # Add book format based on item type
        if item.item_type == ItemType.ebook:
            schema["bookFormat"] = "https://schema.org/EBook"
        elif item.item_type == ItemType.audiobook:
            schema["@type"] = "Audiobook"
        elif item.item_type == ItemType.book:
            # Could be hardcover or paperback - default to hardcover
            schema["bookFormat"] = "https://schema.org/Hardcover"

        # Add availability as Offer
        from ..models.catalog import ItemStatus
        availability_map = {
            ItemStatus.available: "InStock",
            ItemStatus.checked_out: "OutOfStock",
            ItemStatus.on_hold: "PreOrder",
            ItemStatus.in_transit: "BackOrder",
            ItemStatus.lost: "Discontinued",
            ItemStatus.damaged: "OutOfStock",
        }

        availability = availability_map.get(item.status, "InStock")

        schema["offers"] = {
            "@type": "Offer",
            "availability": f"https://schema.org/{availability}",
            "price": "0",
            "priceCurrency": "USD",
            "category": "Library Lending",
            "itemCondition": "https://schema.org/UsedCondition",
        }

        # Add location
        if item.location:
            schema["offers"]["areaServed"] = {
                "@type": "Place",
                "name": item.location,
            }

        # Add library as provider
        if include_library:
            schema["provider"] = self.LIBRARY_INFO
            schema["offers"]["seller"] = self.LIBRARY_INFO

        return schema

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _contributor_to_schema_org(self, contributor: BibframeContributor) -> dict[str, Any]:
        if contributor.contributor_type == "organization":
            schema = {
                "@type": "Organization",
                "name": contributor.name,
            }
        elif contributor.contributor_type == "meeting":
            schema = {
                "@type": "Event",
                "name": contributor.name,
            }
        else:
            schema = {
                "@type": "Person",
                "name": contributor.name,
            }

            # Add person-specific fields
            if contributor.given_name:
                schema["givenName"] = contributor.given_name
            if contributor.family_name:
                schema["familyName"] = contributor.family_name
            if contributor.birth_date:
                schema["birthDate"] = contributor.birth_date
            if contributor.death_date:
                schema["deathDate"] = contributor.death_date

        # Add authority links as sameAs
        same_as = []
        if contributor.viaf_id:
            same_as.append(f"https://viaf.org/viaf/{contributor.viaf_id}")
        if contributor.lcnaf_id:
            same_as.append(f"https://id.loc.gov/authorities/names/{contributor.lcnaf_id}")
        if contributor.wikidata_id:
            same_as.append(f"https://www.wikidata.org/entity/{contributor.wikidata_id}")
        if contributor.orcid:
            same_as.append(f"https://orcid.org/{contributor.orcid}")

        if same_as:
            schema["sameAs"] = same_as

        return schema

    def _language_code_to_schema(self, lang_code: str) -> str:
        # Schema.org accepts ISO 639-1 codes preferentially
        iso_639_2_to_1 = {
            "eng": "en",
            "spa": "es",
            "fre": "fr",
            "ger": "de",
            "ita": "it",
            "por": "pt",
            "rus": "ru",
            "chi": "zh",
            "jpn": "ja",
            "kor": "ko",
            "ara": "ar",
            "heb": "he",
            "hin": "hi",
            "dut": "nl",
            "pol": "pl",
            "swe": "sv",
            "dan": "da",
            "nor": "no",
            "fin": "fi",
        }
        return iso_639_2_to_1.get(lang_code, lang_code)

    # =========================================================================
    # HTML Embedding
    # =========================================================================

    def to_html_script_tag(self, schema: dict[str, Any]) -> str:
        json_str = json.dumps(schema, indent=2, ensure_ascii=False)
        return f'<script type="application/ld+json">\n{json_str}\n</script>'

    def generate_breadcrumb_schema(
        self,
        path: list[tuple[str, str]],
    ) -> dict[str, Any]:
        items = []
        for i, (name, url) in enumerate(path, 1):
            items.append({
                "@type": "ListItem",
                "position": i,
                "name": name,
                "item": url,
            })

        return {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": items,
        }

    def generate_search_action_schema(self) -> dict[str, Any]:
        return {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "url": self.BASE_URL,
            "name": _LIBRARY_NAME,
            "potentialAction": {
                "@type": "SearchAction",
                "target": {
                    "@type": "EntryPoint",
                    "urlTemplate": f"{self.BASE_URL}/catalog/search?q={{search_term_string}}",
                },
                "query-input": "required name=search_term_string",
            },
        }

    def generate_library_organization_schema(self) -> dict[str, Any]:
        same_as = []
        if settings.facebook_handle:
            same_as.append(f"https://www.facebook.com/{settings.facebook_handle}")
        if settings.twitter_handle:
            same_as.append(f"https://twitter.com/{settings.twitter_handle.lstrip('@')}")

        schema: dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": ["Library", "LocalBusiness"],
            "@id": f"{self.BASE_URL}/#library",
            "name": _LIBRARY_NAME,
            "url": self.BASE_URL,
            "logo": f"{self.BASE_URL}/images/logo.png",
            "description": f"{_LIBRARY_NAME} provides free access to books, media, and digital resources for our community.",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": os.environ.get("LIBRARY_STREET", ""),
                "addressLocality": os.environ.get("LIBRARY_CITY", ""),
                "addressRegion": "State",
                "postalCode": "12345",
                "addressCountry": "US",
            },
            "openingHoursSpecification": [
                {
                    "@type": "OpeningHoursSpecification",
                    "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                    "opens": "09:00",
                    "closes": "20:00",
                },
                {
                    "@type": "OpeningHoursSpecification",
                    "dayOfWeek": "Saturday",
                    "opens": "10:00",
                    "closes": "17:00",
                },
            ],
            "priceRange": "Free",
            "hasOfferCatalog": {
                "@type": "OfferCatalog",
                "name": "Library Catalog",
                "url": f"{self.BASE_URL}/catalog",
            },
        }

        if settings.library_latitude or settings.library_longitude:
            schema["geo"] = {
                "@type": "GeoCoordinates",
                "latitude": settings.library_latitude,
                "longitude": settings.library_longitude,
            }
        if settings.library_phone:
            schema["telephone"] = settings.library_phone
        if settings.library_email:
            schema["email"] = settings.library_email
        if same_as:
            schema["sameAs"] = same_as

        return schema


# Singleton instance
schema_org_service = SchemaOrgService()
