"""Pydantic schemas for access credentials and gate scans."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class IssueTokensRequest(BaseModel):
    reservation_id: uuid.UUID


class IssueTokensResponse(BaseModel):
    reservation_id: uuid.UUID
    entry_token: str
    exit_token: str
    valid_from: datetime
    valid_until: datetime


class ValidateScanRequest(BaseModel):
    opaque_token: str
    guard_id: uuid.UUID | None = None


class ValidateScanResponse(BaseModel):
    status: str
    message: str
    token_type: str
    reservation_id: uuid.UUID
    consumed_at: datetime
