from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.monitoring import EventType, Severity


class MonitoringRuleBase(BaseModel):
    event_type: EventType
    min_duration_seconds: float = Field(ge=0.0)
    required_occurrences: int = Field(ge=1)
    confidence_threshold: float = Field(ge=0.0, le=1.0)
    severity: Severity
    is_active: bool = True
    description: str | None = None


class MonitoringRuleResponse(MonitoringRuleBase):
    """Read-only view of a persisted monitoring rule."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class MonitoringRuleListResponse(BaseModel):
    items: list[MonitoringRuleResponse]
