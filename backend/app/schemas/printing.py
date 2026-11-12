# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict

from pydantic import BaseModel, Field

from app.schemas._base import MoneyDecimal, StrictInputSchema


class PrintJobCreateRequest(StrictInputSchema):
    job_name: str = Field(..., min_length=1, max_length=255)
    pages: int = Field(..., gt=0)
    copies: int = Field(1, ge=1, le=100)
    color_mode: str = Field("blackwhite", pattern="^(blackwhite|color)$")
    paper_size: str = Field("letter", pattern="^(letter|legal|a4)$")
    double_sided: bool = True
    page_range: Optional[str] = Field(None, max_length=100)  # e.g., "1-5,8,10-12"
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    device_type: Optional[str] = None


class PrintJobUpdateRequest(StrictInputSchema):
    copies: Optional[int] = Field(None, ge=1, le=100)
    color_mode: Optional[str] = Field(None, pattern="^(blackwhite|color)$")
    paper_size: Optional[str] = Field(None, pattern="^(letter|legal|a4)$")
    double_sided: Optional[bool] = None


class PrintJobResponse(BaseModel):
    id: int
    job_name: str
    job_uid: str
    status: str
    pages: int
    copies: int
    color_mode: str
    paper_size: str
    double_sided: bool
    cost: MoneyDecimal
    cost_breakdown: Optional[Dict] = None
    printer_name: Optional[str] = None
    release_code: Optional[str] = None
    submitted_at: datetime
    completed_at: Optional[datetime] = None
    file_size_bytes: Optional[int] = None
    file_mime_type: Optional[str] = None

    class Config:
        from_attributes = True


class PrintJobListResponse(BaseModel):
    items: List[PrintJobResponse]
    total: int
    page: int
    per_page: int


class PrintCostEstimate(BaseModel):
    pages: int
    copies: int
    color_mode: str
    double_sided: bool
    cost_per_page: MoneyDecimal
    subtotal: MoneyDecimal
    discount: MoneyDecimal = Decimal("0.00")
    total: MoneyDecimal


class PrinterResponse(BaseModel):
    id: int
    name: str
    printer_type: str
    status: str
    location: str
    supports_color: bool
    supports_double_sided: bool
    is_enabled: bool

    class Config:
        from_attributes = True


class PrinterListResponse(BaseModel):
    items: List[PrinterResponse]
    total: int


class PrintReleaseRequest(StrictInputSchema):
    payment_method: Optional[str] = Field(None, pattern="^(account_balance|credit_card|cash)$")


class PrintPreviewResponse(BaseModel):
    job_id: int
    preview_url: Optional[str] = None
    page_count: int
    file_type: Optional[str] = None
