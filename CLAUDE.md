# Exam Nigahban — Claude Code Instructions

## 1. Project

Exam Nigahban is an AI-assisted online examination monitoring and evidence-generation platform.

The system supports:

- Secure student examination
- Administrator-managed accounts
- Online exams
- Camera permission and system readiness checks
- AI-assisted face and head-pose monitoring
- Mobile phone detection
- Temporal monitoring rules
- Evidence generation
- Real-time administrator alerts
- Human review of monitoring evidence
- Administrative actions and audit history

The system must remain professional, secure, maintainable, and suitable for hackathon demonstration.

---

## 2. Engineering Principle

Build the system incrementally.

Before changing code:

1. Read the relevant requirements.
2. Inspect the existing implementation.
3. Understand dependencies.
4. Make the smallest appropriate change.
5. Test the change.
6. Review the Git diff.
7. Report what was changed and verified.

Do not make unrelated changes.

Do not rewrite working code without a clear reason.

Do not introduce unnecessary architecture.

---

## 3. Source of Truth

Use the following priority:

1. Approved SRS
2. PROJECT_SPEC.md
3. CLAUDE.md
4. TASKS.md
5. Existing implementation

If requirements conflict with the existing implementation, follow the approved requirements.

If an architectural decision is unclear, do not silently invent a new architecture.

---

## 4. Approved Technology Stack

### Frontend

- React
- Vite
- JavaScript ES2022+
- Bootstrap 5.3
- CSS3
- Axios
- React Router
- Native WebSocket API
- Browser MediaDevices API

### AI / Computer Vision

- MediaPipe Face Landmarker
- Ultralytics YOLO
- Browser-side processing where practical
- Mobile phone detection

### Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- WebSocket

### Database

- MySQL

### Development

- Visual Studio Code
- Git
- GitHub
- Claude Code
- Postman
- Google Chrome

---

## 5. Architecture

Use a modular monolithic architecture for the MVP.

High-level flow:

Student Browser
        |
        v
React Frontend
        |
        +--> Camera / Browser APIs
        |
        +--> MediaPipe Face Landmarker
        |
        +--> YOLO Mobile Phone Detection
        |
        v
FastAPI Backend
        |
        +--> Authentication
        +--> Exam Services
        +--> Monitoring Services
        +--> Evidence Services
        +--> WebSocket Services
        |
        v
MySQL

Admin Dashboard receives monitoring events and evidence through the backend.

Do not stream every webcam frame to the backend unnecessarily.

Process monitoring locally where practical and send only required events, evidence, and metadata.

---

## 6. Frontend Rules

Use React component-based architecture.

Prefer:

- Reusable components
- Small focused components
- Clear page boundaries
- Reusable hooks when useful
- Centralized API configuration
- Consistent error handling
- Loading states
- Empty states
- Responsive Bootstrap layouts
- Accessible controls

Do not introduce:

- Redux
- Tailwind CSS
- Next.js
- jQuery
- Vue
- Angular

unless explicitly approved.

Keep dependencies minimal.

---

## 7. Backend Rules

Separate backend responsibilities into appropriate modules such as:

- API routes
- Services
- Schemas
- Database models
- Authentication
- WebSocket handling

Do not place large business-logic implementations directly inside route handlers.

Validate all external input.

Never expose:

- Passwords
- Database credentials
- API keys
- Internal stack traces
- Secret tokens

to clients.

---

## 8. Database

Use MySQL.

Core entities include:

- Users
- Students
- Exams
- Questions
- Exam Sessions
- Student Answers
- Monitoring Rules
- Monitoring Events
- Evidence
- Administrative Actions
- System Logs

Use appropriate:

- Primary keys
- Foreign keys
- Constraints
- Timestamps
- Indexes

Passwords must never be stored in plaintext.

Secrets must be supplied through environment variables.

---

## 9. Authentication

Roles:

- ADMIN
- STUDENT

Only administrators can create accounts.

Students must not have public self-registration.

Authentication must use secure password hashing.

Every protected endpoint must verify authentication and authorization.

Never trust role information supplied directly by the browser.

---

## 10. AI Monitoring

Exam Nigahban is an AI-assisted monitoring and evidence-generation system.

It is NOT an autonomous cheating-decision system.

AI identifies predefined observable conditions.

The administrator makes the final decision.

Never use:

- Cheating Confirmed
- Student Is Cheating
- Guilty

Prefer:

- Monitoring Alert
- Suspicious Activity Detected
- Evidence Generated
- Pending Review
- Confirmed
- Dismissed

---

## 11. Monitoring Scope

### Head / Gaze

- HEAD_LEFT
- HEAD_RIGHT
- HEAD_UP
- HEAD_DOWN
- LOOKING_AWAY

### Face

- FACE_ABSENT
- MULTIPLE_FACES

### Object Detection

Only:

- MOBILE_PHONE

Do not add smartwatch, camera, laptop, or other prohibited-object detection unless the approved specification is changed.

---

## 12. Temporal Monitoring

Avoid triggering important evidence from a single noisy frame.

Use:

- Confidence thresholds
- Duration thresholds
- Occurrence counts
- Temporal persistence
- Smoothing where appropriate

Baseline rules:

- Head movement: >3 seconds and repeated occurrences
- Face absent: approximately 5 seconds
- Multiple faces: approximately 2 seconds
- Mobile phone: approximately 1 second with high confidence

Monitoring thresholds should be configurable rather than duplicated throughout the codebase.

---

## 13. Evidence

Evidence should contain, where applicable:

- Evidence ID
- Student ID
- Exam ID
- Session ID
- Activity type
- Confidence
- Duration
- Occurrence number
- Timestamp
- Severity
- Image path
- Review status
- Metadata

Review statuses:

- PENDING_REVIEW
- CONFIRMED
- IGNORED

The system generates evidence.

The administrator performs the final review.

---

## 14. Real-Time Monitoring

Use WebSocket communication for real-time monitoring events.

Do not send unnecessary high-frequency data.

Handle:

- Connection failures
- Reconnection
- Duplicate events
- Stale events
- Authentication failures

The application should remain stable if a WebSocket connection temporarily fails.

---

## 15. UI / UX

Use the approved Exam Nigahban design system.

### Student UI

Prioritize:

- Low distraction
- Clear instructions
- Exam focus
- Camera/system status
- Visible timer
- Question navigation
- Accessible controls

### Admin UI

Prioritize:

- Real-time monitoring
- Alert visibility
- Evidence review
- Filtering
- Student/session status
- Administrative actions
- Auditability

Do not introduce arbitrary colors.

Use the approved project colors consistently.

Do not communicate important information using color alone.

---

## 16. Security

Never commit:

- `.env`
- Passwords
- API keys
- JWT secrets
- Database credentials
- Private keys
- Authentication tokens

Use `.env.example` for safe configuration examples.

Validate external input.

Use secure database access patterns.

Protect administrative endpoints.

Protect evidence access.

---

## 17. Evidence Storage

Runtime evidence must not be committed to Git.

Store evidence metadata in MySQL.

Store evidence files through a dedicated storage abstraction.

The implementation should allow future migration to object storage without redesigning the monitoring system.

---

## 18. Testing

Important features must be verified.

Test at minimum:

- Authentication
- Authorization
- Exam creation
- Question management
- Exam sessions
- Answer submission
- Monitoring rules
- Evidence creation
- WebSocket events
- Evidence review
- Administrative actions

A feature is not complete merely because code has been written.

---

## 19. Git Workflow

Work in small, reviewable increments.

Before committing:

1. Review changed files.
2. Run `git diff`.
3. Run relevant tests.
4. Check for secrets.
5. Verify the affected workflow.

Use meaningful commit messages.

Examples:

- `feat: add authentication foundation`
- `feat: implement exam session workflow`
- `feat: add monitoring event engine`
- `feat: add evidence review workflow`
- `fix: handle websocket reconnect`
- `docs: update project specification`

Do not rewrite Git history unless explicitly requested.

---

## 20. Dependency Policy

Before installing a dependency:

1. Check whether the existing stack already provides the capability.
2. Confirm the dependency is necessary.
3. Prefer stable and well-maintained packages.
4. Keep dependencies minimal.
5. Document important architectural dependencies.

Do not add packages simply because they are popular.

---

## 21. Avoid Over-Engineering

This is a hackathon MVP.

Do not introduce unnecessarily:

- Redis
- Kubernetes
- Microservices
- Message brokers
- Multiple databases
- Complex event buses
- Large cloud infrastructure

Prefer a clean modular monolith.

---

## 22. Development Milestones

Follow this order:

1. Repository foundation
2. Project configuration
3. Frontend foundation
4. Backend foundation
5. Database schema
6. Authentication
7. Student workflow
8. Admin workflow
9. Exam engine
10. Camera permission and system check
11. AI monitoring foundation
12. Head/face monitoring
13. Mobile phone detection
14. Temporal rule engine
15. Evidence generation
16. WebSocket alerts
17. Evidence review
18. Audit logging
19. Integration testing
20. UI/UX refinement
21. Security review
22. Hackathon demonstration preparation

Do not jump randomly between milestones.

---

## 23. Definition of Done

A task is complete only when:

- Requirements are implemented.
- Architecture is respected.
- Relevant tests pass.
- The affected workflow is verified.
- No secrets are exposed.
- No unnecessary dependencies were introduced.
- Git diff has been reviewed.
- Documentation is updated when required.

---

## 24. Claude Working Rules

When working on a task:

1. Read the relevant documentation first.
2. Inspect the existing files.
3. Explain the implementation plan briefly.
4. Make focused changes.
5. Do not modify unrelated files.
6. Run appropriate validation.
7. Review the result.
8. Report changed files and verification results.

If a requirement is ambiguous and affects security, architecture, data integrity, or the user workflow, ask before making a major assumption.

---

## 25. Final Principle

Build Exam Nigahban incrementally, securely, and professionally.

Prefer simple, maintainable, testable solutions over unnecessary complexity.