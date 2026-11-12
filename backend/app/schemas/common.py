# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
from typing import Any, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, Field

# ============================================================================
# Generic Type Variable
# ============================================================================

T = TypeVar('T')


# ============================================================================
# Pagination Schemas
# ============================================================================


class PaginationInfo(BaseModel):

    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    per_page: int = Field(..., ge=1, le=500, description="Items per page")
    total: int = Field(..., ge=0, description="Total number of items across all pages")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")

    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "per_page": 20,
                "total": 100,
                "total_pages": 5,
                "has_next": True,
                "has_previous": False,
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):

    data: List[T] = Field(..., description="List of items for this page")
    pagination: PaginationInfo = Field(..., description="Pagination metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "data": [
                    {"id": 1, "title": "Item 1"},
                    {"id": 2, "title": "Item 2"},
                ],
                "pagination": {
                    "page": 1,
                    "per_page": 20,
                    "total": 100,
                    "total_pages": 5,
                    "has_next": True,
                    "has_previous": False,
                },
            }
        }


class CursorPaginatedResponse(BaseModel, Generic[T]):

    data: List[T] = Field(..., description="List of items")
    cursor: Optional[str] = Field(
        None, description="Cursor for next page (None if no more results)"
    )
    has_more: bool = Field(..., description="Whether there are more results")

    class Config:
        json_schema_extra = {
            "example": {
                "data": [
                    {"id": 1, "title": "Item 1"},
                    {"id": 2, "title": "Item 2"},
                ],
                "cursor": "eyJpZCI6IDIwfQ==",
                "has_more": True,
            }
        }


# ============================================================================
# Error Response Schemas
# ============================================================================


class ErrorDetail(BaseModel):

    field: Optional[str] = Field(
        None, description="Field name (if applicable)"
    )
    message: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code for programmatic handling")

    class Config:
        json_schema_extra = {
            "example": {
                "field": "email",
                "message": "Invalid email format",
                "code": "INVALID_FORMAT",
            }
        }


class ErrorResponse(BaseModel):

    type: str = Field(
        ...,
        description="Error type (VALIDATION_ERROR, NOT_FOUND, UNAUTHORIZED, SERVER_ERROR, etc.)"
    )
    message: str = Field(..., description="Human-readable error message")
    code: str = Field(..., description="Machine-readable error code for programmatic handling")
    status_code: int = Field(..., description="HTTP status code")
    request_id: Optional[str] = Field(
        None, description="Request ID for tracking and debugging"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the error occurred"
    )
    details: Optional[List[ErrorDetail]] = Field(
        None, description="Additional error details (e.g., validation errors)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "type": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "code": "VALIDATION_FAILED",
                "status_code": 400,
                "request_id": "req_550e8400_e29b_41d4_a716",
                "timestamp": "2026-01-28T10:30:45.123000+00:00",
                "details": [
                    {
                        "field": "email",
                        "message": "Invalid email format",
                        "code": "INVALID_FORMAT",
                    }
                ],
            }
        }


# ============================================================================
# Success Response Schemas
# ============================================================================


class SuccessResponse(BaseModel, Generic[T]):

    data: T = Field(..., description="The returned resource or data")
    message: Optional[str] = Field(
        None, description="Optional success message"
    )
    status_code: int = Field(
        200, description="HTTP status code"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the response was generated"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "data": {"id": 123, "name": "Item"},
                "message": "Item created successfully",
                "status_code": 201,
                "timestamp": "2026-01-28T10:30:45.123000+00:00",
            }
        }


class MessageResponse(BaseModel):

    message: str = Field(..., description="Response message")
    status_code: int = Field(
        200, description="HTTP status code"
    )
    request_id: Optional[str] = Field(
        None, description="Request ID for tracking"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the response was generated"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Item deleted successfully",
                "status_code": 200,
                "request_id": "req_550e8400_e29b_41d4_a716",
                "timestamp": "2026-01-28T10:30:45.123000+00:00",
            }
        }


class BulkOperationResponse(BaseModel):

    message: str = Field(..., description="Operation summary")
    total: int = Field(..., ge=0, description="Total items processed")
    succeeded: int = Field(..., ge=0, description="Number of successful operations")
    failed: int = Field(..., ge=0, description="Number of failed operations")
    status_code: int = Field(
        200, description="HTTP status code"
    )
    errors: Optional[List[dict]] = Field(
        None, description="Details of failed items"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the operation completed"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Bulk delete completed",
                "total": 100,
                "succeeded": 95,
                "failed": 5,
                "status_code": 200,
                "errors": [
                    {"item_id": 10, "error": "Item not found"},
                    {"item_id": 20, "error": "Permission denied"},
                ],
                "timestamp": "2026-01-28T10:30:45.123000+00:00",
            }
        }


# ============================================================================
# Job/Background Task Response Schemas
# ============================================================================


class JobResponse(BaseModel):

    job_id: Optional[str] = Field(
        None, description="Job identifier for tracking"
    )
    status: str = Field(
        ...,
        description="Job status (pending, running, completed, failed, cancelled)"
    )
    message: str = Field(..., description="Job description or result message")
    result: Optional[dict] = Field(
        None, description="Job execution result data"
    )
    status_code: int = Field(
        200, description="HTTP status code"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the job completed or status was last updated"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job_550e8400_e29b_41d4_a716",
                "status": "completed",
                "message": "Hold expiry processing completed",
                "result": {
                    "processed": 100,
                    "succeeded": 98,
                    "failed": 2,
                },
                "status_code": 200,
                "timestamp": "2026-01-28T10:30:45.123000+00:00",
            }
        }


# ============================================================================
# Admin & Monitoring Response Schemas
# ============================================================================


class EndpointAccessInfo(BaseModel):

    endpoint: str = Field(..., description="Endpoint identifier (METHOD /path)")
    hit_count: int = Field(..., ge=0, description="Number of requests")
    last_accessed: Optional[datetime] = Field(None, description="Last request timestamp")


class EndpointStatsResponse(BaseModel):

    enabled: bool = Field(..., description="Whether endpoint tracking is enabled")
    total_endpoints: int = Field(..., ge=0, description="Total tracked endpoints")
    total_requests: int = Field(..., ge=0, description="Total requests across all endpoints")
    uptime: Optional[dict] = Field(None, description="Uptime information")
    most_accessed: List[EndpointAccessInfo] = Field(..., description="Top 10 most accessed endpoints")
    status_code_distribution: dict = Field(..., description="Distribution of HTTP status codes")

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "total_endpoints": 145,
                "total_requests": 50000,
                "uptime": {"days": 30, "hours": 5},
                "most_accessed": [
                    {"endpoint": "GET /api/v1/catalog/search", "hit_count": 5000, "last_accessed": "2026-02-04T10:30:45Z"}
                ],
                "status_code_distribution": {"200": 48000, "401": 1000, "404": 500, "500": 500},
            }
        }


class SingleEndpointStatsResponse(BaseModel):

    enabled: bool = Field(..., description="Whether endpoint tracking is enabled")
    endpoint_stats: Optional[dict] = Field(None, description="Endpoint statistics")

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "endpoint_stats": {
                    "hit_count": 5000,
                    "last_accessed": "2026-02-04T10:30:45Z",
                    "status_codes": {"200": 4900, "400": 100},
                },
            }
        }


# ============================================================================
# Utility Types for Type Hints
# ============================================================================


ApiResponse = Union[
    PaginatedResponse,
    CursorPaginatedResponse,
    SuccessResponse,
    MessageResponse,
    BulkOperationResponse,
    JobResponse,
    ErrorResponse,
]
"""Union of all possible API response types."""
