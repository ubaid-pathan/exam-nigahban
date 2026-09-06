"""Report generation for administrators.

Read-only throughout: a report never changes what it describes.

Cost is four queries regardless of how much activity a session produced --
session context, flagged activities, the decisions on them, and enforcement
-- rather than one query per activity.
"""

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.api.routes.enforcement import _effective_status
from app.db.models import (
    AdminAction,
    EnforcementAction,
    Evidence,
    Exam,
    ExamSession,
    MonitoringEvent,
    Student,
    User,
)
from app.db.session import get_db
from app.schemas.report import (
    ReportDecision,
    ReportEnforcement,
    ReportEvent,
    ReportExam,
    ReportSession,
    ReportStudent,
    RosterFilterOptions,
    RosterReport,
    RosterRow,
    SessionCaseReport,
)

router = APIRouter(
    prefix="/api/reports",
    tags=["reports"],
    dependencies=[Depends(require_admin)],
)


@router.get("/sessions/{session_id}", response_model=SessionCaseReport)
def get_session_case_report(
    session_id: int,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SessionCaseReport:
    """The complete record of one student's exam session.

    Combines the flagged activities, the evidence captured for them, every
    administrator decision, and every enforcement action into the single
    document a disciplinary process needs. Ordered chronologically, because
    a case is read as a sequence of events rather than as a set of counts.

    Nothing here asserts wrongdoing: the report states what the system
    flagged and what a named administrator decided about it.
    """
    row = (
        db.query(ExamSession, Student, Exam)
        .join(Student, Student.id == ExamSession.student_id)
        .join(Exam, Exam.id == ExamSession.exam_id)
        .filter(ExamSession.id == session_id)
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam session not found",
        )

    session_row, student, exam = row

    # Evidence is unique per event, so this outer join cannot duplicate rows.
    event_rows = (
        db.query(MonitoringEvent, Evidence.id.label("evidence_id"))
        .outerjoin(Evidence, Evidence.event_id == MonitoringEvent.id)
        .filter(MonitoringEvent.session_id == session_id)
        .order_by(MonitoringEvent.detected_at, MonitoringEvent.id)
        .all()
    )
    event_ids = [event.id for event, _ in event_rows]

    decisions_by_event: dict[int, list[ReportDecision]] = {}
    if event_ids:
        decision_rows = (
            db.query(AdminAction, User.username)
            .join(User, User.id == AdminAction.admin_id)
            .filter(AdminAction.event_id.in_(event_ids))
            .order_by(AdminAction.created_at, AdminAction.id)
            .all()
        )
        for action, admin_username in decision_rows:
            decisions_by_event.setdefault(action.event_id, []).append(
                ReportDecision(
                    id=action.id,
                    action=action.action,
                    reason=action.reason,
                    admin_username=admin_username,
                    created_at=action.created_at,
                )
            )

    events = [
        ReportEvent(
            id=event.id,
            event_type=event.event_type,
            severity=event.severity,
            confidence=event.confidence,
            duration_seconds=event.duration_seconds,
            occurrences=event.occurrences,
            detected_at=event.detected_at,
            status=event.status,
            source=event.source,
            evidence_id=evidence_id,
            decisions=decisions_by_event.get(event.id, []),
        )
        for event, evidence_id in event_rows
    ]

    enforcement_rows = (
        db.query(EnforcementAction, User.username)
        .join(User, User.id == EnforcementAction.admin_id)
        .filter(EnforcementAction.session_id == session_id)
        .order_by(EnforcementAction.created_at, EnforcementAction.id)
        .all()
    )
    enforcement_actions = [
        ReportEnforcement(
            id=action.id,
            action_type=action.action_type,
            reason=action.reason,
            status=action.status,
            effective_status=_effective_status(action),
            blocked_until=action.blocked_until,
            created_at=action.created_at,
            admin_username=admin_username,
            event_id=action.event_id,
        )
        for action, admin_username in enforcement_rows
    ]

    return SessionCaseReport(
        generated_at=datetime.utcnow(),
        generated_by=current_admin.username,
        student=ReportStudent(
            student_id=student.student_id,
            full_name=student.full_name,
            department=student.department,
            class_name=student.class_name,
        ),
        exam=ReportExam(
            id=exam.id,
            title=exam.title,
            duration_minutes=exam.duration_minutes,
        ),
        session=ReportSession(
            id=session_row.id,
            status=session_row.status,
            started_at=session_row.started_at,
            ended_at=session_row.ended_at,
            score=session_row.score,
        ),
        total_events=len(events),
        confirmed_events=sum(1 for e in events if e.status == "CONFIRMED"),
        ignored_events=sum(1 for e in events if e.status == "IGNORED"),
        pending_events=sum(1 for e in events if e.status == "PENDING_REVIEW"),
        high_severity_events=sum(1 for e in events if e.severity == "high"),
        events=events,
        enforcement_actions=enforcement_actions,
    )


# Hard ceiling on a CSV export. An unbounded export of a large institution
# would build the whole file in memory; this keeps the endpoint predictable
# while comfortably covering any realistic cohort.
CSV_EXPORT_LIMIT = 5000


def _roster_query(
    db: Session,
    department: str | None,
    class_name: str | None,
    exam_id: int | None,
    session_status: str | None,
):
    """The roster's base query, shared by the JSON and CSV endpoints.

    Activity and enforcement counts come from grouped SUBQUERIES that are
    LEFT JOINed, rather than from joining those rows directly. That matters
    for two reasons: joining both tables at once would multiply their rows
    against each other and inflate every count, and an inner join would
    silently drop sessions with no flagged activity -- which are exactly
    the rows a cohort report exists to show.
    """
    activity = (
        db.query(
            MonitoringEvent.session_id.label("session_id"),
            func.count(MonitoringEvent.id).label("total_events"),
            func.sum(case((MonitoringEvent.severity == "high", 1), else_=0)).label(
                "high_severity_events"
            ),
            func.sum(case((MonitoringEvent.status == "CONFIRMED", 1), else_=0)).label(
                "confirmed_events"
            ),
            func.sum(
                case((MonitoringEvent.status == "PENDING_REVIEW", 1), else_=0)
            ).label("pending_events"),
        )
        .group_by(MonitoringEvent.session_id)
        .subquery()
    )

    enforcement = (
        db.query(
            EnforcementAction.session_id.label("session_id"),
            func.count(EnforcementAction.id).label("enforcement_actions"),
        )
        .group_by(EnforcementAction.session_id)
        .subquery()
    )

    query = (
        db.query(
            ExamSession,
            Student,
            Exam,
            func.coalesce(activity.c.total_events, 0).label("total_events"),
            func.coalesce(activity.c.high_severity_events, 0).label(
                "high_severity_events"
            ),
            func.coalesce(activity.c.confirmed_events, 0).label("confirmed_events"),
            func.coalesce(activity.c.pending_events, 0).label("pending_events"),
            func.coalesce(enforcement.c.enforcement_actions, 0).label(
                "enforcement_actions"
            ),
        )
        .join(Student, Student.id == ExamSession.student_id)
        .join(Exam, Exam.id == ExamSession.exam_id)
        .outerjoin(activity, activity.c.session_id == ExamSession.id)
        .outerjoin(enforcement, enforcement.c.session_id == ExamSession.id)
    )

    if department is not None:
        query = query.filter(Student.department == department)
    if class_name is not None:
        query = query.filter(Student.class_name == class_name)
    if exam_id is not None:
        query = query.filter(Exam.id == exam_id)
    if session_status is not None:
        query = query.filter(ExamSession.status == session_status)

    return query.order_by(
        Student.department, Student.class_name, Student.full_name, ExamSession.id
    )


def _to_roster_row(row) -> RosterRow:
    session_row, student, exam = row[0], row[1], row[2]
    return RosterRow(
        session_id=session_row.id,
        session_status=session_row.status,
        started_at=session_row.started_at,
        ended_at=session_row.ended_at,
        score=session_row.score,
        student_id=student.student_id,
        student_full_name=student.full_name,
        department=student.department,
        class_name=student.class_name,
        exam_id=exam.id,
        exam_title=exam.title,
        total_events=int(row.total_events or 0),
        high_severity_events=int(row.high_severity_events or 0),
        confirmed_events=int(row.confirmed_events or 0),
        pending_events=int(row.pending_events or 0),
        enforcement_actions=int(row.enforcement_actions or 0),
    )


@router.get("/roster/filters", response_model=RosterFilterOptions)
def get_roster_filter_options(db: Session = Depends(get_db)) -> RosterFilterOptions:
    """The program and section values present in the student roster.

    Returned so the report's filters offer values that actually exist. It
    also makes inconsistent data visible: a program recorded under two
    spellings appears twice here, rather than silently splitting a cohort
    report into two groups.

    NULLs are excluded: "not recorded" is the absence of a value, not a
    cohort to filter by, and the roster rows report those explicitly.
    """
    departments = [
        value
        for (value,) in db.query(Student.department)
        .filter(Student.department.isnot(None))
        .distinct()
        .order_by(Student.department)
        .all()
    ]
    class_names = [
        value
        for (value,) in db.query(Student.class_name)
        .filter(Student.class_name.isnot(None))
        .distinct()
        .order_by(Student.class_name)
        .all()
    ]
    return RosterFilterOptions(departments=departments, class_names=class_names)


@router.get("/roster", response_model=RosterReport)
def get_roster_report(
    department: str | None = None,
    class_name: str | None = None,
    exam_id: int | None = None,
    session_status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> RosterReport:
    """Monitoring outcomes across a cohort: a program, a section, an exam.

    One row per candidate attempt, including attempts that produced no
    flagged activity at all -- a cohort report has to be able to state
    "monitored, nothing found", which is most of any healthy roster.

    Totals describe every row matching the filters rather than the current
    page, since a cohort report is read for its aggregate first.
    """
    rows = _roster_query(db, department, class_name, exam_id, session_status).all()
    items = [_to_roster_row(row) for row in rows]

    total = len(items)
    start = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size

    return RosterReport(
        generated_at=datetime.utcnow(),
        generated_by=current_admin.username,
        items=items[start : start + page_size],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        total_sessions=total,
        sessions_with_activity=sum(1 for i in items if i.total_events > 0),
        total_flagged_events=sum(i.total_events for i in items),
        total_enforcement_actions=sum(i.enforcement_actions for i in items),
    )


@router.get("/roster.csv")
def export_roster_csv(
    department: str | None = None,
    class_name: str | None = None,
    exam_id: int | None = None,
    session_status: str | None = None,
    db: Session = Depends(get_db),
) -> Response:
    """The same roster as a CSV download, for analysis outside the system.

    Written with the standard library csv module -- no new dependency --
    and capped at CSV_EXPORT_LIMIT rows so the response stays bounded.
    Missing program/section values are written as "Not recorded" rather
    than as blanks, so a spreadsheet cannot quietly group them together
    with real values.
    """
    rows = (
        _roster_query(db, department, class_name, exam_id, session_status)
        .limit(CSV_EXPORT_LIMIT)
        .all()
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "Student ID",
            "Name",
            "Program",
            "Section",
            "Exam",
            "Session ID",
            "Session Status",
            "Started",
            "Ended",
            "Score",
            "Flagged Activities",
            "High Severity",
            "Confirmed",
            "Awaiting Review",
            "Enforcement Actions",
        ]
    )
    for row in rows:
        item = _to_roster_row(row)
        writer.writerow(
            [
                item.student_id,
                item.student_full_name,
                item.department or "Not recorded",
                item.class_name or "Not recorded",
                item.exam_title,
                item.session_id,
                item.session_status,
                item.started_at.isoformat(sep=" ", timespec="seconds"),
                item.ended_at.isoformat(sep=" ", timespec="seconds")
                if item.ended_at
                else "",
                "" if item.score is None else item.score,
                item.total_events,
                item.high_severity_events,
                item.confirmed_events,
                item.pending_events,
                item.enforcement_actions,
            ]
        )

    filename = f"exam-nigahban-roster-{datetime.utcnow():%Y%m%d-%H%M%S}.csv"
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
