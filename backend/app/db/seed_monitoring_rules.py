"""Seed default AI-monitoring temporal rules.

These values mirror frontend/src/monitoring/constants.js and the baseline
rule table in CLAUDE.md / PROJECT_SPEC.md.  The seed function is idempotent:
run it as many times as you like; existing rows are updated in place and
missing rows are inserted.
"""

from sqlalchemy.orm import Session

from app.db.models import MonitoringRule


# Baseline MVP temporal rules.  Kept in one place so backend, frontend, and
# documentation all share the same numbers.  The MOBILE_PHONE rule is scoped
# to the YOLOX phone-detection pipeline and uses its own tighter thresholds.
DEFAULT_MONITORING_RULES = [
    {
        "event_type": "HEAD_LEFT",
        "min_duration_seconds": 3.0,
        "required_occurrences": 3,
        "confidence_threshold": 0.75,
        "severity": "medium",
        "description": "Head turned left beyond threshold for a sustained period.",
    },
    {
        "event_type": "HEAD_RIGHT",
        "min_duration_seconds": 3.0,
        "required_occurrences": 3,
        "confidence_threshold": 0.75,
        "severity": "medium",
        "description": "Head turned right beyond threshold for a sustained period.",
    },
    {
        "event_type": "HEAD_UP",
        "min_duration_seconds": 3.0,
        "required_occurrences": 3,
        "confidence_threshold": 0.75,
        "severity": "medium",
        "description": "Head tilted up beyond threshold for a sustained period.",
    },
    {
        "event_type": "HEAD_DOWN",
        "min_duration_seconds": 3.0,
        "required_occurrences": 3,
        "confidence_threshold": 0.75,
        "severity": "medium",
        "description": "Head tilted down beyond threshold for a sustained period.",
    },
    {
        "event_type": "LOOKING_AWAY",
        "min_duration_seconds": 3.0,
        "required_occurrences": 3,
        "confidence_threshold": 0.75,
        "severity": "medium",
        "description": "Head/gaze oriented away from the screen beyond threshold.",
    },
    {
        "event_type": "FACE_ABSENT",
        "min_duration_seconds": 3.0,
        "required_occurrences": 1,
        "confidence_threshold": 0.5,
        "severity": "high",
        "description": "No face visible in frame for a sustained period.",
    },
    {
        "event_type": "MULTIPLE_FACES",
        "min_duration_seconds": 2.0,
        "required_occurrences": 1,
        "confidence_threshold": 0.5,
        "severity": "high",
        "description": "More than one face visible in frame.",
    },
    {
        "event_type": "MOBILE_PHONE",
        "min_duration_seconds": 1.0,
        "required_occurrences": 1,
        "confidence_threshold": 0.8,
        "severity": "high",
        "description": "Mobile phone detected in frame by YOLOX pipeline.",
    },
]


def seed_monitoring_rules(db: Session) -> tuple[int, int]:
    """Upsert default monitoring rules and return (inserted, updated) counts.

    Existing rows are matched by event_type; their configuration values are
    refreshed from DEFAULT_MONITORING_RULES so seeding is repeatable after
    rule changes.  Rows removed from DEFAULT_MONITORING_RULES are left alone.
    """
    inserted = 0
    updated = 0

    existing_by_type = {
        rule.event_type: rule
        for rule in db.query(MonitoringRule).all()
    }

    for defaults in DEFAULT_MONITORING_RULES:
        event_type = defaults["event_type"]
        existing = existing_by_type.get(event_type)

        if existing is None:
            db.add(MonitoringRule(**defaults))
            inserted += 1
        else:
            existing.min_duration_seconds = defaults["min_duration_seconds"]
            existing.required_occurrences = defaults["required_occurrences"]
            existing.confidence_threshold = defaults["confidence_threshold"]
            existing.severity = defaults["severity"]
            existing.description = defaults["description"]
            # is_active is intentionally left alone so a disabled rule isn't
            # silently re-enabled every time init_db runs.
            updated += 1

    db.commit()
    return inserted, updated
