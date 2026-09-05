# Exam Nigahban — Development Tasks

## Project Status

- Phase: Core development complete (Phases 1-7); polish and hardening remain (Phases 8-10)
- Status: Deployed to production and verified live (Vercel frontend, Render backend, Neon PostgreSQL)
- Current Milestone: Post-deployment hardening — UI/UX polish, security review, demo readiness
- Development Model: Incremental, test-driven, Git checkpoint based
- Primary Coding Agent: Claude Code
- Source of Truth: `PROJECT_SPEC.md` and `CLAUDE.md`

---

# Phase 1 — Foundation

## Repository & Development Setup

- [x] Verify repository structure
- [x] Initialize Git repository
- [x] Create project directory structure
- [x] Create backend directory
- [x] Create frontend directory
- [x] Create AI directory
- [x] Create database directory
- [x] Create documentation directory
- [x] Create evidence directory
- [x] Create tests directory
- [x] Create Python virtual environment
- [x] Configure environment variables
- [x] Configure `.env` loading
- [x] Configure `.env.example`
- [x] Verify `.gitignore` (verified: `.env` files ignored, never committed)
- [x] Verify no secrets are committed (verified via `git log --all -S` sweep: no DB passwords or SECRET_KEY values in history)
- [ ] Finalize `PROJECT_SPEC.md`
- [ ] Finalize `CLAUDE.md`
- [ ] Finalize `TASKS.md`

## Frontend Foundation

- [x] Initialize React + Vite
- [x] Configure JavaScript environment
- [x] Install Bootstrap 5.3
- [x] Configure Axios
- [x] Configure React Router
- [x] Establish frontend folder structure
- [x] Create base application layout
- [x] Create reusable UI components structure
- [x] Configure frontend environment variables
- [x] Implement frontend API client
- [x] Implement frontend health-check connection

## Backend Foundation

- [x] Initialize FastAPI application
- [x] Configure Python environment
- [x] Configure application settings
- [x] Configure MySQL connection
- [x] Configure SQLAlchemy
- [x] Create database base
- [x] Create database session
- [x] Create initial models
- [x] Create database tables
- [x] Implement `/health`
- [x] Verify Swagger/OpenAPI
- [x] Establish API router structure (`app/api/routes/`, 11 routers)
- [x] Establish service layer structure (`app/services/`)
- [x] Establish schema structure (`app/schemas/`)
- [x] Establish WebSocket structure (`app/websocket/`)
- [x] Establish error-handling structure (HTTPException responses + frontend `apiError` utilities)
- [x] Establish logging structure (`app/core/logging.py`)

## Database Foundation

- [x] Create `users` table
- [x] Create `students` table
- [x] Create `exams` table
- [x] Create `questions` table
- [x] Create `exam_sessions` table
- [x] Create `student_answers` table
- [x] Create `monitoring_rules` table (global rules only; per-exam customization removed by design)
- [x] Create `monitoring_events` table
- [x] Create `evidence` table
- [x] Create `admin_actions` table
- [ ] Create `system_logs` table (not implemented; audit needs are covered by `admin_actions` plus application logging — add only if a separate system-event log is ever required)
- [x] Verify foreign-key relationships
- [x] Verify indexes and unique constraints
- [x] Verify database initialization (`init_db.py`, exercised on local MySQL and production Neon)
- [x] Prepare database seed data (`seed_monitoring_rules`, `seed_demo_data` — both idempotent)

## Foundation Verification

- [x] Verify backend starts successfully
- [x] Verify MySQL connection
- [x] Verify database metadata registration
- [x] Verify health endpoint
- [x] Verify frontend starts successfully
- [x] Verify frontend-to-backend communication
- [x] Verify CORS configuration
- [x] Verify WebSocket connection structure
- [x] Run foundation tests (273 backend + 190 frontend tests passing)
- [x] Review project structure
- [x] Commit Foundation milestone

---

# Phase 2 — Authentication & User Management

## Authentication Backend

- [x] Create authentication schemas
- [x] Implement secure password hashing
- [x] Implement password verification
- [x] Implement login endpoint
- [x] Implement logout
- [x] Implement current-user endpoint
- [x] Implement authentication/session or token management
- [x] Implement authentication expiration
- [x] Implement invalid credential handling
- [x] Implement inactive-account handling

## Authorization

- [x] Implement role validation
- [x] Implement protected API dependencies
- [x] Implement admin-only authorization
- [x] Implement student-only authorization
- [x] Prevent students from accessing admin APIs
- [x] Prevent unauthorized resource access (session/answer/evidence ownership enforced and tested)
- [x] Verify backend authorization independently of frontend

## Administrator Management

- [x] Create administrator account
- [x] View administrator accounts
- [x] Update administrator account
- [x] Activate/deactivate administrator account
- [x] Validate administrator permissions

## Student Management

- [x] Create student account
- [x] Generate/store student profile
- [x] View students
- [x] View student details
- [x] Update student details
- [x] Activate/deactivate student
- [x] Prevent student self-registration
- [x] Validate student ownership and access

## Authentication Frontend

- [x] Create login page
- [x] Create login form validation
- [x] Implement authentication state
- [x] Implement protected routes
- [x] Implement role-based route handling
- [x] Implement logout
- [x] Implement authentication error states

## Authentication Testing

- [x] Test valid login
- [x] Test invalid login
- [x] Test inactive account
- [x] Test unauthorized API access
- [x] Test student/admin role restrictions
- [x] Test logout
- [ ] Test expired authentication
- [x] Test protected frontend routes

## Git Checkpoint

- [x] Commit Authentication milestone

---

# Phase 3 — Examination Management

## Examination Backend

- [x] Create exam schemas
- [x] Create exam API router
- [x] Implement exam creation
- [x] Implement exam listing
- [x] Implement exam detail
- [x] Implement exam update
- [x] Implement exam activation/deactivation
- [x] Implement exam deletion where appropriate
- [x] Validate exam ownership and authorization

## Question Management

- [x] Create question schemas
- [x] Create question API router
- [x] Implement question creation
- [x] Implement question listing
- [x] Implement question update
- [x] Implement question deletion
- [x] Validate question data
- [x] Prevent correct answers from being exposed unnecessarily

## Examination Sessions

- [x] Create exam-session service (ownership/state logic lives in `app/api/routes/student_exams.py`, the project's convention in lieu of a separate service file)
- [x] Create exam-session API
- [x] Implement session creation
- [x] Implement session start
- [x] Implement session state management
- [x] Implement session timeout
- [x] Implement session completion
- [x] Implement session submission
- [x] Prevent duplicate active sessions where required
- [x] Validate student session ownership

## Student Answers

- [x] Create answer schemas
- [x] Implement answer submission
- [x] Implement answer update
- [x] Validate answer ownership
- [x] Prevent access to other students' answers
- [x] Preserve submitted answers

## Result Calculation

- [x] Implement score calculation
- [x] Calculate result after submission
- [x] Store result
- [x] Return appropriate result/status
- [x] Prevent unauthorized result modification

## Examination Testing

- [x] Test exam CRUD
- [x] Test question CRUD
- [x] Test session creation
- [x] Test session lifecycle
- [x] Test answer submission
- [x] Test answer ownership
- [x] Test exam submission
- [x] Test result calculation

## Git Checkpoint

- [x] Commit Examination milestone

---

# Phase 4 — Student Examination Workflow

## Terms & Conditions

- [x] Create Terms & Conditions screen
- [x] Display examination requirements
- [x] Require explicit acceptance
- [ ] Record acceptance where required
- [x] Prevent continuation without acceptance

## Camera Permission

- [x] Request browser camera permission
- [x] Detect permission status
- [x] Handle permission denied
- [x] Handle unavailable camera
- [x] Provide retry workflow
- [x] Prevent exam start without required camera access

## Pre-Exam System Check

- [x] Create system-check screen
- [x] Verify camera availability
- [x] Verify camera stream
- [ ] Verify face visibility
- [ ] Verify AI readiness
- [x] Display check status
- [x] Provide retry controls
- [x] Prevent exam start when required checks fail

## Student Examination Interface

- [x] Create examination layout
- [x] Display question
- [x] Display answer options
- [x] Implement question navigation
- [x] Implement current-question indicator
- [x] Implement examination timer
- [x] Preserve selected answers
- [x] Implement submit confirmation
- [x] Implement examination submission
- [x] Implement submission confirmation screen

## Student Workflow Testing

- [x] Test complete student workflow
- [x] Test terms acceptance
- [x] Test camera permission
- [x] Test failed system check
- [x] Test successful system check
- [x] Test exam start
- [x] Test navigation
- [x] Test timer
- [x] Test answer persistence
- [x] Test submission

## Git Checkpoint

- [x] Commit Student Examination milestone

---

# Phase 5 — AI Monitoring Foundation

## Webcam Integration

- [x] Implement browser webcam access
- [x] Create camera preview component
- [x] Handle camera initialization
- [x] Handle camera errors
- [ ] Handle camera disconnection (mid-stream device unplug is not explicitly detected; only initial permission/availability failures are handled)
- [x] Release camera resources correctly
- [x] Prevent unnecessary video upload

## Face Monitoring

- [x] Integrate MediaPipe Face Landmarker
- [x] Implement face presence detection
- [x] Implement facial landmark processing
- [x] Implement head-pose estimation
- [x] Implement head-left detection
- [x] Implement head-right detection
- [x] Implement head-up detection
- [x] Implement head-down detection
- [x] Implement looking-away detection
- [x] Implement temporal smoothing

## Face Absence

- [x] Detect face absence
- [x] Track absence duration
- [x] Apply configured threshold
- [x] Generate event when threshold is satisfied

## Multiple Faces

- [x] Detect multiple faces
- [x] Track persistence
- [x] Apply configured threshold
- [x] Generate event when threshold is satisfied

## Mobile Phone Detection

Delivered in Milestone 6: YOLOX-nano ONNX inference runs in a Web Worker in the student's browser (`frontend/src/monitoring/objectDetection/`, wired into `TakeExamPage` via `useMobilePhoneMonitoring`), with server-side rule validation via the `MOBILE_PHONE` monitoring rule and `source: "browser_yolox"` event tagging.

- [x] Integrate YOLO inference
- [x] Load required model
- [x] Detect mobile phone class
- [x] Filter predictions to mobile phone only
- [x] Apply confidence threshold
- [x] Apply approximately 1-second persistence
- [x] Generate monitoring event when rule is satisfied

## AI Monitoring Rules

Superseded: thresholds now live in the backend-owned `monitoring_rules` table (seeded from `app/core/monitoring_constants.py` by `init_db.py`), and every posted monitoring event is validated against the configured global rule server-side. The frontend constants remain the detection-side source for the browser temporal rule engine. Per-exam rule customization was built, evaluated, and deliberately removed; rules are a fixed global configuration.

- [x] Create monitoring rule model
- [x] Create monitoring rule schema
- [x] Create monitoring rule API/service (admin-only `GET /api/admin/monitoring/rules` listing)
- [x] Configure activity types
- [x] Configure minimum duration
- [x] Configure required occurrences
- [x] Configure confidence threshold
- [x] Configure severity
- [ ] Enable/disable rules (`is_active` is enforced by event validation, but there is no admin toggle API — optional future work now that rules are global-by-design)

## Temporal Rule Engine

- [x] Create temporal monitoring service
- [x] Track detection duration
- [x] Track occurrences
- [x] Track confidence
- [x] Apply temporal smoothing
- [x] Prevent duplicate continuous events
- [x] Apply configured rule thresholds
- [x] Generate structured monitoring events

## AI Testing

- [x] Test face detection
- [x] Test head-left detection
- [x] Test head-right detection
- [x] Test head-up detection
- [x] Test head-down detection
- [x] Test looking-away detection
- [x] Test face absence
- [x] Test multiple faces
- [x] Test mobile phone detection (useMobilePhoneMonitoring, phoneObservation, and objectDetection suites)
- [x] Test confidence thresholds
- [x] Test duration thresholds
- [x] Test occurrence thresholds
- [x] Test false-positive scenarios

## Git Checkpoint

- [x] Commit AI Monitoring milestone

---

# Phase 6 — Monitoring Events & Evidence

## Monitoring Events

Delivered early, as part of the Phase 5 AI Monitoring Foundation milestone (needed so the browser-side temporal rule engine had somewhere to persist stabilized events for future admin review):

- [x] Create monitoring event model (`backend/app/models/monitoring_event.py`)
- [x] Create monitoring event schema (`backend/app/schemas/monitoring.py`)
- [x] Create monitoring event service (ownership/validation logic lives directly in `backend/app/api/routes/monitoring.py`, consistent with how `student_exams.py` also has no separate service-layer file)
- [x] Store activity type
- [x] Store confidence
- [x] Store duration
- [x] Store occurrence count
- [x] Store severity
- [x] Store detection timestamp
- [x] Store event status
- [ ] Generate unique event ID (uses the existing auto-increment integer PK convention used by every other table in this schema, not a formatted `EVT-...` display ID)

## Evidence Capture

- [x] Create evidence service (`app/services/evidence_storage.py`)
- [x] Capture evidence image when rule triggers
- [x] Avoid unnecessary duplicate captures (one capture per rule-satisfied event; events deduplicated upstream by the temporal rule engine)
- [x] Store evidence path
- [x] Store evidence timestamp
- [x] Store evidence metadata (including base64 fallback payload for ephemeral filesystems)
- [x] Associate evidence with monitoring event
- [x] Implement evidence filesystem abstraction

## Evidence API

- [x] Create evidence schemas
- [x] Create evidence router
- [x] List evidence
- [x] View evidence details
- [x] Retrieve evidence securely (admin-only, JWT-gated image endpoint)
- [x] Filter evidence (event_id / session_id)
- [x] Validate evidence authorization

## Evidence Review

- [x] Implement PENDING_REVIEW status
- [x] Implement CONFIRMED status
- [x] Implement IGNORED status
- [x] Implement evidence confirmation
- [x] Implement evidence dismissal
- [x] Allow review reason
- [x] Prevent students from reviewing evidence

## Evidence Testing

- [x] Test event generation
- [x] Test evidence capture
- [x] Test evidence storage
- [x] Test evidence retrieval
- [x] Test evidence authorization
- [x] Test evidence review
- [x] Test duplicate-event prevention

## Git Checkpoint

- [x] Commit Evidence milestone

---

# Phase 7 — Real-Time Monitoring & Administration

## WebSocket

- [x] Implement WebSocket endpoint
- [x] Implement connection handling
- [x] Implement disconnection handling
- [x] Implement authentication for WebSocket access (JWT via query param)
- [x] Broadcast monitoring events to authorized administrators
- [x] Broadcast evidence notifications
- [x] Handle reconnect where practical (frontend auto-reconnect with live-connection indicator)
- [x] Prevent unauthorized WebSocket access

## Admin Dashboard

- [x] Create dashboard layout
- [x] Display active examinations
- [x] Display active students
- [x] Display pending alerts
- [x] Display high-severity events
- [x] Display recent events
- [x] Display monitoring statistics
- [x] Implement dashboard loading state
- [x] Implement dashboard empty state
- [x] Implement dashboard error state

## Live Monitoring

- [x] Create live monitoring screen (Monitoring Events page + live alert indicator)
- [x] Display active examination sessions
- [x] Display student information
- [x] Display monitoring status
- [x] Display latest alert
- [x] Display severity
- [x] Display event count
- [x] Display latest event time
- [x] Update alerts in real time

## Evidence Center

Delivered within the Monitoring Events page (event queue with status/event-type/session filters + `EvidenceReviewPanel` detail/review view) rather than as a separate screen; richer evidence-level filters remain open below.

- [x] Create evidence center
- [x] Display evidence list
- [ ] Implement student filter
- [ ] Implement exam filter
- [ ] Implement activity filter
- [ ] Implement severity filter
- [ ] Implement status filter
- [ ] Implement timestamp sorting
- [x] Implement evidence detail view

## Administrative Actions

- [x] Implement evidence confirmation
- [x] Implement evidence dismissal
- [x] Store administrator action
- [x] Store optional reason
- [x] Validate administrator authorization

## Audit History

- [x] Create admin-actions model
- [x] Create audit service (listing/query logic in `app/api/routes/audit.py`)
- [x] Record evidence review actions
- [ ] Record account actions
- [ ] Record examination actions
- [ ] Record question actions
- [ ] Record monitoring-rule changes (moot: rules are now static global configuration with no admin editing surface)
- [x] Create audit history API
- [x] Create audit history UI

## Real-Time Testing

- [x] Test WebSocket connection
- [x] Test monitoring event delivery
- [x] Test evidence notification
- [x] Test admin dashboard updates
- [x] Test unauthorized WebSocket access
- [x] Test reconnect behavior

## Git Checkpoint

- [x] Commit Real-Time Administration milestone

---

# Phase 8 — UI/UX & Design System

## Design System

- [ ] Finalize application color palette
- [ ] Finalize typography
- [ ] Finalize spacing system
- [ ] Finalize button styles
- [ ] Finalize form styles
- [ ] Finalize card styles
- [ ] Finalize table styles
- [ ] Finalize badge styles
- [ ] Finalize alert styles
- [ ] Finalize modal styles
- [ ] Create reusable UI components

## Student UI

- [x] Login screen
- [x] Terms & Conditions screen
- [x] Camera permission screen
- [x] System readiness screen
- [x] Exam instructions screen
- [x] Active examination screen
- [x] Submission confirmation
- [x] Result/status screen

## Administrator UI

- [x] Admin login
- [x] Dashboard
- [x] Live monitoring
- [x] Evidence center
- [x] Evidence detail/review
- [x] Student management
- [x] Exam management
- [x] Question management
- [x] Examination sessions (active sessions surfaced on the dashboard and monitoring queue)
- [ ] Monitoring settings (removed by design — monitoring rules are a fixed global configuration; see the `monitoring_rules` table)
- [x] Audit history

## Responsive Design

- [ ] Desktop layout
- [ ] Laptop layout
- [ ] Tablet compatibility where practical
- [ ] Responsive tables
- [ ] Responsive forms
- [ ] Responsive navigation
- [ ] Responsive evidence views

## UI States

- [x] Loading states (`LoadingState` component across pages)
- [x] Empty states (`EmptyState` component across pages)
- [ ] Success states
- [x] Error states (`ErrorState` component + `apiError` utilities)
- [ ] Retry states
- [x] Confirmation dialogs (`ConfirmModal` component)
- [ ] Toast/notification feedback

## Accessibility

- [ ] Keyboard navigation
- [ ] Visible focus states
- [ ] Sufficient contrast
- [ ] Clear form labels
- [ ] Accessible buttons
- [ ] Do not rely only on color for status
- [ ] Accessible error messages

## Visual Review

- [ ] Review spacing consistency
- [ ] Review typography consistency
- [ ] Review component consistency
- [ ] Review icon consistency
- [ ] Review alert terminology
- [ ] Remove unnecessary visual complexity
- [ ] Final visual consistency review

## Git Checkpoint

- [ ] Commit UI/UX milestone

---

# Phase 9 — Security, Privacy & Performance

## Security

- [ ] Review authentication security
- [ ] Review authorization
- [ ] Review password handling
- [ ] Review API validation
- [ ] Review evidence authorization
- [ ] Review session ownership
- [ ] Review student data isolation
- [ ] Review admin permissions
- [ ] Review WebSocket authorization
- [x] Verify `.env` is ignored
- [x] Verify no secrets in source code
- [ ] Review error-message exposure

## Privacy

- [x] Verify no continuous webcam recording (feed is processed browser-side; only a single JPEG frame is captured when a rule is satisfied)
- [x] Verify evidence is generated only when required (capture happens only for rule-validated events carrying an image)
- [x] Verify evidence access restrictions (admin-only endpoints, student access returns 403 — tested)
- [ ] Verify unnecessary personal data is not collected
- [ ] Review evidence retention approach
- [ ] Review sensitive data handling

## Performance

- [ ] Review frontend rendering performance
- [ ] Review API response performance
- [ ] Review database queries
- [ ] Review AI inference performance
- [ ] Review browser CPU/memory usage
- [ ] Review evidence capture overhead
- [ ] Review WebSocket performance
- [ ] Prevent unnecessary network traffic

## Git Checkpoint

- [ ] Commit Security & Performance milestone

---

# Phase 10 — Testing & Hackathon Readiness

## Unit Testing

- [x] Authentication tests
- [x] Authorization tests
- [x] Exam tests
- [x] Question tests (within `test_exams.py`)
- [x] Session tests
- [x] Answer tests
- [x] Monitoring rule tests
- [x] Temporal rule tests
- [x] Evidence tests
- [x] Audit tests

## Integration Testing

- [x] Authentication API integration
- [x] Student management integration
- [x] Exam management integration
- [x] Examination session integration
- [x] Monitoring event integration
- [x] Evidence integration
- [x] WebSocket integration

## End-to-End Testing

- [ ] Admin login
- [ ] Create student
- [ ] Create examination
- [ ] Add questions
- [ ] Student login
- [ ] Accept terms
- [ ] Grant camera permission
- [ ] Complete system check
- [ ] Start examination
- [ ] Generate monitoring event
- [ ] Generate evidence
- [ ] Receive admin alert
- [ ] Review evidence
- [ ] Submit examination
- [ ] View result/status
- [ ] Verify audit history

## AI Calibration

- [ ] Calibrate head-left threshold
- [ ] Calibrate head-right threshold
- [ ] Calibrate head-up threshold
- [ ] Calibrate head-down threshold
- [ ] Calibrate looking-away threshold
- [ ] Calibrate face-absence duration
- [ ] Calibrate multiple-face duration
- [ ] Calibrate mobile-phone confidence
- [ ] Calibrate mobile-phone persistence
- [ ] Record final tested thresholds

## False-Positive Testing

- [ ] Normal head movement
- [ ] Natural eye movement
- [ ] Temporary face obstruction
- [ ] Camera lighting changes
- [ ] Camera angle changes
- [ ] Background objects
- [ ] Multiple-person scenarios
- [ ] Mobile phone false-positive scenarios
- [ ] Temporary detection noise

## Performance Testing

- [ ] Student examination performance
- [ ] AI processing performance
- [ ] Evidence generation performance
- [ ] Admin dashboard performance
- [ ] WebSocket performance
- [ ] Database performance

## Security Review

- [ ] Authentication review
- [ ] Authorization review
- [ ] API security review
- [ ] Evidence access review
- [ ] Data isolation review
- [ ] Secret management review
- [ ] Error exposure review

## Demo Preparation

- [x] Create demo administrator account (seeded in production: `admin` / `Admin@2026`)
- [x] Create demo student account (five seeded student accounts)
- [x] Create demo examination (two seeded exams)
- [x] Create demo questions (five per exam)
- [ ] Prepare demo monitoring scenarios
- [ ] Prepare demo evidence
- [ ] Prepare demo environment
- [ ] Verify camera setup
- [ ] Verify AI models
- [ ] Verify database
- [ ] Verify WebSocket
- [ ] Verify complete demo workflow

## Documentation

- [ ] Finalize `PROJECT_SPEC.md`
- [ ] Finalize `CLAUDE.md`
- [ ] Finalize `TASKS.md`
- [x] Update README
- [x] Document installation
- [x] Document environment variables
- [x] Document database setup
- [x] Document API usage (Swagger/OpenAPI at `/docs`)
- [x] Document AI monitoring
- [ ] Document demo procedure
- [ ] Document known limitations

## Final Release

- [ ] Clean repository
- [ ] Remove temporary files
- [ ] Remove debug code
- [ ] Remove test secrets
- [ ] Verify `.gitignore`
- [ ] Run complete test suite
- [ ] Run final application verification
- [ ] Review Git history
- [ ] Create final Git tag/release
- [ ] Push final GitHub repository
- [ ] Verify repository documentation
- [ ] Verify hackathon demo readiness

---

# Development Rules

- [ ] Complete tasks in dependency order.
- [ ] Do not skip verification for completed milestones.
- [ ] Do not mark a task complete without testing it.
- [ ] Do not modify unrelated functionality.
- [ ] Do not introduce unnecessary dependencies.
- [ ] Do not change the approved architecture without justification.
- [ ] Do not create duplicate implementations.
- [ ] Keep the system lightweight and maintainable.
- [ ] Use Git checkpoints after major phases.
- [ ] Keep `PROJECT_SPEC.md` as the functional source of truth.
- [ ] Keep `CLAUDE.md` as the AI-agent development source of truth.
- [ ] Keep `TASKS.md` as the implementation progress tracker.
- [ ] Use human review for all AI-generated monitoring evidence.
- [ ] Do not label AI monitoring events as confirmed cheating.

---

# Definition of Done

A task can be marked `[x]` only when:

1. The implementation is complete.
2. The implementation follows `PROJECT_SPEC.md`.
3. Relevant validation exists.
4. Relevant tests pass.
5. Existing functionality still works.
6. Security requirements are satisfied.
7. No secrets are exposed.
8. The feature has been manually verified where applicable.
9. Documentation is updated where necessary.
10. The related Git checkpoint is completed where required.

---

# Final Development Objective

The completed system must demonstrate:

```text
Admin
  ↓
Create Student
  ↓
Create Examination
  ↓
Add Questions
  ↓
Student Login
  ↓
Accept Terms
  ↓
Grant Camera Permission
  ↓
System Readiness Check
  ↓
Start Examination
  ↓
AI-Assisted Monitoring
  ↓
Temporal Rule Validation
  ↓
Monitoring Event
  ↓
Evidence Generation
  ↓
Real-Time Admin Alert
  ↓
Admin Evidence Review
  ↓
Admin Decision
  ↓
Audit Record
  ↓
Exam Submission
  ↓
Result / Status