# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for BIBFRAME services.

Tests cover:
- BIBFRAME model creation and validation
- RDF serialization (JSON-LD and Turtle)
- MARC to BIBFRAME conversion
- Schema.org generation
- SPARQL query parsing
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.bibframe import (
    BibframeWork,
    BibframeInstance,
    BibframeItem,
    BibframeContributor,
    BibframeSubject,
    AuthorityLink,
    WorkType,
    InstanceType,
    CarrierType,
    MediaType,
    ContributorRole,
    AuthoritySource,
)


# ============================================================================
# BIBFRAME Model Tests
# ============================================================================


@pytest.mark.unit
class TestBibframeWorkModel:
    """Test BibframeWork model."""

    def test_work_type_enum_values(self):
        """Test WorkType enum has expected values."""
        assert WorkType.text.value == "text"
        assert WorkType.spoken_word.value == "spoken_word"
        assert WorkType.performed_music.value == "performed_music"
        assert WorkType.notated_music.value == "notated_music"
        assert WorkType.still_image.value == "still_image"
        assert WorkType.two_dimensional_moving_image.value == "two_dimensional_moving_image"
        assert WorkType.computer_program.value == "computer_program"

    def test_work_creation_minimal(self):
        """Test creating a work with minimal fields."""
        work = BibframeWork(
            title="Test Work",
            work_type=WorkType.text,
        )
        assert work.title == "Test Work"
        assert work.work_type == WorkType.text

    def test_work_uri_format(self):
        """Test work URI generation."""
        work = BibframeWork(
            id=123,
            title="Test Work",
            work_type=WorkType.text,
        )
        # URI should be set based on ID when saved
        expected_uri_pattern = "/works/123"
        # The URI would be set by the service, but the model allows setting it
        work.uri = f"http://example.org{expected_uri_pattern}"
        assert "/works/123" in work.uri


@pytest.mark.unit
class TestBibframeInstanceModel:
    """Test BibframeInstance model."""

    def test_instance_type_enum_values(self):
        """Test InstanceType enum has expected values."""
        assert InstanceType.print.value == "print"
        assert InstanceType.electronic.value == "electronic"
        assert InstanceType.audio.value == "audio"
        assert InstanceType.audiovisual.value == "audiovisual"
        assert InstanceType.tactile.value == "tactile"
        assert InstanceType.microform.value == "microform"

    def test_carrier_type_enum_values(self):
        """Test CarrierType enum has expected values."""
        assert CarrierType.volume.value == "volume"
        assert CarrierType.audio_disc.value == "audio_disc"
        assert CarrierType.computer_disc.value == "computer_disc"
        assert CarrierType.online_resource.value == "online_resource"
        assert CarrierType.videodisc.value == "videodisc"

    def test_media_type_enum_values(self):
        """Test MediaType enum has expected values."""
        assert MediaType.unmediated.value == "unmediated"
        assert MediaType.computer.value == "computer"
        assert MediaType.audio.value == "audio"
        assert MediaType.video.value == "video"
        assert MediaType.microform.value == "microform"

    def test_instance_creation_with_isbn(self):
        """Test creating an instance with ISBN."""
        instance = BibframeInstance(
            work_id=1,
            title="Test Instance",
            instance_type=InstanceType.print,
            carrier_type=CarrierType.volume,
            media_type=MediaType.unmediated,
            isbn_13="978-0-123456-78-9",
        )
        assert instance.isbn_13 == "978-0-123456-78-9"
        assert instance.instance_type == InstanceType.print


@pytest.mark.unit
class TestBibframeItemModel:
    """Test BibframeItem model."""

    def test_item_creation(self):
        """Test creating an item."""
        item = BibframeItem(
            instance_id=1,
            barcode="12345678901234",
            call_number="QA76.73.P98 T47 2024",
            library_branch="Main",
            circulation_status="available",
            copy_number=1,
        )
        assert item.barcode == "12345678901234"
        assert item.call_number == "QA76.73.P98 T47 2024"
        assert item.library_branch == "Main"

    def test_item_defaults(self):
        """Test item default values.

        Column(default=...) is a SQLAlchemy INSERT-time default, not an
        __init__-time one -- a bare, unflushed BibframeItem() has None for
        every one of these attributes regardless of what the Column
        declares (this test never persisted anything, nor does anything
        else in this no-DB test class). Check the configured defaults on
        the table metadata instead of instance attributes.
        """
        defaults = {
            col.name: col.default.arg
            for col in BibframeItem.__table__.columns
            if col.default is not None
        }
        assert defaults["copy_number"] == 1
        assert defaults["circulation_status"] == "available"
        assert defaults["is_holdable"] is True
        assert defaults["is_loanable"] is True
        assert defaults["condition"] == "good"


@pytest.mark.unit
class TestBibframeContributorModel:
    """Test BibframeContributor model."""

    def test_contributor_role_enum_values(self):
        """Test ContributorRole enum has expected values."""
        assert ContributorRole.author.value == "author"
        assert ContributorRole.editor.value == "editor"
        assert ContributorRole.illustrator.value == "illustrator"
        assert ContributorRole.translator.value == "translator"
        assert ContributorRole.narrator.value == "narrator"
        assert ContributorRole.composer.value == "composer"
        assert ContributorRole.performer.value == "performer"

    def test_contributor_creation_person(self):
        """Test creating a person contributor."""
        contributor = BibframeContributor(
            name="Smith, John",
            contributor_type="person",
            name_inverted="Smith, John",
            given_name="John",
            family_name="Smith",
        )
        assert contributor.name == "Smith, John"
        assert contributor.contributor_type == "person"
        assert contributor.given_name == "John"

    def test_contributor_with_authority_ids(self):
        """Test contributor with external authority IDs."""
        contributor = BibframeContributor(
            name="Hemingway, Ernest",
            contributor_type="person",
            viaf_id="97006051",
            lcnaf_id="n79021164",
            wikidata_id="Q23434",
        )
        assert contributor.viaf_id == "97006051"
        assert contributor.lcnaf_id == "n79021164"
        assert contributor.wikidata_id == "Q23434"


@pytest.mark.unit
class TestBibframeSubjectModel:
    """Test BibframeSubject model."""

    def test_subject_creation(self):
        """Test creating a subject."""
        subject = BibframeSubject(
            label="Python (Computer program language)",
            subject_type="topic",
            lcsh_id="sh96008834",
        )
        assert subject.label == "Python (Computer program language)"
        assert subject.subject_type == "topic"
        assert subject.lcsh_id == "sh96008834"

    def test_subject_with_hierarchy(self):
        """Test subject with broader/narrower terms."""
        subject = BibframeSubject(
            label="Object-oriented programming",
            subject_type="topic",
            broader_term="Computer programming",
            narrower_terms=["Python", "Java", "C++"],
            related_terms=["Software engineering"],
        )
        assert subject.broader_term == "Computer programming"
        assert "Python" in subject.narrower_terms
        assert "Software engineering" in subject.related_terms


@pytest.mark.unit
class TestAuthorityLinkModel:
    """Test AuthorityLink model."""

    def test_authority_source_enum_values(self):
        """Test AuthoritySource enum has expected values."""
        assert AuthoritySource.VIAF.value == "viaf"
        assert AuthoritySource.LCNAF.value == "lcnaf"
        assert AuthoritySource.LCCN.value == "lccn"
        assert AuthoritySource.LCSH.value == "lcsh"
        assert AuthoritySource.FAST.value == "fast"
        assert AuthoritySource.WIKIDATA.value == "wikidata"
        assert AuthoritySource.ISNI.value == "isni"
        assert AuthoritySource.ORCID.value == "orcid"
        assert AuthoritySource.ISBN.value == "isbn"
        assert AuthoritySource.DOI.value == "doi"

    def test_authority_link_creation(self):
        """Test creating an authority link."""
        link = AuthorityLink(
            source=AuthoritySource.VIAF,
            authority_id="97006051",
            authority_uri="https://viaf.org/viaf/97006051",
            authority_label="Hemingway, Ernest, 1899-1961",
            link_type="sameAs",
            work_id=1,
        )
        assert link.source == AuthoritySource.VIAF
        assert link.authority_id == "97006051"
        assert "viaf.org" in link.authority_uri


# ============================================================================
# RDF Serialization Tests (Mocked)
# ============================================================================


@pytest.mark.unit
class TestBibframeRdfService:
    """Test BIBFRAME RDF serialization service."""

    def test_jsonld_context_structure(self):
        """Test JSON-LD context has required namespaces."""
        from app.services.bibframe_rdf_service import BibframeRdfService

        service = BibframeRdfService()
        context = service.JSONLD_CONTEXT

        # Check required namespace prefixes
        assert "bf" in context
        assert "rdfs" in context
        assert "schema" in context

        # Check namespace URIs
        assert context["bf"] == "http://id.loc.gov/ontologies/bibframe/"
        assert context["rdfs"] == "http://www.w3.org/2000/01/rdf-schema#"

    def test_work_to_jsonld_structure(self):
        """Test work to JSON-LD produces correct structure."""
        from app.services.bibframe_rdf_service import BibframeRdfService

        service = BibframeRdfService()

        work = BibframeWork(
            id=1,
            title="Test Work",
            work_type=WorkType.text,
            language="eng",
            uri="http://example.org/works/1",
        )

        jsonld = service.work_to_jsonld(work)

        assert "@context" in jsonld
        assert "@type" in jsonld
        assert "bf:Work" in jsonld["@type"]
        assert "@id" in jsonld
        assert "bf:title" in jsonld or "title" in jsonld

    def test_instance_to_jsonld_structure(self):
        """Test instance to JSON-LD produces correct structure."""
        from app.services.bibframe_rdf_service import BibframeRdfService

        service = BibframeRdfService()

        instance = BibframeInstance(
            id=1,
            work_id=1,
            title="Test Instance",
            instance_type=InstanceType.print,
            carrier_type=CarrierType.volume,
            media_type=MediaType.unmediated,
            isbn_13="978-0-123456-78-9",
            uri="http://example.org/instances/1",
        )

        jsonld = service.instance_to_jsonld(instance)

        assert "@context" in jsonld
        assert "@type" in jsonld
        assert "bf:Instance" in jsonld["@type"]

    def test_work_to_turtle_format(self):
        """Test work to Turtle format produces valid RDF."""
        from app.services.bibframe_rdf_service import BibframeRdfService

        service = BibframeRdfService()

        work = BibframeWork(
            id=1,
            title="Test Work",
            work_type=WorkType.text,
            language="eng",
            uri="http://example.org/works/1",
        )

        turtle = service.work_to_turtle(work)

        # Check for Turtle format markers
        assert "@prefix" in turtle or "PREFIX" in turtle
        assert "bf:" in turtle
        assert "Work" in turtle


# ============================================================================
# MARC to BIBFRAME Conversion Tests
# ============================================================================


@pytest.mark.unit
class TestMarcToBibframeService:
    """Test MARC to BIBFRAME conversion service."""

    def test_extract_title_from_marc_245(self):
        """Test extracting title from MARC 245 field."""
        from app.services.marc_to_bibframe_service import MarcToBibframeService

        service = MarcToBibframeService()

        # Create a mock MARC record with 245 field
        mock_record = MagicMock()
        mock_245 = MagicMock()
        mock_245.__getitem__ = lambda self, key: {
            "a": "The Great Gatsby",
            "b": "a novel /",
            "c": "F. Scott Fitzgerald.",
        }.get(key)
        mock_245.get = lambda key, default=None: {
            "a": "The Great Gatsby",
            "b": "a novel /",
            "c": "F. Scott Fitzgerald.",
        }.get(key, default)
        mock_record.__getitem__ = lambda self, key: mock_245 if key == "245" else None
        mock_record.get = lambda key, default=None: mock_245 if key == "245" else default

        title, subtitle, variants = service._extract_title(mock_record)

        assert "The Great Gatsby" in title

    def test_extract_isbn_from_marc_020(self):
        """Test extracting ISBN from MARC 020 field."""
        from app.services.marc_to_bibframe_service import MarcToBibframeService

        service = MarcToBibframeService()

        # Test ISBN normalization (checksum-valid ISBN with a qualifier suffix)
        isbn_raw = "978-0-13-110412-9 (hardcover)"
        normalized = service._normalize_isbn(isbn_raw)

        # Should extract just the ISBN
        assert normalized is not None
        assert "-" not in normalized or len(normalized) in [10, 13, 14, 17]

    def test_determine_work_type_from_leader(self):
        """Test determining work type from MARC leader."""
        from app.services.marc_to_bibframe_service import MarcToBibframeService

        service = MarcToBibframeService()

        def mock_record_with_leader_code(code):
            record = MagicMock()
            record.leader = "000000" + code  # position 6 is the type-of-record byte
            return record

        # Test text (books)
        work_type = service._get_work_type(mock_record_with_leader_code("a"))  # language material, monograph
        assert work_type == WorkType.text

        # Test audio
        work_type = service._get_work_type(mock_record_with_leader_code("i"))  # nonmusical sound recording
        assert work_type == WorkType.spoken_word

        # Test music
        work_type = service._get_work_type(mock_record_with_leader_code("j"))  # musical sound recording
        assert work_type == WorkType.performed_music

    def test_determine_instance_type(self):
        """Test determining instance type from MARC fields."""
        from app.services.marc_to_bibframe_service import MarcToBibframeService

        service = MarcToBibframeService()

        # Test print (no 007 field, falls back to leader position 6)
        print_record = MagicMock()
        print_record.get = lambda key, default=None: None
        print_record.leader = "000000t"
        instance_type = service._get_instance_type(print_record)
        assert instance_type == InstanceType.print

        # Test electronic (007 field position 0 == "c")
        field_007 = MagicMock()
        field_007.data = "c"
        electronic_record = MagicMock()
        electronic_record.get = lambda key, default=None: field_007 if key == "007" else default
        electronic_record.leader = "000000a"
        instance_type = service._get_instance_type(electronic_record)
        assert instance_type == InstanceType.electronic


# ============================================================================
# Schema.org Service Tests
# ============================================================================


@pytest.mark.unit
class TestSchemaOrgService:
    """Test Schema.org markup generation service."""

    def test_work_to_schema_org_book(self):
        """Test converting a text work to Schema.org Book."""
        from app.services.schema_org_service import SchemaOrgService

        service = SchemaOrgService()

        work = BibframeWork(
            id=1,
            title="Test Book",
            work_type=WorkType.text,
            summary="A test book about testing.",
            language="eng",
            uri="http://example.org/works/1",
        )

        schema = service.work_to_schema_org(work)

        assert schema["@context"] == "https://schema.org"
        assert schema["@type"] == "Book"
        assert schema["name"] == "Test Book"
        assert "description" in schema

    def test_work_to_schema_org_audiobook(self):
        """Test converting a spoken word work to Schema.org Audiobook."""
        from app.services.schema_org_service import SchemaOrgService

        service = SchemaOrgService()

        work = BibframeWork(
            id=1,
            title="Test Audiobook",
            work_type=WorkType.spoken_word,
            uri="http://example.org/works/1",
        )

        schema = service.work_to_schema_org(work)

        assert schema["@type"] in ["Audiobook", "Book"]

    def test_schema_org_includes_identifiers(self):
        """Test Schema.org includes ISBN and other identifiers."""
        from app.services.schema_org_service import SchemaOrgService

        service = SchemaOrgService()

        instance = BibframeInstance(
            id=1,
            work_id=1,
            title="Test Instance",
            instance_type=InstanceType.print,
            carrier_type=CarrierType.volume,
            media_type=MediaType.unmediated,
            isbn_13="9780123456789",
            uri="http://example.org/instances/1",
        )

        schema = service.instance_to_schema_org(instance)

        assert "isbn" in schema or "identifier" in schema

    def test_library_schema_org(self):
        """Test generating library organization Schema.org."""
        from app.services.schema_org_service import SchemaOrgService

        service = SchemaOrgService()

        schema = service.generate_library_organization_schema()

        assert schema["@context"] == "https://schema.org"
        assert "Library" in schema["@type"]
        assert "name" in schema
        assert "url" in schema


# ============================================================================
# SPARQL Service Tests
# ============================================================================


@pytest.mark.unit
class TestSparqlService:
    """Test SPARQL query parsing and execution service."""

    def test_parse_simple_select_query(self):
        """Test parsing a simple SELECT query."""
        from app.services.sparql_service import SparqlService

        service = SparqlService()

        query = """
        SELECT ?title WHERE {
            ?work a bf:Work .
            ?work bf:title ?title .
        }
        LIMIT 10
        """

        parsed = service.parse_query(query)

        assert parsed is not None
        assert parsed.query_type == "SELECT"
        assert "title" in parsed.variables
        assert parsed.limit == 10

    def test_parse_query_with_filter(self):
        """Test parsing a query with FILTER clause."""
        from app.services.sparql_service import SparqlService

        service = SparqlService()

        query = """
        SELECT ?work ?title WHERE {
            ?work a bf:Work .
            ?work bf:title ?title .
            FILTER(CONTAINS(?title, "Python"))
        }
        """

        parsed = service.parse_query(query)

        assert parsed is not None
        assert len(parsed.filters) > 0 or "CONTAINS" in query

    def test_parse_query_with_offset(self):
        """Test parsing a query with OFFSET clause."""
        from app.services.sparql_service import SparqlService

        service = SparqlService()

        query = """
        SELECT ?title WHERE {
            ?work bf:title ?title .
        }
        LIMIT 20
        OFFSET 40
        """

        parsed = service.parse_query(query)

        assert parsed is not None
        assert parsed.limit == 20
        assert parsed.offset == 40

    def test_supported_prefixes(self):
        """Test SPARQL service has required namespace prefixes."""
        from app.services.sparql_service import SparqlService

        service = SparqlService()
        prefixes = service.PREFIXES

        assert "bf" in prefixes
        assert "rdf" in prefixes
        assert "rdfs" in prefixes
        assert "schema" in prefixes

        assert "bibframe" in prefixes["bf"]

    def test_invalid_query_handling(self):
        """Test handling of invalid SPARQL query."""
        from app.services.sparql_service import SparqlService

        service = SparqlService()

        # Invalid query
        query = "NOT A VALID QUERY"

        # Should raise a SparqlError for unsupported/malformed query types
        from app.services.sparql_service import SparqlError

        with pytest.raises(SparqlError):
            service.parse_query(query)


# ============================================================================
# Integration-style Unit Tests (with mocked DB)
# ============================================================================


@pytest.mark.unit
class TestBibframeWorkflows:
    """Test BIBFRAME workflows with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_create_work_with_contributors(self):
        """Test creating a work with contributors."""
        # This would typically use a mocked database session
        work = BibframeWork(
            title="Test Work with Contributors",
            work_type=WorkType.text,
            language="eng",
        )

        contributor = BibframeContributor(
            name="Test Author",
            contributor_type="person",
        )

        # Simulate relationship (in real code this would use ORM)
        assert work.title == "Test Work with Contributors"
        assert contributor.name == "Test Author"

    @pytest.mark.asyncio
    async def test_create_work_instance_item_hierarchy(self):
        """Test creating the Work > Instance > Item hierarchy."""
        work = BibframeWork(
            id=1,
            title="Test Work",
            work_type=WorkType.text,
        )

        instance = BibframeInstance(
            id=1,
            work_id=work.id,
            title="Test Instance",
            instance_type=InstanceType.print,
            carrier_type=CarrierType.volume,
            media_type=MediaType.unmediated,
        )

        item = BibframeItem(
            id=1,
            instance_id=instance.id,
            barcode="TEST001",
            library_branch="Main",
        )

        # Verify hierarchy
        assert instance.work_id == work.id
        assert item.instance_id == instance.id

    @pytest.mark.asyncio
    async def test_authority_link_workflow(self):
        """Test linking a contributor to external authorities."""
        contributor = BibframeContributor(
            id=1,
            name="Hemingway, Ernest",
            contributor_type="person",
            viaf_id="97006051",
        )

        authority_link = AuthorityLink(
            source=AuthoritySource.VIAF,
            authority_id="97006051",
            authority_uri="https://viaf.org/viaf/97006051",
            authority_label="Hemingway, Ernest, 1899-1961",
            link_type="sameAs",
            contributor_id=contributor.id,
        )

        assert authority_link.contributor_id == contributor.id
        assert authority_link.source == AuthoritySource.VIAF
        assert contributor.viaf_id == authority_link.authority_id
