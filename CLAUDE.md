# EXAM NIGAHBAN — CLAUDE CODE DEVELOPMENT GUIDELINES

> **Authoritative development specification for Claude Code**
>
> Project: Exam Nigahban
> Purpose: AI-assisted online examination monitoring system
> Target: AI National / Alibaba Cloud AI Hackathon Pakistan 2026
> Development Stage: Hackathon MVP / Production-quality prototype
> Last Updated: August 2026

---

# 1. PROJECT IDENTITY

## 1.1 Project Name

Exam Nigahban

## 1.2 Project Purpose

Exam Nigahban is an AI-assisted online examination monitoring system designed to help administrators monitor examination sessions and generate reviewable evidence of potentially suspicious activities.

The system combines:

- Secure online examinations
- Student authentication
- Mandatory camera verification
- Real-time AI-assisted monitoring
- Head-pose analysis
- Face presence analysis
- Multiple-face detection
- Mobile-phone detection
- Temporal activity rules
- Automatic evidence capture
- Real-time administrator alerts
- Human-admin review and decision making
- Examination management
- Student management
- Evidence and audit management

## 1.3 Core Principle

Exam Nigahban is an AI-assisted monitoring and evidence-generation system.

The AI must NOT independently declare that a student cheated.

The system detects potentially suspicious monitoring events, generates evidence, and presents that evidence to an authorized administrator.

Final decisions always remain with the human administrator.

Never implement wording, logic, UI, or database states that incorrectly imply:

"AI confirmed cheating."

Preferred terminology:

- Monitoring Alert
- Suspicious Activity
- Evidence Generated
- Evidence Pending Review
- Confirmed by Admin
- Ignored by Admin
- Admin Review

---

# 2. AUTHORITATIVE TECHNOLOGY STACK

The following technology choices are mandatory for the MVP unless explicitly changed by the project owner.

## 2.1 Frontend

- React
- Vite
- JavaScript ES2022+
- Bootstrap 5.3
- CSS3
- Axios
- React Router
- Native WebSocket API
- Browser MediaDevices / getUserMedia()
- MediaPipe Face Landmarker

## 2.2 Backend

- Python 3.12+
- FastAPI
- Pydantic
- Pydantic Settings
- SQLAlchemy
- PyMySQL
- MySQL
- WebSocket

## 2.3 AI

### Face / Head Monitoring

Use:

- MediaPipe Face Landmarker

For:

- Face presence
- Head orientation
- Head left
- Head right
- Head up
- Head down
- Looking away

### Object Detection

Use:

- YOLO

For the MVP, object detection is restricted to:

MOBILE PHONE / CELL PHONE ONLY.

Do NOT implement detection requirements for:

- Smartwatch
- Digital camera
- Laptop
- Tablet
- Other prohibited devices

Only the mobile-phone detection event is required.

---

# 3. SYSTEM ARCHITECTURE

The overall architecture is:

Student Browser
    |
    v
React + Vite Frontend
    |
    +----------------------+
    |                      |
    v                      v
Local AI Processing      FastAPI API
(MediaPipe + YOLO)          |
                             |
                    +--------+--------+
                    |                 |
                    v                 v
                  MySQL           WebSocket
                    |                 |
                    v                 v
              Evidence/Data      Admin Dashboard
                    |
                    v
             Human Admin Review

## 3.1 Examination Flow

Student Login
    |
    v
Terms & Conditions
    |
    v
Camera Permission
    |
    v
System / Camera Check
    |
    v
Exam Ready
    |
    v
Start Examination
    |
    v
Real-Time AI Monitoring
    |
    +-----------------------------+
    |                             |
    v                             v
Head/Face Analysis        Mobile Phone Detection
    |                             |
    +-------------+---------------+
                  |
                  v
           Temporal Rule Engine
                  |
                  v
            Monitoring Event
                  |
                  v
            Evidence Capture
                  |
                  v
             FastAPI Backend
                  |
           +------+------+
           |             |
           v             v
         MySQL       WebSocket
                         |
                         v
                 Admin Dashboard
                         |
                         v
                    Human Review

---

# 4. NON-NEGOTIABLE REQUIREMENTS

The following rules MUST NOT be violated without explicit approval from the project owner.

## 4.1 Authentication

- Students cannot self-register.
- Only authorized administrators can create user accounts.
- Admin can create Student accounts.
- Admin can create other Admin accounts.
- Passwords must never be stored in plaintext.
- Passwords must be securely hashed.
- Authentication must use secure sessions/tokens.
- Role-based authorization is mandatory.

Roles:

- ADMIN
- STUDENT

## 4.2 Camera Permission

Camera permission is mandatory for examination participation.

The student cannot start an examination unless:

1. Camera permission is granted.
2. Camera is accessible.
3. Required pre-exam checks pass.

Do not provide a "skip camera" option.

## 4.3 AI Monitoring

AI monitoring must operate during the active examination session.

Required monitoring:

- Head left
- Head right
- Head up
- Head down
- Looking away
- Face absent
- Multiple faces
- Mobile phone

## 4.4 Mobile Phone Detection

Mobile phone detection is the ONLY required prohibited-object detection.

Do not add unnecessary object categories.

The system should:

1. Detect a mobile phone.
2. Apply a confidence threshold.
3. Require approximately one second of persistence.
4. Generate a monitoring event.
5. Capture evidence.
6. Send an alert to the administrator.

Thresholds must remain configurable.

## 4.5 Temporal Detection

Do not generate a serious monitoring event based on a single noisy frame.

Use temporal logic.

Baseline rules:

| Activity | Minimum Duration | Occurrences | Confidence | Severity |
|---|---:|---:|---:|---|
| HEAD_LEFT | >3 sec | 3 | >=0.75 | Medium |
| HEAD_RIGHT | >3 sec | 3 | >=0.75 | Medium |
| HEAD_UP | >3 sec | 3 | >=0.75 | Medium |
| HEAD_DOWN | >3 sec | 3 | >=0.75 | Medium |
| LOOKING_AWAY | >3 sec | 3 | >=0.75 | Medium |
| FACE_ABSENT | >3 sec | 1 | Configurable | High |
| MULTIPLE_FACES | >2 sec | 1 | Configurable | High |
| MOBILE_PHONE | approximately 1 sec | 1 | >=0.40 | High |

These values are baseline MVP configuration.

Do not hard-code them throughout the application.

Store monitoring thresholds in configuration/database structures where appropriate.

---

# 5. AI PROCESSING RULES

## 5.1 Local Processing

Where practical, AI inference should occur locally in the student's browser.

Do NOT continuously stream raw webcam video to the backend.

Preferred flow:

Webcam
    |
    v
Browser
    |
    +--> MediaPipe
    |
    +--> YOLO
    |
    v
Monitoring Rules
    |
    v
Only suspicious events/evidence
    |
    v
Backend

## 5.2 Backend Responsibilities

The backend should receive:

- Monitoring events
- Confidence
- Duration
- Activity type
- Session ID
- Student ID
- Timestamp
- Evidence image when required
- Relevant metadata

The backend should NOT receive unnecessary continuous webcam frames.

## 5.3 Head Pose

Use MediaPipe facial landmarks and transformation information.

Pipeline:

Webcam
    |
    v
MediaPipe Face Landmarker
    |
    v
Face Detection
    |
    v
Facial Landmarks / Transformation
    |
    v
Head Pose Estimation
    |
    v
Temporal Smoothing
    |
    v
Duration / Occurrence Rules
    |
    v
Monitoring Event

Avoid raw frame-by-frame alert generation.

Use smoothing/debouncing to reduce false positives.

---

# 6. MONITORING EVENT MODEL

Every generated monitoring event should contain, where applicable:

- Event ID
- Student ID
- Exam ID
- Session ID
- Activity type
- Confidence
- Duration
- Occurrence number
- Severity
- Timestamp
- Status

Example:

EVT-2026-000145

Student: STU-1024
Exam: DEMO-EXAM-01
Activity: HEAD_RIGHT
Severity: Medium
Confidence: 87.4%
Duration: 4.2 sec
Occurrence: 3/3
Detected At: 2026-08-22 12:21:14
Status: PENDING_REVIEW

---

# 7. EVIDENCE GENERATION

Evidence should be generated only when the configured monitoring rule is satisfied.

Evidence should include:

- Evidence ID
- Event ID
- Image path
- Capture timestamp
- Activity type
- Confidence
- Duration
- Relevant metadata

Example:

evidence/
    2026/
        08/
            22/
                EVT-2026-000145.jpg

Do not store unnecessary duplicate images.

Do not capture evidence continuously.

Evidence storage must remain abstracted so that local filesystem storage can later be replaced with object storage if required.

---

# 8. DATABASE ARCHITECTURE

Current core tables include:

- users
- students
- exams
- questions
- exam_sessions
- student_answers

Additional monitoring-related tables should include:

- monitoring_rules
- monitoring_events
- evidence
- admin_actions
- system_logs

## 8.1 users

Fields:

- id
- username
- password_hash
- role
- status
- created_at

## 8.2 students

Fields:

- id
- user_id
- student_id
- full_name
- department
- class
- is_active
- created_at

## 8.3 exams

Fields:

- id
- title
- description
- duration_minutes
- status
- created_at

## 8.4 questions

Fields:

- id
- exam_id
- question_text
- option_a
- option_b
- option_c
- option_d
- correct_answer

## 8.5 exam_sessions

Fields:

- id
- student_id
- exam_id
- started_at
- ended_at
- status
- score

## 8.6 student_answers

Store student answers associated with an examination session and question.

## 8.7 monitoring_rules

Fields:

- id
- activity_type
- enabled
- min_duration_sec
- required_occurrences
- confidence_threshold
- severity

## 8.8 monitoring_events

Fields:

- id
- session_id
- event_type
- confidence
- duration
- occurrences
- severity
- detected_at
- status

## 8.9 evidence

Fields:

- id
- event_id
- image_path
- captured_at
- metadata

## 8.10 admin_actions

Fields:

- id
- event_id
- admin_id
- action
- reason
- created_at

---

# 9. CURRENT DATABASE STATE

The repository already contains a working MySQL database.

Current foundational tables:

- users
- students
- exams
- questions
- exam_sessions
- student_answers

IMPORTANT:

Do NOT destroy or recreate the existing database unnecessarily.

Do NOT reset the database during normal development.

Before changing existing models:

1. Inspect the current model.
2. Inspect the current database schema.
3. Determine migration impact.
4. Make the smallest safe change.
5. Verify existing functionality.

Do not delete existing tables merely to simplify development.

---

# 10. AUTHENTICATION AND SECURITY

Security is mandatory.

## 10.1 Passwords

Never store plaintext passwords.

Use secure password hashing.

## 10.2 Secrets

Never commit:

.env

Never expose:

- Database passwords
- Secret keys
- API keys
- Tokens
- Private credentials

Use:

.env
.env.example

.env.example must contain placeholders only.

## 10.3 Authentication

Implement:

- Login
- Logout
- Authentication verification
- Role-based authorization
- Session/token expiration
- Protected routes

Roles:

- ADMIN
- STUDENT

---

# 11. API DESIGN

Use RESTful API conventions.

Expected API structure:

POST   /api/auth/login
POST   /api/auth/logout
GET    /api/auth/me

GET    /api/students
POST   /api/students
GET    /api/students/{id}
PUT    /api/students/{id}
DELETE /api/students/{id}

GET    /api/exams
POST   /api/exams
GET    /api/exams/{id}
PUT    /api/exams/{id}
DELETE /api/exams/{id}

GET    /api/exams/{id}/questions
POST   /api/exams/{id}/questions

POST   /api/exam-sessions
GET    /api/exam-sessions/{id}

POST   /api/monitoring/events
GET    /api/monitoring/events

GET    /api/evidence
GET    /api/evidence/{id}

POST   /api/evidence/{id}/review

Exact route naming may be refined during implementation, but maintain consistency.

---

# 12. WEBSOCKET

WebSocket is required for real-time monitoring alerts.

Preferred flow:

Student Browser
    |
    v
Monitoring Event
    |
    v
FastAPI
    |
    v
WebSocket
    |
    v
Admin Dashboard

The admin dashboard should receive new monitoring alerts without requiring a manual page refresh.

Do not use WebSocket for unnecessary bulk data transfer.

---

# 13. FRONTEND ARCHITECTURE

Use:

- React
- Vite
- JavaScript
- Bootstrap 5.3
- CSS3
- Axios
- React Router
- Native WebSocket

Do NOT introduce:

- Redux
- Tailwind CSS
- Next.js
- jQuery
- Angular
- Vue
- Heavy UI frameworks
- Unnecessary state-management libraries

Keep the frontend lightweight.

---

# 14. FRONTEND SCREEN INVENTORY

## 14.1 Student Screens

Required screens:

1. Login
2. Terms & Conditions
3. Camera Permission
4. System / Camera Check
5. Exam Ready
6. Active Examination
7. Submission Confirmation
8. Exam Status / Result

Flow:

Login
    ↓
Terms & Conditions
    ↓
Camera Permission
    ↓
System / Camera Check
    ↓
Exam Ready
    ↓
Active Examination
    ↓
Submission Confirmation
    ↓
Exam Status / Result

## 14.2 Admin Screens

Required screens:

- Admin Login
- Dashboard
- Live Monitoring
- Evidence Center
- Evidence Detail / Review
- Student Management
- Exam Management
- Question Management
- Exam Sessions
- Audit / Action History
- System Settings

---

# 15. UI / UX PRINCIPLES

The UI must be:

- Professional
- Modern
- Minimal
- Consistent
- Responsive
- Accessible
- Fast
- Easy to understand

## 15.1 Student Experience

Student interface should be:

- Calm
- Low-distraction
- Focused on examination
- Clear
- Simple

Avoid unnecessary animations.

## 15.2 Admin Experience

Admin interface should be:

- Information-rich
- Operational
- Easy to scan
- Alert-focused
- Efficient for reviewing evidence

---

# 16. UI COMPONENT SYSTEM

Use reusable components.

Examples:

- Button
- Input
- Select
- Modal
- Badge
- Alert
- Toast
- Card
- Table
- Pagination
- LoadingState
- EmptyState
- ErrorState
- ConfirmDialog
- CameraPreview
- ExamTimer
- QuestionCard
- EvidenceCard
- EvidenceViewer
- MonitoringAlert
- StatusBadge

Do not duplicate UI logic unnecessarily.

---

# 17. ACCESSIBILITY

Follow practical accessibility standards.

Ensure:

- Visible keyboard focus
- Proper labels
- Sufficient color contrast
- Keyboard-friendly controls
- Meaningful button labels
- Accessible form validation
- Do not rely on color alone to communicate status

---

# 18. MONITORING UI LANGUAGE

Never display:

CHEATING DETECTED

STUDENT IS CHEATING

AI CONFIRMED CHEATING

Use:

- Monitoring Alert
- Suspicious Activity
- Evidence Generated
- Pending Review
- Admin Review Required

Admin decisions can be:

- CONFIRMED
- IGNORED

The UI must clearly distinguish AI-generated evidence from the administrator's final decision.

---

# 19. ERROR HANDLING

Every important operation must handle:

- Loading state
- Success state
- Empty state
- Error state

Backend errors should return consistent responses.

Frontend should show user-friendly messages.

Do not expose:

- Stack traces
- Database errors
- Internal paths
- Secrets
- Debug information

to normal users.

---

# 20. LOGGING

Use structured application logging where useful.

Log:

- Authentication events
- Important API errors
- Exam session events
- Monitoring events
- Evidence generation
- Admin actions
- Security-related events

Do NOT log:

- Passwords
- Access tokens
- Secret keys
- Sensitive credentials

---

# 21. PRIVACY

The system handles sensitive examination information.

Therefore:

- Collect only required information.
- Do not continuously store webcam video.
- Store evidence only when monitoring rules trigger.
- Restrict evidence access to authorized administrators.
- Do not expose student monitoring data publicly.
- Do not place credentials in source code.
- Keep evidence storage controlled.

---

# 22. TESTING REQUIREMENTS

Every major implementation task must be tested.

## 22.1 Backend

Test:

- API tests
- Authentication tests
- Authorization tests
- Database tests
- Validation tests
- Monitoring event tests

## 22.2 Frontend

Test:

- Login flow
- Camera permission flow
- Exam flow
- Admin dashboard
- Evidence review
- WebSocket alerts

## 22.3 AI

Test:

- Face present
- Face absent
- Multiple faces
- Head left
- Head right
- Head up
- Head down
- Looking away
- Mobile phone detection
- False-positive resistance
- Temporal rules

Do not claim an AI feature works without testing it.

---

# 23. GIT WORKFLOW

Use Git consistently.

Before significant work:

git status

After a completed task:

git add .
git commit -m "Clear description of completed task"

Use small, meaningful commits.

Examples:

feat: add authentication API
feat: add student management
feat: add exam question APIs
feat: add monitoring event model
feat: add evidence review workflow
feat: add live monitoring dashboard
fix: correct exam session validation
test: add authentication tests

Do not create giant commits containing unrelated changes.

---

# 24. CLAUDE CODE WORKFLOW

Claude Code MUST follow this workflow.

## Step 1 — Read Instructions

Always read:

CLAUDE.md

before making changes.

## Step 2 — Inspect

Before implementing a feature:

- Inspect relevant files.
- Understand existing architecture.
- Check existing models.
- Check existing routes.
- Check existing components.
- Check dependencies.
- Check current database state.

## Step 3 — Plan

Provide a concise implementation plan before significant changes.

## Step 4 — Implement

Implement only the requested/scoped task.

## Step 5 — Verify

Run appropriate:

- Tests
- Linters
- Syntax checks
- API checks
- Build checks

## Step 6 — Report

Clearly report:

- What changed
- Files changed
- Tests performed
- Results
- Any remaining issue

---

# 25. CLAUDE CODE BEHAVIOR RULES

Claude must:

- Follow this document.
- Preserve existing working functionality.
- Make minimal changes.
- Prefer simple solutions.
- Reuse existing components and services.
- Avoid unnecessary dependencies.
- Avoid unrelated refactoring.
- Ask for clarification when requirements conflict.
- Identify risks before destructive changes.
- Verify changes.

Claude must NOT:

- Rebuild the project from scratch without approval.
- Delete the database.
- Delete working modules unnecessarily.
- Replace the selected architecture.
- Introduce unnecessary frameworks.
- Add unrelated features.
- Modify .env secrets unnecessarily.
- Commit secrets.
- Claim untested functionality works.
- Automatically classify a student as cheating.

---

# 26. DO NOT OVER-ENGINEER THE MVP

The hackathon MVP must prioritize:

1. Reliability
2. Demonstrability
3. AI monitoring
4. Evidence generation
5. Real-time admin visibility
6. Security
7. Professional UI
8. Testing

Avoid unnecessary infrastructure such as:

- Redis
- Kubernetes
- Microservices
- Message queues
- Complex distributed systems
- Excessive caching
- Complex event buses

unless a genuine technical requirement appears.

The MVP should remain simple enough for a small development team to maintain.

---

# 27. CURRENT REPOSITORY STRUCTURE

Expected structure:

Exam-Nigahban/
|
├── backend/
│   ├── app/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── websocket/
│   │   └── main.py
│   │
│   ├── tests/
│   ├── .env
│   ├── .env.example
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── vite.config.js
│
├── ai/
│   ├── face/
│   ├── object_detection/
│   └── monitoring/
│
├── database/
│   ├── migrations/
│   └── seeds/
│
├── evidence/
│
├── docs/
│
├── tests/
│
├── CLAUDE.md
├── TASKS.md
├── PROJECT_SPEC.md
└── README.md

The actual repository may differ temporarily.

Do not restructure everything merely to match this diagram.

Preserve working code and evolve toward this structure incrementally.

---

# 28. CURRENT IMPLEMENTATION STATUS

The following foundation has already been implemented and verified:

- Git repository initialized
- Project structure created
- Python virtual environment
- FastAPI application
- MySQL database
- SQLAlchemy connection
- Configuration system
- User model
- Student model
- Exam model
- Question model
- ExamSession model
- StudentAnswer model
- Database tables
- FastAPI health endpoint
- Swagger/OpenAPI documentation
- MySQL connection verified

Current foundational database tables:

- users
- students
- exams
- questions
- exam_sessions
- student_answers

Do not rebuild these components from scratch.

Continue development from the existing implementation.

---

# 29. PRIORITY ORDER

Unless the project owner specifies otherwise, implement remaining functionality approximately in this order.

## Phase 1 — Authentication

- Password hashing
- Login
- Logout
- Authentication
- Role-based authorization
- Admin account management
- Student account management

## Phase 2 — Exam Management

- Exam CRUD
- Question CRUD
- Exam sessions
- Student answers
- Exam submission
- Basic scoring

## Phase 3 — Student Examination Flow

- Terms & Conditions
- Camera permission
- Camera readiness
- System check
- Exam interface
- Timer
- Submission

## Phase 4 — AI Monitoring

- MediaPipe face detection
- Head-pose estimation
- Looking-away detection
- Face absence
- Multiple faces
- YOLO mobile-phone detection

## Phase 5 — Temporal Rule Engine

- Duration tracking
- Occurrence tracking
- Confidence thresholds
- Event generation
- Severity

## Phase 6 — Evidence

- Evidence capture
- Evidence storage
- Evidence metadata
- Evidence API

## Phase 7 — Real-Time Administration

- WebSocket
- Live monitoring
- Monitoring alerts
- Evidence center
- Evidence review
- Admin actions

## Phase 8 — Polish

- Error handling
- Security review
- UI refinement
- Testing
- Performance
- Demo preparation
- Documentation

---

# 30. DEFINITION OF DONE

A feature is NOT considered complete merely because code was written.

A feature is complete only when:

- Requirements are implemented.
- Existing functionality remains working.
- Code follows project architecture.
- Appropriate validation exists.
- Errors are handled.
- Relevant tests pass.
- UI works where applicable.
- API behavior is verified.
- Security considerations are addressed.
- No secrets are committed.
- Claude reports exactly what was changed and verified.

---

# 31. HACKATHON MVP BOUNDARY

## IN SCOPE

- Secure authentication
- Admin-created accounts
- Student examination
- Camera permission
- Pre-exam system check
- AI-assisted monitoring
- Head pose
- Face absence
- Multiple faces
- Mobile phone detection
- Temporal suspicious-activity rules
- Evidence capture
- Real-time admin alerts
- Evidence review
- Admin decisions
- Audit history
- Professional responsive UI

## OUT OF SCOPE

Unless explicitly approved:

- Autonomous cheating decisions
- Continuous video recording
- Smartwatch detection
- Digital-camera detection
- Laptop detection
- Advanced biometric identity recognition
- Complex cloud infrastructure
- Microservice architecture
- Unnecessary third-party integrations
- Mobile application
- Large-scale production deployment infrastructure

---

# 32. FINAL ENGINEERING PRINCIPLE

Build Exam Nigahban as a:

SECURE, LIGHTWEIGHT, EXPLAINABLE, AI-ASSISTED EXAMINATION MONITORING SYSTEM.

Prioritize:

Correctness
    >
Reliability
    >
Security
    >
Explainability
    >
Performance
    >
Visual Polish

Do not optimize for complexity.

Do not optimize for the number of technologies used.

Optimize for a system that can be:

1. Demonstrated confidently.
2. Tested reliably.
3. Understood by judges.
4. Maintained by a small team.
5. Extended after the hackathon.

---

# 33. IMPORTANT AGENT INSTRUCTION

Before changing ANY file:

1. Read CLAUDE.md.
2. Inspect the relevant existing implementation.
3. Identify dependencies and side effects.
4. Explain the proposed change briefly.
5. Implement only the approved/scoped task.
6. Test the change.
7. Report the result.

Never assume that an empty or incomplete-looking file means it should be recreated.

Never overwrite working code without inspection.

Never make broad architectural changes without explicit approval.

Never delete data or project files as a shortcut.

When uncertain, stop and ask the project owner.

---

# END OF EXAM NIGAHBAN CLAUDE CODE DEVELOPMENT GUIDELINES