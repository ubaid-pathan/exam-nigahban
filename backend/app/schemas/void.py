"""Schemas for voiding records.

Voiding is how a record stops having effect without being destroyed. The
request shape reflects the two things that make it defensible: the acting
administrator proves it is really them, and states why.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class VoidRequest(BaseModel):
    # The acting administrator's OWN password, re-entered at the moment of
    # the action. An admin session alone is not enough to remove records
    # from every queue and report; a stolen or unattended session must not
    # be able to. Never logged, never stored, never echoed back.
    password: str = Field(min_length=1)

    # Mandatory and substantive. A voided record keeps this permanently --
    # it is the only account of why something vanished from the audit
    # trail, so "test" is not a useful thing to find here a year later.
    reason: str = Field(min_length=10, max_length=1000)


class VoidedRecordResponse(BaseModel):
    """One voided record, as shown in the system administrator's review of
    what has been removed from the visible record."""

    id: int
    kind: str  # "monitoring_event" | "exam"
    label: str
    voided_at: datetime
    voided_by: str
    void_reason: str


class VoidedRecordListResponse(BaseModel):
    items: list[VoidedRecordResponse]
    total: int
