# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from io import BytesIO

logger = get_logger(__name__)


def tag_pdf(pdf_bytes: bytes, title: str, lang: str = "en") -> bytes:
    try:
        import pikepdf

        pdf = pikepdf.open(BytesIO(pdf_bytes))

        # Mark as tagged
        pdf.Root.MarkInfo = pikepdf.Dictionary({"/Marked": True})

        # Set language
        pdf.Root.Lang = pikepdf.String(lang)

        # Set document title
        with pdf.open_metadata() as meta:
            meta["dc:title"] = title

        # Create minimal structure tree
        struct_elem = pdf.make_indirect(pikepdf.Dictionary({
            "/Type": pikepdf.Name("/StructElem"),
            "/S": pikepdf.Name("/Document"),
        }))
        struct_tree = pdf.make_indirect(pikepdf.Dictionary({
            "/Type": pikepdf.Name("/StructTreeRoot"),
            "/K": struct_elem,
            "/ParentTree": pikepdf.Dictionary(),
        }))
        struct_elem["/P"] = struct_tree
        pdf.Root.StructTreeRoot = struct_tree

        output = BytesIO()
        pdf.save(output)
        return output.getvalue()

    except Exception:  # noqa: BLE001 -- PDF tagging fallback: any failure returns untagged PDF, never crash route
        logger.warning(f"Failed to tag PDF '{title}', returning untagged", exc_info=True)
        return pdf_bytes
