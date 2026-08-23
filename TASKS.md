# Exam Nigahban — Development Tasks

## Project Status

- Phase: Foundation
- Status: In Progress
- Current Milestone: Foundation Verification & Development Setup
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
- [ ] Verify `.gitignore`
- [ ] Verify no secrets are committed
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
- [ ] Establish API router structure
- [ ] Establish service layer structure
- [ ] Establish schema structure
- [ ] Establish WebSocket structure
- [ ] Establish error-handling structure
- [ ] Establish logging structure

## Database Foundation

- [x] Create `users` table
- [x] Create `students` table
- [x] Create `exams` table
- [x] Create `questions` table
- [x] Create `exam_sessions` table
- [x] Create `student_answers` table
- [ ] Create `monitoring_rules` table
- [ ] Create `monitoring_events` table
- [ ] Create `evidence` table
- [ ] Create `admin_actions` table
- [ ] Create `system_logs` table
- [ ] Verify foreign-key relationships
- [ ] Verify indexes and unique constraints
- [ ] Verify database initialization
- [ ] Prepare database seed data

## Foundation Verification

- [x] Verify backend starts successfully
- [x] Verify MySQL connection
- [x] Verify database metadata registration
- [x] Verify health endpoint
- [x] Verify frontend starts successfully
- [x] Verify frontend-to-backend communication
- [x] Verify CORS configuration
- [ ] Verify WebSocket connection structure
- [ ] Run foundation tests
- [ ] Review project structure
- [ ] Commit Foundation milestone

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
- [ ] Prevent unauthorized resource access
- [x] Verify backend authorization independently of frontend

## Administrator Management

- [x] Create administrator account
- [ ] View administrator accounts
- [ ] Update administrator account
- [ ] Activate/deactivate administrator account
- [ ] Validate administrator permissions

## Student Management

- [x] Create student account
- [x] Generate/store student profile
- [ ] View students
- [ ] View student details
- [ ] Update student details
- [ ] Activate/deactivate student
- [x] Prevent student self-registration
- [ ] Validate student ownership and access

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

- [ ] Commit Authentication milestone

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

- [ ] Create exam-session service
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

- [ ] Commit Examination milestone

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

- [ ] Commit Student Examination milestone

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

Out of scope for this milestone (approved as a face-monitoring-only milestone); deferred to a future YOLO milestone.

- [ ] Integrate YOLO inference
- [ ] Load required model
- [ ] Detect mobile phone class
- [ ] Filter predictions to mobile phone only
- [ ] Apply confidence threshold
- [ ] Apply approximately 1-second persistence
- [ ] Generate monitoring event when rule is satisfied

## AI Monitoring Rules

Thresholds were centralized as versioned constants modules (frontend `src/monitoring/constants.js`, backend `app/core/monitoring_constants.py`) rather than a database-backed rules table, since the milestone only required avoiding hard-coded values, not runtime-configurable rules. A DB-backed `monitoring_rules` table with an admin-facing enable/disable API remains a candidate for a later milestone if runtime reconfiguration is needed.

- [ ] Create monitoring rule model
- [ ] Create monitoring rule schema
- [ ] Create monitoring rule API/service
- [x] Configure activity types
- [x] Configure minimum duration
- [x] Configure required occurrences
- [x] Configure confidence threshold
- [x] Configure severity
- [ ] Enable/disable rules

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
- [ ] Test mobile phone detection (out of scope this milestone)
- [x] Test confidence thresholds
- [x] Test duration thresholds
- [x] Test occurrence thresholds
- [x] Test false-positive scenarios

## Git Checkpoint

- [ ] Commit AI Monitoring milestone (pending project-owner approval per milestone instructions)

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

- [ ] Create evidence service
- [ ] Capture evidence image when rule triggers
- [ ] Avoid unnecessary duplicate captures
- [ ] Store evidence path
- [ ] Store evidence timestamp
- [ ] Store evidence metadata
- [ ] Associate evidence with monitoring event
- [ ] Implement evidence filesystem abstraction

## Evidence API

- [ ] Create evidence schemas
- [ ] Create evidence router
- [ ] List evidence
- [ ] View evidence details
- [ ] Retrieve evidence securely
- [ ] Filter evidence
- [ ] Validate evidence authorization

## Evidence Review

- [ ] Implement PENDING_REVIEW status
- [ ] Implement CONFIRMED status
- [ ] Implement IGNORED status
- [ ] Implement evidence confirmation
- [ ] Implement evidence dismissal
- [ ] Allow review reason
- [ ] Prevent students from reviewing evidence

## Evidence Testing

- [ ] Test event generation
- [ ] Test evidence capture
- [ ] Test evidence storage
- [ ] Test evidence retrieval
- [ ] Test evidence authorization
- [ ] Test evidence review
- [ ] Test duplicate-event prevention

## Git Checkpoint

- [ ] Commit Evidence milestone

---

# Phase 7 — Real-Time Monitoring & Administration

## WebSocket

- [ ] Implement WebSocket endpoint
- [ ] Implement connection handling
- [ ] Implement disconnection handling
- [ ] Implement authentication for WebSocket access
- [ ] Broadcast monitoring events to authorized administrators
- [ ] Broadcast evidence notifications
- [ ] Handle reconnect where practical
- [ ] Prevent unauthorized WebSocket access

## Admin Dashboard

- [ ] Create dashboard layout
- [ ] Display active examinations
- [ ] Display active students
- [ ] Display pending alerts
- [ ] Display high-severity events
- [ ] Display recent events
- [ ] Display monitoring statistics
- [ ] Implement dashboard loading state
- [ ] Implement dashboard empty state
- [ ] Implement dashboard error state

## Live Monitoring

- [ ] Create live monitoring screen
- [ ] Display active examination sessions
- [ ] Display student information
- [ ] Display monitoring status
- [ ] Display latest alert
- [ ] Display severity
- [ ] Display event count
- [ ] Display latest event time
- [ ] Update alerts in real time

## Evidence Center

- [ ] Create evidence center
- [ ] Display evidence list
- [ ] Implement student filter
- [ ] Implement exam filter
- [ ] Implement activity filter
- [ ] Implement severity filter
- [ ] Implement status filter
- [ ] Implement timestamp sorting
- [ ] Implement evidence detail view

## Administrative Actions

- [ ] Implement evidence confirmation
- [ ] Implement evidence dismissal
- [ ] Store administrator action
- [ ] Store optional reason
- [ ] Validate administrator authorization

## Audit History

- [ ] Create admin-actions model
- [ ] Create audit service
- [ ] Record evidence review actions
- [ ] Record account actions
- [ ] Record examination actions
- [ ] Record question actions
- [ ] Record monitoring-rule changes
- [ ] Create audit history API
- [ ] Create audit history UI

## Real-Time Testing

- [ ] Test WebSocket connection
- [ ] Test monitoring event delivery
- [ ] Test evidence notification
- [ ] Test admin dashboard updates
- [ ] Test unauthorized WebSocket access
- [ ] Test reconnect behavior

## Git Checkpoint

- [ ] Commit Real-Time Administration milestone

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

- [ ] Login screen
- [ ] Terms & Conditions screen
- [ ] Camera permission screen
- [ ] System readiness screen
- [ ] Exam instructions screen
- [ ] Active examination screen
- [ ] Submission confirmation
- [ ] Result/status screen

## Administrator UI

- [ ] Admin login
- [ ] Dashboard
- [ ] Live monitoring
- [ ] Evidence center
- [ ] Evidence detail/review
- [ ] Student management
- [ ] Exam management
- [ ] Question management
- [ ] Examination sessions
- [ ] Monitoring settings
- [ ] Audit history

## Responsive Design

- [ ] Desktop layout
- [ ] Laptop layout
- [ ] Tablet compatibility where practical
- [ ] Responsive tables
- [ ] Responsive forms
- [ ] Responsive navigation
- [ ] Responsive evidence views

## UI States

- [ ] Loading states
- [ ] Empty states
- [ ] Success states
- [ ] Error states
- [ ] Retry states
- [ ] Confirmation dialogs
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
- [ ] Verify `.env` is ignored
- [ ] Verify no secrets in source code
- [ ] Review error-message exposure

## Privacy

- [ ] Verify no continuous webcam recording
- [ ] Verify evidence is generated only when required
- [ ] Verify evidence access restrictions
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

- [ ] Authentication tests
- [ ] Authorization tests
- [ ] Exam tests
- [ ] Question tests
- [ ] Session tests
- [ ] Answer tests
- [ ] Monitoring rule tests
- [ ] Temporal rule tests
- [ ] Evidence tests
- [ ] Audit tests

## Integration Testing

- [ ] Authentication API integration
- [ ] Student management integration
- [ ] Exam management integration
- [ ] Examination session integration
- [ ] Monitoring event integration
- [ ] Evidence integration
- [ ] WebSocket integration

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

- [ ] Create demo administrator account
- [ ] Create demo student account
- [ ] Create demo examination
- [ ] Create demo questions
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
- [ ] Update README
- [ ] Document installation
- [ ] Document environment variables
- [ ] Document database setup
- [ ] Document API usage
- [ ] Document AI monitoring
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