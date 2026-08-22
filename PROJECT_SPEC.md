# Exam Nigahban — Project Specification

**Document:** PROJECT_SPEC.md  
**Project:** Exam Nigahban  
**Version:** 1.0  
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

---

# 2. Project Goals

The MVP must demonstrate:

1. Secure administrator and student authentication.
2. Administrator-controlled account creation.
3. Online examination management.
4. Controlled student examination workflow.
5. Camera permission enforcement.
6. Pre-examination system readiness verification.
7. Real-time AI-assisted monitoring.
8. Temporal monitoring rules.
9. Mobile phone detection.
10. Evidence generation.
11. Real-time administrator alerts.
12. Evidence review and administrative action.
13. Auditability.
14. Professional responsive UI/UX.

---

# 3. User Roles

## 3.1 Administrator

Administrators can:

- Log in securely.
- Create student accounts.
- Create administrator accounts.
- Manage students.
- Create and manage exams.
- Add and manage questions.
- View examination sessions.
- Monitor active examinations.
- Receive real-time monitoring alerts.
- Review evidence.
- Confirm or dismiss evidence.
- Record administrative actions.
- View audit history.

---

## 3.2 Student

Students can:

- Log in using administrator-provided credentials.
- View examination terms and conditions.
- Accept required terms.
- Grant camera permission.
- Complete system readiness checks.
- Start an assigned examination.
- Answer questions.
- Navigate questions.
- View remaining examination time.
- Submit the examination.
- View appropriate examination status/result information.

Students cannot:

- Self-register.
- Create administrator accounts.
- Modify monitoring rules.
- Access other students' examinations.
- Access administrative functions.
- Access other students' evidence.

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