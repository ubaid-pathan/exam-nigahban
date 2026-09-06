import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { downloadRosterCsv, getRosterFilterOptions, getRosterReport } from '../../api/reports'
import { listExams } from '../../api/exams'
import { getErrorMessage } from '../../utils/apiError'
import { sessionStatusBadgeClass, sessionStatusLabel } from '../../utils/sessionStatus'
import { formatDateTimePKT } from '../../utils/dateFormat'
import LoadingState from '../../components/LoadingState'
import ErrorState from '../../components/ErrorState'
import EmptyState from '../../components/EmptyState'

const PAGE_SIZE = 25
const EMPTY_FILTERS = { department: '', className: '', examId: '', sessionStatus: '' }

const SESSION_STATUSES = ['in_progress', 'submitted', 'expired', 'cancelled']

// Monitoring outcomes across a cohort -- a program, a section, an exam --
// rather than one candidate's case. Every attempt is listed, including the
// ones that produced nothing: "monitored, nothing found" is the result for
// most of a healthy roster, and a report that only showed flagged
// candidates could not answer whether a section was monitored at all.
export default function RosterReportPage() {
  const [draft, setDraft] = useState(EMPTY_FILTERS)
  const [applied, setApplied] = useState(EMPTY_FILTERS)
  const [page, setPage] = useState(1)

  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [options, setOptions] = useState({ departments: [], class_names: [] })
  const [exams, setExams] = useState([])
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setReport(await getRosterReport({ ...applied, page, pageSize: PAGE_SIZE }))
    } catch (err) {
      setError(getErrorMessage(err, 'Unable to generate the roster report.'))
    } finally {
      setLoading(false)
    }
  }, [applied, page])

  useEffect(() => {
    load()
  }, [load])

  // Filter values are fetched rather than hard-coded, so the dropdowns
  // only ever offer programs and sections that actually exist.
  useEffect(() => {
    let cancelled = false
    Promise.all([getRosterFilterOptions(), listExams()])
      .then(([filterOptions, examList]) => {
        if (cancelled) return
        setOptions(filterOptions)
        setExams(examList)
      })
      .catch(() => {
        // Losing the dropdown values degrades the filters to "All"; the
        // report itself still works, so this must not surface as an error.
      })
    return () => {
      cancelled = true
    }
  }, [])

  const handleExport = async () => {
    setExporting(true)
    setExportError('')
    try {
      await downloadRosterCsv(applied)
    } catch (err) {
      setExportError(getErrorMessage(err, 'Unable to export the roster as CSV.'))
    } finally {
      setExporting(false)
    }
  }

  const applyFilters = (event) => {
    event.preventDefault()
    setPage(1)
    setApplied(draft)
  }

  const clearFilters = () => {
    setDraft(EMPTY_FILTERS)
    setApplied(EMPTY_FILTERS)
    setPage(1)
  }

  const setField = (field) => (event) =>
    setDraft((current) => ({ ...current, [field]: event.target.value }))

  return (
    <div>
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-4">
        <h1 className="h4 mb-0">Roster Report</h1>
        <div className="d-flex gap-2">
          {/* Fetched as a blob through the authenticated client, not a
              plain <a href>: the endpoint needs the same bearer auth as
              every other admin call, and a browser navigation cannot
              attach that header. Carries the applied filters, so the file
              matches the table on screen. */}
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm"
            disabled={exporting}
            onClick={handleExport}
          >
            {exporting ? 'Preparing...' : 'Export CSV'}
          </button>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => window.print()}
          >
            Print / Save as PDF
          </button>
        </div>
      </div>

      {exportError && (
        <div className="alert alert-danger py-2 small d-print-none" role="alert">
          {exportError}
        </div>
      )}

      <form className="row g-2 align-items-end mb-4 d-print-none" onSubmit={applyFilters}>
        <div className="col-6 col-md-3">
          <label htmlFor="roster-department" className="form-label small">
            Program
          </label>
          <select
            id="roster-department"
            className="form-select form-select-sm"
            value={draft.department}
            onChange={setField('department')}
          >
            <option value="">All</option>
            {options.departments.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </div>

        <div className="col-6 col-md-3">
          <label htmlFor="roster-section" className="form-label small">
            Section
          </label>
          <select
            id="roster-section"
            className="form-select form-select-sm"
            value={draft.className}
            onChange={setField('className')}
          >
            <option value="">All</option>
            {options.class_names.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </div>

        <div className="col-6 col-md-3">
          <label htmlFor="roster-exam" className="form-label small">
            Exam
          </label>
          <select
            id="roster-exam"
            className="form-select form-select-sm"
            value={draft.examId}
            onChange={setField('examId')}
          >
            <option value="">All</option>
            {exams.map((exam) => (
              <option key={exam.id} value={exam.id}>
                {exam.title}
              </option>
            ))}
          </select>
        </div>

        <div className="col-6 col-md-3">
          <label htmlFor="roster-status" className="form-label small">
            Session Status
          </label>
          <select
            id="roster-status"
            className="form-select form-select-sm"
            value={draft.sessionStatus}
            onChange={setField('sessionStatus')}
          >
            <option value="">All</option>
            {SESSION_STATUSES.map((value) => (
              <option key={value} value={value}>
                {sessionStatusLabel(value)}
              </option>
            ))}
          </select>
        </div>

        <div className="col-12 d-flex gap-2">
          <button type="submit" className="btn btn-primary btn-sm">
            Apply
          </button>
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm"
            onClick={clearFilters}
          >
            Clear
          </button>
        </div>
      </form>

      {loading && <LoadingState message="Generating roster report..." />}
      {!loading && error && <ErrorState message={error} onRetry={load} />}

      {!loading && !error && report && (
        <>
          <div className="report__header mb-4">
            <h2 className="report__title">Cohort Monitoring Roster</h2>
            <p className="report__provenance">
              Generated {formatDateTimePKT(report.generated_at)} by {report.generated_by}
            </p>
            <p className="report__notice">
              This report records examination activities flagged by automated monitoring
              and the enforcement recorded against each attempt. Automated monitoring does
              not determine misconduct; a flagged activity becomes a finding only when an
              authorised administrator confirms it.
            </p>
          </div>

          <dl className="report__grid mb-4">
            <dt>Attempts covered</dt>
            <dd>{report.total_sessions}</dd>
            <dt>Attempts with flagged activity</dt>
            <dd>{report.sessions_with_activity}</dd>
            <dt>Total flagged activities</dt>
            <dd>{report.total_flagged_events}</dd>
            <dt>Enforcement actions recorded</dt>
            <dd>{report.total_enforcement_actions}</dd>
          </dl>

          {report.items.length === 0 ? (
            <EmptyState
              title="No attempts match these filters"
              message="No examination attempt matches the selected program, section, exam or status."
            />
          ) : (
            <>
              <div className="table-responsive">
                <table className="report__table">
                  <thead>
                    <tr>
                      <th>Student</th>
                      <th>Program</th>
                      <th>Section</th>
                      <th>Exam</th>
                      <th>Status</th>
                      <th>Score</th>
                      <th>Flagged</th>
                      <th>High</th>
                      <th>Confirmed</th>
                      <th>Pending</th>
                      <th>Enforcement</th>
                      <th className="d-print-none">Report</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.items.map((row) => (
                      <tr key={row.session_id}>
                        <td>
                          {row.student_full_name}
                          <div className="text-muted small">{row.student_id}</div>
                        </td>
                        <td>
                          {row.department || (
                            <span className="text-muted">Not recorded</span>
                          )}
                        </td>
                        <td>
                          {row.class_name || (
                            <span className="text-muted">Not recorded</span>
                          )}
                        </td>
                        <td>{row.exam_title}</td>
                        <td>
                          <span
                            className={`badge ${sessionStatusBadgeClass(row.session_status)}`}
                          >
                            {sessionStatusLabel(row.session_status)}
                          </span>
                        </td>
                        <td>
                          {row.score != null ? (
                            `${row.score}%`
                          ) : (
                            <span className="text-muted">&mdash;</span>
                          )}
                        </td>
                        <td>{row.total_events}</td>
                        <td className={row.high_severity_events > 0 ? 'text-danger fw-semibold' : ''}>
                          {row.high_severity_events}
                        </td>
                        <td>{row.confirmed_events}</td>
                        <td>{row.pending_events}</td>
                        <td>{row.enforcement_actions}</td>
                        <td className="d-print-none">
                          <Link
                            to={`/admin/reports/sessions/${row.session_id}`}
                            className="btn btn-sm btn-outline-secondary"
                          >
                            Open
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="d-flex justify-content-between align-items-center mt-3 d-print-none">
                <p className="text-muted small mb-0">
                  Page {report.page} of {report.total_pages} ({report.total} attempt
                  {report.total === 1 ? '' : 's'})
                </p>
                <div className="d-flex gap-2">
                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm"
                    onClick={() => setPage((current) => Math.max(1, current - 1))}
                    disabled={page <= 1}
                  >
                    Previous
                  </button>
                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm"
                    onClick={() =>
                      setPage((current) =>
                        current < report.total_pages ? current + 1 : current,
                      )
                    }
                    disabled={page >= report.total_pages}
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}
