# Exam Nigahban — University Deployment Proposal

**Document Type:** Formal Deployment Proposal  
**Prepared For:** University Examination Section  
**System:** Exam Nigahban — AI-Assisted Online Examination Monitoring Platform  
**Version:** 1.0  
**Date:** September 2026  
**Classification:** Official — For Internal Review  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Overview](#2-system-overview)
3. [Functional Capabilities](#3-functional-capabilities)
4. [Architecture & Technical Specifications](#4-architecture--technical-specifications)
5. [Security Framework](#5-security-framework)
6. [Data Privacy & Protection](#6-data-privacy--protection)
7. [Quality Assurance & Testing](#7-quality-assurance--testing)
8. [AI Monitoring — Accuracy & Limitations](#8-ai-monitoring--accuracy--limitations)
9. [Deployment Options](#9-deployment-options)
10. [Hardware & Infrastructure Requirements](#10-hardware--infrastructure-requirements)
11. [Standard Operating Procedures](#11-standard-operating-procedures)
12. [Risk Assessment & Mitigation](#12-risk-assessment--mitigation)
13. [Acceptance Criteria](#13-acceptance-criteria)
14. [Training Plan](#14-training-plan)
15. [Maintenance & Support](#15-maintenance--support)
16. [Compliance & Standards](#16-compliance--standards)
17. [Cost Analysis](#17-cost-analysis)
18. [Approval & Sign-Off](#18-approval--sign-off)

---

## 1. Executive Summary

Exam Nigahban is a web-based online examination platform with integrated AI-assisted monitoring designed to support universities in conducting secure, transparent, and auditable online examinations.

The system addresses a critical institutional need: **how to conduct online examinations with integrity while ensuring that no student is unfairly penalized by an automated system.**

Unlike conventional proctoring solutions that make autonomous decisions, Exam Nigahban follows a **human-in-the-loop** philosophy — AI detects and flags suspicious activity, generates structured evidence, and presents it to authorized examination administrators for review and final decision.

### Key Institutional Benefits

| Benefit | Description |
|---|---|
| **Examination Integrity** | Real-time AI monitoring of head movement, face absence, multiple persons, and mobile phone usage during examinations |
| **No Autonomous Decisions** | AI only generates evidence and alerts; final decisions remain with the examination controller |
| **Complete Audit Trail** | Every administrative action is timestamped, attributed, and permanently recorded |
| **Zero Licensing Cost** | Built entirely on open-source technology — no recurring software fees |
| **Data Sovereignty** | Can be deployed on university-owned servers; student data never leaves institutional control |
| **Privacy-First AI** | AI processing occurs in the student's browser; no continuous video is uploaded or stored |

### Verified System Metrics

| Metric | Value |
|---|---|
| Automated test suite | **464 tests** (264 backend + 200 frontend), all passing |
| API endpoints | **30+ REST endpoints** with role-based authorization |
| Database models | **9 relational models** with full referential integrity |
| Monitoring capabilities | **8 distinct AI-monitored conditions** |
| Frontend screens | **18 application pages** covering full student and admin workflows |
| WebSocket real-time channel | Live monitoring alerts with automatic reconnection |

---

## 2. System Overview

### 2.1 Purpose

To provide the university examination section with a secure, professional, and auditable platform for conducting online examinations with AI-assisted monitoring that supports — but does not replace — human judgment.

### 2.2 Design Philosophy

```
   AI Detects  →  Rule Engine Validates  →  Evidence Generated
        →  Administrator Alerted  →  Human Reviews  →  Decision Made
                                          →  Audit Recorded
```

The system **never** uses terminology such as "cheating detected" or "student is cheating." The correct institutional terminology is enforced throughout:

- Monitoring Alert
- Suspicious Activity Observed
- Evidence Generated
- Pending Review
- Admin Review Required
- Evidence Confirmed
- Evidence Dismissed

### 2.3 User Roles

| Role | Authority | Created By |
|---|---|---|
| **Administrator** | Full system access: manage students, exams, questions, monitoring, evidence review, audit history | System setup / other administrators |
| **Student** | Take assigned examinations only; no self-registration; no access to admin functions | Administrator-controlled creation only |

Students **cannot** self-register. All accounts are created by authorized administrators, preventing unauthorized access.

---

## 3. Functional Capabilities

### 3.1 Examination Management

| Capability | Status |
|---|---|
| Create, edit, activate, deactivate, delete examinations | Implemented |
| Add, edit, remove multiple-choice questions (4 options) | Implemented |
| Configure examination duration | Implemented |
| Assign examinations to students | Implemented |
| View examination sessions and results | Implemented |
| Automatic score calculation on submission | Implemented |

### 3.2 Student Examination Workflow

The system enforces a controlled, sequential workflow:

```
Student Login
    → Terms & Conditions (must accept)
    → Camera Permission (mandatory — cannot proceed without it)
    → Pre-Exam System Readiness Check
        • Camera availability verified
        • Camera stream validated
        • Face visibility confirmed
        • AI engine readiness checked
    → Exam Instructions
    → Start Examination (timer begins)
    → AI-Assisted Monitoring (active throughout)
    → Answer Questions with navigation
    → Submit Examination
    → Confirmation & Result
```

Each step is enforced on both frontend and backend. Students cannot skip steps or access examination content before authorization.

### 3.3 AI-Assisted Monitoring

| Monitored Condition | Detection Method | Severity |
|---|---|---|
| Head turned left (>3 sec, 3 occurrences) | MediaPipe Face Landmarker | Medium |
| Head turned right (>3 sec, 3 occurrences) | MediaPipe Face Landmarker | Medium |
| Head tilted up (>3 sec, 3 occurrences) | MediaPipe Face Landmarker | Medium |
| Head tilted down (>3 sec, 3 occurrences) | MediaPipe Face Landmarker | Medium |
| Looking away (>3 sec, 3 occurrences) | MediaPipe Face Landmarker | Medium |
| Face absent from frame (>5 sec) | MediaPipe Face Landmarker | High |
| Multiple faces detected (>2 sec) | MediaPipe Face Landmarker | High |
| Mobile phone visible (~1 sec) | YOLO Object Detection | High |

**Temporal Rule Engine:** The system does not flag single frames. Conditions must persist for configured durations and meet occurrence thresholds before generating an alert. This significantly reduces false positives caused by normal student movement.

### 3.4 Evidence Generation

When a monitoring rule is satisfied, the system captures:

| Evidence Component | Description |
|---|---|
| Evidence ID | Unique system identifier |
| Event ID | Associated monitoring event |
| Student ID | Identified student |
| Examination ID | Associated examination |
| Session ID | Examination session reference |
| Activity Type | Which condition was triggered |
| Confidence Score | AI confidence percentage (e.g., 87.4%) |
| Duration | How long the condition persisted |
| Occurrence Count | Number of times observed (e.g., 3/3) |
| Severity | Medium or High |
| Timestamp | Exact detection time |
| Evidence Image | Timestamped JPEG captured from webcam at moment of event |

Evidence images are stored in a structured directory: `evidence/YYYY/MM/DD/EVT-{id}.jpg`

### 3.5 Real-Time Administrator Alerts

Administrators receive monitoring alerts via WebSocket in real time without page refresh. The alert includes full event metadata, enabling immediate attention to sessions requiring review.

### 3.6 Evidence Review & Decision

Administrators can:
- View evidence with the captured image
- View all metadata (confidence, duration, severity, timestamps)
- **Confirm** the evidence (flag for further action)
- **Dismiss** the evidence (false positive / not actionable)
- Record a review reason
- All decisions are permanently recorded in the audit log

### 3.7 Administrative Dashboard

| Dashboard Feature | Description |
|---|---|
| Active examinations overview | Currently running examinations and their status |
| Active students | Students currently in examination sessions |
| Pending alerts | Monitoring events awaiting review |
| High-severity events | Priority events requiring immediate attention |
| Recent monitoring events | Chronological feed of all events |
| Review statistics | Confirmed vs. dismissed evidence counts |

### 3.8 Audit System

Every administrative action is recorded with:

| Audit Field | Description |
|---|---|
| Action ID | Unique identifier |
| Administrator | Who performed the action |
| Action Type | What was done (e.g., evidence confirmed, student disabled) |
| Related Entity | Which exam/student/event was affected |
| Reason | Optional justification provided by administrator |
| Timestamp | When the action was performed |

Audit records are **read-only** and cannot be modified or deleted by any user, ensuring institutional accountability.

---

## 4. Architecture & Technical Specifications

### 4.1 System Architecture

```
┌───────────────────────────────────────────────────────────┐
│                     Student Browser                        │
│                                                           │
│  Webcam → MediaPipe (Face/Head) → Temporal Rule Engine    │
│         → YOLO (Phone Detection)    → Evidence Capture    │
│                                                           │
│  AI processing is 100% browser-side. No raw video is      │
│  uploaded to the server.                                  │
└────────────────────────┬──────────────────────────────────┘
                         │ Events + Evidence (HTTPS)
                         v
┌───────────────────────────────────────────────────────────┐
│                   Application Server                       │
│                                                           │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │   Nginx     │  │   FastAPI    │  │   WebSocket    │  │
│  │  (Reverse   │→ │   Backend    │→ │  (Real-Time    │  │
│  │   Proxy)    │  │  (Gunicorn)  │  │   Alerts)      │  │
│  └─────────────┘  └──────┬───────┘  └────────┬───────┘  │
│                           │                    │          │
│                           v                    v          │
│                    ┌──────────────┐    ┌──────────────┐   │
│                    │   Database   │    │   Evidence   │   │
│                    │  (MySQL 8)   │    │   Storage    │   │
│                    └──────────────┘    └──────────────┘   │
└───────────────────────────────────────────────────────────┘
                         │
                         │ WebSocket (WSS)
                         v
┌───────────────────────────────────────────────────────────┐
│                Administrator Dashboard                     │
│  Live Monitoring | Evidence Center | Audit History         │
└───────────────────────────────────────────────────────────┘
```

### 4.2 Technology Stack

| Component | Technology | Version | License |
|---|---|---|---|
| Frontend Framework | React | 19.x | MIT |
| Build Tool | Vite | 8.x | MIT |
| UI Framework | Bootstrap | 5.3.x | MIT |
| Face/Head Analysis | MediaPipe Face Landmarker | 1.x | Apache 2.0 |
| Object Detection | YOLO (ONNX Runtime Web) | 1.29.x | MIT |
| Backend Framework | FastAPI | Latest | MIT |
| Application Server | Gunicorn + Uvicorn | Latest | MIT |
| ORM | SQLAlchemy | Latest | MIT |
| Database | MySQL | 8.0+ | GPL / Commercial |
| Authentication | JWT + bcrypt | Latest | MIT |
| Real-Time | WebSocket (native) | — | Standard |
| Reverse Proxy | Nginx | 1.24+ | BSD |

**All components are open-source with zero licensing fees.**

### 4.3 Database Schema

| Table | Purpose | Key Fields |
|---|---|---|
| `users` | Authentication & account management | id, username, password_hash, role, status |
| `students` | Student profiles | student_id, full_name, department, class |
| `exams` | Examination definitions | title, description, duration, status |
| `questions` | MCQ questions | question_text, options A-D, correct_answer |
| `exam_sessions` | Student examination attempts | start_time, end_time, status, score |
| `student_answers` | Submitted answers | session_id, question_id, selected_answer |
| `monitoring_events` | AI-generated alerts | event_type, confidence, duration, severity |
| `evidence` | Captured evidence images | event_id, image_path, metadata |
| `admin_actions` | Audit trail | admin_id, action, reason, timestamp |

### 4.4 API Endpoints

| Category | Endpoints | Authorization |
|---|---|---|
| Authentication | Login, Logout, Verify Token | Public / Authenticated |
| User Management | CRUD users, activate/deactivate | Admin only |
| Student Management | CRUD student profiles | Admin only |
| Exam Management | CRUD exams | Admin only |
| Question Management | CRUD questions per exam | Admin only |
| Exam Sessions | Create, view, submit | Role-based |
| Monitoring | Submit events, list events | Role-based |
| Evidence | List, view, review (confirm/dismiss) | Admin only |
| Dashboard | Operational statistics | Admin only |
| Audit | View audit history | Admin only |
| WebSocket | Real-time monitoring alerts | Admin only |

All endpoints enforce server-side authorization. The backend never trusts client-supplied role information.

---

## 5. Security Framework

### 5.1 Authentication

| Security Measure | Implementation |
|---|---|
| Password storage | bcrypt hashing (never stored in plaintext) |
| Token format | JSON Web Tokens (JWT) with HMAC-SHA256 signing |
| Token expiration | Configurable (default: 8 hours) |
| Secret key enforcement | Application refuses to start with placeholder or weak keys (< 32 chars) |
| Session validation | Token verified on every API request; inactive accounts rejected |
| Brute-force protection | Rate limiting configurable via Nginx |

### 5.2 Authorization

| Security Measure | Implementation |
|---|---|
| Role-based access control | Admin and Student roles enforced server-side |
| Endpoint protection | Every API route verifies authentication and role before processing |
| Data isolation | Students can only access their own sessions, answers, and results |
| Admin functions | Completely inaccessible to student accounts |
| Evidence access | Restricted to authorized administrators only |

### 5.3 Network Security

| Layer | Protection |
|---|---|
| Transport | HTTPS/TLS encryption (all traffic encrypted in transit) |
| WebSocket | WSS (encrypted WebSocket) |
| Database | Localhost-only binding; not exposed to network |
| Firewall | Only ports 80 (HTTP→HTTPS redirect) and 443 (HTTPS) open |
| CORS | Strictly limited to the university's domain |
| Evidence storage | Filesystem permissions restricted (750); Nginx `internal` directive prevents direct URL access |

### 5.4 Application Security

| Protection | Implementation |
|---|---|
| Input validation | Pydantic schemas validate all API inputs |
| Evidence image validation | Base64 decoding, JPEG magic-byte check, 300 KB size limit |
| Secret management | Environment variables in `.env` file; never committed to source control |
| Error handling | Internal errors never expose stack traces, database queries, or file paths to users |
| Audit immutability | Audit records are append-only; no update or delete operations available |

---

## 6. Data Privacy & Protection

### 6.1 Data Collection Policy

| Data Type | Collected | Purpose | Retention |
|---|---|---|---|
| Student name, ID, department | Yes | Account management | Until account deletion |
| Examination answers | Yes | Grading | Per institutional policy |
| Monitoring event metadata | Yes | Evidence review | Per institutional policy |
| Evidence images | Yes (only on rule trigger) | Administrative review | Per institutional policy |
| Webcam video | **No** | — | **Never recorded or stored** |
| Biometric data | **No** | — | Facial landmarks are computed in-browser and discarded |
| Location data | **No** | — | Not collected |

### 6.2 Privacy Architecture

1. **No continuous video upload.** The student's webcam feed is processed entirely within their browser. Only a single JPEG frame is captured when a monitoring rule is satisfied.

2. **No facial recognition.** The system detects face presence, head orientation, and multiple faces. It does not identify or compare facial features.

3. **Evidence is generated only on rule triggers.** The system does not continuously capture or store images. An evidence image is captured only after temporal rules confirm a monitoring condition.

4. **Evidence access is restricted.** Only authorized administrators can view evidence. Evidence images are served through Nginx's `internal` directive and cannot be accessed via direct URL.

5. **No third-party data sharing.** All data remains within the university's infrastructure. No external APIs, analytics services, or cloud storage are required.

### 6.3 Data Retention

The system does not enforce automatic data deletion. Retention periods should be configured according to the university's examination data retention policy. Recommended:

| Data | Recommended Retention |
|---|---|
| Examination records | 3 years minimum |
| Evidence images | Until conclusion of any related academic proceedings |
| Audit logs | Permanent (indefinite retention) |
| Student accounts | Until graduation or de-enrollment + 1 year |

---

## 7. Quality Assurance & Testing

### 7.1 Test Suite Summary

| Category | Test Count | Framework | Status |
|---|---|---|---|
| Backend API tests | **264 tests** | pytest + httpx | All passing |
| Frontend unit tests | **200 tests** | Vitest | All passing (17 test files) |
| **Total** | **464 automated tests** | — | **All passing** |

### 7.2 Backend Test Coverage

| Test Module | Coverage Area |
|---|---|
| `test_auth.py` | Login, logout, invalid credentials, token validation, inactive accounts |
| `test_admin_management.py` | Admin account CRUD, role enforcement |
| `test_student_management.py` | Student CRUD, activation/deactivation, profile management |
| `test_exams.py` | Exam CRUD, status management, authorization |
| `test_student_exams.py` | Session creation, answer submission, timer, scoring |
| `test_monitoring.py` | Event ingestion, rule validation, severity classification |
| `test_monitoring_events.py` | Event lifecycle, temporal validation, edge cases |
| `test_evidence.py` | Evidence capture, image validation, storage, retrieval |
| `test_admin_dashboard.py` | Dashboard statistics, operational overview |
| `test_audit.py` | Audit log creation, immutability, query |
| `test_audit_log.py` | Extended audit trail verification |
| `test_create_admin.py` | Admin CLI creation tool |
| `test_config.py` | Configuration validation, secret key enforcement |

### 7.3 Frontend Test Coverage

| Test Module | Coverage Area |
|---|---|
| `adminAlertsSocket.test.js` | WebSocket connection, reconnection, error handling, StrictMode safety |
| `headPose.test.js` | Head orientation estimation from facial landmarks |
| `temporalRuleEngine.test.js` | Duration tracking, occurrence counting, event generation |
| `evidenceCapture.test.js` | Image capture, base64 encoding, validation |
| `useMobilePhoneMonitoring.test.js` | YOLO integration, phone detection lifecycle |
| `mobilePhoneMonitorService.test.js` | Phone monitoring service, worker communication |
| `decode.test.js` | YOLO output decoding |
| `preprocess.test.js` | Image preprocessing for model input |
| `yoloxWorkerClient.test.js` | Web Worker communication, error recovery |
| Additional tests | Observation tracking, phone observation, monitoring API |

### 7.4 Running Tests

```bash
# Backend
cd backend
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows
pytest tests/ -v

# Frontend
cd frontend
npx vitest run
```

---

## 8. AI Monitoring — Accuracy & Limitations

### 8.1 How It Works

The AI monitoring system uses two browser-side models:

**MediaPipe Face Landmarker** processes the webcam feed to:
- Detect face presence/absence
- Extract 478 facial landmarks
- Estimate head orientation (pitch, yaw, roll)
- Classify head direction (left, right, up, down, looking away)
- Detect multiple faces in frame

**YOLO (ONNX Runtime)** processes downsampled frames to:
- Detect mobile phones in the camera view
- Filter detections to the "cell phone" class only

### 8.2 False Positive Mitigation

The system employs multiple layers of false positive reduction:

1. **Confidence Thresholds:** Detections below 75% confidence (head) or 80% confidence (phone) are discarded.
2. **Duration Requirements:** Head conditions must persist for >3 seconds. Face absence requires >5 seconds.
3. **Occurrence Counting:** Head events require 3 separate occurrences before triggering.
4. **Temporal Smoothing:** Single anomalous frames are ignored; sustained patterns are required.
5. **Human Review:** Even when all rules trigger, the event is flagged as "Pending Review" — not a final decision.

### 8.3 Known Limitations (Transparent Disclosure)

| Limitation | Impact | Mitigation |
|---|---|---|
| Poor lighting | Reduced detection confidence | Pre-exam system check advises student; low-confidence events are filtered |
| Low-quality webcam | Inaccurate head pose estimation | System readiness check validates camera stream |
| Camera positioning | Angled cameras may affect direction detection | Calibration during readiness check |
| Background objects | Possible false phone detection | Temporal rules require sustained detection; human review |
| Multiple people passing by | Multiple face triggers | Human review distinguishes exam environment |
| Browser performance | Slower inference on old hardware | Graceful degradation; events still timestamped |

**These limitations are why the system does not make autonomous decisions.** Every alert is evidence for human review, not a verdict.

---

## 9. Deployment Options

### Option A: On-Premises University Server (Recommended)

| Aspect | Detail |
|---|---|
| Hosting | University data center or server room |
| Domain | `exam-nigahban.university.edu.pk` (or institutional subdomain) |
| Data location | 100% on university infrastructure |
| Network access | LAN + optional internet for remote students |
| SSL | University CA or Let's Encrypt |
| Maintenance | University IT department |
| **Advantage** | Full data sovereignty; no recurring cloud costs; LAN-speed access |

### Option B: Cloud Deployment

| Aspect | Detail |
|---|---|
| Backend hosting | Render (Web Service) |
| Frontend hosting | Vercel |
| Database | Neon PostgreSQL (free tier available) |
| Domain | Custom domain mapped to cloud services |
| Data location | Cloud provider data centers |
| **Advantage** | Zero infrastructure maintenance; automatic scaling; already partially configured |

### Option C: Hybrid

| Aspect | Detail |
|---|---|
| Backend + Database | On-premises university server |
| Frontend | Cloud CDN (Vercel) for global performance |
| **Advantage** | Data sovereignty for backend; fast frontend delivery |

**Recommendation for University:** Option A (On-Premises) is recommended for maximum data control, zero recurring costs, and compliance with institutional data governance policies.

---

## 10. Hardware & Infrastructure Requirements

### 10.1 Server Requirements (On-Premises)

| Resource | Minimum | Recommended (100 concurrent students) |
|---|---|---|
| CPU | 4 cores | 8 cores |
| RAM | 8 GB | 16 GB |
| Storage | 50 GB SSD | 200 GB SSD (evidence accumulates over time) |
| OS | Ubuntu 22.04 LTS or Windows Server 2019+ | Ubuntu 22.04 LTS |
| Network | 100 Mbps LAN | 1 Gbps LAN |
| Python | 3.12+ | 3.12+ |
| Node.js | 18 LTS | 20 LTS |
| MySQL | 8.0+ | 8.0+ |
| Nginx | 1.24+ | Latest stable |

> **No GPU required.** AI processing runs in each student's browser, not on the server.

### 10.2 Student Workstation Requirements

| Requirement | Specification |
|---|---|
| Browser | Google Chrome 110+ or Mozilla Firefox 115+ |
| Webcam | Built-in or USB webcam (mandatory) |
| JavaScript | Enabled |
| Screen resolution | 1280×720 minimum |
| RAM | 4 GB minimum (AI models run in browser) |
| Internet/LAN | Stable connection to server |

---

## 11. Standard Operating Procedures

### 11.1 Before Examination Day

| Step | Action | Responsible |
|---|---|---|
| 1 | Verify server is running: `systemctl status exam-nigahban` | IT Administrator |
| 2 | Verify database connectivity: check `/health` endpoint | IT Administrator |
| 3 | Create student accounts for all examinees | Examination Controller |
| 4 | Create examination and add questions | Examination Controller |
| 5 | Verify monitoring rules are configured (default thresholds recommended) | Examination Controller |
| 6 | Conduct a pilot test with 2-3 students to verify camera + monitoring | IT Administrator |

### 11.2 During Examination

| Step | Action | Responsible |
|---|---|---|
| 1 | Students log in with provided credentials | Students |
| 2 | Students complete camera check and system readiness | Students |
| 3 | Monitor the Admin Dashboard for real-time alerts | Examination Controller |
| 4 | Review high-severity alerts immediately | Examination Controller |
| 5 | Flag or dismiss alerts as they arrive | Examination Controller |

### 11.3 After Examination

| Step | Action | Responsible |
|---|---|---|
| 1 | Review all pending evidence in the Evidence Center | Examination Controller |
| 2 | Confirm or dismiss each evidence item with reason | Examination Controller |
| 3 | Export audit log for institutional records | Examination Controller |
| 4 | Review examination results and scores | Examination Controller |
| 5 | Archive evidence per institutional retention policy | IT Administrator |

### 11.4 Incident Response

If a student disputes a monitoring event:

1. The administrator opens the Evidence Center
2. Locates the specific evidence by student, exam, or timestamp
3. Shows the evidence image, confidence score, and duration
4. The administrator's decision (confirm/dismiss) with reason is recorded in the audit log
5. The audit log serves as the institutional record of the review process

---

## 12. Risk Assessment & Mitigation

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Server downtime during exam | Low | High | Systemd auto-restart; Nginx health checks; backup server on standby |
| Database corruption | Very Low | Critical | Daily automated backups; MySQL binary logging enabled |
| AI false positive accuses innocent student | Medium | High | Temporal rules reduce false positives; human review is mandatory; evidence must be confirmed by admin |
| Student claims monitoring didn't work | Low | Medium | Pre-exam system readiness check validates camera + AI; all events are logged |
| Unauthorized access to evidence | Low | High | Filesystem permissions (750); Nginx internal directive; admin-only API access; JWT authentication |
| Network failure during exam | Medium | Medium | Answers are submitted to backend in real time; session state preserved; student can reconnect |
| Secret key compromise | Very Low | Critical | Key validation enforces minimum 32 chars; key is never logged or transmitted |
| Evidence storage full | Low | Medium | Monitoring alerts when disk usage exceeds threshold; evidence retention policy |

---

## 13. Acceptance Criteria

The system is ready for production deployment when the following criteria are satisfied:

### 13.1 Functional Acceptance

| # | Criterion | Verification Method |
|---|---|---|
| 1 | Admin can create student accounts | Manual test |
| 2 | Admin can create exams with questions | Manual test |
| 3 | Student can log in and complete the full exam workflow | Manual test |
| 4 | Camera permission is enforced (cannot bypass) | Manual test |
| 5 | System readiness check validates camera and AI | Manual test |
| 6 | AI monitoring detects all 8 conditions | Controlled demo |
| 7 | Evidence is generated with image and metadata | Controlled demo |
| 8 | Admin receives real-time alerts | Manual test |
| 9 | Admin can review, confirm, and dismiss evidence | Manual test |
| 10 | Audit log records all administrative actions | Manual test |
| 11 | Students cannot access admin functions | Security test |
| 12 | Students cannot access other students' data | Security test |
| 13 | All 464 automated tests pass | `pytest` + `vitest run` |

### 13.2 Security Acceptance

| # | Criterion | Verification Method |
|---|---|---|
| 1 | HTTPS is enforced; HTTP redirects to HTTPS | Browser test |
| 2 | JWT tokens expire after configured time | API test |
| 3 | Passwords are never stored in plaintext | Database inspection |
| 4 | `.env` file is not accessible via web | URL test |
| 5 | Database port is not exposed externally | Port scan |
| 6 | CORS restricts to university domain only | Browser devtools |
| 7 | Evidence images cannot be accessed without authentication | Direct URL test |

### 13.3 Performance Acceptance

| # | Criterion | Target |
|---|---|---|
| 1 | API response time (non-monitoring) | < 200ms |
| 2 | Dashboard load time | < 3 seconds |
| 3 | WebSocket alert delivery | < 1 second |
| 4 | Concurrent student support | 50+ simultaneous sessions |

---

## 14. Training Plan

### 14.1 IT Administrator Training (1 day)

| Topic | Duration |
|---|---|
| System architecture overview | 1 hour |
| Server installation and configuration | 2 hours |
| SSL/TLS setup | 30 minutes |
| Backup and recovery procedures | 1 hour |
| Monitoring server health and logs | 1 hour |
| User management and troubleshooting | 1 hour |
| Security hardening checklist | 30 minutes |

### 14.2 Examination Controller Training (1 day)

| Topic | Duration |
|---|---|
| System overview and philosophy | 1 hour |
| Creating student accounts (bulk) | 1 hour |
| Creating exams and managing questions | 1.5 hours |
| Live monitoring dashboard walkthrough | 1 hour |
| Evidence review workflow (confirm/dismiss) | 1.5 hours |
| Audit log and reporting | 30 minutes |
| Hands-on practice session | 1.5 hours |

### 14.3 Student Orientation (30 minutes, before first exam)

| Topic | Duration |
|---|---|
| How to log in | 5 minutes |
| Camera permission and system check | 10 minutes |
| Exam interface walkthrough | 10 minutes |
| What monitoring means (and what it doesn't mean) | 5 minutes |

---

## 15. Maintenance & Support

### 15.1 Routine Maintenance

| Task | Frequency | Responsible |
|---|---|---|
| Database backup | Daily (automated) | IT Administrator |
| Evidence storage backup | Weekly (automated) | IT Administrator |
| OS security updates | Monthly | IT Administrator |
| Application dependency updates | Quarterly | Developer / IT |
| SSL certificate renewal | Annually (auto with Let's Encrypt) | IT Administrator |
| Log rotation and cleanup | Monthly | IT Administrator |
| Disk usage monitoring | Weekly (automated alert) | IT Administrator |

### 15.2 Support Escalation

| Level | Issue Type | Response Time | Contact |
|---|---|---|---|
| L1 | Student login issues, camera problems | Immediate | IT Helpdesk |
| L2 | Server issues, database connectivity | Within 1 hour | IT Administrator |
| L3 | Application bugs, feature requests | Within 24 hours | Development Team |

---

## 16. Compliance & Standards

### 16.1 Technical Standards Met

| Standard | Applicability |
|---|---|
| HTTPS/TLS encryption | All data in transit |
| bcrypt password hashing | OWASP password storage guidelines |
| JWT (RFC 7519) | Token-based authentication |
| REST API design | Consistent, well-documented endpoints |
| Role-based access control (RBAC) | Authorization enforcement |
| SQL injection prevention | SQLAlchemy parameterized queries |
| Input validation | Pydantic schema validation on all inputs |
| Content Security | CORS, security headers, evidence access controls |

### 16.2 Institutional Compliance

| Requirement | How the System Addresses It |
|---|---|
| Student data protection | Data stored on university servers only; no third-party access |
| Examination record integrity | Database referential integrity; audit trail for all actions |
| Fair assessment | AI does not make final decisions; human review required |
| Transparency | Students can view their results; evidence is reviewable with full metadata |
| Accountability | Every admin action is permanently logged with identity and timestamp |
| Non-discrimination | AI does not perform facial recognition or identity-based analysis |

### 16.3 Open-Source Compliance

All dependencies use permissive open-source licenses (MIT, Apache 2.0, BSD). No GPL-licensed code is linked in a way that would require source disclosure of the university's modifications. The system can be freely used, modified, and deployed without licensing concerns.

---

## 17. Cost Analysis

### 17.1 On-Premises Deployment

| Item | One-Time Cost | Recurring Cost |
|---|---|---|
| Server hardware (if new) | PKR 150,000 – 300,000 | — |
| Or: existing university server | PKR 0 | — |
| Software licenses | **PKR 0** | **PKR 0** |
| SSL certificate | **PKR 0** | **PKR 0** |
| Domain (if new subdomain) | PKR 0 | PKR 0 (university domain) |
| Electricity & network | — | Minimal (existing infrastructure) |
| IT staff training | 1 day | — |
| Annual maintenance | — | Negligible |
| **Total Year 1** | **PKR 0 – 300,000** | **Near zero** |

### 17.2 Comparison: Commercial Proctoring Solutions

| Commercial Solution | Typical Cost | Data Control |
|---|---|---|
| Cloud-based proctoring (per student/exam) | PKR 200–500 per student per exam | Data on vendor servers |
| Enterprise proctoring license | PKR 500,000 – 2,000,000/year | Vendor-dependent |
| **Exam Nigahban** | **PKR 0 licensing** | **100% university-controlled** |

**For 500 students × 2 exams/semester:** A commercial solution would cost PKR 200,000–500,000 per semester. Exam Nigahban costs PKR 0 in licensing, permanently.

---

## 18. Approval & Sign-Off

### 18.1 Stakeholder Review

| Stakeholder | Role | Review Date | Signature |
|---|---|---|---|
| Controller of Examinations | Functional approval | ___________ | ___________ |
| Director IT / CIO | Technical approval | ___________ | ___________ |
| Dean / Academic Head | Institutional approval | ___________ | ___________ |
| Legal / Compliance Officer | Privacy & policy review | ___________ | ___________ |

### 18.2 Deployment Authorization

| Milestone | Date | Authorized By |
|---|---|---|
| Proposal accepted | ___________ | ___________ |
| Server provisioned | ___________ | ___________ |
| System installed and configured | ___________ | ___________ |
| Testing and UAT completed | ___________ | ___________ |
| Staff training completed | ___________ | ___________ |
| Pilot examination conducted | ___________ | ___________ |
| **Production deployment approved** | ___________ | ___________ |

---

## Appendix A: Demonstration Script

For presenting to the examination section, the following demo flow showcases the complete system:

```
1. Administrator Login
   → Show professional dashboard with statistics

2. Create Student Account
   → Demonstrate admin-controlled account creation

3. Create Examination
   → Add 5 MCQ questions with correct answers

4. Student Login
   → Show controlled workflow: Terms → Camera → System Check → Instructions

5. Student Starts Examination
   → Show clean, low-distraction exam interface with timer

6. AI Monitoring in Action
   → Deliberately look away from camera (triggers HEAD_RIGHT after 3 sec × 3)
   → Show evidence being generated in real time

7. Administrator Receives Alert
   → Dashboard updates in real time without page refresh

8. Evidence Review
   → Open Evidence Center
   → Show evidence image, confidence (87%), duration (4.2 sec), severity
   → Demonstrate Confirm and Dismiss with reason

9. Student Submits Exam
   → Show confirmation and result

10. Audit Log
    → Show complete trail: exam created, student created, evidence reviewed
    → Emphasize: every action is recorded with administrator identity

Key Message: "The AI detected, the system recorded, the human decided."
```

## Appendix B: Evidence Sample

Example monitoring event as presented to administrators:

```
Event ID:        EVT-2026-000145
Student:         Ahmad Khan (FA22-BCS-001)
Examination:     Introduction to Artificial Intelligence
Session:         SES-2026-0042
Activity:        HEAD_RIGHT
Severity:        Medium
Confidence:      87.4%
Duration:        4.2 seconds
Occurrences:     3/3
Detected At:     2026-09-04 10:21:14 UTC
Status:          PENDING_REVIEW
Evidence Image:  2026/09/04/EVT-000145.jpg
```

## Appendix C: Glossary

| Term | Definition |
|---|---|
| **Monitoring Event** | An AI-detected condition that has satisfied temporal rules and been recorded |
| **Evidence** | A monitoring event with supporting image and metadata |
| **Temporal Rule** | A condition requiring sustained detection over time before triggering |
| **Human-in-the-Loop** | Design philosophy where AI assists but humans make final decisions |
| **Evidence Review** | Administrative process of confirming or dismissing an AI-generated event |
| **Audit Trail** | Immutable record of all administrative actions in the system |
| **WebSocket** | Real-time communication channel for instant admin alerts |
| **MediaPipe** | Google's framework for browser-based face and landmark detection |
| **YOLO** | Real-time object detection model used for mobile phone detection |
| **RBAC** | Role-Based Access Control — restricting system access based on user role |

---

**Document End**

*Exam Nigahban — Reliable Monitoring. Explainable Evidence. Human Review.*
