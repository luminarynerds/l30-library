# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from ..core.config import get_settings

settings = get_settings()

from ..models.bibframe import (
    AuthorityLink,
    BibframeContributor,
    BibframeInstance,
    BibframeItem,
    BibframeSubject,
    BibframeWork,
    work_contributors,
    work_subjects,
)


class SparqlError(Exception):
    pass


@dataclass
class TriplePattern:
    subject: str
    predicate: str
    object: str
    optional: bool = False


@dataclass
class Filter:
    expression: str
    variables: list[str] = field(default_factory=list)


@dataclass
class ParsedQuery:
    query_type: str  # SELECT, CONSTRUCT, ASK, DESCRIBE
    variables: list[str]
    distinct: bool = False
    patterns: list[TriplePattern] = field(default_factory=list)
    filters: list[Filter] = field(default_factory=list)
    limit: Optional[int] = None
    offset: Optional[int] = None
    order_by: list[tuple[str, str]] = field(default_factory=list)  # (variable, direction)


class SparqlService:

    # Namespace prefixes
    PREFIXES = {
        "bf": "http://id.loc.gov/ontologies/bibframe/",
        "bflc": "http://id.loc.gov/ontologies/bflc/",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "owl": "http://www.w3.org/2002/07/owl#",
        "schema": "https://schema.org/",
        "dcterms": "http://purl.org/dc/terms/",
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
    }

    # Mapping of RDF types to database models
    TYPE_TO_MODEL = {
        "bf:Work": BibframeWork,
        "http://id.loc.gov/ontologies/bibframe/Work": BibframeWork,
        "bf:Instance": BibframeInstance,
        "http://id.loc.gov/ontologies/bibframe/Instance": BibframeInstance,
        "bf:Item": BibframeItem,
        "http://id.loc.gov/ontologies/bibframe/Item": BibframeItem,
        "bf:Agent": BibframeContributor,
        "bf:Person": BibframeContributor,
        "bf:Organization": BibframeContributor,
        "http://id.loc.gov/ontologies/bibframe/Agent": BibframeContributor,
        "bf:Topic": BibframeSubject,
        "http://id.loc.gov/ontologies/bibframe/Topic": BibframeSubject,
    }

    # Mapping of BIBFRAME predicates to model fields
    PREDICATE_MAPPING = {
        # Work predicates
        "bf:title": ("BibframeWork", "title"),
        "bf:mainTitle": ("BibframeWork", "title"),
        "bf:subtitle": ("BibframeWork", "subtitle"),
        "bf:language": ("BibframeWork", "language"),
        "bf:summary": ("BibframeWork", "summary"),
        "bf:content": ("BibframeWork", "work_type"),
        "bf:classification": ("BibframeWork", "dewey_classification"),
        "dcterms:created": ("BibframeWork", "created_at"),

        # Instance predicates
        "bf:identifiedBy": ("BibframeInstance", "isbn_13"),
        "bf:isbn": ("BibframeInstance", "isbn_13"),
        "bf:publisher": ("BibframeInstance", "publisher"),
        "bf:publicationYear": ("BibframeInstance", "publication_year"),
        "bf:extent": ("BibframeInstance", "extent"),
        "bf:instanceOf": ("BibframeInstance", "work_id"),

        # Item predicates
        "bf:barcode": ("BibframeItem", "barcode"),
        "bf:shelfMark": ("BibframeItem", "call_number"),
        "bf:itemOf": ("BibframeItem", "instance_id"),
        "bf:heldBy": ("BibframeItem", "library_branch"),

        # Contributor predicates
        "rdfs:label": ("BibframeContributor", "name"),
        "schema:name": ("BibframeContributor", "name"),
        "schema:givenName": ("BibframeContributor", "given_name"),
        "schema:familyName": ("BibframeContributor", "family_name"),

        # Subject predicates
        "skos:prefLabel": ("BibframeSubject", "label"),
    }

    # Base URI for local resources
    BASE_URI = settings.bibframe_base_uri

    def __init__(self):
        pass

    def parse_query(self, sparql: str) -> ParsedQuery:
        # Normalize whitespace
        sparql = " ".join(sparql.split())

        # Extract and apply PREFIX declarations
        prefix_pattern = r"PREFIX\s+(\w+):\s*<([^>]+)>"
        for match in re.finditer(prefix_pattern, sparql, re.IGNORECASE):
            prefix, uri = match.groups()
            self.PREFIXES[prefix] = uri

        # Remove PREFIX declarations for further parsing
        sparql = re.sub(prefix_pattern, "", sparql, flags=re.IGNORECASE).strip()

        # Determine query type
        query_type_match = re.match(r"(SELECT|CONSTRUCT|ASK|DESCRIBE)", sparql, re.IGNORECASE)
        if not query_type_match:
            raise SparqlError("Unsupported query type. Only SELECT is currently supported.")

        query_type = query_type_match.group(1).upper()

        if query_type != "SELECT":
            raise SparqlError(f"Query type {query_type} is not yet supported. Use SELECT.")

        # Parse SELECT clause
        distinct = bool(re.search(r"SELECT\s+DISTINCT", sparql, re.IGNORECASE))
        variables_match = re.search(
            r"SELECT\s+(?:DISTINCT\s+)?(.+?)\s+WHERE",
            sparql,
            re.IGNORECASE
        )
        if not variables_match:
            raise SparqlError("Could not parse SELECT variables")

        variables_str = variables_match.group(1)
        if variables_str.strip() == "*":
            variables = ["*"]
        else:
            variables = re.findall(r"\?(\w+)", variables_str)

        # Extract WHERE clause
        where_match = re.search(r"WHERE\s*\{(.+?)\}", sparql, re.IGNORECASE | re.DOTALL)
        if not where_match:
            raise SparqlError("Could not parse WHERE clause")

        where_clause = where_match.group(1)

        # Parse triple patterns
        patterns = self._parse_patterns(where_clause)

        # Parse FILTER expressions
        filters = self._parse_filters(where_clause)

        # Parse LIMIT
        limit = None
        limit_match = re.search(r"LIMIT\s+(\d+)", sparql, re.IGNORECASE)
        if limit_match:
            limit = int(limit_match.group(1))

        # Parse OFFSET
        offset = None
        offset_match = re.search(r"OFFSET\s+(\d+)", sparql, re.IGNORECASE)
        if offset_match:
            offset = int(offset_match.group(1))

        # Parse ORDER BY
        order_by = []
        order_match = re.search(r"ORDER\s+BY\s+(.+?)(?:LIMIT|OFFSET|$)", sparql, re.IGNORECASE)
        if order_match:
            order_str = order_match.group(1)
            for var_match in re.finditer(r"(ASC|DESC)?\s*\(\s*\?(\w+)\s*\)|\?(\w+)", order_str, re.IGNORECASE):
                direction = (var_match.group(1) or "ASC").upper()
                var = var_match.group(2) or var_match.group(3)
                if var:
                    order_by.append((var, direction))

        return ParsedQuery(
            query_type=query_type,
            variables=variables,
            distinct=distinct,
            patterns=patterns,
            filters=filters,
            limit=limit,
            offset=offset,
            order_by=order_by,
        )

    def _parse_patterns(self, where_clause: str) -> list[TriplePattern]:
        patterns = []

        # Handle OPTIONAL blocks
        optional_matches = list(re.finditer(r"OPTIONAL\s*\{([^}]+)\}", where_clause, re.IGNORECASE))
        for match in optional_matches:
            optional_content = match.group(1)
            for pattern in self._extract_triples(optional_content):
                pattern.optional = True
                patterns.append(pattern)

        # Remove OPTIONAL and FILTER blocks for main pattern parsing
        main_clause = re.sub(r"OPTIONAL\s*\{[^}]+\}", "", where_clause, flags=re.IGNORECASE)
        main_clause = re.sub(r"FILTER\s*\([^)]+\)", "", main_clause, flags=re.IGNORECASE)

        # Parse main triple patterns
        for pattern in self._extract_triples(main_clause):
            patterns.append(pattern)

        return patterns

    def _extract_triples(self, clause: str) -> list[TriplePattern]:
        patterns = []

        # Pattern for triples: subject predicate object .
        # Handles variables (?var), prefixed URIs (bf:Work), and literals ("string")
        triple_pattern = r'([?\w:<>/]+)\s+([?\w:<>/]+)\s+([?\w:<>/"]+)\s*[.;]?'

        for match in re.finditer(triple_pattern, clause):
            subject, predicate, obj = match.groups()
            subject = subject.strip()
            predicate = predicate.strip()
            obj = obj.strip()

            # Skip empty patterns
            if not subject or not predicate or not obj:
                continue

            # Expand 'a' to rdf:type
            if predicate == "a":
                predicate = "rdf:type"

            patterns.append(TriplePattern(
                subject=subject,
                predicate=predicate,
                object=obj,
            ))

        return patterns

    def _parse_filters(self, where_clause: str) -> list[Filter]:
        filters = []

        filter_pattern = r"FILTER\s*\(([^)]+)\)"
        for match in re.finditer(filter_pattern, where_clause, re.IGNORECASE):
            expression = match.group(1)
            variables = re.findall(r"\?(\w+)", expression)
            filters.append(Filter(expression=expression, variables=variables))

        return filters

    async def execute(self, sparql: str, db: AsyncSession) -> dict[str, Any]:
        try:
            parsed = self.parse_query(sparql)
        except SparqlError as e:
            return {
                "error": str(e),
                "head": {"vars": []},
                "results": {"bindings": []},
            }

        # Build and execute SQL query
        try:
            results = await self._execute_select(parsed, db)
        except Exception as e:  # noqa: BLE001 -- SPARQL query boundary: surface execution error in response, never crash route
            return {
                "error": f"Query execution error: {str(e)}",
                "head": {"vars": parsed.variables},
                "results": {"bindings": []},
            }

        return {
            "head": {"vars": parsed.variables},
            "results": {"bindings": results},
        }

    async def _execute_select(
        self,
        parsed: ParsedQuery,
        db: AsyncSession,
    ) -> list[dict[str, Any]]:
        results = []

        # Determine the primary model from type patterns
        primary_model = None

        for pattern in parsed.patterns:
            if pattern.predicate in ("rdf:type", "a"):
                model = self.TYPE_TO_MODEL.get(pattern.object)
                if model:
                    primary_model = model
                    break

        if not primary_model:
            # Default to Work
            primary_model = BibframeWork

        # Build base query
        query = select(primary_model)

        # Apply FILTER conditions
        for filter_expr in parsed.filters:
            filter_condition = self._translate_filter(filter_expr, primary_model)
            if filter_condition is not None:
                query = query.where(filter_condition)

        # Apply LIMIT and OFFSET
        if parsed.limit:
            query = query.limit(min(parsed.limit, 1000))  # Cap at 1000
        else:
            query = query.limit(100)  # Default limit

        if parsed.offset:
            query = query.offset(parsed.offset)

        # Execute query
        result = await db.execute(query)
        entities = result.scalars().all()

        # Build result bindings
        for entity in entities:
            binding = {}

            for var in parsed.variables:
                if var == "*":
                    continue

                value = self._extract_value(entity, var, parsed.patterns)
                if value is not None:
                    binding[var] = self._format_value(value, entity)

            if binding:
                results.append(binding)

        return results

    def _translate_filter(self, filter_expr: Filter, model) -> Any:
        expr = filter_expr.expression

        # Handle CONTAINS(?var, "value")
        contains_match = re.search(r"CONTAINS\s*\(\s*\?(\w+)\s*,\s*[\"']([^\"']+)[\"']\s*\)", expr, re.IGNORECASE)
        if contains_match:
            var, value = contains_match.groups()
            field = self._get_model_field(model, var)
            if field:
                safe_value = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                return field.ilike(f"%{safe_value}%")

        # Handle REGEX(?var, "pattern")
        regex_match = re.search(r"REGEX\s*\(\s*\?(\w+)\s*,\s*[\"']([^\"']+)[\"']\s*\)", expr, re.IGNORECASE)
        if regex_match:
            var, pattern = regex_match.groups()
            field = self._get_model_field(model, var)
            if field:
                # PostgreSQL regex
                return field.op("~")(pattern)

        # Handle comparison operators
        comp_match = re.search(r"\?(\w+)\s*([<>=!]+)\s*[\"']?([^\"']+)[\"']?", expr)
        if comp_match:
            var, op, value = comp_match.groups()
            field = self._get_model_field(model, var)
            if field:
                if op == "=":
                    return field == value
                elif op == "!=":
                    return field != value
                elif op == ">":
                    return field > value
                elif op == "<":
                    return field < value
                elif op == ">=":
                    return field >= value
                elif op == "<=":
                    return field <= value

        return None

    def _get_model_field(self, model, var_name: str):
        # Common variable name to field mappings
        var_to_field = {
            "title": "title",
            "name": "name",
            "label": "label",
            "author": "author",
            "isbn": "isbn_13",
            "publisher": "publisher",
            "year": "publication_year",
            "language": "language",
            "barcode": "barcode",
        }

        field_name = var_to_field.get(var_name, var_name)

        if hasattr(model, field_name):
            return getattr(model, field_name)

        return None

    def _extract_value(self, entity, var: str, patterns: list[TriplePattern]) -> Any:
        # Find the pattern that binds this variable
        for pattern in patterns:
            if pattern.object == f"?{var}":
                # Get field from predicate
                predicate = pattern.predicate
                mapping = self.PREDICATE_MAPPING.get(predicate)
                if mapping:
                    _, field_name = mapping
                    if hasattr(entity, field_name):
                        return getattr(entity, field_name)

        # Try direct attribute access
        if hasattr(entity, var):
            return getattr(entity, var)

        # Common variable names
        common_mappings = {
            "title": "title",
            "name": "name",
            "label": "label",
            "isbn": "isbn_13",
            "author": "author",
            "publisher": "publisher",
            "year": "publication_year",
            "language": "language",
            "uri": "uri",
        }

        if var in common_mappings:
            attr = common_mappings[var]
            if hasattr(entity, attr):
                return getattr(entity, attr)

        return None

    def _format_value(self, value: Any, entity: Any = None) -> dict[str, Any]:
        if value is None:
            return {"type": "literal", "value": ""}

        if isinstance(value, str):
            # Check if it's a URI
            if value.startswith("http://") or value.startswith("https://"):
                return {"type": "uri", "value": value}
            return {"type": "literal", "value": value}

        if isinstance(value, bool):
            return {
                "type": "literal",
                "value": str(value).lower(),
                "datatype": "http://www.w3.org/2001/XMLSchema#boolean",
            }

        if isinstance(value, int):
            return {
                "type": "literal",
                "value": str(value),
                "datatype": "http://www.w3.org/2001/XMLSchema#integer",
            }

        if isinstance(value, float):
            return {
                "type": "literal",
                "value": str(value),
                "datatype": "http://www.w3.org/2001/XMLSchema#decimal",
            }

        if hasattr(value, "isoformat"):
            return {
                "type": "literal",
                "value": value.isoformat(),
                "datatype": "http://www.w3.org/2001/XMLSchema#dateTime",
            }

        # Default to string
        return {"type": "literal", "value": str(value)}

    def get_service_description(self) -> str:
        return f"""@prefix sd: <http://www.w3.org/ns/sparql-service-description#> .
@prefix bf: <http://id.loc.gov/ontologies/bibframe/> .
@prefix void: <http://rdfs.org/ns/void#> .

<{self.BASE_URI}/sparql> a sd:Service ;
    sd:endpoint <{self.BASE_URI}/sparql> ;
    sd:supportedLanguage sd:SPARQL11Query ;
    sd:resultFormat <http://www.w3.org/ns/formats/SPARQL_Results_JSON> ;
    sd:feature sd:BasicFederatedQuery ;
    sd:defaultDataset [
        a sd:Dataset ;
        sd:defaultGraph [
            a sd:Graph ;
            void:triples 0 ;
            void:class bf:Work, bf:Instance, bf:Item
        ]
    ] .
"""


# Singleton instance
sparql_service = SparqlService()
