
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject, BooleanObject, DictionaryObject, NameObject,
    NumberObject, TextStringObject, IndirectObject,
)


# Map ReportLab paragraph style names to PDF structure tags
_STYLE_TAG_MAP = {
    "title": "/H1",
    "heading": "/H1",
    "subheading": "/H2",
    "section_heading": "/H2",
    "subsection": "/H3",
    "body": "/P",
    "body_bold": "/P",
    "body_small": "/P",
    "body_right": "/P",
    "info_label": "/Span",
    "info_value": "/Span",
    "footer": "/P",
    "notice_title": "/H1",
    "notice_body": "/P",
    "notice_detail": "/P",
    "toc_entry": "/P",
}


class AccessibleDocTemplate(SimpleDocTemplate):

    def __init__(self, *args, title="", author="", subject="", **kwargs):
        super().__init__(*args, **kwargs)
        self._a11y_title = title
        self._a11y_author = author
        self._a11y_subject = subject
        self._struct_elements = []
        self._current_page = 0

    def afterFlowable(self, flowable):
        tag = "/P"
        if isinstance(flowable, Paragraph):
            style_name = getattr(flowable.style, "name", "")
            tag = _STYLE_TAG_MAP.get(style_name, "/P")
        elif isinstance(flowable, Table):
            tag = "/Table"
        self._struct_elements.append({
            "tag": tag,
            "page": self.page,
        })
        super().afterFlowable(flowable)


def apply_pdf_ua_metadata(pdf_bytes: bytes, title: str = "", author: str = "",
                           subject: str = "", lang: str = "en-US") -> bytes:
    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()

    # Copy all pages
    for page in reader.pages:
        writer.add_page(page)

    # Copy metadata and set new values
    writer.add_metadata({
        "/Title": title,
        "/Author": author or "L30 Board Governance System",
        "/Subject": subject,
        "/Producer": "L30 Board PDF Generator",
        "/Creator": "L30 Library System",
    })

    # Get catalog reference
    catalog = writer._root_object

    # Mark as tagged PDF
    mark_info = DictionaryObject()
    mark_info[NameObject("/Marked")] = BooleanObject(True)
    catalog[NameObject("/MarkInfo")] = mark_info

    # Set document language
    catalog[NameObject("/Lang")] = TextStringObject(lang)

    # Display document title in viewer title bar
    viewer_prefs = DictionaryObject()
    viewer_prefs[NameObject("/DisplayDocTitle")] = BooleanObject(True)
    catalog[NameObject("/ViewerPreferences")] = viewer_prefs

    # Build minimal structure tree
    # StructTreeRoot -> Document element
    doc_elem = DictionaryObject()
    doc_elem[NameObject("/Type")] = NameObject("/StructElem")
    doc_elem[NameObject("/S")] = NameObject("/Document")
    doc_elem[NameObject("/K")] = ArrayObject()  # children (empty -- content tagging would need marked content IDs)

    struct_tree = DictionaryObject()
    struct_tree[NameObject("/Type")] = NameObject("/StructTreeRoot")
    struct_tree[NameObject("/K")] = writer._add_object(doc_elem)
    struct_tree[NameObject("/ParentTree")] = writer._add_object(DictionaryObject({
        NameObject("/Type"): NameObject("/NumberTree"),
        NameObject("/Nums"): ArrayObject(),
    }))

    # Role map for common tags
    role_map = DictionaryObject()
    for tag in ["/H1", "/H2", "/H3", "/P", "/Table", "/Span", "/Document"]:
        role_map[NameObject(tag)] = NameObject(tag)
    struct_tree[NameObject("/RoleMap")] = role_map

    catalog[NameObject("/StructTreeRoot")] = writer._add_object(struct_tree)

    output = BytesIO()
    writer.write(output)
    return output.getvalue()
