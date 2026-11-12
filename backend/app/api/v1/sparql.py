# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
SPARQL Endpoint API

This module provides a SPARQL endpoint for querying BIBFRAME data
using the SPARQL query language.

Endpoint: POST /api/v1/sparql/query
          GET /api/v1/sparql/query?query=...

The endpoint follows the SPARQL 1.1 Protocol specification:
https://www.w3.org/TR/sparql11-protocol/

Supported features:
- SELECT queries with basic graph patterns
- FILTER expressions
- LIMIT, OFFSET, ORDER BY
- Content negotiation (JSON, XML results)

Example usage:
```
POST /api/v1/sparql/query
Content-Type: application/sparql-query

SELECT ?title ?author WHERE {
  ?work a bf:Work .
  ?work bf:title/bf:mainTitle ?title .
}
LIMIT 10
```
"""

from typing import Optional
import xml.etree.ElementTree as ET

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.rate_limit import limiter
from ...services.sparql_service import sparql_service


router = APIRouter(prefix="/sparql", tags=["SPARQL"])


# ============================================================================
# Request/Response Models
# ============================================================================


class SparqlQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000, description="SPARQL query string")
    default_graph_uri: Optional[str] = Field(None, description="Default graph URI (not yet supported)")
    named_graph_uri: Optional[list[str]] = Field(None, description="Named graph URIs (not yet supported)")


class SparqlBinding(BaseModel):
    type: str  # "uri", "literal", "bnode"
    value: str
    datatype: Optional[str] = None
    lang: Optional[str] = Field(None, alias="xml:lang")


class SparqlResults(BaseModel):
    head: dict
    results: dict


# ============================================================================
# Helper Functions
# ============================================================================


def get_result_format(accept: Optional[str], format_param: Optional[str]) -> str:
    if format_param:
        format_param = format_param.lower()
        if format_param in ("json", "application/sparql-results+json"):
            return "json"
        elif format_param in ("xml", "application/sparql-results+xml"):
            return "xml"
        elif format_param in ("csv", "text/csv"):
            return "csv"

    if accept:
        accept = accept.lower()
        if "application/sparql-results+json" in accept or "application/json" in accept:
            return "json"
        elif "application/sparql-results+xml" in accept or "application/xml" in accept:
            return "xml"
        elif "text/csv" in accept:
            return "csv"

    return "json"  # Default


def results_to_xml(results: dict) -> str:
    # Create root element
    root = ET.Element("sparql")
    root.set("xmlns", "http://www.w3.org/2005/sparql-results#")

    # Add head element with variables
    head = ET.SubElement(root, "head")
    for var in results.get("head", {}).get("vars", []):
        var_elem = ET.SubElement(head, "variable")
        var_elem.set("name", var)

    # Add results element
    results_elem = ET.SubElement(root, "results")

    for binding in results.get("results", {}).get("bindings", []):
        result_elem = ET.SubElement(results_elem, "result")

        for var_name, value_info in binding.items():
            binding_elem = ET.SubElement(result_elem, "binding")
            binding_elem.set("name", var_name)

            value_type = value_info.get("type", "literal")
            if value_type == "uri":
                uri_elem = ET.SubElement(binding_elem, "uri")
                uri_elem.text = value_info.get("value", "")
            elif value_type == "bnode":
                bnode_elem = ET.SubElement(binding_elem, "bnode")
                bnode_elem.text = value_info.get("value", "")
            else:
                literal_elem = ET.SubElement(binding_elem, "literal")
                literal_elem.text = value_info.get("value", "")
                if "datatype" in value_info:
                    literal_elem.set("datatype", value_info["datatype"])
                if "xml:lang" in value_info:
                    literal_elem.set("{http://www.w3.org/XML/1998/namespace}lang", value_info["xml:lang"])

    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def results_to_csv(results: dict) -> str:
    lines = []

    vars = results.get("head", {}).get("vars", [])
    lines.append(",".join(vars))

    for binding in results.get("results", {}).get("bindings", []):
        row = []
        for var in vars:
            value_info = binding.get(var, {})
            value = value_info.get("value", "")
            # Escape CSV special characters
            if "," in value or '"' in value or "\n" in value:
                value = '"' + value.replace('"', '""') + '"'
            row.append(value)
        lines.append(",".join(row))

    return "\n".join(lines)


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/query")
@limiter.limit("30/minute")
async def sparql_query_get(
    request: Request,
    query: str = Query(..., min_length=1, max_length=10000, description="SPARQL query"),
    default_graph_uri: Optional[str] = Query(None, alias="default-graph-uri"),
    format: Optional[str] = Query(None, description="Result format: json, xml, csv"),
    accept: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a SPARQL query via HTTP GET.

    This follows the SPARQL 1.1 Protocol specification for query via GET.
    The query must be URL-encoded in the query parameter.

    Example:
    ```
    GET /api/v1/sparql/query?query=SELECT%20%3Ftitle%20WHERE%20%7B%20%3Fwork%20bf%3Atitle%20%3Ftitle%20%7D
    ```
    """
    result_format = get_result_format(accept, format)

    results = await sparql_service.execute(query, db)

    if "error" in results and results["error"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=results["error"])

    if result_format == "xml":
        xml_output = results_to_xml(results)
        return Response(
            content=xml_output,
            media_type="application/sparql-results+xml",
        )
    elif result_format == "csv":
        csv_output = results_to_csv(results)
        return Response(
            content=csv_output,
            media_type="text/csv",
        )
    else:
        return JSONResponse(
            content=results,
            media_type="application/sparql-results+json",
        )


@router.post("/query")
@limiter.limit("30/minute")
async def sparql_query_post(
    request: Request,
    format: Optional[str] = Query(None, description="Result format: json, xml, csv"),
    accept: Optional[str] = Header(None),
    content_type: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a SPARQL query via HTTP POST.

    Supports two content types:
    - application/sparql-query: Query string in request body
    - application/x-www-form-urlencoded: Query in 'query' parameter

    Example with direct query:
    ```
    POST /api/v1/sparql/query
    Content-Type: application/sparql-query

    SELECT ?title WHERE { ?work bf:title ?title } LIMIT 10
    ```
    """
    body = await request.body()
    query = None

    if content_type and "application/sparql-query" in content_type:
        # Direct query in body
        query = body.decode("utf-8")
    elif content_type and "application/x-www-form-urlencoded" in content_type:
        # Form-encoded
        form = await request.form()
        query = form.get("query", "")
    elif content_type and "application/json" in content_type:
        # JSON body
        import json
        data = json.loads(body)
        query = data.get("query", "")
    else:
        # Try to parse as plain text query
        query = body.decode("utf-8")

    if not query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No query provided")

    result_format = get_result_format(accept, format)

    results = await sparql_service.execute(query, db)

    if "error" in results and results["error"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=results["error"])

    if result_format == "xml":
        xml_output = results_to_xml(results)
        return Response(
            content=xml_output,
            media_type="application/sparql-results+xml",
        )
    elif result_format == "csv":
        csv_output = results_to_csv(results)
        return Response(
            content=csv_output,
            media_type="text/csv",
        )
    else:
        return JSONResponse(
            content=results,
            media_type="application/sparql-results+json",
        )


@router.get("")
@limiter.limit("60/minute")
async def sparql_service_description(
    request: Request,
    accept: Optional[str] = Header(None),
):
    """
    Return SPARQL Service Description.

    When the SPARQL endpoint is accessed without a query parameter,
    it returns a service description document describing the endpoint's
    capabilities.
    """
    description = sparql_service.get_service_description()

    if accept and "text/turtle" in accept:
        return Response(
            content=description,
            media_type="text/turtle",
        )
    elif accept and "application/ld+json" in accept:
        # Convert to JSON-LD (simplified)
        return JSONResponse(
            content={
                "@context": {
                    "sd": "http://www.w3.org/ns/sparql-service-description#",
                    "bf": "http://id.loc.gov/ontologies/bibframe/",
                },
                "@type": "sd:Service",
                "sd:endpoint": f"{request.base_url}api/v1/sparql/query",
                "sd:supportedLanguage": "sd:SPARQL11Query",
                "sd:resultFormat": [
                    "http://www.w3.org/ns/formats/SPARQL_Results_JSON",
                    "http://www.w3.org/ns/formats/SPARQL_Results_XML",
                ],
            },
            media_type="application/ld+json",
        )
    else:
        return Response(
            content=description,
            media_type="text/turtle",
        )


@router.get("/prefixes")
async def get_prefixes(request: Request):
    """
    Return the supported namespace prefixes.

    These prefixes can be used in SPARQL queries without explicit
    PREFIX declarations.
    """
    return {
        "prefixes": sparql_service.PREFIXES,
        "example_query": """
PREFIX bf: <http://id.loc.gov/ontologies/bibframe/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?work ?title WHERE {
  ?work a bf:Work .
  ?work bf:title ?title .
}
LIMIT 10
""".strip(),
    }


@router.get("/examples")
async def get_example_queries(request: Request):
    """
    Return example SPARQL queries for this endpoint.

    These examples demonstrate the supported query patterns
    and can be used as templates.
    """
    return {
        "examples": [
            {
                "name": "List all works with titles",
                "description": "Simple query to list works and their titles",
                "query": """
SELECT ?work ?title WHERE {
  ?work a bf:Work .
  ?work bf:title ?title .
}
LIMIT 20
""".strip(),
            },
            {
                "name": "Search works by title",
                "description": "Find works with 'science' in the title",
                "query": """
SELECT ?work ?title WHERE {
  ?work a bf:Work .
  ?work bf:title ?title .
  FILTER(CONTAINS(?title, "science"))
}
LIMIT 10
""".strip(),
            },
            {
                "name": "List instances with ISBN",
                "description": "Find all instances that have an ISBN",
                "query": """
SELECT ?instance ?title ?isbn WHERE {
  ?instance a bf:Instance .
  ?instance bf:title ?title .
  ?instance bf:isbn ?isbn .
}
LIMIT 20
""".strip(),
            },
            {
                "name": "Find items by library branch",
                "description": "List items held at a specific branch",
                "query": """
SELECT ?item ?barcode ?callNumber WHERE {
  ?item a bf:Item .
  ?item bf:barcode ?barcode .
  ?item bf:shelfMark ?callNumber .
  ?item bf:heldBy "Main" .
}
LIMIT 20
""".strip(),
            },
            {
                "name": "Works with contributors",
                "description": "Find works and their associated contributors",
                "query": """
SELECT ?work ?title ?contributor WHERE {
  ?work a bf:Work .
  ?work bf:title ?title .
  ?work bf:contribution ?contribNode .
  ?contribNode bf:agent ?agent .
  ?agent rdfs:label ?contributor .
}
LIMIT 20
""".strip(),
            },
        ],
    }
