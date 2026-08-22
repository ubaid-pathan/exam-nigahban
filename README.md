# Exam Nigahban

**AI-Assisted Online Examination Monitoring & Evidence Generation Platform**

Exam Nigahban is a secure web-based examination platform designed to support online exams through real-time, AI-assisted monitoring and evidence generation.

The system detects predefined monitoring conditions such as prolonged head movement, face absence, multiple faces, and mobile phone presence. When configurable monitoring rules are satisfied, the system generates evidence and alerts an administrator for human review.

> **Important:** Exam Nigahban provides AI-assisted monitoring and evidence generation. It does not autonomously determine that a student has cheated. Final decisions remain with an authorized administrator.

---

## Project Objectives

- Provide a controlled online examination environment.
- Prevent unauthorized student account creation.
- Verify camera readiness before an examination begins.
- Monitor predefined examination conditions in real time.
- Generate structured evidence when monitoring rules are triggered.
- Deliver monitoring alerts to administrators in real time.
- Provide an evidence review and administrative action workflow.
- Maintain an auditable record of monitoring events and administrative decisions.

---

## Core Features

### Student

- Secure login
- Terms & Conditions acceptance
- Mandatory camera permission
- Pre-exam system and camera verification
- Online examination
- Question navigation
- Examination timer
- Answer submission
- AI-assisted monitoring during examination

### AI-Assisted Monitoring

- Head left detection
- Head right detection
- Head up detection
- Head down detection
- Looking-away detection
- Face absence detection
- Multiple-face detection
- Mobile phone detection
- Temporal duration and occurrence-based rule evaluation
- Confidence-based event filtering
- Evidence image generation

### Administrator

- Secure administrator login
- Student account management
- Administrator account management
- Examination management
- Question management
- Live monitoring dashboard
- Real-time monitoring alerts
- Evidence center
- Evidence detail and review
- Confirm / dismiss monitoring events
- Administrative action history
- Audit logging

---

## Technology Stack

### Frontend

- React
- Vite
- JavaScript (ES2022+)
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
- Mobile phone detection as the initial object-detection scope

### Backend

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- WebSocket

### Database

- MySQL

### Development Tools

- Visual Studio Code
- Git
- GitHub
- Claude Code
- Postman
- Google Chrome

---

## High-Level Architecture

```text
Student Browser
      |
      | Secure Authentication
      v
+-----------------------+
|     React Frontend    |
|                       |
|  Exam Interface       |
|  Camera Interface     |
|  MediaPipe            |
|  YOLO                 |
|  Monitoring Engine    |
+-----------+-----------+
            |
            | Events / Evidence Metadata
            v
+-----------------------+
|     FastAPI Backend   |
|                       |
| Authentication        |
| Exam Services         |
| Monitoring Services   |
| Evidence Services     |
| WebSocket Services    |
+-----------+-----------+
            |
            v
+-----------------------+
|       MySQL           |
|                       |
| Users                 |
| Students              |
| Exams                 |
| Sessions              |
| Events                |
| Evidence Metadata     |
| Admin Actions         |
+-----------------------+
            |
            v
+-----------------------+
|   Admin Dashboard     |
|                       |
| Live Monitoring       |
| Evidence Review       |
| Administrative Action |
+-----------------------+

