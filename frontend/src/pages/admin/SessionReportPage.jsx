import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getSessionCaseReport } from '../../api/reports'
import { fetchEvidenceImageBlob } from '../../api/evidence'
import { getErrorMessage } from '../../utils/apiError'
import {
  eventStatusBadgeClass,
  eventStatusLabel,
  eventTypeLabel,
  severityBadgeClass,
  severityLabel,
} from '../../utils/monitoringStatus'
import {
  actionTypeBadgeClass,
  actionTypeLabel,
  enforcementStatusBadgeClass,
  enforcementStatusLabel,
} from '../../utils/enforcementStatus'
import { sessionStatusLabel } from '../../utils/sessionStatus'
import { formatDateTimePKT } from '../../utils/dateFormat'
import LoadingState from '../../components/LoadingState'
import ErrorState from '../../components/ErrorState'

// The examination case report: one student, one session, as a document
// rather than a dashboard. Printing it (Print -> Save as PDF) produces the
// artifact an administrator attaches to a disciplinary file, which is why
// the layout is paginated by a print stylesheet rather than rendered to a
// PDF server-side -- no dependency, and the browser does the hard part.
//
// Evidence images are embedded only for CONFIRMED activities. Illustrating
// an activity an administrator reviewed and dismissed would misrepresent
// the record; those still appear in the table, without a picture.
//
// Language throughout follows CLAUDE.md section 18: this document records
// that the system flagged an activity and that a named administrator
// reached a decision about it. It never asserts that a student cheated.
export default function SessionReportPage() {
  const { sessionId } = useParams()

  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  // evidenceId -> object URL, for the confirmed activities only.
  const [images, setImages] = useState({})

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setReport(await getSessionCaseReport(sessionId))
    } catch (err) {
      setError(getErrorMessage(err, 'Unable to generate this report.'))
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  useEffect(() => {
    load()
  }, [load])

  // The image endpoint requires the same bearer auth as every other admin
  // call, so a plain <img src> cannot fetch it -- each image is pulled as
  // a blob and rendered from an object URL, exactly as
  // EvidenceReviewPanel does for a single image. Every URL created here is
  // revoked on unmount so a long report does not leak them.
  useEffect(() => {
    if (!report) return undefined

    const wanted = report.events
      .filter((event) => event.status === 'CONFIRMED' && event.evidence_id != null)
      .map((event) => event.evidence_id)

    let cancelled = false
    const created = []

    Promise.all(
      wanted.map(async (evidenceId) => {
        try {
          const blob = await fetchEvidenceImageBlob(evidenceId)
          if (cancelled) return null
          const url = URL.createObjectURL(blob)
          created.push(url)
          return [evidenceId, url]
        } catch {
          // A missing image must not break the document; the activity is
          // still listed, and the caption says the image is unavailable.
          return null
        }
      }),
    ).then((pairs) => {
      if (cancelled) return
      setImages(Object.fromEntries(pairs.filter(Boolean)))
    })

    return () => {
      cancelled = true
      created.forEach((url) => URL.revokeObjectURL(url))
    }
  }, [report])

  if (loading) return <LoadingState message="Generating report..." />
  if (error) return <ErrorState message={error} onRetry={load} />
  if (!report) return null

  const { student, exam, session } = report
  const confirmedWithEvidence = report.events.filter(
    (event) => event.status === 'CONFIRMED' && event.evidence_id != null,
  )

  return (
    <div className="report">
      {/* Controls only. The document's own title below is the page
          heading -- repeating it here printed the same line twice. */}
      <div className="report__toolbar d-print-none d-flex justify-content-end gap-2 mb-4">
        <button type="button" className="btn btn-primary" onClick={() => window.print()}>
          Print / Save as PDF
        </button>
      </div>

      <header className="report__header">
        <h1 className="report__title">Examination Case Report</h1>
        <p className="report__provenance">
          Generated {formatDateTimePKT(report.generated_at)} by {report.generated_by}
        </p>
        {/* States the AI/human boundary on the document itself, so it
            cannot be separated from the findings it qualifies. */}
        <p className="report__notice">
          This report records examination activities flagged by automated monitoring and
          the decisions reached by an authorised administrator. Automated monitoring does
          not determine misconduct; every confirmation below was made by the named
          administrator.
        </p>
      </header>

      <section className="report__section">
        <h2 className="report__heading">Candidate</h2>
        <dl className="report__grid">
          <dt>Name</dt>
          <dd>{student.full_name}</dd>
          <dt>Student ID</dt>
          <dd>{student.student_id}</dd>
          <dt>Program</dt>
          <dd>{student.department || <span className="text-muted">Not recorded</span>}</dd>
          <dt>Section</dt>
          <dd>{student.class_name || <span className="text-muted">Not recorded</span>}</dd>
        </dl>
      </section>

      <section className="report__section">
        <h2 className="report__heading">Examination</h2>
        <dl className="report__grid">
          <dt>Exam</dt>
          <dd>{exam.title}</dd>
          <dt>Duration</dt>
          <dd>{exam.duration_minutes} minutes</dd>
          <dt>Session</dt>
          <dd>#{session.id}</dd>
          <dt>Status</dt>
          <dd>{sessionStatusLabel(session.status)}</dd>
          <dt>Started</dt>
          <dd>{formatDateTimePKT(session.started_at)}</dd>
          <dt>Ended</dt>
          <dd>
            {session.ended_at ? (
              formatDateTimePKT(session.ended_at)
            ) : (
              <span className="text-muted">Not ended</span>
            )}
          </dd>
          <dt>Score</dt>
          <dd>
            {session.score != null ? (
              `${session.score}%`
            ) : (
              <span className="text-muted">Not recorded</span>
            )}
          </dd>
        </dl>
      </section>

      <section className="report__section">
        <h2 className="report__heading">Summary</h2>
        <dl className="report__grid">
          <dt>Activities flagged</dt>
          <dd>{report.total_events}</dd>
          <dt>Confirmed by administrator</dt>
          <dd>{report.confirmed_events}</dd>
          <dt>Dismissed by administrator</dt>
          <dd>{report.ignored_events}</dd>
          <dt>Awaiting review</dt>
          <dd>{report.pending_events}</dd>
          <dt>High severity</dt>
          <dd>{report.high_severity_events}</dd>
        </dl>
      </section>

      <section className="report__section">
        <h2 className="report__heading">Flagged activity</h2>
        {report.events.length === 0 ? (
          <p className="report__empty">
            No examination activity was flagged during this session.
          </p>
        ) : (
          <table className="report__table">
            <thead>
              <tr>
                <th>Detected</th>
                <th>Activity</th>
                <th>Severity</th>
                <th>Confidence</th>
                <th>Duration</th>
                <th>Decision</th>
                <th>Decided by</th>
              </tr>
            </thead>
            <tbody>
              {report.events.map((event) => {
                const latest = event.decisions[event.decisions.length - 1]
                return (
                  <tr key={event.id}>
                    <td className="text-nowrap">{formatDateTimePKT(event.detected_at)}</td>
                    <td>{eventTypeLabel(event.event_type)}</td>
                    <td>
                      <span className={`badge ${severityBadgeClass(event.severity)}`}>
                        {severityLabel(event.severity)}
                      </span>
                    </td>
                    <td>{(event.confidence * 100).toFixed(1)}%</td>
                    <td>{Number(event.duration_seconds).toFixed(2)}s</td>
                    <td>
                      <span className={`badge ${eventStatusBadgeClass(event.status)}`}>
                        {eventStatusLabel(event.status)}
                      </span>
                    </td>
                    <td>
                      {latest ? (
                        latest.admin_username
                      ) : (
                        <span className="text-muted">&mdash;</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </section>

      {confirmedWithEvidence.length > 0 && (
        <section className="report__section">
          <h2 className="report__heading">Evidence for confirmed activity</h2>
          <p className="report__note">
            Images are shown only for activities an administrator confirmed. Activities
            that were dismissed or are still awaiting review appear in the table above
            without an image.
          </p>
          <div className="report__evidence">
            {confirmedWithEvidence.map((event) => (
              <figure key={event.id} className="report__figure">
                {images[event.evidence_id] ? (
                  <img
                    src={images[event.evidence_id]}
                    alt={`Evidence captured for ${eventTypeLabel(event.event_type)}`}
                  />
                ) : (
                  <div className="report__figure-missing">Image unavailable</div>
                )}
                <figcaption>
                  <strong>{eventTypeLabel(event.event_type)}</strong>
                  <br />
                  {formatDateTimePKT(event.detected_at)}
                  <br />
                  {event.decisions.length > 0 && (
                    <>
                      Confirmed by {event.decisions[event.decisions.length - 1].admin_username}
                      {event.decisions[event.decisions.length - 1].reason && (
                        <>
                          <br />
                          Reason: {event.decisions[event.decisions.length - 1].reason}
                        </>
                      )}
                    </>
                  )}
                </figcaption>
              </figure>
            ))}
          </div>
        </section>
      )}

      <section className="report__section">
        <h2 className="report__heading">Administrator decisions</h2>
        {report.events.every((event) => event.decisions.length === 0) ? (
          <p className="report__empty">No review decisions have been recorded.</p>
        ) : (
          <table className="report__table">
            <thead>
              <tr>
                <th>Recorded</th>
                <th>Activity</th>
                <th>Decision</th>
                <th>Reason</th>
                <th>Administrator</th>
              </tr>
            </thead>
            <tbody>
              {report.events.flatMap((event) =>
                event.decisions.map((decision) => (
                  <tr key={decision.id}>
                    <td className="text-nowrap">{formatDateTimePKT(decision.created_at)}</td>
                    <td>{eventTypeLabel(event.event_type)}</td>
                    <td>{eventStatusLabel(decision.action)}</td>
                    <td>
                      {decision.reason || <span className="text-muted">Not given</span>}
                    </td>
                    <td>{decision.admin_username}</td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
        )}
      </section>

      <section className="report__section">
        <h2 className="report__heading">Enforcement actions</h2>
        {report.enforcement_actions.length === 0 ? (
          <p className="report__empty">
            No enforcement action was taken against this candidate for this session.
          </p>
        ) : (
          <table className="report__table">
            <thead>
              <tr>
                <th>Recorded</th>
                <th>Action</th>
                <th>State</th>
                <th>Reason</th>
                <th>Administrator</th>
              </tr>
            </thead>
            <tbody>
              {report.enforcement_actions.map((action) => (
                <tr key={action.id}>
                  <td className="text-nowrap">{formatDateTimePKT(action.created_at)}</td>
                  <td>
                    <span className={`badge ${actionTypeBadgeClass(action.action_type)}`}>
                      {actionTypeLabel(action.action_type)}
                    </span>
                  </td>
                  <td>
                    <span
                      className={`badge ${enforcementStatusBadgeClass(action.effective_status)}`}
                    >
                      {enforcementStatusLabel(action.effective_status)}
                    </span>
                  </td>
                  <td>{action.reason}</td>
                  <td>{action.admin_username}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Signature block: the document is only meaningful once a person
          takes responsibility for it, and a printed report needs somewhere
          for that to happen. */}
      <section className="report__section report__signature">
        <div>
          <div className="report__signature-line" />
          <p>Reviewing administrator</p>
        </div>
        <div>
          <div className="report__signature-line" />
          <p>Date</p>
        </div>
      </section>
    </div>
  )
}
