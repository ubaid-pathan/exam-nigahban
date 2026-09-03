"""Centralized monitoring configuration shared by the event-ingestion API.

Mirrors the baseline temporal-rule table in CLAUDE.md / PROJECT_SPEC.md so
thresholds are not duplicated across the codebase. The browser-side temporal
rule engine (frontend/src/monitoring/constants.js) applies these same
baseline values before an event ever reaches the backend; this module is
used here only to validate that an incoming event's type/severity are
recognized, not to re-run temporal logic server-side.
"""

# Face-monitoring activity types (Phase 5B/5C) plus mobile-phone detection
# (YOLO -- Milestone 6 Phase 2 Step 5; the browser-side YOLOX Worker
# pipeline and its own isolated temporal rule engine were added in Steps
# 1-3, frontend-only until this step).
ALLOWED_EVENT_TYPES = {
    "HEAD_LEFT",
    "HEAD_RIGHT",
    "HEAD_UP",
    "HEAD_DOWN",
    "LOOKING_AWAY",
    "FACE_ABSENT",
    "MULTIPLE_FACES",
    "MOBILE_PHONE",
}

ALLOWED_SEVERITIES = {"low", "medium", "high"}

DEFAULT_SEVERITY_BY_EVENT_TYPE = {
    "HEAD_LEFT": "medium",
    "HEAD_RIGHT": "medium",
    "HEAD_UP": "medium",
    "HEAD_DOWN": "medium",
    "LOOKING_AWAY": "medium",
    "FACE_ABSENT": "high",
    "MULTIPLE_FACES": "high",
}

MONITORING_EVENT_SOURCE = "browser_mediapipe"
