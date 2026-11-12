# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import re
from datetime import datetime
from io import BytesIO
from typing import Any, Optional

from pymarc import MARCReader, Record, Field

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
from ..models.catalog import CatalogItem
from ..utils.title_extraction_utils import normalize_title_for_sorting
from ..utils.identifier_normalizer import IdentifierNormalizer


class MarcToBibframeService:

    # MARC Leader position 06 to Work type mapping
    LEADER_06_TO_WORK_TYPE = {
        "a": WorkType.text,                    # Language material
        "c": WorkType.notated_music,           # Notated music
        "d": WorkType.notated_music,           # Manuscript notated music
        "e": WorkType.cartographic_image,      # Cartographic material
        "f": WorkType.cartographic_image,      # Manuscript cartographic
        "g": WorkType.two_dimensional_moving_image,  # Projected medium
        "i": WorkType.spoken_word,             # Nonmusical sound recording
        "j": WorkType.performed_music,         # Musical sound recording
        "k": WorkType.still_image,             # Two-dimensional nonprojectable graphic
        "m": WorkType.computer_program,        # Computer file
        "o": WorkType.other,                   # Kit
        "p": WorkType.other,                   # Mixed materials
        "r": WorkType.three_dimensional_form,  # Three-dimensional artifact
        "t": WorkType.text,                    # Manuscript language material
    }

    # MARC 007 position 00 to Instance type mapping
    FIELD_007_TO_INSTANCE_TYPE = {
        "a": InstanceType.print,       # Map
        "c": InstanceType.electronic,  # Electronic resource
        "d": InstanceType.print,       # Globe
        "f": InstanceType.tactile,     # Tactile material
        "g": InstanceType.audiovisual, # Projected graphic
        "h": InstanceType.microform,   # Microform
        "k": InstanceType.print,       # Nonprojected graphic
        "m": InstanceType.audiovisual, # Motion picture
        "o": InstanceType.print,       # Kit
        "q": InstanceType.print,       # Notated music
        "r": InstanceType.print,       # Remote-sensing image
        "s": InstanceType.audio,       # Sound recording
        "t": InstanceType.print,       # Text
        "v": InstanceType.audiovisual, # Videorecording
        "z": InstanceType.print,       # Unspecified
    }

    # MARC 007 to Carrier type (for sound recordings)
    FIELD_007_CARRIER = {
        "d": CarrierType.audio_disc,     # Sound disc
        "e": CarrierType.other,          # Cylinder
        "g": CarrierType.other,          # Sound cartridge
        "i": CarrierType.other,          # Sound-track film
        "q": CarrierType.other,          # Roll
        "s": CarrierType.audiocassette,  # Sound cassette
        "t": CarrierType.other,          # Sound-tape reel
        "u": CarrierType.other,          # Unspecified
        "w": CarrierType.other,          # Wire recording
        "z": CarrierType.other,          # Other
    }

    # MARC 338 $b to Carrier type mapping
    RDA_CARRIER_CODES = {
        "nc": CarrierType.volume,
        "nb": CarrierType.sheet,
        "nr": CarrierType.object,
        "sd": CarrierType.audio_disc,
        "ss": CarrierType.audiocassette,
        "cd": CarrierType.computer_disc,
        "cr": CarrierType.online_resource,
        "vd": CarrierType.videodisc,
        "vc": CarrierType.videocassette,
        "hd": CarrierType.microfilm_reel,
        "he": CarrierType.microfiche,
    }

    # MARC 337 $b to Media type mapping
    RDA_MEDIA_CODES = {
        "n": MediaType.unmediated,
        "c": MediaType.computer,
        "s": MediaType.audio,
        "v": MediaType.video,
        "h": MediaType.microform,
        "g": MediaType.projected,
        "e": MediaType.stereographic,
        "p": MediaType.microscopic,
    }

    # MARC relator codes to ContributorRole mapping
    RELATOR_CODES = {
        "aut": ContributorRole.author,
        "edt": ContributorRole.editor,
        "ill": ContributorRole.illustrator,
        "trl": ContributorRole.translator,
        "cmp": ContributorRole.composer,
        "lyr": ContributorRole.lyricist,
        "prf": ContributorRole.performer,
        "nrt": ContributorRole.narrator,
        "drt": ContributorRole.director,
        "pro": ContributorRole.producer,
        "pht": ContributorRole.photographer,
        "com": ContributorRole.compiler,
        "ctb": ContributorRole.contributor,
        "cre": ContributorRole.creator,
    }

    # Language code mapping (MARC to ISO 639-2/B)
    # MARC uses ISO 639-2/B codes already, but some need normalization
    LANGUAGE_CODE_MAP = {
        "eng": "eng",
        "spa": "spa",
        "fre": "fre",
        "ger": "ger",
        "ita": "ita",
        "por": "por",
        "rus": "rus",
        "chi": "chi",
        "jpn": "jpn",
        "kor": "kor",
        "ara": "ara",
        "heb": "heb",
        "hin": "hin",
        "und": "und",  # Undetermined
        "mul": "mul",  # Multiple languages
        "zxx": "zxx",  # No linguistic content
    }

    def __init__(self):
        self.warnings: list[str] = []

    def convert_marc_record(
        self,
        record: Record,
        catalog_item: Optional[CatalogItem] = None,
    ) -> dict[str, Any]:
        self.warnings = []

        # Extract work-level data
        work = self._create_work(record, catalog_item)

        # Extract instance-level data
        instance = self._create_instance(record, work, catalog_item)

        # Extract contributors
        contributors, contributor_links = self._extract_contributors(record)

        # Extract subjects
        subjects, subject_links = self._extract_subjects(record)

        # Combine authority links
        authority_links = contributor_links + subject_links

        # Add identifier-based authority links
        authority_links.extend(self._extract_identifier_links(record, instance))

        return {
            "work": work,
            "instance": instance,
            "contributors": contributors,
            "subjects": subjects,
            "authority_links": authority_links,
            "warnings": self.warnings,
        }

    def convert_marc_xml(
        self,
        marc_xml: str,
        catalog_item: Optional[CatalogItem] = None,
    ) -> dict[str, Any]:
        from pymarc import parse_xml_to_array
        from io import StringIO

        records = parse_xml_to_array(StringIO(marc_xml))
        if not records:
            self.warnings.append("No records found in MARC XML")
            return {
                "work": None,
                "instance": None,
                "contributors": [],
                "subjects": [],
                "authority_links": [],
                "warnings": self.warnings,
            }

        return self.convert_marc_record(records[0], catalog_item)

    def convert_marc21_binary(
        self,
        marc_data: bytes,
        catalog_item: Optional[CatalogItem] = None,
    ) -> dict[str, Any]:
        reader = MARCReader(BytesIO(marc_data))
        record = next(reader, None)
        if not record:
            self.warnings.append("No records found in MARC data")
            return {
                "work": None,
                "instance": None,
                "contributors": [],
                "subjects": [],
                "authority_links": [],
                "warnings": self.warnings,
            }

        return self.convert_marc_record(record, catalog_item)

    def convert_catalog_item(self, catalog_item: CatalogItem) -> dict[str, Any]:
        self.warnings = []

        # Create Work from catalog item
        work = BibframeWork(
            title=catalog_item.title,
            title_sort=self._generate_sort_title(catalog_item.title),
            work_type=self._catalog_item_type_to_work_type(catalog_item.item_type),
            language="eng",  # Default
            summary=catalog_item.description,
            dewey_classification=catalog_item.dewey_decimal,
            lc_classification=catalog_item.lc_classification,
            catalog_item_id=catalog_item.id,
            source="local",
            source_record_id=f"CAT-{catalog_item.id}",
        )

        # Parse subjects
        if catalog_item.subjects:
            work.genre_form = json.dumps([s.strip() for s in re.split(r"[,;]", catalog_item.subjects) if s.strip()])

        # Create Instance
        instance = BibframeInstance(
            title=catalog_item.title,
            instance_type=self._catalog_item_type_to_instance_type(catalog_item.item_type),
            carrier_type=self._catalog_item_type_to_carrier(catalog_item.item_type),
            media_type=self._catalog_item_type_to_media(catalog_item.item_type),
            isbn_13=self._normalize_isbn(catalog_item.isbn) if catalog_item.isbn else None,
            publisher=catalog_item.publisher,
            publication_year=catalog_item.publication_year,
            page_count=catalog_item.page_count,
            cover_url=catalog_item.cover_url,
            catalog_item_id=catalog_item.id,
            source="local",
            source_record_id=f"CAT-{catalog_item.id}",
        )

        # Create Item
        item = BibframeItem(
            barcode=catalog_item.barcode,
            call_number=catalog_item.call_number,
            shelving_location=catalog_item.location,
            circulation_status=str(catalog_item.status) if catalog_item.status else "available",
        )

        # Create contributor if author exists
        contributors = []
        if catalog_item.author:
            contributor = BibframeContributor(
                name=catalog_item.author,
                contributor_type="person",
                name_inverted=self._invert_name(catalog_item.author),
                name_sort=self._generate_sort_name(catalog_item.author),
            )
            contributors.append(contributor)

        # Create subjects from subjects field
        subjects = []
        if catalog_item.subjects:
            for subject_label in re.split(r"[,;]", catalog_item.subjects):
                subject_label = subject_label.strip()
                if subject_label:
                    subject = BibframeSubject(
                        label=subject_label,
                        label_normalized=subject_label.lower(),
                        subject_type="topic",
                    )
                    subjects.append(subject)

        return {
            "work": work,
            "instance": instance,
            "item": item,
            "contributors": contributors,
            "subjects": subjects,
            "authority_links": [],
            "warnings": self.warnings,
        }

    def convert_catalog_item_from_dict(self, record_dict: dict[str, Any]) -> dict[str, Any]:
        self.warnings = []

        title = record_dict.get("title", "Unknown Title")
        author = record_dict.get("author")
        isbn = record_dict.get("isbn")
        publisher = record_dict.get("publisher")
        publication_year = record_dict.get("publication_year")
        description = record_dict.get("description")
        subjects_list = record_dict.get("subjects", [])
        lc_call = record_dict.get("lc_call_number")
        dewey = record_dict.get("dewey_decimal")
        edition = record_dict.get("edition")
        page_count = record_dict.get("page_count")
        control_number = record_dict.get("control_number")

        work = BibframeWork(
            title=title,
            title_sort=normalize_title_for_sorting(title) if title else None,
            work_type=WorkType.text,
            language="eng",
            summary=description,
            dewey_classification=dewey,
            lc_classification=lc_call,
            source="z3950_import",
            source_record_id=control_number,
        )

        if subjects_list:
            work.genre_form = json.dumps(subjects_list)

        instance = BibframeInstance(
            title=title,
            instance_type=InstanceType.print,
            carrier_type=CarrierType.volume,
            media_type=MediaType.unmediated,
            isbn_13=IdentifierNormalizer.normalize_isbn(isbn) if isbn else None,
            publisher=publisher,
            publication_year=publication_year,
            page_count=page_count,
            source="z3950_import",
            source_record_id=control_number,
        )

        if edition:
            instance.edition = edition

        contributors = []
        if author:
            contributors.append(BibframeContributor(
                name=author,
                contributor_type="person",
                name_inverted=self._invert_name(author),
                name_sort=self._generate_sort_name(author),
            ))

        subjects = []
        for subj in subjects_list:
            if subj:
                subjects.append(BibframeSubject(
                    label=subj,
                    label_normalized=subj.lower().rstrip(". "),
                    subject_type="topic",
                ))

        return {
            "work": work,
            "instance": instance,
            "contributors": contributors,
            "subjects": subjects,
            "authority_links": [],
            "warnings": self.warnings,
        }

    # =========================================================================
    # Private Methods - Entity Creation
    # =========================================================================

    def _create_work(
        self,
        record: Record,
        catalog_item: Optional[CatalogItem] = None,
    ) -> BibframeWork:
        # Extract work type from Leader
        work_type = self._get_work_type(record)

        # Extract title from 245
        title, subtitle, title_variants = self._extract_title(record)

        # Extract language from 008 or 041
        language = self._extract_language(record)

        # Extract classification
        dewey = self._extract_dewey(record)
        lc_class = self._extract_lc_classification(record)

        # Extract summary from 520
        summary = self._extract_summary(record)

        # Extract table of contents from 505
        toc = self._extract_toc(record)

        # Extract genre/form from 655
        genre_form = self._extract_genre_form(record)

        # Extract series from 490, 800, 810, 830
        series_title, series_number = self._extract_series(record)

        # Extract notes from various 5XX fields
        notes = self._extract_work_notes(record)

        # Extract intended audience from 521
        audience = self._extract_audience(record)

        # Extract control number for source tracking
        control_number = self._extract_control_number(record)

        work = BibframeWork(
            title=title,
            title_sort=self._generate_sort_title(title),
            subtitle=subtitle,
            title_variant=json.dumps(title_variants) if title_variants else None,
            work_type=work_type,
            language=language,
            summary=summary,
            table_of_contents=toc,
            genre_form=json.dumps(genre_form) if genre_form else None,
            dewey_classification=dewey,
            lc_classification=lc_class,
            series_title=series_title,
            series_number=series_number,
            intended_audience=audience,
            notes=json.dumps(notes) if notes else None,
            source="marc",
            source_record_id=control_number,
            catalog_item_id=catalog_item.id if catalog_item else None,
        )

        return work

    def _create_instance(
        self,
        record: Record,
        work: BibframeWork,
        catalog_item: Optional[CatalogItem] = None,
    ) -> BibframeInstance:
        # Instance type from 007 or leader
        instance_type = self._get_instance_type(record)

        # Carrier and media types from 337/338 or derived
        carrier_type, media_type = self._get_carrier_media_types(record)

        # Title (may include statement of responsibility)
        title = work.title
        title_statement = self._extract_title_statement(record)

        # Identifiers
        isbn_10, isbn_13 = self._extract_isbns(record)
        lccn = self._extract_lccn(record)
        oclc = self._extract_oclc(record)
        issn = self._extract_issn(record)

        # Publication info from 260 or 264
        publisher, place, pub_date, pub_year, copyright_date = self._extract_publication_info(record)

        # Edition from 250
        edition = self._extract_edition(record)

        # Physical description from 300
        extent, dimensions, page_count = self._extract_physical_description(record)

        # Notes
        notes = self._extract_instance_notes(record)

        # Control number
        control_number = self._extract_control_number(record)

        instance = BibframeInstance(
            title=title,
            subtitle=work.subtitle,
            title_statement=title_statement,
            instance_type=instance_type,
            carrier_type=carrier_type,
            media_type=media_type,
            isbn_10=isbn_10,
            isbn_13=isbn_13,
            lccn=lccn,
            oclc_number=oclc,
            issn=issn,
            publisher=publisher,
            publisher_place=place,
            publication_date=pub_date,
            publication_year=pub_year,
            copyright_date=copyright_date,
            edition=edition,
            extent=extent,
            dimensions=dimensions,
            page_count=page_count,
            notes=json.dumps(notes) if notes else None,
            source="marc",
            source_record_id=control_number,
            catalog_item_id=catalog_item.id if catalog_item else None,
        )

        return instance

    # =========================================================================
    # Private Methods - Field Extraction
    # =========================================================================

    def _get_work_type(self, record: Record) -> WorkType:
        leader = record.leader
        if leader and len(leader) > 6:
            type_code = leader[6]
            return self.LEADER_06_TO_WORK_TYPE.get(type_code, WorkType.other)
        return WorkType.text

    def _get_instance_type(self, record: Record) -> InstanceType:
        field_007 = record.get("007")
        if field_007 and hasattr(field_007, "data") and len(field_007.data) > 0:
            cat_code = field_007.data[0]
            return self.FIELD_007_TO_INSTANCE_TYPE.get(cat_code, InstanceType.print)

        # Fall back to leader
        leader = record.leader
        if leader and len(leader) > 6:
            type_code = leader[6]
            if type_code in ["c", "d", "j"]:
                return InstanceType.audio
            elif type_code in ["g", "m"]:
                return InstanceType.audiovisual
            elif type_code in ["e", "f"]:
                return InstanceType.print  # Cartographic

        return InstanceType.print

    def _get_carrier_media_types(self, record: Record) -> tuple[CarrierType, MediaType]:
        carrier_type = CarrierType.volume
        media_type = MediaType.unmediated

        # Try RDA fields first
        field_337 = record.get("337")
        if field_337:
            code = field_337.get("b", "")
            media_type = self.RDA_MEDIA_CODES.get(code, MediaType.unmediated)

        field_338 = record.get("338")
        if field_338:
            code = field_338.get("b", "")
            carrier_type = self.RDA_CARRIER_CODES.get(code, CarrierType.volume)

        # If no RDA fields, derive from 007
        if not field_337 and not field_338:
            field_007 = record.get("007")
            if field_007 and hasattr(field_007, "data"):
                data = field_007.data
                if len(data) > 0:
                    cat = data[0]
                    if cat == "c":  # Electronic
                        carrier_type = CarrierType.online_resource
                        media_type = MediaType.computer
                    elif cat == "s":  # Sound
                        media_type = MediaType.audio
                        if len(data) > 1:
                            carrier_type = self.FIELD_007_CARRIER.get(data[1], CarrierType.audio_disc)
                    elif cat == "v":  # Video
                        carrier_type = CarrierType.videodisc
                        media_type = MediaType.video
                    elif cat == "h":  # Microform
                        carrier_type = CarrierType.microfilm_reel
                        media_type = MediaType.microform

        return carrier_type, media_type

    def _extract_title(self, record: Record) -> tuple[str, Optional[str], list[str]]:
        title = ""
        subtitle = None
        variants = []

        field_245 = record.get("245")
        if field_245:
            title = field_245.get("a", "").rstrip(" /:")
            subtitle = field_245.get("b", "").rstrip(" /:")
            if subtitle:
                subtitle = subtitle.strip()

        # Get variant titles from 246
        for field_246 in record.get_fields("246"):
            variant = field_246.get("a", "")
            if variant:
                variants.append(variant.strip())

        if not title:
            title = "Untitled"
            self.warnings.append("No title found in MARC 245")

        return title, subtitle if subtitle else None, variants

    def _extract_title_statement(self, record: Record) -> Optional[str]:
        field_245 = record.get("245")
        if field_245:
            parts = []
            for subfield in ["a", "b", "c"]:
                value = field_245.get(subfield, "")
                if value:
                    parts.append(value.strip())
            if parts:
                return " ".join(parts)
        return None

    def _extract_language(self, record: Record) -> str:
        # Try 008 positions 35-37
        field_008 = record.get("008")
        if field_008 and hasattr(field_008, "data") and len(field_008.data) >= 38:
            lang_code = field_008.data[35:38]
            if lang_code in self.LANGUAGE_CODE_MAP:
                return self.LANGUAGE_CODE_MAP[lang_code]
            if lang_code.isalpha():
                return lang_code

        # Try 041 $a
        field_041 = record.get("041")
        if field_041:
            lang_code = field_041.get("a", "")[:3]
            if lang_code:
                return lang_code

        return "und"  # Undetermined

    def _extract_dewey(self, record: Record) -> Optional[str]:
        field_082 = record.get("082")
        if field_082:
            return field_082.get("a", "").strip()
        return None

    def _extract_lc_classification(self, record: Record) -> Optional[str]:
        for tag in ["050", "090"]:
            field = record.get(tag)
            if field:
                class_num = field.get("a", "")
                item_num = field.get("b", "")
                if class_num:
                    return f"{class_num} {item_num}".strip()
        return None

    def _extract_summary(self, record: Record) -> Optional[str]:
        field_520 = record.get("520")
        if field_520:
            return field_520.get("a", "").strip()
        return None

    def _extract_toc(self, record: Record) -> Optional[str]:
        field_505 = record.get("505")
        if field_505:
            return field_505.get("a", "").strip()
        return None

    def _extract_genre_form(self, record: Record) -> list[str]:
        genres = []
        for field_655 in record.get_fields("655"):
            term = field_655.get("a", "").rstrip(".")
            if term:
                genres.append(term)
        return genres

    def _extract_series(self, record: Record) -> tuple[Optional[str], Optional[str]]:
        series_title = None
        series_number = None

        # Try 490 first
        field_490 = record.get("490")
        if field_490:
            series_title = field_490.get("a", "").rstrip(" ;,")
            series_number = field_490.get("v", "")

        # Try 800/810/830 for authority-controlled series
        if not series_title:
            for tag in ["800", "810", "830"]:
                field = record.get(tag)
                if field:
                    series_title = field.get("t", "").rstrip(" ;,")
                    series_number = field.get("v", "")
                    break

        return series_title if series_title else None, series_number if series_number else None

    def _extract_audience(self, record: Record) -> Optional[str]:
        field_521 = record.get("521")
        if field_521:
            return field_521.get("a", "").strip()
        return None

    def _extract_work_notes(self, record: Record) -> list[str]:
        notes = []
        # General note (500), bibliography (504), contents (505 already extracted)
        for tag in ["500", "504"]:
            for field in record.get_fields(tag):
                note = field.get("a", "").strip()
                if note:
                    notes.append(note)
        return notes

    def _extract_instance_notes(self, record: Record) -> list[str]:
        notes = []
        # Numbering (515), type of file (516), system details (538)
        for tag in ["515", "516", "538"]:
            for field in record.get_fields(tag):
                note = field.get("a", "").strip()
                if note:
                    notes.append(note)
        return notes

    def _extract_control_number(self, record: Record) -> Optional[str]:
        field_001 = record.get("001")
        if field_001 and hasattr(field_001, "data"):
            return field_001.data.strip()
        return None

    def _extract_isbns(self, record: Record) -> tuple[Optional[str], Optional[str]]:
        isbn_10 = None
        isbn_13 = None

        for field_020 in record.get_fields("020"):
            isbn = field_020.get("a", "")
            if isbn:
                # Use centralized normalization
                i10, i13 = IdentifierNormalizer.normalize_isbn(isbn)
                if i10 and not isbn_10:
                    isbn_10 = i10
                if i13 and not isbn_13:
                    isbn_13 = i13

        return isbn_10, isbn_13

    def _extract_lccn(self, record: Record) -> Optional[str]:
        field_010 = record.get("010")
        if field_010:
            lccn = field_010.get("a", "").strip()
            if lccn:
                return IdentifierNormalizer.normalize_lccn(lccn)
        return None

    def _extract_oclc(self, record: Record) -> Optional[str]:
        # Check 035 for OCoLC prefix
        for field_035 in record.get_fields("035"):
            system_num = field_035.get("a", "")
            if "(OCoLC)" in system_num:
                return re.sub(r"\D", "", system_num)

        # Check 001 if library uses OCLC control numbers
        field_001 = record.get("001")
        if field_001 and hasattr(field_001, "data"):
            data = field_001.data.strip()
            if data.startswith("ocm") or data.startswith("ocn") or data.startswith("on"):
                return re.sub(r"\D", "", data)

        return None

    def _extract_issn(self, record: Record) -> Optional[str]:
        field_022 = record.get("022")
        if field_022:
            issn = field_022.get("a", "")
            if issn:
                normalized = IdentifierNormalizer.normalize_issn(issn)
                return normalized if normalized else None
        return None

    def _extract_publication_info(
        self, record: Record
    ) -> tuple[Optional[str], Optional[str], Optional[str], Optional[int], Optional[str]]:
        publisher = None
        place = None
        pub_date = None
        pub_year = None
        copyright_date = None

        # Try 264 first (RDA)
        for field_264 in record.get_fields("264"):
            ind2 = field_264.indicator2
            if ind2 == "1":  # Publication
                place = place or field_264.get("a", "").rstrip(" :,")
                publisher = publisher or field_264.get("b", "").rstrip(" ,")
                pub_date = pub_date or field_264.get("c", "").rstrip(".")
            elif ind2 == "4":  # Copyright
                copyright_date = field_264.get("c", "").rstrip(".")

        # Fall back to 260
        if not publisher:
            field_260 = record.get("260")
            if field_260:
                place = place or field_260.get("a", "").rstrip(" :,")
                publisher = publisher or field_260.get("b", "").rstrip(" ,")
                pub_date = pub_date or field_260.get("c", "").rstrip(".")
                copyright = field_260.get("c", "")
                if "c" in copyright.lower() or "©" in copyright:
                    copyright_date = copyright.rstrip(".")

        # Extract year from date
        if pub_date:
            year_match = re.search(r"(\d{4})", pub_date)
            if year_match:
                pub_year = int(year_match.group(1))

        return publisher, place, pub_date, pub_year, copyright_date

    def _extract_edition(self, record: Record) -> Optional[str]:
        field_250 = record.get("250")
        if field_250:
            return field_250.get("a", "").strip()
        return None

    def _extract_physical_description(
        self, record: Record
    ) -> tuple[Optional[str], Optional[str], Optional[int]]:
        extent = None
        dimensions = None
        page_count = None

        field_300 = record.get("300")
        if field_300:
            extent = field_300.get("a", "").rstrip(" ;:")
            dimensions = field_300.get("c", "").rstrip(" ;")

            # Try to extract page count
            if extent:
                page_match = re.search(r"(\d+)\s*(?:p\.|pages)", extent, re.I)
                if page_match:
                    page_count = int(page_match.group(1))

        return extent, dimensions, page_count

    # =========================================================================
    # Private Methods - Contributors
    # =========================================================================

    def _extract_contributors(
        self, record: Record
    ) -> tuple[list[BibframeContributor], list[AuthorityLink]]:
        contributors = []
        authority_links = []

        # Main entry (100, 110, 111)
        for tag in ["100", "110", "111"]:
            field = record.get(tag)
            if field:
                contributor, links = self._parse_contributor_field(field, is_primary=True)
                if contributor:
                    contributors.append(contributor)
                    authority_links.extend(links)

        # Added entries (700, 710, 711)
        for tag in ["700", "710", "711"]:
            for field in record.get_fields(tag):
                contributor, links = self._parse_contributor_field(field, is_primary=False)
                if contributor:
                    contributors.append(contributor)
                    authority_links.extend(links)

        return contributors, authority_links

    def _parse_contributor_field(
        self, field: Field, is_primary: bool = False
    ) -> tuple[Optional[BibframeContributor], list[AuthorityLink]]:
        authority_links = []

        # Determine contributor type from tag
        tag = field.tag
        if tag in ["100", "700"]:
            contributor_type = "person"
        elif tag in ["110", "710"]:
            contributor_type = "organization"
        elif tag in ["111", "711"]:
            contributor_type = "meeting"
        else:
            contributor_type = "person"

        # Extract name
        name = field.get("a", "").rstrip(",.")
        if not name:
            return None, []

        # For persons, try to parse name parts
        given_name = None
        family_name = None
        birth_date = None
        death_date = None

        if contributor_type == "person":
            # Name in $a is usually "Family, Given"
            if "," in name:
                parts = name.split(",", 1)
                family_name = parts[0].strip()
                given_name = parts[1].strip() if len(parts) > 1 else None

            # Dates from $d
            dates = field.get("d", "")
            date_match = re.search(r"(\d{4})-?(\d{4})?", dates)
            if date_match:
                birth_date = date_match.group(1)
                death_date = date_match.group(2)

        # Extract role from $e or $4
        role = ContributorRole.author if is_primary else ContributorRole.contributor
        relator = field.get("e", "") or field.get("4", "")
        if relator:
            relator_code = relator[:3].lower()
            role = self.RELATOR_CODES.get(relator_code, role)

        # Authority control number from $0
        authority_num = field.get("0", "")

        contributor = BibframeContributor(
            name=name,
            contributor_type=contributor_type,
            name_inverted=name if "," in name else self._invert_name(name),
            name_sort=self._generate_sort_name(name),
            given_name=given_name,
            family_name=family_name,
            birth_date=birth_date,
            death_date=death_date,
        )

        # Create authority link if we have an authority number
        if authority_num:
            link = self._parse_authority_number(authority_num)
            if link:
                authority_links.append(link)

        return contributor, authority_links

    # =========================================================================
    # Private Methods - Subjects
    # =========================================================================

    def _extract_subjects(
        self, record: Record
    ) -> tuple[list[BibframeSubject], list[AuthorityLink]]:
        subjects = []
        authority_links = []

        # Subject headings
        subject_tags = {
            "600": "person",
            "610": "organization",
            "611": "meeting",
            "630": "topic",  # Uniform title
            "648": "temporal",
            "650": "topic",
            "651": "place",
            "653": "topic",  # Uncontrolled
            "655": "topic",  # Genre/form (also topic)
        }

        for tag, subject_type in subject_tags.items():
            for field in record.get_fields(tag):
                subject, links = self._parse_subject_field(field, subject_type)
                if subject:
                    subjects.append(subject)
                    authority_links.extend(links)

        return subjects, authority_links

    def _parse_subject_field(
        self, field: Field, subject_type: str
    ) -> tuple[Optional[BibframeSubject], list[AuthorityLink]]:
        authority_links = []

        # Build subject heading from subfields
        label_parts = []
        for code in ["a", "b", "c", "d", "v", "x", "y", "z"]:
            value = field.get(code, "")
            if value:
                label_parts.append(value.rstrip(".,"))

        if not label_parts:
            return None, []

        label = " -- ".join(label_parts)

        # Determine authority source from indicator 2
        source = None
        source_id = None
        lcsh_id = None
        fast_id = None

        ind2 = field.indicator2
        if ind2 == "0":
            source = AuthoritySource.LCSH
        elif ind2 == "7":
            source_term = field.get("2", "")
            if source_term == "fast":
                source = AuthoritySource.FAST
            elif source_term == "lcsh":
                source = AuthoritySource.LCSH

        # Authority number from $0
        authority_num = field.get("0", "")
        if authority_num:
            if "id.loc.gov/authorities/subjects/" in authority_num:
                lcsh_id = authority_num.split("/")[-1]
            elif "id.worldcat.org/fast/" in authority_num:
                fast_id = authority_num.split("/")[-1]
            else:
                link = self._parse_authority_number(authority_num)
                if link:
                    authority_links.append(link)

        subject = BibframeSubject(
            label=label,
            label_normalized=label.lower(),
            subject_type=subject_type,
            source=source,
            source_id=source_id,
            lcsh_id=lcsh_id,
            fast_id=fast_id,
        )

        return subject, authority_links

    # =========================================================================
    # Private Methods - Identifiers and Authority Links
    # =========================================================================

    def _extract_identifier_links(
        self, record: Record, instance: BibframeInstance
    ) -> list[AuthorityLink]:
        links = []

        # ISBN
        if instance.isbn_13:
            links.append(AuthorityLink(
                source=AuthoritySource.ISBN,
                authority_id=instance.isbn_13,
                authority_uri=f"urn:isbn:{instance.isbn_13}",
                link_type="identifier",
            ))

        # LCCN
        if instance.lccn:
            links.append(AuthorityLink(
                source=AuthoritySource.LCCN,
                authority_id=instance.lccn,
                authority_uri=f"https://lccn.loc.gov/{instance.lccn}",
                link_type="identifier",
            ))

        # OCLC
        if instance.oclc_number:
            links.append(AuthorityLink(
                source=AuthoritySource.OCLC,
                authority_id=instance.oclc_number,
                authority_uri=f"https://www.worldcat.org/oclc/{instance.oclc_number}",
                link_type="identifier",
            ))

        return links

    def _parse_authority_number(self, authority_num: str) -> Optional[AuthorityLink]:
        # Common patterns:
        # (DLC)n12345678 - LC authority
        # http://id.loc.gov/authorities/names/n12345678
        # (viaf)12345678
        # https://viaf.org/viaf/12345678

        if "id.loc.gov/authorities/names/" in authority_num:
            authority_id = authority_num.split("/")[-1]
            return AuthorityLink(
                source=AuthoritySource.LCNAF,
                authority_id=authority_id,
                authority_uri=authority_num if authority_num.startswith("http") else f"https://id.loc.gov/authorities/names/{authority_id}",
                link_type="sameAs",
            )

        if "viaf.org/viaf/" in authority_num:
            authority_id = authority_num.split("/")[-1]
            return AuthorityLink(
                source=AuthoritySource.VIAF,
                authority_id=authority_id,
                authority_uri=authority_num if authority_num.startswith("http") else f"https://viaf.org/viaf/{authority_id}",
                link_type="sameAs",
            )

        if authority_num.startswith("(DLC)"):
            authority_id = authority_num[5:].strip()
            return AuthorityLink(
                source=AuthoritySource.LCNAF,
                authority_id=authority_id,
                authority_uri=f"https://id.loc.gov/authorities/names/{authority_id}",
                link_type="sameAs",
            )

        return None

    # =========================================================================
    # Private Methods - Utilities
    # =========================================================================

    def _generate_sort_title(self, title: str) -> str:
        return normalize_title_for_sorting(title)

    def _generate_sort_name(self, name: str) -> str:
        # If already inverted, just return lowercase
        if "," in name:
            return name.lower()
        # Otherwise, try to invert
        return self._invert_name(name).lower()

    def _invert_name(self, name: str) -> str:
        if "," in name:
            return name  # Already inverted
        parts = name.rsplit(" ", 1)
        if len(parts) == 2:
            return f"{parts[1]}, {parts[0]}"
        return name

    def _isbn10_to_isbn13(self, isbn10: str) -> str:
        _, isbn_13 = IdentifierNormalizer.normalize_isbn(isbn10)
        return isbn_13 if isbn_13 else isbn10

    def _normalize_isbn(self, isbn: str) -> Optional[str]:
        if not isbn:
            return None
        _, isbn_13 = IdentifierNormalizer.normalize_isbn(isbn)
        return isbn_13

    def _catalog_item_type_to_work_type(self, item_type) -> WorkType:
        from ..models.catalog import ItemType as CatalogItemType
        mapping = {
            CatalogItemType.book: WorkType.text,
            CatalogItemType.ebook: WorkType.text,
            CatalogItemType.audiobook: WorkType.spoken_word,
            CatalogItemType.dvd: WorkType.two_dimensional_moving_image,
            CatalogItemType.cd: WorkType.performed_music,
            CatalogItemType.magazine: WorkType.text,
            CatalogItemType.game: WorkType.other,
            CatalogItemType.other: WorkType.other,
        }
        return mapping.get(item_type, WorkType.other)

    def _catalog_item_type_to_instance_type(self, item_type) -> InstanceType:
        from ..models.catalog import ItemType as CatalogItemType
        mapping = {
            CatalogItemType.book: InstanceType.print,
            CatalogItemType.ebook: InstanceType.electronic,
            CatalogItemType.audiobook: InstanceType.audio,
            CatalogItemType.dvd: InstanceType.audiovisual,
            CatalogItemType.cd: InstanceType.audio,
            CatalogItemType.magazine: InstanceType.print,
            CatalogItemType.game: InstanceType.print,
            CatalogItemType.other: InstanceType.print,
        }
        return mapping.get(item_type, InstanceType.print)

    def _catalog_item_type_to_carrier(self, item_type) -> CarrierType:
        from ..models.catalog import ItemType as CatalogItemType
        mapping = {
            CatalogItemType.book: CarrierType.volume,
            CatalogItemType.ebook: CarrierType.online_resource,
            CatalogItemType.audiobook: CarrierType.online_resource,
            CatalogItemType.dvd: CarrierType.videodisc,
            CatalogItemType.cd: CarrierType.audio_disc,
            CatalogItemType.magazine: CarrierType.volume,
            CatalogItemType.game: CarrierType.object,
            CatalogItemType.other: CarrierType.other,
        }
        return mapping.get(item_type, CarrierType.other)

    def _catalog_item_type_to_media(self, item_type) -> MediaType:
        from ..models.catalog import ItemType as CatalogItemType
        mapping = {
            CatalogItemType.book: MediaType.unmediated,
            CatalogItemType.ebook: MediaType.computer,
            CatalogItemType.audiobook: MediaType.computer,
            CatalogItemType.dvd: MediaType.video,
            CatalogItemType.cd: MediaType.audio,
            CatalogItemType.magazine: MediaType.unmediated,
            CatalogItemType.game: MediaType.unmediated,
            CatalogItemType.other: MediaType.unmediated,
        }
        return mapping.get(item_type, MediaType.unmediated)


# Singleton instance
marc_to_bibframe_service = MarcToBibframeService()
