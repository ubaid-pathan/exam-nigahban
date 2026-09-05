from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.models import MonitoringRule
from app.db.session import get_db
from app.schemas.monitoring_rule import MonitoringRuleListResponse

router = APIRouter(
    prefix="/api/admin/monitoring/rules",
    tags=["monitoring-rules"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=MonitoringRuleListResponse)
def list_monitoring_rules(
    db: Session = Depends(get_db),
) -> MonitoringRuleListResponse:
    """Return the configured AI-monitoring temporal rules."""
    rules = (
        db.query(MonitoringRule)
        .order_by(MonitoringRule.event_type)
        .all()
    )
    return MonitoringRuleListResponse(items=rules)
