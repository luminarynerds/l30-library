# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import os
from datetime import datetime, timezone
from io import BytesIO


class _UnclosableBytesIO(BytesIO):

    def close(self) -> None:  # type: ignore[override]
        return None
from typing import Optional
import xml.etree.ElementTree as ET

from pymarc import Record, Field, Subfield, XMLWriter, MARCWriter
from sqlalchemy import inspect as sa_inspect

from ..core.branding import branding
from ..core.config import get_settings

settings = get_settings()
from ..models.catalog import CatalogItem, ItemType, ContentRating


def _relationship_is_loaded(obj, attr_name: str) -> bool:
    return attr_name not in sa_inspect(obj).unloaded

_LIBRARY_CODE = os.environ.get("LIBRARY_CODE", "L30")
_LIBRARY_NAME = os.environ.get("LIBRARY_NAME", "My Library")


# MARC21 field definitions
# https://www.loc.gov/marc/bibliographic/

ITEM_TYPE_TO_MATERIAL_TYPE = {
    ItemType.book: "a",  # Language material
    ItemType.audiobook: "i",  # Nonmusical sound recording
    ItemType.ebook: "a",  # Language material (computer file)
    ItemType.dvd: "g",  # Projected medium
    ItemType.bluray: "g",  # Projected medium
    ItemType.cd: "j",  # Musical sound recording
    ItemType.vinyl: "j",  # Musical sound recording
    ItemType.magazine: "a",  # Language material (serial)
    ItemType.game: "r",  # Three-dimensional artifact
    ItemType.equipment: "r",  # Three-dimensional artifact
    ItemType.kit: "o",  # Kit
    ItemType.other: "o",  # Kit
}

ITEM_TYPE_TO_BIB_LEVEL = {
    ItemType.book: "m",  # Monograph
    ItemType.audiobook: "m",
    ItemType.ebook: "m",
    ItemType.dvd: "m",
    ItemType.bluray: "m",
    ItemType.cd: "m",
    ItemType.vinyl: "m",
    ItemType.magazine: "s",  # Serial
    ItemType.game: "m",
    ItemType.equipment: "m",
    ItemType.kit: "c",  # Collection
    ItemType.other: "m",
}

# Content rating display strings
CONTENT_RATING_DISPLAY = {
    ContentRating.g: "MPAA rating: G",
    ContentRating.pg: "MPAA rating: PG",
    ContentRating.pg13: "MPAA rating: PG-13",
    ContentRating.r: "MPAA rating: R",
    ContentRating.nc17: "MPAA rating: NC-17",
    ContentRating.e: "ESRB rating: E (Everyone)",
    ContentRating.e10: "ESRB rating: E10+ (Everyone 10+)",
    ContentRating.t: "ESRB rating: T (Teen)",
    ContentRating.m: "ESRB rating: M (Mature)",
    ContentRating.ao: "ESRB rating: AO (Adults Only)",
    ContentRating.explicit: "Parental advisory: Explicit content",
    ContentRating.clean: "Clean version",
    ContentRating.unrated: "Unrated",
    ContentRating.not_rated: "Not rated",
}

LANGUAGE_CODES = {
    "en": "eng",
    "es": "spa",
    "fr": "fre",
    "de": "ger",
    "it": "ita",
    "pt": "por",
    "ru": "rus",
    "zh": "chi",
    "ja": "jpn",
    "ko": "kor",
}


class CatalogMARCService:

    # Library identifiers (customize for your library)
    LIBRARY_CODE = _LIBRARY_CODE
    LIBRARY_NAME = _LIBRARY_NAME
    CATALOGING_SOURCE = f"{_LIBRARY_CODE}cat"  # Cataloging source code

    def generate_leader(self, item: CatalogItem) -> str:
        material_type = ITEM_TYPE_TO_MATERIAL_TYPE.get(item.item_type, "a")
        bib_level = ITEM_TYPE_TO_BIB_LEVEL.get(item.item_type, "m")
        return f"00000n{material_type}{bib_level} a2200000 a 4500"

    def generate_008(self, item: CatalogItem) -> str:
        now = datetime.now(timezone.utc)
        date_entered = now.strftime("%y%m%d")

        pub_year = str(item.publication_year or now.year)
        if len(pub_year) != 4:
            pub_year = str(now.year)

        # Default to English
        lang = "eng"

        # Material-specific positions (18-34) vary by format
        # For books, this includes illustrations, target audience, form, etc.
        if item.item_type == ItemType.book:
            material_data = "    " + " " + " " + "    " + " " + "0" + "0" + "0" + " " + "0" + " " + "eng"
        elif item.item_type == ItemType.ebook:
            material_data = "    " + " " + "o" + "    " + " " + "0" + "0" + "0" + " " + "0" + " " + "eng"
        else:
            material_data = "                 "

        # Build the 008 field
        field_008 = (
            f"{date_entered}"  # 00-05: Date entered
            f"s"  # 06: Single date
            f"{pub_year}"  # 07-10: Date 1
            f"    "  # 11-14: Date 2 (blank)
            f"xxu"  # 15-17: United States
            f"{material_data[:17]}"  # 18-34: Material data
            f"{lang}"  # 35-37: Language
            f" "  # 38: Modified record
            f"d"  # 39: Cataloging source
        )

        return field_008[:40].ljust(40)

    def create_marc_record(self, item: CatalogItem) -> Record:
        record = Record()

        # Set leader
        record.leader = self.generate_leader(item)

        # 001 - Control Number
        record.add_field(Field(tag="001", data=f"{branding.MARC_PREFIX}-CAT-{item.id:08d}"))

        # 005 - Date and Time of Latest Transaction
        record.add_field(
            Field(tag="005", data=datetime.now().strftime("%Y%m%d%H%M%S.0"))
        )

        # 008 - Fixed-Length Data Elements
        record.add_field(Field(tag="008", data=self.generate_008(item)))

        # 020 - ISBN (if provided)
        if item.isbn:
            record.add_field(
                Field(
                    tag="020",
                    indicators=[" ", " "],
                    subfields=[Subfield(code="a", value=item.isbn)],
                )
            )

        # 040 - Cataloging Source
        record.add_field(
            Field(
                tag="040",
                indicators=[" ", " "],
                subfields=[
                    Subfield(code="a", value=self.CATALOGING_SOURCE),
                    Subfield(code="b", value="eng"),
                    Subfield(code="e", value="rda"),
                    Subfield(code="c", value=self.CATALOGING_SOURCE),
                ],
            )
        )

        # 050 - Library of Congress Call Number (if staff-provided)
        if item.lc_classification:
            record.add_field(
                Field(
                    tag="050",
                    indicators=["1", "4"],  # LC assignment, non-LC agency
                    subfields=[Subfield(code="a", value=item.lc_classification)],
                )
            )

        # 082 - Dewey Decimal Classification (if staff-provided)
        if item.dewey_decimal:
            record.add_field(
                Field(
                    tag="082",
                    indicators=["0", "4"],  # Full edition, non-LC agency
                    subfields=[Subfield(code="a", value=item.dewey_decimal)],
                )
            )

        # 100 - Main Entry - Personal Name
        # For music: use artist; for films: use director; otherwise: use author
        main_entry_name = None
        if item.item_type in (ItemType.cd, ItemType.vinyl) and item.artist:
            main_entry_name = item.artist
        elif item.item_type in (ItemType.dvd, ItemType.bluray) and item.director:
            main_entry_name = item.director
        elif item.author:
            main_entry_name = item.author

        if main_entry_name:
            # Try to format as "Last, First" if possible
            name_formatted = main_entry_name
            if "," not in name_formatted and " " in name_formatted and "," not in name_formatted:
                # Simple heuristic: "First Last" -> "Last, First"
                # Skip if multiple names (contains "and" or ",")
                if " and " not in name_formatted.lower():
                    parts = name_formatted.rsplit(" ", 1)
                    if len(parts) == 2:
                        name_formatted = f"{parts[1]}, {parts[0]}"

            record.add_field(
                Field(
                    tag="100",
                    indicators=["1", " "],  # Surname entry
                    subfields=[
                        Subfield(code="a", value=f"{name_formatted}."),
                    ],
                )
            )

        # 245 - Title Statement
        # Subfield order per MARC: $a, $n (number of part), $p (name of part), $c.
        title_subfields = [Subfield(code="a", value=f"{item.title}")]
        if item.volume_number:
            title_subfields.append(Subfield(code="n", value=item.volume_number))
        if item.volume_label:
            title_subfields.append(Subfield(code="p", value=item.volume_label))
        if item.author:
            title_subfields.append(Subfield(code="c", value=f"{item.author}."))

        # Calculate non-filing characters (for articles like "The", "A", "An")
        nonfiling = 0
        title_lower = item.title.lower()
        if title_lower.startswith("the "):
            nonfiling = 4
        elif title_lower.startswith("an "):
            nonfiling = 3
        elif title_lower.startswith("a "):
            nonfiling = 2

        indicator1 = "0" if not item.author else "1"  # No added entry if no author
        record.add_field(
            Field(tag="245", indicators=[indicator1, str(nonfiling)], subfields=title_subfields)
        )

        # 250 - Edition Statement
        if item.edition:
            record.add_field(
                Field(
                    tag="250",
                    indicators=[" ", " "],
                    subfields=[Subfield(code="a", value=item.edition)],
                )
            )

        # 260/264 - Publication Information
        if item.publisher or item.publication_year:
            pub_subfields = []
            if item.publisher:
                pub_subfields.append(Subfield(code="b", value=f"{item.publisher},"))
            if item.publication_year:
                pub_subfields.append(Subfield(code="c", value=str(item.publication_year)))

            if pub_subfields:
                record.add_field(
                    Field(tag="264", indicators=[" ", "1"], subfields=pub_subfields)
                )

        # 490 - Series Statement (+ 830 traced added entry for structured sets)
        # If this item belongs to a MultiPartSet, prefer the set title and emit
        # an 830 added entry so siblings can be discovered as a coherent set.
        # Fall back to the free-form series_name on the item.
        set_title = None
        if (
            _relationship_is_loaded(item, "multipart_set")
            and item.multipart_set is not None
        ):
            set_title = item.multipart_set.title

        if set_title:
            designation = item.volume_number or (
                str(item.sequence_in_set) if item.sequence_in_set else None
            )
            series_subfields = [Subfield(code="a", value=set_title)]
            if designation:
                series_subfields.append(Subfield(code="v", value=designation))
            # Indicator1=1: series traced (a corresponding 830 follows).
            record.add_field(
                Field(tag="490", indicators=["1", " "], subfields=series_subfields)
            )
            added_subfields = [Subfield(code="a", value=set_title)]
            if designation:
                added_subfields.append(Subfield(code="v", value=designation))
            record.add_field(
                Field(tag="830", indicators=[" ", "0"], subfields=added_subfields)
            )
        elif item.series_name:
            series_subfields = [Subfield(code="a", value=item.series_name)]
            if item.series_number:
                series_subfields.append(Subfield(code="v", value=item.series_number))

            record.add_field(
                Field(tag="490", indicators=["1", " "], subfields=series_subfields)
            )

        # 300 - Physical Description
        extent_parts = []
        if item.page_count:
            extent_parts.append(f"{item.page_count} pages")
        elif item.item_type == ItemType.dvd:
            disc_text = f"{item.disc_count} videodisc" if item.disc_count else "1 videodisc"
            if item.disc_count and item.disc_count > 1:
                disc_text += "s"
            extent_parts.append(disc_text)
        elif item.item_type == ItemType.bluray:
            disc_text = f"{item.disc_count} Blu-ray disc" if item.disc_count else "1 Blu-ray disc"
            if item.disc_count and item.disc_count > 1:
                disc_text += "s"
            extent_parts.append(disc_text)
        elif item.item_type == ItemType.cd:
            disc_text = f"{item.disc_count} audio disc" if item.disc_count else "1 audio disc"
            if item.disc_count and item.disc_count > 1:
                disc_text += "s"
            extent_parts.append(disc_text)
        elif item.item_type == ItemType.vinyl:
            disc_text = f"{item.disc_count} vinyl record" if item.disc_count else "1 vinyl record"
            if item.disc_count and item.disc_count > 1:
                disc_text += "s"
            extent_parts.append(disc_text)
        elif item.item_type == ItemType.audiobook:
            extent_parts.append("audio file")
        elif item.item_type == ItemType.ebook:
            extent_parts.append("1 online resource")
        elif item.item_type == ItemType.kit:
            extent_parts.append("1 kit")
        elif item.item_type == ItemType.equipment:
            extent_parts.append("1 item")
        else:
            extent_parts.append("1 item")

        # Add dimensions if available (for equipment/kits)
        physical_subfields = [Subfield(code="a", value=" ".join(extent_parts))]
        if item.dimensions and item.item_type in (ItemType.equipment, ItemType.kit):
            physical_subfields.append(Subfield(code="c", value=item.dimensions))

        record.add_field(
            Field(
                tag="300",
                indicators=[" ", " "],
                subfields=physical_subfields,
            )
        )

        # 306 - Playing Time (for audio/video items)
        if item.runtime_minutes and item.item_type in (ItemType.dvd, ItemType.bluray, ItemType.cd, ItemType.vinyl, ItemType.audiobook):
            # Convert minutes to HHMMSS format
            hours = item.runtime_minutes // 60
            minutes = item.runtime_minutes % 60
            time_str = f"{hours:02d}{minutes:02d}00"
            record.add_field(
                Field(
                    tag="306",
                    indicators=[" ", " "],
                    subfields=[Subfield(code="a", value=time_str)],
                )
            )

        # 336/337/338 - Content/Media/Carrier Type (RDA) for ebooks
        if item.item_type == ItemType.ebook:
            record.add_field(
                Field(
                    tag="336",
                    indicators=[" ", " "],
                    subfields=[
                        Subfield(code="a", value="text"),
                        Subfield(code="b", value="txt"),
                        Subfield(code="2", value="rdacontent"),
                    ],
                )
            )
            record.add_field(
                Field(
                    tag="337",
                    indicators=[" ", " "],
                    subfields=[
                        Subfield(code="a", value="computer"),
                        Subfield(code="b", value="c"),
                        Subfield(code="2", value="rdamedia"),
                    ],
                )
            )
            record.add_field(
                Field(
                    tag="338",
                    indicators=[" ", " "],
                    subfields=[
                        Subfield(code="a", value="online resource"),
                        Subfield(code="b", value="cr"),
                        Subfield(code="2", value="rdacarrier"),
                    ],
                )
            )

        # 500 - General Notes (for equipment: brand, model, material)
        if item.item_type in (ItemType.equipment, ItemType.kit):
            note_parts = []
            if item.brand:
                note_parts.append(f"Brand: {item.brand}")
            if item.model_number:
                note_parts.append(f"Model: {item.model_number}")
            if item.material:
                note_parts.append(f"Material: {item.material}")
            if note_parts:
                record.add_field(
                    Field(
                        tag="500",
                        indicators=[" ", " "],
                        subfields=[Subfield(code="a", value="; ".join(note_parts))],
                    )
                )

        # 505 - Contents Note (for kits)
        if item.kit_contents and item.item_type == ItemType.kit:
            record.add_field(
                Field(
                    tag="505",
                    indicators=["0", " "],  # Complete contents
                    subfields=[Subfield(code="a", value=item.kit_contents)],
                )
            )

        # 508 - Creation/Production Credits Note (for films)
        if item.item_type in (ItemType.dvd, ItemType.bluray):
            credits_parts = []
            if item.director:
                credits_parts.append(f"Director: {item.director}")
            if item.studio:
                credits_parts.append(f"Studio: {item.studio}")
            if credits_parts:
                record.add_field(
                    Field(
                        tag="508",
                        indicators=[" ", " "],
                        subfields=[Subfield(code="a", value="; ".join(credits_parts))],
                    )
                )

        # 511 - Participant or Performer Note (for films: actors; for music: performer)
        if item.actors and item.item_type in (ItemType.dvd, ItemType.bluray):
            record.add_field(
                Field(
                    tag="511",
                    indicators=["1", " "],  # Cast
                    subfields=[Subfield(code="a", value=f"Cast: {item.actors}")],
                )
            )

        # 520 - Summary/Description
        if item.description:
            summary = item.description[:1500]  # Truncate long descriptions
            record.add_field(
                Field(
                    tag="520",
                    indicators=[" ", " "],
                    subfields=[Subfield(code="a", value=summary)],
                )
            )

        # 521 - Target Audience Note (content rating)
        if item.content_rating:
            rating_text = CONTENT_RATING_DISPLAY.get(item.content_rating, str(item.content_rating))
            record.add_field(
                Field(
                    tag="521",
                    indicators=["8", " "],  # No display constant
                    subfields=[Subfield(code="a", value=rating_text)],
                )
            )

        # 538 - System Details Note (for games: platform)
        if item.platform and item.item_type == ItemType.game:
            system_note = f"Platform: {item.platform}"
            if item.player_count:
                system_note += f"; {item.player_count}"
            record.add_field(
                Field(
                    tag="538",
                    indicators=[" ", " "],
                    subfields=[Subfield(code="a", value=system_note)],
                )
            )

        # 650 - Subject Headings
        if item.subjects:
            # Split subjects by comma or semicolon
            import re

            subjects = re.split(r"[,;]", item.subjects)
            for subject in subjects[:10]:  # Limit to 10 subjects
                subject = subject.strip()
                if subject:
                    record.add_field(
                        Field(
                            tag="650",
                            indicators=[" ", "0"],  # LCSH
                            subfields=[Subfield(code="a", value=f"{subject}.")],
                        )
                    )

        # 710 - Corporate Name (Library)
        record.add_field(
            Field(
                tag="710",
                indicators=["2", " "],
                subfields=[
                    Subfield(code="a", value=self.LIBRARY_NAME),
                ],
            )
        )

        # 852 - Location (holdings)
        if item.location or item.call_number:
            loc_subfields = []
            if item.location:
                loc_subfields.append(Subfield(code="b", value=item.location))
            if item.call_number:
                loc_subfields.append(Subfield(code="h", value=item.call_number))

            if loc_subfields:
                record.add_field(
                    Field(tag="852", indicators=[" ", " "], subfields=loc_subfields)
                )

        # 856 - Electronic Location (for ebooks)
        if item.item_type == ItemType.ebook:
            record.add_field(
                Field(
                    tag="856",
                    indicators=["4", "0"],  # HTTP, resource
                    subfields=[
                        Subfield(
                            code="u",
                            value=f"{settings.schema_org_base_url}/catalog/{item.id}",
                        ),
                        Subfield(code="y", value="Access online"),
                        Subfield(code="z", value="Library card required"),
                    ],
                )
            )

        return record

    def export_marc21(self, record: Record) -> bytes:
        output = _UnclosableBytesIO()
        writer = MARCWriter(output)
        writer.write(record)
        writer.close()
        return output.getvalue()

    def export_marc21_batch(self, records: list[Record]) -> bytes:
        output = _UnclosableBytesIO()
        writer = MARCWriter(output)
        for record in records:
            writer.write(record)
        writer.close()
        return output.getvalue()

    def export_marcxml(self, record: Record) -> str:
        output = _UnclosableBytesIO()
        writer = XMLWriter(output)
        writer.write(record)
        writer.close()
        return output.getvalue().decode("utf-8")

    def export_marcxml_batch(self, records: list[Record]) -> str:
        output = _UnclosableBytesIO()
        writer = XMLWriter(output)
        for record in records:
            writer.write(record)
        writer.close()
        return output.getvalue().decode("utf-8")

    def export_dublin_core(self, item: CatalogItem) -> str:
        dc = ET.Element("oai_dc:dc")
        dc.set("xmlns:oai_dc", "http://www.openarchives.org/OAI/2.0/oai_dc/")
        dc.set("xmlns:dc", "http://purl.org/dc/elements/1.1/")

        # dc:title
        ET.SubElement(dc, "dc:title").text = item.title

        # dc:creator (author for books, director for films, artist for music, brand for equipment)
        creator = None
        if item.item_type in (ItemType.cd, ItemType.vinyl) and item.artist:
            creator = item.artist
        elif item.item_type in (ItemType.dvd, ItemType.bluray) and item.director:
            creator = item.director
        elif item.item_type in (ItemType.equipment, ItemType.kit) and item.brand:
            creator = item.brand
        elif item.author:
            creator = item.author

        if creator:
            ET.SubElement(dc, "dc:creator").text = creator

        # dc:subject
        if item.subjects:
            import re

            subjects = re.split(r"[,;]", item.subjects)
            for subj in subjects:
                subj = subj.strip()
                if subj:
                    ET.SubElement(dc, "dc:subject").text = subj

        # dc:description
        if item.description:
            ET.SubElement(dc, "dc:description").text = item.description[:500]

        # dc:publisher
        if item.publisher:
            ET.SubElement(dc, "dc:publisher").text = item.publisher

        # dc:date
        if item.publication_year:
            ET.SubElement(dc, "dc:date").text = str(item.publication_year)

        # dc:type
        ET.SubElement(dc, "dc:type").text = str(item.item_type).capitalize()

        # dc:identifier
        if item.isbn:
            ET.SubElement(dc, "dc:identifier").text = f"ISBN:{item.isbn}"
        ET.SubElement(dc, "dc:identifier").text = f"{branding.MARC_PREFIX}-CAT:{item.id}"

        # dc:language
        ET.SubElement(dc, "dc:language").text = "eng"

        # dc:rights
        ET.SubElement(
            dc, "dc:rights"
        ).text = f"Available through {_LIBRARY_NAME}"

        return ET.tostring(dc, encoding="unicode", xml_declaration=True)


# Singleton instance
catalog_marc_service = CatalogMARCService()
