# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from app.core.logging import get_logger
import os
from datetime import datetime
from typing import Any, Optional

from ..core.config import get_settings

settings = get_settings()

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

_bibframe_logger = get_logger(__name__)


def _track_bibframe_parse_error() -> None:
    try:
        from ..core.metrics import increment
        increment("data_parse_error_total", {"service": "bibframe", "field": "json_field"})
    except Exception:  # noqa: BLE001 -- metrics emission must not break parse-error logging
        _bibframe_logger.debug("Failed to emit BIBFRAME parse error metric")
    _bibframe_logger.warning("BIBFRAME JSON field parse error during RDF serialization")


class BibframeRdfService:

    # Base URIs
    BASE_URI = settings.bibframe_base_uri

    # Namespace prefixes
    NAMESPACES = {
        "bf": "http://id.loc.gov/ontologies/bibframe/",
        "bflc": "http://id.loc.gov/ontologies/bflc/",
        "madsrdf": "http://www.loc.gov/mads/rdf/v1#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "schema": "https://schema.org/",
        "dcterms": "http://purl.org/dc/terms/",
        "foaf": "http://xmlns.com/foaf/0.1/",
        "owl": "http://www.w3.org/2002/07/owl#",
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "lsc": f"{BASE_URI}/ns/",
    }

    # JSON-LD context
    JSONLD_CONTEXT = {
        "@vocab": "http://id.loc.gov/ontologies/bibframe/",
        "bf": "http://id.loc.gov/ontologies/bibframe/",
        "bflc": "http://id.loc.gov/ontologies/bflc/",
        "madsrdf": "http://www.loc.gov/mads/rdf/v1#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "schema": "https://schema.org/",
        "dcterms": "http://purl.org/dc/terms/",
        "foaf": "http://xmlns.com/foaf/0.1/",
        "owl": "http://www.w3.org/2002/07/owl#",
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        # Property mappings
        "title": {"@id": "bf:title", "@type": "@id"},
        "mainTitle": "bf:mainTitle",
        "subtitle": "bf:subtitle",
        "contribution": {"@id": "bf:contribution", "@type": "@id"},
        "agent": {"@id": "bf:agent", "@type": "@id"},
        "role": {"@id": "bf:role", "@type": "@id"},
        "subject": {"@id": "bf:subject", "@type": "@id"},
        "classification": {"@id": "bf:classification", "@type": "@id"},
        "identifiedBy": {"@id": "bf:identifiedBy", "@type": "@id"},
        "hasInstance": {"@id": "bf:hasInstance", "@type": "@id"},
        "instanceOf": {"@id": "bf:instanceOf", "@type": "@id"},
        "hasItem": {"@id": "bf:hasItem", "@type": "@id"},
        "itemOf": {"@id": "bf:itemOf", "@type": "@id"},
        "provisionActivity": {"@id": "bf:provisionActivity", "@type": "@id"},
        "extent": "bf:extent",
        "dimensions": "bf:dimensions",
        "carrier": {"@id": "bf:carrier", "@type": "@id"},
        "media": {"@id": "bf:media", "@type": "@id"},
        "language": {"@id": "bf:language", "@type": "@id"},
        "summary": "bf:summary",
        "tableOfContents": "bf:tableOfContents",
        "genreForm": {"@id": "bf:genreForm", "@type": "@id"},
        "intendedAudience": "bf:intendedAudience",
        "note": "bf:note",
        "electronicLocator": {"@id": "bf:electronicLocator", "@type": "@id"},
        "heldBy": {"@id": "bf:heldBy", "@type": "@id"},
        "shelfMark": "bf:shelfMark",
        "barcode": "bf:barcode",
        # Authority links
        "sameAs": {"@id": "owl:sameAs", "@type": "@id"},
        "closeMatch": {"@id": "skos:closeMatch", "@type": "@id"},
        "exactMatch": {"@id": "skos:exactMatch", "@type": "@id"},
    }

    # Work type mappings to BIBFRAME content types
    WORK_TYPE_URIS = {
        WorkType.text: "http://id.loc.gov/vocabulary/contentTypes/txt",
        WorkType.spoken_word: "http://id.loc.gov/vocabulary/contentTypes/spw",
        WorkType.performed_music: "http://id.loc.gov/vocabulary/contentTypes/prm",
        WorkType.still_image: "http://id.loc.gov/vocabulary/contentTypes/sti",
        WorkType.two_dimensional_moving_image: "http://id.loc.gov/vocabulary/contentTypes/tdi",
        WorkType.three_dimensional_moving_image: "http://id.loc.gov/vocabulary/contentTypes/tdm",
        WorkType.cartographic_image: "http://id.loc.gov/vocabulary/contentTypes/cri",
        WorkType.notated_music: "http://id.loc.gov/vocabulary/contentTypes/ntm",
        WorkType.computer_program: "http://id.loc.gov/vocabulary/contentTypes/cop",
        WorkType.computer_dataset: "http://id.loc.gov/vocabulary/contentTypes/cod",
    }

    # Carrier type mappings
    CARRIER_TYPE_URIS = {
        CarrierType.volume: "http://id.loc.gov/vocabulary/carriers/nc",
        CarrierType.online_resource: "http://id.loc.gov/vocabulary/carriers/cr",
        CarrierType.audio_disc: "http://id.loc.gov/vocabulary/carriers/sd",
        CarrierType.computer_disc: "http://id.loc.gov/vocabulary/carriers/cd",
        CarrierType.videodisc: "http://id.loc.gov/vocabulary/carriers/vd",
    }

    # Media type mappings
    MEDIA_TYPE_URIS = {
        MediaType.unmediated: "http://id.loc.gov/vocabulary/mediaTypes/n",
        MediaType.computer: "http://id.loc.gov/vocabulary/mediaTypes/c",
        MediaType.audio: "http://id.loc.gov/vocabulary/mediaTypes/s",
        MediaType.video: "http://id.loc.gov/vocabulary/mediaTypes/v",
        MediaType.microform: "http://id.loc.gov/vocabulary/mediaTypes/h",
    }

    # Role mappings to MARC relator codes
    ROLE_URIS = {
        ContributorRole.author: "http://id.loc.gov/vocabulary/relators/aut",
        ContributorRole.editor: "http://id.loc.gov/vocabulary/relators/edt",
        ContributorRole.illustrator: "http://id.loc.gov/vocabulary/relators/ill",
        ContributorRole.translator: "http://id.loc.gov/vocabulary/relators/trl",
        ContributorRole.composer: "http://id.loc.gov/vocabulary/relators/cmp",
        ContributorRole.narrator: "http://id.loc.gov/vocabulary/relators/nrt",
        ContributorRole.director: "http://id.loc.gov/vocabulary/relators/drt",
        ContributorRole.producer: "http://id.loc.gov/vocabulary/relators/pro",
        ContributorRole.performer: "http://id.loc.gov/vocabulary/relators/prf",
        ContributorRole.photographer: "http://id.loc.gov/vocabulary/relators/pht",
        ContributorRole.contributor: "http://id.loc.gov/vocabulary/relators/ctb",
        ContributorRole.creator: "http://id.loc.gov/vocabulary/relators/cre",
    }

    # Authority source URIs
    AUTHORITY_BASE_URIS = {
        AuthoritySource.VIAF: "https://viaf.org/viaf/",
        AuthoritySource.LCNAF: "https://id.loc.gov/authorities/names/",
        AuthoritySource.LCCN: "https://lccn.loc.gov/",
        AuthoritySource.LCSH: "https://id.loc.gov/authorities/subjects/",
        AuthoritySource.FAST: "https://id.worldcat.org/fast/",
        AuthoritySource.WIKIDATA: "https://www.wikidata.org/entity/",
        AuthoritySource.ISNI: "https://isni.org/isni/",
        AuthoritySource.ORCID: "https://orcid.org/",
        AuthoritySource.GND: "https://d-nb.info/gnd/",
        AuthoritySource.OCLC: "https://www.worldcat.org/oclc/",
    }

    def __init__(self, base_uri: Optional[str] = None):
        if base_uri:
            self.BASE_URI = base_uri
            self.NAMESPACES["lsc"] = f"{base_uri}/ns/"

    # =========================================================================
    # Entity URI Generation
    # =========================================================================

    def get_work_uri(self, work: BibframeWork) -> str:
        return work.uri or f"{self.BASE_URI}/works/{work.id}"

    def get_instance_uri(self, instance: BibframeInstance) -> str:
        return instance.uri or f"{self.BASE_URI}/instances/{instance.id}"

    def get_item_uri(self, item: BibframeItem) -> str:
        return item.uri or f"{self.BASE_URI}/items/{item.id}"

    def get_contributor_uri(self, contributor: BibframeContributor) -> str:
        return contributor.uri or f"{self.BASE_URI}/contributors/{contributor.id}"

    def get_subject_uri(self, subject: BibframeSubject) -> str:
        return subject.uri or f"{self.BASE_URI}/subjects/{subject.id}"

    # =========================================================================
    # JSON-LD Serialization
    # =========================================================================

    def work_to_jsonld(
        self,
        work: BibframeWork,
        include_instances: bool = True,
        include_authorities: bool = True,
        embed_context: bool = True,
    ) -> dict[str, Any]:
        work_uri = self.get_work_uri(work)

        jsonld = {
            "@id": work_uri,
            "@type": ["bf:Work"],
        }

        if embed_context:
            jsonld["@context"] = self.JSONLD_CONTEXT

        # Title (as bf:Title node)
        title_node = {
            "@type": "bf:Title",
            "bf:mainTitle": work.title,
        }
        if work.subtitle:
            title_node["bf:subtitle"] = work.subtitle
        if work.title_variant:
            try:
                variants = json.loads(work.title_variant) if isinstance(work.title_variant, str) else work.title_variant
                if variants:
                    title_node["bf:variantTitle"] = variants
            except (json.JSONDecodeError, TypeError):
                _track_bibframe_parse_error()
        jsonld["bf:title"] = title_node

        # Content type
        if work.work_type:
            content_uri = self.WORK_TYPE_URIS.get(work.work_type)
            if content_uri:
                jsonld["bf:content"] = {"@id": content_uri}
            else:
                jsonld["bf:content"] = {"rdfs:label": work.work_type}

        # Language
        if work.language:
            jsonld["bf:language"] = {
                "@id": f"http://id.loc.gov/vocabulary/languages/{work.language}"
            }

        # Summary
        if work.summary:
            jsonld["bf:summary"] = {
                "@type": "bf:Summary",
                "rdfs:label": work.summary
            }

        # Table of contents
        if work.table_of_contents:
            jsonld["bf:tableOfContents"] = {
                "@type": "bf:TableOfContents",
                "rdfs:label": work.table_of_contents
            }

        # Genre/Form
        if work.genre_form:
            try:
                genres = json.loads(work.genre_form) if isinstance(work.genre_form, str) else work.genre_form
                if genres:
                    jsonld["bf:genreForm"] = [
                        {"@type": "bf:GenreForm", "rdfs:label": g} for g in genres
                    ]
            except (json.JSONDecodeError, TypeError):
                _track_bibframe_parse_error()

        # Classification
        classifications = []
        if work.dewey_classification:
            classifications.append({
                "@type": "bf:ClassificationDdc",
                "bf:classificationPortion": work.dewey_classification,
                "bf:source": {"@id": "http://id.loc.gov/vocabulary/classSchemes/ddc"}
            })
        if work.lc_classification:
            classifications.append({
                "@type": "bf:ClassificationLcc",
                "bf:classificationPortion": work.lc_classification,
                "bf:source": {"@id": "http://id.loc.gov/vocabulary/classSchemes/lcc"}
            })
        if classifications:
            jsonld["bf:classification"] = classifications

        # Series
        if work.series_title:
            series_node = {
                "@type": "bf:Series",
                "bf:title": {"bf:mainTitle": work.series_title}
            }
            if work.series_number:
                series_node["bf:seriesEnumeration"] = work.series_number
            jsonld["bf:hasSeries"] = series_node

        # Intended audience
        if work.intended_audience:
            jsonld["bf:intendedAudience"] = {
                "@type": "bf:IntendedAudience",
                "rdfs:label": work.intended_audience
            }

        # Notes
        if work.notes:
            try:
                notes = json.loads(work.notes) if isinstance(work.notes, str) else work.notes
                if notes:
                    jsonld["bf:note"] = [
                        {"@type": "bf:Note", "rdfs:label": n} for n in notes
                    ]
            except (json.JSONDecodeError, TypeError):
                _track_bibframe_parse_error()

        # Contributors
        if work.contributors:
            contributions = []
            for contrib in work.contributors:
                contribution = self._contributor_to_contribution(contrib)
                contributions.append(contribution)
            if contributions:
                jsonld["bf:contribution"] = contributions

        # Subjects
        if work.subjects:
            subjects = []
            for subj in work.subjects:
                subject_node = self._subject_to_jsonld(subj)
                subjects.append(subject_node)
            if subjects:
                jsonld["bf:subject"] = subjects

        # Authority links
        if include_authorities and work.authority_links:
            same_as = []
            for link in work.authority_links:
                authority_uri = self._get_authority_uri(link)
                if authority_uri:
                    same_as.append({"@id": authority_uri})
            if same_as:
                jsonld["owl:sameAs"] = same_as

        # Linked instances
        if include_instances and work.instances:
            jsonld["bf:hasInstance"] = [
                {"@id": self.get_instance_uri(inst)} for inst in work.instances
            ]

        # Additional linked data
        if work.linked_data:
            for key, value in work.linked_data.items():
                if key not in jsonld:
                    jsonld[key] = value

        # Administrative metadata
        jsonld["dcterms:created"] = work.created_at.isoformat() if work.created_at else None
        if work.updated_at:
            jsonld["dcterms:modified"] = work.updated_at.isoformat()

        return jsonld

    def instance_to_jsonld(
        self,
        instance: BibframeInstance,
        include_work: bool = True,
        include_items: bool = True,
        include_authorities: bool = True,
        embed_context: bool = True,
    ) -> dict[str, Any]:
        instance_uri = self.get_instance_uri(instance)

        jsonld = {
            "@id": instance_uri,
            "@type": ["bf:Instance"],
        }

        if embed_context:
            jsonld["@context"] = self.JSONLD_CONTEXT

        # Link to work
        if include_work and instance.work_id:
            if instance.work:
                jsonld["bf:instanceOf"] = {"@id": self.get_work_uri(instance.work)}
            else:
                jsonld["bf:instanceOf"] = {"@id": f"{self.BASE_URI}/works/{instance.work_id}"}

        # Title
        title_node = {
            "@type": "bf:Title",
            "bf:mainTitle": instance.title,
        }
        if instance.subtitle:
            title_node["bf:subtitle"] = instance.subtitle
        jsonld["bf:title"] = title_node

        # Identifiers
        identifiers = []
        if instance.isbn_13:
            identifiers.append({
                "@type": "bf:Isbn",
                "rdf:value": instance.isbn_13
            })
        if instance.isbn_10:
            identifiers.append({
                "@type": "bf:Isbn",
                "rdf:value": instance.isbn_10,
                "bf:qualifier": "ISBN-10"
            })
        if instance.lccn:
            identifiers.append({
                "@type": "bf:Lccn",
                "rdf:value": instance.lccn
            })
        if instance.oclc_number:
            identifiers.append({
                "@type": "bf:Local",
                "rdf:value": instance.oclc_number,
                "bf:source": {"rdfs:label": "OCoLC"}
            })
        if instance.issn:
            identifiers.append({
                "@type": "bf:Issn",
                "rdf:value": instance.issn
            })
        if identifiers:
            jsonld["bf:identifiedBy"] = identifiers

        # Carrier type
        carrier_uri = self.CARRIER_TYPE_URIS.get(instance.carrier_type)
        if carrier_uri:
            jsonld["bf:carrier"] = {"@id": carrier_uri}

        # Media type
        media_uri = self.MEDIA_TYPE_URIS.get(instance.media_type)
        if media_uri:
            jsonld["bf:media"] = {"@id": media_uri}

        # Publication info (provisionActivity)
        if instance.publisher or instance.publication_date or instance.publisher_place:
            provision = {
                "@type": "bf:Publication"
            }
            if instance.publisher:
                provision["bf:agent"] = {
                    "@type": "bf:Agent",
                    "rdfs:label": instance.publisher
                }
            if instance.publisher_place:
                provision["bf:place"] = {
                    "@type": "bf:Place",
                    "rdfs:label": instance.publisher_place
                }
            if instance.publication_date:
                provision["bf:date"] = instance.publication_date
            elif instance.publication_year:
                provision["bf:date"] = str(instance.publication_year)
            jsonld["bf:provisionActivity"] = provision

        # Copyright
        if instance.copyright_date:
            jsonld["bf:copyrightDate"] = instance.copyright_date

        # Edition
        if instance.edition:
            jsonld["bf:editionStatement"] = instance.edition

        # Physical description
        if instance.extent or instance.page_count:
            extent_value = instance.extent or f"{instance.page_count} pages"
            jsonld["bf:extent"] = {
                "@type": "bf:Extent",
                "rdfs:label": extent_value
            }

        if instance.dimensions:
            jsonld["bf:dimensions"] = instance.dimensions

        if instance.illustration_note:
            jsonld["bf:illustrativeContent"] = {
                "@type": "bf:Illustration",
                "rdfs:label": instance.illustration_note
            }

        # Cover image
        if instance.cover_url:
            jsonld["bf:coverArt"] = {
                "@type": "bf:CoverArt",
                "bf:electronicLocator": {"@id": instance.cover_url}
            }

        # Electronic access
        if instance.access_url:
            jsonld["bf:electronicLocator"] = {"@id": instance.access_url}

        # Digital format
        if instance.digital_format:
            jsonld["bf:digitalCharacteristic"] = {
                "@type": "bf:FileType",
                "rdfs:label": instance.digital_format
            }

        # Notes
        if instance.notes:
            try:
                notes = json.loads(instance.notes) if isinstance(instance.notes, str) else instance.notes
                if notes:
                    jsonld["bf:note"] = [
                        {"@type": "bf:Note", "rdfs:label": n} for n in notes
                    ]
            except (json.JSONDecodeError, TypeError):
                _track_bibframe_parse_error()

        # Instance-specific contributors
        if instance.contributors:
            contributions = []
            for contrib in instance.contributors:
                contribution = self._contributor_to_contribution(contrib)
                contributions.append(contribution)
            if contributions:
                jsonld["bf:contribution"] = contributions

        # Authority links
        if include_authorities and instance.authority_links:
            same_as = []
            for link in instance.authority_links:
                authority_uri = self._get_authority_uri(link)
                if authority_uri:
                    same_as.append({"@id": authority_uri})
            if same_as:
                jsonld["owl:sameAs"] = same_as

        # Linked items
        if include_items and instance.items:
            jsonld["bf:hasItem"] = [
                {"@id": self.get_item_uri(item)} for item in instance.items
            ]

        # Additional linked data
        if instance.linked_data:
            for key, value in instance.linked_data.items():
                if key not in jsonld:
                    jsonld[key] = value

        # Administrative metadata
        jsonld["dcterms:created"] = instance.created_at.isoformat() if instance.created_at else None
        if instance.updated_at:
            jsonld["dcterms:modified"] = instance.updated_at.isoformat()

        return jsonld

    def item_to_jsonld(
        self,
        item: BibframeItem,
        include_instance: bool = True,
        include_authorities: bool = True,
        embed_context: bool = True,
    ) -> dict[str, Any]:
        item_uri = self.get_item_uri(item)

        jsonld = {
            "@id": item_uri,
            "@type": ["bf:Item"],
        }

        if embed_context:
            jsonld["@context"] = self.JSONLD_CONTEXT

        # Link to instance
        if include_instance and item.instance_id:
            if item.instance:
                jsonld["bf:itemOf"] = {"@id": self.get_instance_uri(item.instance)}
            else:
                jsonld["bf:itemOf"] = {"@id": f"{self.BASE_URI}/instances/{item.instance_id}"}

        # Identifiers
        identifiers = []
        if item.barcode:
            identifiers.append({
                "@type": "bf:Barcode",
                "rdf:value": item.barcode
            })
        if item.accession_number:
            identifiers.append({
                "@type": "bf:Local",
                "rdf:value": item.accession_number,
                "bf:qualifier": "accession"
            })
        if identifiers:
            jsonld["bf:identifiedBy"] = identifiers

        # Shelf mark / call number
        if item.call_number:
            jsonld["bf:shelfMark"] = {
                "@type": "bf:ShelfMark",
                "rdfs:label": item.call_number
            }

        # Location / holding
        held_by = {
            "@type": "bf:Agent",
            "rdfs:label": os.environ.get("LIBRARY_NAME", "My Library")
        }
        if item.library_branch:
            held_by["bf:place"] = {"rdfs:label": item.library_branch}
        jsonld["bf:heldBy"] = held_by

        # Sublocation
        if item.shelving_location:
            jsonld["bf:sublocation"] = {
                "@type": "bf:Sublocation",
                "rdfs:label": item.shelving_location
            }

        # Collection
        if item.collection:
            jsonld["bf:usageAndAccessPolicy"] = {
                "@type": "bf:UsageAndAccessPolicy",
                "rdfs:label": f"Collection: {item.collection}"
            }

        # Circulation status
        if item.circulation_status:
            jsonld["bf:circulationStatus"] = item.circulation_status

        # Electronic access
        if item.electronic_locator:
            jsonld["bf:electronicLocator"] = {"@id": item.electronic_locator}

        # Notes
        if item.public_note:
            jsonld["bf:note"] = {
                "@type": "bf:Note",
                "rdfs:label": item.public_note
            }

        # Acquisition info
        if item.acquisition_date:
            jsonld["bf:acquisitionDate"] = item.acquisition_date.isoformat()

        # Authority links
        if include_authorities and item.authority_links:
            same_as = []
            for link in item.authority_links:
                authority_uri = self._get_authority_uri(link)
                if authority_uri:
                    same_as.append({"@id": authority_uri})
            if same_as:
                jsonld["owl:sameAs"] = same_as

        # Additional linked data
        if item.linked_data:
            for key, value in item.linked_data.items():
                if key not in jsonld:
                    jsonld[key] = value

        # Administrative metadata
        jsonld["dcterms:created"] = item.created_at.isoformat() if item.created_at else None
        if item.updated_at:
            jsonld["dcterms:modified"] = item.updated_at.isoformat()

        return jsonld

    def contributor_to_jsonld(
        self,
        contributor: BibframeContributor,
        include_authorities: bool = True,
        embed_context: bool = True,
    ) -> dict[str, Any]:
        contributor_uri = self.get_contributor_uri(contributor)

        # Determine type based on contributor_type
        rdf_types = ["bf:Agent"]
        if contributor.contributor_type == "person":
            rdf_types.append("bf:Person")
        elif contributor.contributor_type == "organization":
            rdf_types.append("bf:Organization")
        elif contributor.contributor_type == "meeting":
            rdf_types.append("bf:Meeting")

        jsonld = {
            "@id": contributor_uri,
            "@type": rdf_types,
            "rdfs:label": contributor.name,
        }

        if embed_context:
            jsonld["@context"] = self.JSONLD_CONTEXT

        # Person-specific fields
        if contributor.contributor_type == "person":
            if contributor.given_name:
                jsonld["schema:givenName"] = contributor.given_name
            if contributor.family_name:
                jsonld["schema:familyName"] = contributor.family_name
            if contributor.birth_date:
                jsonld["schema:birthDate"] = contributor.birth_date
            if contributor.death_date:
                jsonld["schema:deathDate"] = contributor.death_date

        # Alternate names
        if contributor.alternate_names:
            try:
                alt_names = json.loads(contributor.alternate_names) if isinstance(contributor.alternate_names, str) else contributor.alternate_names
                if alt_names:
                    jsonld["schema:alternateName"] = alt_names
            except (json.JSONDecodeError, TypeError):
                _track_bibframe_parse_error()

        # Biography
        if contributor.biography:
            jsonld["schema:description"] = contributor.biography

        # Authority links as owl:sameAs
        same_as = []
        if contributor.viaf_id:
            same_as.append({"@id": f"https://viaf.org/viaf/{contributor.viaf_id}"})
        if contributor.lcnaf_id:
            same_as.append({"@id": f"https://id.loc.gov/authorities/names/{contributor.lcnaf_id}"})
        if contributor.wikidata_id:
            same_as.append({"@id": f"https://www.wikidata.org/entity/{contributor.wikidata_id}"})
        if contributor.isni:
            same_as.append({"@id": f"https://isni.org/isni/{contributor.isni}"})
        if contributor.orcid:
            same_as.append({"@id": f"https://orcid.org/{contributor.orcid}"})

        if include_authorities and contributor.authority_links:
            for link in contributor.authority_links:
                authority_uri = self._get_authority_uri(link)
                if authority_uri and not any(s.get("@id") == authority_uri for s in same_as):
                    same_as.append({"@id": authority_uri})

        if same_as:
            jsonld["owl:sameAs"] = same_as

        return jsonld

    # =========================================================================
    # Turtle Serialization
    # =========================================================================

    def work_to_turtle(
        self,
        work: BibframeWork,
        include_instances: bool = True,
        include_authorities: bool = True,
    ) -> str:
        jsonld = self.work_to_jsonld(work, include_instances, include_authorities, embed_context=False)
        return self._jsonld_to_turtle(jsonld)

    def instance_to_turtle(
        self,
        instance: BibframeInstance,
        include_work: bool = True,
        include_items: bool = True,
        include_authorities: bool = True,
    ) -> str:
        jsonld = self.instance_to_jsonld(instance, include_work, include_items, include_authorities, embed_context=False)
        return self._jsonld_to_turtle(jsonld)

    def item_to_turtle(
        self,
        item: BibframeItem,
        include_instance: bool = True,
        include_authorities: bool = True,
    ) -> str:
        jsonld = self.item_to_jsonld(item, include_instance, include_authorities, embed_context=False)
        return self._jsonld_to_turtle(jsonld)

    def _jsonld_to_turtle(self, jsonld: dict[str, Any]) -> str:
        lines = []

        # Prefixes
        for prefix, uri in self.NAMESPACES.items():
            lines.append(f"@prefix {prefix}: <{uri}> .")
        lines.append("")

        # Subject
        subject_uri = jsonld.get("@id", "_:blank")
        lines.append(f"<{subject_uri}>")

        # Types
        types = jsonld.get("@type", [])
        if isinstance(types, str):
            types = [types]
        if types:
            type_strs = [self._to_prefixed_uri(t) for t in types]
            lines.append(f"    a {', '.join(type_strs)} ;")

        # Properties
        properties = []
        for key, value in jsonld.items():
            if key.startswith("@"):
                continue

            predicate = self._to_prefixed_uri(key)
            obj_str = self._value_to_turtle(value)
            if obj_str:
                properties.append(f"    {predicate} {obj_str}")

        if properties:
            lines.append(" ;\n".join(properties) + " .")
        else:
            # Remove trailing semicolon from type declaration
            if lines[-1].endswith(" ;"):
                lines[-1] = lines[-1][:-2] + " ."

        return "\n".join(lines)

    def _to_prefixed_uri(self, uri_or_curie: str) -> str:
        if uri_or_curie.startswith("http://") or uri_or_curie.startswith("https://"):
            for prefix, base_uri in self.NAMESPACES.items():
                if uri_or_curie.startswith(base_uri):
                    local = uri_or_curie[len(base_uri):]
                    return f"{prefix}:{local}"
            return f"<{uri_or_curie}>"

        # Already prefixed
        if ":" in uri_or_curie and not uri_or_curie.startswith("_:"):
            return uri_or_curie

        # Default to bf: namespace
        return f"bf:{uri_or_curie}"

    def _value_to_turtle(self, value: Any) -> str:
        if value is None:
            return ""

        if isinstance(value, dict):
            if "@id" in value:
                return f"<{value['@id']}>"
            if "@value" in value:
                literal = value["@value"]
                if "@type" in value:
                    return f'"{literal}"^^{self._to_prefixed_uri(value["@type"])}'
                if "@language" in value:
                    return f'"{literal}"@{value["@language"]}'
                return f'"{literal}"'
            # Blank node
            return "[]"

        if isinstance(value, list):
            if not value:
                return ""
            items = [self._value_to_turtle(v) for v in value]
            items = [i for i in items if i]
            return ", ".join(items) if items else ""

        if isinstance(value, bool):
            return "true" if value else "false"

        if isinstance(value, (int, float)):
            return str(value)

        if isinstance(value, str):
            # Escape quotes
            escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            return f'"{escaped}"'

        return f'"{value}"'

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _contributor_to_contribution(
        self,
        contributor: BibframeContributor,
        role: ContributorRole = ContributorRole.author,
    ) -> dict[str, Any]:
        contribution = {
            "@type": "bf:Contribution",
            "bf:agent": {
                "@id": self.get_contributor_uri(contributor),
                "@type": "bf:Person" if contributor.contributor_type == "person" else "bf:Agent",
                "rdfs:label": contributor.name,
            }
        }

        # Role
        role_uri = self.ROLE_URIS.get(role)
        if role_uri:
            contribution["bf:role"] = {"@id": role_uri}

        # Authority links on agent
        same_as = []
        if contributor.viaf_id:
            same_as.append({"@id": f"https://viaf.org/viaf/{contributor.viaf_id}"})
        if contributor.lcnaf_id:
            same_as.append({"@id": f"https://id.loc.gov/authorities/names/{contributor.lcnaf_id}"})
        if contributor.wikidata_id:
            same_as.append({"@id": f"https://www.wikidata.org/entity/{contributor.wikidata_id}"})
        if same_as:
            contribution["bf:agent"]["owl:sameAs"] = same_as

        return contribution

    def _subject_to_jsonld(self, subject: BibframeSubject) -> dict[str, Any]:
        subject_types = {
            "topic": "bf:Topic",
            "place": "bf:Place",
            "temporal": "bf:Temporal",
            "person": "bf:Person",
            "organization": "bf:Organization",
        }

        rdf_type = subject_types.get(subject.subject_type, "bf:Topic")

        node = {
            "@id": self.get_subject_uri(subject),
            "@type": rdf_type,
            "rdfs:label": subject.label,
        }

        # Authority links
        same_as = []
        if subject.lcsh_id:
            same_as.append({"@id": f"https://id.loc.gov/authorities/subjects/{subject.lcsh_id}"})
        if subject.fast_id:
            same_as.append({"@id": f"https://id.worldcat.org/fast/{subject.fast_id}"})
        if subject.wikidata_id:
            same_as.append({"@id": f"https://www.wikidata.org/entity/{subject.wikidata_id}"})
        if same_as:
            node["owl:sameAs"] = same_as

        return node

    def _get_authority_uri(self, link: AuthorityLink) -> Optional[str]:
        if link.authority_uri:
            return link.authority_uri

        base_uri = self.AUTHORITY_BASE_URIS.get(link.source)
        if base_uri and link.authority_id:
            return f"{base_uri}{link.authority_id}"

        return None

    # =========================================================================
    # Streaming Export (Memory-Efficient)
    # =========================================================================

    def stream_jsonld_export(
        self,
        works: Optional[list[BibframeWork]] = None,
        instances: Optional[list[BibframeInstance]] = None,
        items: Optional[list[BibframeItem]] = None,
        include_authorities: bool = True,
        buffer_size: int = 100,
    ) -> str:
        output_lines = []
        output_lines.append('{"@context":')
        output_lines.append(json.dumps(self.JSONLD_CONTEXT, ensure_ascii=False))
        output_lines.append(',"@graph":[')

        first_item = True

        # Stream works
        if works:
            for work in works:
                jsonld = self.work_to_jsonld(work, include_authorities=include_authorities, embed_context=False)
                if not first_item:
                    output_lines.append(',')
                output_lines.append(json.dumps(jsonld, ensure_ascii=False))
                first_item = False

        # Stream instances
        if instances:
            for instance in instances:
                jsonld = self.instance_to_jsonld(instance, include_authorities=include_authorities, embed_context=False)
                if not first_item:
                    output_lines.append(',')
                output_lines.append(json.dumps(jsonld, ensure_ascii=False))
                first_item = False

        # Stream items
        if items:
            for item in items:
                jsonld = self.item_to_jsonld(item, include_authorities=include_authorities, embed_context=False)
                if not first_item:
                    output_lines.append(',')
                output_lines.append(json.dumps(jsonld, ensure_ascii=False))
                first_item = False

        output_lines.append(']}')
        return ''.join(output_lines)

    def stream_turtle_export(
        self,
        works: Optional[list[BibframeWork]] = None,
        instances: Optional[list[BibframeInstance]] = None,
        items: Optional[list[BibframeItem]] = None,
        include_authorities: bool = True,
    ) -> str:
        lines = []

        # Prefixes (output once at beginning)
        for prefix, uri in self.NAMESPACES.items():
            lines.append(f"@prefix {prefix}: <{uri}> .")
        lines.append("")

        # Stream works
        if works:
            for work in works:
                turtle = self.work_to_turtle(work, include_authorities=include_authorities)
                # Extract just the triples (skip prefix declarations)
                turtle_lines = turtle.split('\n')
                for line in turtle_lines:
                    if not line.startswith('@prefix'):
                        lines.append(line)
                lines.append("")

        # Stream instances
        if instances:
            for instance in instances:
                turtle = self.instance_to_turtle(instance, include_authorities=include_authorities)
                turtle_lines = turtle.split('\n')
                for line in turtle_lines:
                    if not line.startswith('@prefix'):
                        lines.append(line)
                lines.append("")

        # Stream items
        if items:
            for item in items:
                turtle = self.item_to_turtle(item, include_authorities=include_authorities)
                turtle_lines = turtle.split('\n')
                for line in turtle_lines:
                    if not line.startswith('@prefix'):
                        lines.append(line)
                lines.append("")

        return "\n".join(lines)

    # =========================================================================
    # Batch Export
    # =========================================================================

    def export_graph(
        self,
        works: Optional[list[BibframeWork]] = None,
        instances: Optional[list[BibframeInstance]] = None,
        items: Optional[list[BibframeItem]] = None,
        format: str = "jsonld",
        include_authorities: bool = True,
    ) -> str:
        if format == "jsonld":
            graph = {
                "@context": self.JSONLD_CONTEXT,
                "@graph": []
            }

            if works:
                for work in works:
                    graph["@graph"].append(
                        self.work_to_jsonld(work, include_authorities=include_authorities, embed_context=False)
                    )

            if instances:
                for instance in instances:
                    graph["@graph"].append(
                        self.instance_to_jsonld(instance, include_authorities=include_authorities, embed_context=False)
                    )

            if items:
                for item in items:
                    graph["@graph"].append(
                        self.item_to_jsonld(item, include_authorities=include_authorities, embed_context=False)
                    )

            return json.dumps(graph, indent=2, ensure_ascii=False)

        elif format == "turtle":
            lines = []

            # Prefixes
            for prefix, uri in self.NAMESPACES.items():
                lines.append(f"@prefix {prefix}: <{uri}> .")
            lines.append("")

            if works:
                for work in works:
                    lines.append(self.work_to_turtle(work, include_authorities=include_authorities))
                    lines.append("")

            if instances:
                for instance in instances:
                    lines.append(self.instance_to_turtle(instance, include_authorities=include_authorities))
                    lines.append("")

            if items:
                for item in items:
                    lines.append(self.item_to_turtle(item, include_authorities=include_authorities))
                    lines.append("")

            return "\n".join(lines)

        else:
            raise ValueError(f"Unsupported format: {format}. Use 'jsonld' or 'turtle'.")


# Singleton instance
bibframe_rdf_service = BibframeRdfService()
