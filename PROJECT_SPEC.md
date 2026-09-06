# Exam Nigahban — Project Specification

**Document:** PROJECT_SPEC.md  
**Project:** Exam Nigahban  
**Version:** 1.1  
**Status:** Approved Development Baseline  
**Purpose:** Technical source of truth for implementation

---

# 1. Project Overview

Exam Nigahban is an AI-assisted online examination monitoring and evidence-generation platform.

The system allows authorized administrators to create and manage examinations and student accounts while providing students with a controlled online examination environment.

During an examination, the system performs AI-assisted monitoring of predefined observable conditions such as:

- Head/gaze direction
- Face absence
- Multiple faces
- Mobile phone presence

When configured monitoring conditions are satisfied, the system generates structured monitoring events and supporting evidence.

Administrators receive monitoring alerts in real time and review the generated evidence.

The system does not autonomously determine academic misconduct.

Final decisions remain with authorized administrators.

The system is designed as a lightweight, explainable, human-in-the-loop monitoring platform suitable for the hackathon MVP.

---

# 2. Project Goals

The MVP must demonstrate:

1. Secure administrator and student authentication.
2. Administrator-controlled account creation.
3. Online examination management.
4. Question management.
5. Controlled student examination workflow.
6. Camera permission enforcement.
7. Pre-examination system readiness verification.
8. Real-time AI-assisted monitoring.
9. Head/gaze direction monitoring.
10. Face absence detection.
11. Multiple-face detection.
12. Mobile phone detection.
13. Temporal monitoring rules.
14. Evidence generation.
15. Real-time administrator alerts.
16. Evidence review and administrative action.
17. Auditability.
18. Professional responsive UI/UX.
19. Reliable and demonstrable hackathon implementation.

---

# 3. User Roles

## 3.1 Administrator

Administrators can:

- Log in securely.
- Create student accounts.
- Create administrator accounts.
- Manage students.
- Activate or deactivate student accounts.
- Create and manage exams.
- Add and manage questions.
- Configure monitoring rules where authorized.
- View examination sessions.
- Monitor active examinations.
- Receive real-time monitoring alerts.
- Review monitoring evidence.
- Confirm or dismiss evidence.
- Record administrative actions.
- View audit history.

Administrators must only access functions permitted by their role.

---

## 3.2 Student

Students can:

- Log in using administrator-provided credentials.
- View examination terms and conditions.
- Accept required terms.
- Grant camera permission.
- Complete system readiness checks.
- View assigned examination information.
- Start an assigned examination.
- Answer questions.
- Navigate questions.
- View remaining examination time.
- Submit the examination.
- View appropriate examination status or result information.

Students cannot:

- Self-register.
- Create administrator accounts.
- Modify monitoring rules.
- Access administrative functions.
- Access other students' examinations.
- Access other students' evidence.
- Access monitoring administration functions.

---

# 4. Authentication and Authorization

The system uses role-based access control.

Supported roles:

- ADMIN
- STUDENT

Account creation is administrator-controlled.

Students must not have public self-registration.

Passwords must never be stored in plaintext.

Passwords must be securely hashed.

Protected API endpoints must verify authentication and authorization.

Authorization must be enforced on the backend.

The backend must never trust role information supplied by the browser.

Inactive accounts must not be permitted to access protected functionality.

The authentication system should support:

- Login
- Logout
- Authentication verification
- Protected routes
- Role-based access
- Session or token expiration
- Invalid credential handling
- Account status validation

---

# 5. Student Examination Workflow

The standard workflow is:

```text
Student Login
     ↓
Terms & Conditions
     ↓
Accept Terms
     ↓
Camera Permission
     ↓
Pre-Exam System Check
     ↓
Exam Instructions
     ↓
Start Examination
     ↓
Real-Time AI Monitoring
     ↓
Answer Questions
     ↓
Submit Examination
     ↓
Submission Confirmation
     ↓
Result / Status
5.1 Student Login

The student enters administrator-provided credentials.

The backend validates:

Username
Password
Account status
Student role
5.2 Terms and Conditions

The student must view the examination terms and conditions.

The student must explicitly accept the required terms before continuing.

The system should record acceptance where required for auditability.

5.3 Camera Permission

Camera access is mandatory for monitored examinations.

The student cannot start the examination without camera permission.

The interface must clearly explain why camera access is required.

If permission is denied:

Examination start must remain blocked.
The interface must explain how to grant permission.
The student must be able to retry the permission/readiness process.
5.4 Pre-Exam System Check

Before the examination begins, the system should verify:

Camera availability
Camera permission
Camera stream readiness
Face visibility
Basic AI readiness
Browser readiness where practical

The system should clearly show:

Passed checks
Failed checks
Retry options
5.5 Examination

The student receives the assigned examination.

The examination interface should provide:

Question
Answer options
Question navigation
Current question indicator
Remaining time
Submission control

The interface should be low-distraction and easy to understand.

6. Examination Management

Administrators can manage examinations.

Required functionality:

Create examination
Edit examination
View examination
Activate examination
Deactivate examination
Delete examination where appropriate
Add questions
Edit questions
Remove questions
Configure duration
View examination sessions

Each examination should contain at minimum:

Title
Description
Duration
Status
Questions
Creation timestamp
7. Question Management

The MVP uses multiple-choice questions.

Each question should support:

Question text
Option A
Option B
Option C
Option D
Correct answer
Examination association

Students must not receive the correct answer through the frontend before submission.

Question and answer validation must occur on the backend where appropriate.

8. Examination Sessions

Each student examination attempt must have an examination session.

A session should track:

Session ID
Student
Examination
Start time
End time
Status
Score where applicable

Possible session states include:

NOT_STARTED
IN_PROGRESS
SUBMITTED
COMPLETED
EXPIRED

The exact state model may be refined during implementation while maintaining the same functional behavior.

Students must only be able to access their own active examination sessions.

9. Student Answers

Student answers must be associated with:

Examination session
Student
Question
Selected answer
Timestamp where useful

Students must only be able to create or modify answers belonging to their own active examination session.

Students must never access another student's answers.

10. AI Monitoring

AI monitoring operates during an active examination session.

Required monitoring categories:

Head left
Head right
Head up
Head down
Looking away
Face absent
Multiple faces
Mobile phone

The system should favor temporal analysis over single-frame decisions.

AI monitoring is intended to identify predefined observable conditions and generate evidence.

It is not intended to make autonomous misconduct decisions.

11. AI Technology
11.1 Face and Head Monitoring

The preferred technology is:

MediaPipe Face Landmarker

Required purposes:

Face presence detection
Facial landmark detection
Head orientation estimation
Head left detection
Head right detection
Head up detection
Head down detection
Looking-away detection

Preferred processing flow:

Webcam
   ↓
MediaPipe Face Landmarker
   ↓
Face Detection
   ↓
Facial Landmarks / Transformation
   ↓
Head Pose Estimation
   ↓
Temporal Smoothing
   ↓
Monitoring Rule Engine
   ↓
Monitoring Event
11.2 Mobile Phone Detection

The preferred object detection technology is:

YOLO

The MVP only requires:

Mobile phone / cell phone detection

The monitoring system must filter object detection results to the mobile-phone class.

The MVP does not require detection of:

Smartwatch
Digital camera
Laptop
Tablet
Other prohibited devices

Additional object categories must not be introduced without an explicit requirement.

12. AI Processing Architecture

Where technically practical, AI inference should occur locally in the student's browser.

Preferred architecture:

Webcam
   ↓
Student Browser
   ↓
MediaPipe / YOLO
   ↓
Monitoring Rule Engine
   ↓
Suspicious Condition
   ↓
Evidence Generation
   ↓
FastAPI Backend
   ↓
Database / Evidence Storage
   ↓
WebSocket
   ↓
Admin Dashboard

The system should not continuously upload raw webcam video to the backend.

Only required monitoring information and evidence should be transmitted.

13. Monitoring Rules

Monitoring rules determine when an observable condition becomes a meaningful monitoring event.

Baseline MVP rules:

Activity	Minimum Duration	Required Occurrences	Confidence	Severity
HEAD_LEFT	>3 sec	3	>=0.75	Medium
HEAD_RIGHT	>3 sec	3	>=0.75	Medium
HEAD_UP	>3 sec	3	>=0.75	Medium
HEAD_DOWN	>3 sec	3	>=0.75	Medium
LOOKING_AWAY	>3 sec	3	>=0.75	Medium
FACE_ABSENT	>3 sec	1	Configurable	High
MULTIPLE_FACES	>2 sec	1	Configurable	High
MOBILE_PHONE	approximately 0.5 sec	1	>=0.40	High

These are baseline values.

The values should be configurable rather than duplicated as hard-coded values throughout the application.

Thresholds should be calibrated during testing.

14. Temporal Rule Engine

The monitoring system must reduce false positives caused by individual noisy frames.

The rule engine should consider:

Detection confidence
Detection duration
Number of occurrences
Detection persistence
Activity type
Severity
Configured thresholds

Example:

Head turns right
      ↓
Confidence >= threshold
      ↓
Condition persists >3 seconds
      ↓
Occurrence counted
      ↓
Repeated occurrence
      ↓
Configured threshold satisfied
      ↓
Monitoring Event

Mobile phone detection:

Mobile phone detected
      ↓
Confidence >= threshold
      ↓
Persistence approximately 1 second
      ↓
Monitoring Event
      ↓
Evidence Capture

The rule engine should prevent repeated event generation from the same continuous detection unless the configured event logic allows it.

15. Monitoring Event

A monitoring event represents a condition that has satisfied the configured monitoring rule.

Each event should contain:

Event ID
Student ID
Examination ID
Session ID
Event type
Activity type
Confidence
Duration
Occurrence count
Severity
Detection timestamp
Status

Recommended event statuses:

PENDING_REVIEW
CONFIRMED
IGNORED

Example:

Event ID: EVT-2026-000145
Student ID: STU-1024
Exam ID: DEMO-EXAM-01
Activity: HEAD_RIGHT
Severity: Medium
Confidence: 87.4%
Duration: 4.2 seconds
Occurrence: 3/3
Detected At: 2026-08-22 12:21:14
Status: PENDING_REVIEW
16. Evidence Generation

Evidence is generated when a configured monitoring rule is satisfied.

Evidence should normally include:

Evidence ID
Event ID
Image
Image path
Activity type
Confidence
Duration
Timestamp
Relevant metadata

Example storage structure:

evidence/
    2026/
        08/
            22/
                EVT-2026-000145.jpg

The evidence system should avoid unnecessary duplicate captures.

The system must not continuously capture or store webcam images.

Evidence storage should be implemented behind a service abstraction so local filesystem storage can later be replaced by object storage if required.

17. Real-Time Administrator Alerts

Administrators should receive monitoring alerts in real time.

Preferred architecture:

Student Browser
      ↓
AI Monitoring
      ↓
Monitoring Event
      ↓
FastAPI
      ↓
WebSocket
      ↓
Admin Dashboard

The admin dashboard should update without requiring a manual page refresh.

WebSocket should be used for:

Monitoring event notifications
Evidence notifications
Relevant status updates

WebSocket must not be used as a continuous webcam video transport mechanism.

18. Evidence Review

Administrators must be able to:

View evidence
View event details
View confidence
View duration
View timestamp
View activity type
View severity
Confirm evidence
Ignore or dismiss evidence
Add an optional review reason
Record the administrative action

Recommended status flow:

PENDING_REVIEW
      |
      +------> CONFIRMED
      |
      +------> IGNORED

AI-generated events must never automatically become final disciplinary decisions.

19. Administrator Dashboard

The administrator dashboard should provide an operational overview.

Recommended information:

Active examinations
Active students
Monitoring alerts
Pending evidence
High-severity events
Recent monitoring events
Examination status
Review statistics

The dashboard should prioritize information that helps administrators quickly identify sessions requiring attention.

20. Live Monitoring

The Live Monitoring screen should allow administrators to view active examination sessions.

Recommended information:

Student
Examination
Session status
Monitoring status
Latest alert
Alert severity
Event count
Latest event timestamp

The system should clearly distinguish normal activity from monitoring alerts.

21. Evidence Center

The Evidence Center should allow administrators to:

Browse evidence
Filter by student
Filter by examination
Filter by activity type
Filter by severity
Filter by status
Sort by timestamp
Open evidence details
Review evidence

The evidence interface should make the most important information immediately visible.

22. Auditability

Administrative actions must be recorded.

Examples include:

Evidence confirmed
Evidence ignored
Student account created
Student account disabled
Examination created
Examination modified
Question created
Question modified
Monitoring rule changed

Audit records should include:

Action ID
Administrator
Action type
Related entity
Reason where applicable
Timestamp

Audit records should not be editable by ordinary users.

23. Database Requirements

The foundational database contains:

users
students
exams
questions
exam_sessions
student_answers

The monitoring subsystem should contain:

monitoring_rules
monitoring_events
evidence
admin_actions
system_logs
24. Database Entities
24.1 users

Required fields:

id
username
password_hash
role
status
created_at
24.2 students

Required fields:

id
user_id
student_id
full_name
department
class
is_active
created_at
24.3 exams

Required fields:

id
title
description
duration_minutes
status
created_at
24.4 questions

Required fields:

id
exam_id
question_text
option_a
option_b
option_c
option_d
correct_answer
24.5 exam_sessions

Required fields:

id
student_id
exam_id
started_at
ended_at
status
score
24.6 student_answers

Required relationships:

exam_session
      +
question
      +
student
24.7 monitoring_rules

Required fields:

id
activity_type
enabled
min_duration_sec
required_occurrences
confidence_threshold
severity
24.8 monitoring_events

Required fields:

id
session_id
event_type
confidence
duration
occurrences
severity
detected_at
status
24.9 evidence

Required fields:

id
event_id
image_path
captured_at
metadata
24.10 admin_actions

Required fields:

id
event_id
admin_id
action
reason
created_at
25. API Requirements

The backend should expose consistent REST APIs.

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
PUT    /api/questions/{id}
DELETE /api/questions/{id}

POST   /api/exam-sessions
GET    /api/exam-sessions/{id}
POST   /api/exam-sessions/{id}/submit

POST   /api/monitoring/events
GET    /api/monitoring/events

GET    /api/evidence
GET    /api/evidence/{id}
POST   /api/evidence/{id}/review

GET    /api/audit

Exact endpoint naming may be refined during implementation while preserving consistency and authorization requirements.

26. WebSocket Requirements

A WebSocket channel is required for real-time administrator monitoring.

The WebSocket layer should support:

New monitoring event notification
New evidence notification
Relevant event status updates
Connection handling
Disconnection handling
Reconnection where practical

The WebSocket layer must not transport continuous webcam video.

27. Frontend Technology

The frontend must use:

React
Vite
JavaScript
Bootstrap 5.3
CSS3
Axios
React Router
Native WebSocket API

AI-related browser processing may use:

MediaPipe Face Landmarker
YOLO-compatible browser inference where practical

The frontend should remain lightweight.

Avoid unnecessary frontend frameworks or state-management libraries.

The following should not be introduced without a clear technical requirement:

Redux
Tailwind CSS
Next.js
jQuery
Angular
Vue
Heavy UI component libraries
28. Backend Technology

The backend must use:

Python
FastAPI
SQLAlchemy
MySQL
WebSocket support

The backend should be organized into clear modules such as:

backend/
└── app/
    ├── core/
    ├── db/
    ├── models/
    ├── schemas/
    ├── services/
    ├── websocket/
    └── main.py

The existing backend foundation must be preserved and extended incrementally.

29. Student UI Screens

Required student screens:

Login
Terms & Conditions
Camera Permission
System Readiness Check
Exam Instructions
Active Examination
Submission Confirmation
Exam Status / Result
30. Administrator UI Screens

Required administrator screens:

Admin Login
Dashboard
Live Monitoring
Evidence Center
Evidence Detail / Review
Student Management
Exam Management
Question Management
Examination Sessions
Audit / Action History
Monitoring Settings
31. UI/UX Requirements

The interface must be:

Professional
Modern
Minimal
Consistent
Responsive
Accessible
Fast
Easy to understand
31.1 Student Interface

The student interface should be:

Calm
Focused
Low-distraction
Clear
Simple

Avoid unnecessary animations and visual complexity.

The examination interface should keep important information visible, especially:

Question
Answer options
Current question
Navigation
Remaining time
Submit action
31.2 Administrator Interface

The administrator interface should be:

Information-rich
Operational
Easy to scan
Alert-focused
Efficient for evidence review

The interface should use consistent:

Cards
Tables
Badges
Alerts
Modals
Filters
Buttons
Form controls
32. Monitoring Terminology

The system must NOT use misleading wording such as:

CHEATING DETECTED
STUDENT IS CHEATING
AI CONFIRMED CHEATING

Preferred terminology:

Monitoring Alert
Suspicious Activity
Evidence Generated
Pending Review
Admin Review Required
Evidence Confirmed
Evidence Dismissed

This distinction must be maintained across:

UI
API responses
Database states
Logs
Documentation
33. Error Handling

The system must provide appropriate:

Loading states
Success states
Empty states
Error states
Retry states

Backend errors should use consistent API response structures.

Normal users must not receive:

Stack traces
Database errors
Internal filesystem paths
Secret values
Debug information
34. Security Requirements

The system must:

Hash passwords securely.
Enforce role-based authorization.
Validate user input.
Protect protected API endpoints.
Prevent unauthorized evidence access.
Prevent students from accessing other students' data.
Protect database credentials.
Keep secrets outside source code.
Avoid exposing sensitive error information.
Validate ownership of examination sessions.
Validate ownership of student answers.
Restrict monitoring administration to authorized administrators.
Prevent unauthorized modification of monitoring events.
Prevent students from modifying examination results.

Environment secrets must be stored outside source code.

The .env file must never be committed to Git.

A .env.example file should contain placeholders only.

35. Privacy Requirements

The system handles sensitive examination information.

Therefore:

Collect only required information.
Do not continuously store webcam video.
Generate evidence only when configured monitoring rules trigger.
Restrict evidence to authorized administrators.
Do not expose student monitoring information publicly.
Do not store credentials in source code.
Protect stored evidence.
Avoid unnecessary personal data collection.
Do not use monitoring evidence for purposes outside the examination system without authorization.
36. Performance Requirements

The system should prioritize responsive operation during examination sessions.

Requirements:

Avoid unnecessary backend traffic.
Avoid continuous video upload.
Use local AI processing where practical.
Use efficient WebSocket messaging.
Avoid excessive database queries.
Avoid unnecessary image captures.
Keep the admin dashboard responsive.
Keep the student examination interface lightweight.
Avoid unnecessary frontend re-renders.
Avoid blocking the examination interface with monitoring operations.
37. Testing Requirements

Every major feature must be tested.

37.1 Authentication Testing

Test:

Valid login
Invalid login
Inactive account
Student access to admin routes
Admin access
Logout
Protected endpoints
Unauthorized API requests
37.2 Examination Testing

Test:

Exam creation
Question creation
Exam assignment
Exam start
Answer submission
Question navigation
Timer
Exam submission
Session state
Score calculation
37.3 Camera Testing

Test:

Camera permission granted
Camera permission denied
Camera unavailable
Camera readiness
Face visible
Face unavailable
37.4 AI Testing

Test:

Face present
Face absent
Multiple faces
Head left
Head right
Head up
Head down
Looking away
Mobile phone
Temporal persistence
Confidence thresholds
False-positive scenarios
37.5 Evidence Testing

Test:

Event generation
Evidence capture
Evidence storage
Evidence retrieval
Evidence review
Evidence confirmation
Evidence dismissal
Audit record creation
37.6 Real-Time Testing

Test:

WebSocket connection
Monitoring event notification
Admin alert delivery
Connection recovery where practical
38. Current Implementation Status

The project already contains a working backend foundation.

Implemented and verified:

Git repository
Project structure
Python virtual environment
FastAPI application
MySQL database
SQLAlchemy database connection
Configuration system
User model
Student model
Exam model
Question model
ExamSession model
StudentAnswer model
Database tables
Health endpoint
Swagger/OpenAPI documentation
MySQL connectivity

Current foundational database tables:

users
students
exams
questions
exam_sessions
student_answers

The following major components remain to be implemented or fully verified:

Authentication API
Password hashing
Role-based authorization
Admin account management
Student account management
Examination APIs
Question APIs
Examination session APIs
Student examination workflow
React frontend
Camera permission workflow
Pre-exam system check
MediaPipe monitoring
YOLO mobile-phone detection
Temporal rule engine
Monitoring events
Evidence generation
Evidence storage
WebSocket monitoring
Admin dashboard
Live monitoring
Evidence center
Evidence review
Administrative actions
Audit history
End-to-end testing
Final hackathon demo preparation

Existing components must be preserved unless a justified architectural change is required.

39. Development Priorities

Development should follow this order:

Priority 1 — Authentication

Implement:

Password hashing
Login
Logout
Authentication
Role-based authorization
Admin account management
Student account management
Priority 2 — Examination Management

Implement:

Exam CRUD
Question CRUD
Examination sessions
Student answers
Exam submission
Basic scoring
Priority 3 — Student Examination Flow

Implement:

Terms & Conditions
Camera permission
Camera readiness
System check
Exam instructions
Exam interface
Timer
Submission
Priority 4 — AI Monitoring

Implement:

MediaPipe face detection
Head-pose estimation
Looking-away detection
Face absence
Multiple faces
YOLO mobile-phone detection
Priority 5 — Monitoring Rule Engine

Implement:

Duration tracking
Occurrence tracking
Confidence thresholds
Temporal smoothing
Event generation
Severity classification
Priority 6 — Evidence

Implement:

Evidence capture
Evidence storage
Evidence metadata
Evidence API
Evidence retrieval
Priority 7 — Administrator Monitoring

Implement:

WebSocket
Live monitoring
Real-time alerts
Evidence center
Evidence review
Administrative actions
Audit history
Priority 8 — Finalization

Implement:

Security review
Error handling
UI refinement
Performance improvements
Testing
Demo preparation
Documentation
40. MVP Scope
40.1 In Scope
Secure authentication
Administrator-created accounts
Student accounts
Examination management
Question management
Student examination
Camera permission
Pre-exam system check
AI-assisted monitoring
Head-pose monitoring
Looking-away detection
Face absence detection
Multiple-face detection
Mobile phone detection
Temporal monitoring rules
Evidence capture
Evidence storage
Real-time administrator alerts
Evidence review
Administrative decisions
Audit history
Professional responsive UI
40.2 Out of Scope

Unless explicitly approved:

Autonomous cheating decisions
Continuous video recording
Smartwatch detection
Digital-camera detection
Laptop detection
Tablet detection
Advanced biometric identification
Facial identity recognition
Complex cloud infrastructure
Microservice architecture
Kubernetes
Redis
Large-scale distributed systems
Mobile application
Unnecessary third-party integrations
Advanced production deployment infrastructure
41. Engineering Constraints

The project should remain lightweight and maintainable.

Do not introduce a technology simply because it is available.

Every new dependency should have a clear technical justification.

Prefer:

Existing project components
Simple architecture
Reusable services
Small focused modules
Clear API boundaries
Testable code

Avoid:

Unnecessary abstractions
Premature optimization
Over-engineering
Duplicate implementations
Unrelated refactoring
Rebuilding working components without justification
42. Implementation Rules

Before implementing a feature:

Inspect the existing code.
Inspect related database models.
Inspect existing APIs.
Check whether the functionality already partially exists.
Identify dependencies.
Define the smallest implementation needed.
Implement incrementally.
Test the change.
Verify that existing functionality still works.
Update documentation where required.

Never assume a missing-looking feature should be rebuilt from scratch.

Do not modify unrelated files.

Do not change the approved architecture without justification.

43. Definition of Done

A feature is complete only when:

The specified functionality is implemented.
Existing functionality remains working.
Validation exists.
Errors are handled.
Relevant tests pass.
API behavior is verified.
UI works where applicable.
Security requirements are satisfied.
No secrets are committed.
Documentation is updated where necessary.

Code being written does not automatically mean the feature is complete.

44. Final System Objective

Exam Nigahban should provide a secure, lightweight, explainable, and professional AI-assisted examination monitoring experience.

The final MVP should demonstrate the following complete flow:

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
Suspicious Condition
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

The system must remain focused on:

Reliable monitoring + explainable evidence + human review.

END OF PROJECT SPECIFICATION