# Exam Nigahban

## AI-Assisted Online Examination Monitoring & Evidence Generation Platform

Exam Nigahban is a secure web-based examination platform designed to support online examinations through real-time, AI-assisted monitoring and evidence generation.

The system monitors predefined examination conditions such as prolonged head movement, face absence, multiple faces, and mobile phone presence. When configured monitoring rules are satisfied, the system generates structured evidence and alerts an authorized administrator for human review.

> **Important:** Exam Nigahban provides AI-assisted monitoring and evidence generation. It does not autonomously determine that a student has cheated. Final decisions remain with an authorized administrator.

---

# Project Status

**Current Phase:** Foundation & Core Development

**Project Status:** In Development

**Target:** Hackathon MVP

**Primary Development Agent:** Claude Code

The project currently has a working backend and database foundation, including:

- FastAPI application
- MySQL database
- SQLAlchemy configuration
- Environment configuration
- User model
- Student model
- Exam model
- Question model
- Examination session model
- Student answer model
- Database tables
- Health endpoint
- Swagger/OpenAPI documentation

Major modules currently being developed include:

- Authentication
- Examination management
- Student examination workflow
- AI monitoring
- Evidence generation
- Real-time administrator monitoring
- Evidence review
- Audit logging
- Final UI/UX

---

# Project Objectives

- Provide a controlled online examination environment.
- Prevent unauthorized student account creation.
- Allow administrators to manage student and administrator accounts.
- Verify camera readiness before an examination begins.
- Monitor predefined examination conditions in real time.
- Apply temporal and confidence-based monitoring rules.
- Generate structured evidence when monitoring rules are triggered.
- Deliver monitoring alerts to administrators in real time.
- Provide evidence review and administrative action workflows.
- Maintain an auditable record of monitoring events and administrative decisions.
- Keep the system lightweight, explainable, and suitable for hackathon demonstration.

---

# Core Features

## Student

- Secure login
- Administrator-created accounts
- Terms & Conditions acceptance
- Mandatory camera permission
- Pre-exam system and camera verification
- Examination instructions
- Online examination
- Question navigation
- Examination timer
- Answer submission
- Examination status/result
- AI-assisted monitoring during examination

---

## AI-Assisted Monitoring

Exam Nigahban monitors the following predefined conditions:

- Head left detection
- Head right detection
- Head up detection
- Head down detection
- Looking-away detection
- Face absence detection
- Multiple-face detection
- Mobile phone detection
- Temporal duration evaluation
- Occurrence-based rule evaluation
- Confidence-based filtering
- Monitoring event generation
- Evidence image generation

The system uses temporal rules rather than relying only on individual frames in order to reduce false positives.

---

## Administrator

Administrators can:

- Securely log in
- Create student accounts
- Manage student accounts
- Create administrator accounts
- Manage administrator accounts
- Create and manage examinations
- Create and manage questions
- View examination sessions
- Monitor active examinations
- Receive real-time monitoring alerts
- View monitoring events
- Review evidence
- Confirm or dismiss monitoring events
- Record administrative actions
- View audit history
- Configure monitoring rules where authorized

---

# Monitoring Philosophy

Exam Nigahban follows a **human-in-the-loop** monitoring approach.

The system:

```text
Detects
   ↓
Evaluates
   ↓
Generates Evidence
   ↓
Alerts Administrator
   ↓
Human Review
   ↓
Administrative Decision

The AI system does not make a final determination of academic misconduct.

Monitoring events should therefore be described using terms such as:

Monitoring Alert
Suspicious Activity
Evidence Generated
Pending Review
Admin Review Required
Evidence Confirmed
Evidence Dismissed

The system should not present an AI-generated event as automatically confirmed cheating.

Technology Stack
Frontend
React
Vite
JavaScript (ES2022+)
Bootstrap 5.3
CSS3
Axios
React Router
Native WebSocket API
Browser MediaDevices API
AI / Computer Vision
MediaPipe Face Landmarker
Ultralytics YOLO
Browser-side processing where practical
Mobile phone detection as the initial object-detection scope
Face Monitoring

MediaPipe is used for:

Face detection
Facial landmarks
Head-pose estimation
Head direction
Looking-away analysis
Object Detection

YOLO is initially used only for:

Mobile phone detection

The MVP does not require:

Smartwatch detection
Digital camera detection
Laptop detection
Tablet detection
Other prohibited-device categories
Backend
Python
FastAPI
SQLAlchemy
Pydantic
WebSocket
Database
MySQL
Development Tools
Visual Studio Code
Git
GitHub
Claude Code
Postman
Google Chrome
High-Level Architecture
                    Student Browser
                           |
                           | Authentication
                           v
              +---------------------------+
              |      React Frontend       |
              |                           |
              |   Exam Interface          |
              |   Camera Interface        |
              |   MediaPipe                |
              |   YOLO                     |
              |   Monitoring Engine        |
              +-------------+-------------+
                            |
                            | Events / Evidence Metadata
                            v
              +---------------------------+
              |      FastAPI Backend       |
              |                           |
              | Authentication             |
              | Exam Services              |
              | Monitoring Services        |
              | Evidence Services          |
              | WebSocket Services         |
              +-------------+-------------+
                            |
                            v
              +---------------------------+
              |           MySQL            |
              |                           |
              | Users                       |
              | Students                    |
              | Exams                       |
              | Questions                   |
              | Sessions                    |
              | Answers                     |
              | Monitoring Rules            |
              | Monitoring Events           |
              | Evidence Metadata           |
              | Admin Actions               |
              +-------------+-------------+
                            |
                            | Real-Time Alerts
                            v
              +---------------------------+
              |     Administrator UI       |
              |                           |
              | Dashboard                  |
              | Live Monitoring            |
              | Evidence Center             |
              | Evidence Review            |
              | Administrative Actions     |
              | Audit History              |
              +---------------------------+
AI Monitoring Architecture
Webcam
   |
   v
Browser AI Processing
   |
   +----------------------------+
   |                            |
   v                            v
MediaPipe                    YOLO
   |                            |
   |                            |
Head / Face Analysis       Mobile Phone
   |                        Detection
   |                            |
   +-------------+--------------+
                 |
                 v
        Monitoring Rule Engine
                 |
                 v
       Temporal Rule Evaluation
                 |
                 v
        Monitoring Event
                 |
                 v
         Evidence Generation
                 |
                 v
          FastAPI Backend
                 |
                 +------------------+
                 |                  |
                 v                  v
              MySQL             WebSocket
                                    |
                                    v
                            Admin Dashboard
Monitoring Rules

The baseline MVP uses configurable monitoring rules.

Activity	Minimum Duration	Required Occurrences	Confidence	Severity
HEAD_LEFT	>3 sec	3	>=0.75	Medium
HEAD_RIGHT	>3 sec	3	>=0.75	Medium
HEAD_UP	>3 sec	3	>=0.75	Medium
HEAD_DOWN	>3 sec	3	>=0.75	Medium
LOOKING_AWAY	>3 sec	3	>=0.75	Medium
FACE_ABSENT	>5 sec	1	Configurable	High
MULTIPLE_FACES	>2 sec	1	Configurable	High
MOBILE_PHONE	~1 sec	1	>=0.80	High

These values are baseline configuration values and may be calibrated during testing.

Evidence Generation

When a configured monitoring rule is satisfied, the system generates a monitoring event and supporting evidence.

Evidence may include:

Evidence ID
Monitoring event ID
Student ID
Examination ID
Session ID
Activity type
Confidence
Duration
Occurrence count
Severity
Detection timestamp
Evidence image
Evidence metadata

Example:

Event ID: EVT-2026-000145
Student ID: STU-1024
Exam ID: DEMO-EXAM-01
Activity: HEAD_RIGHT
Severity: Medium
Confidence: 87.4%
Duration: 4.2 seconds
Occurrence: 3/3
Status: PENDING_REVIEW

The system does not continuously record or store webcam video.

Evidence is generated only when configured monitoring conditions are satisfied.

Real-Time Monitoring

The system uses WebSocket communication for real-time administrator notifications.

Student Browser
      |
      v
AI Monitoring
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

Administrators can receive:

Monitoring alerts
Evidence notifications
Relevant monitoring status updates

WebSocket is not used to continuously stream webcam video to the backend.

Student Examination Workflow
Student Login
      |
      v
Terms & Conditions
      |
      v
Accept Terms
      |
      v
Camera Permission
      |
      v
Pre-Exam System Check
      |
      v
Exam Instructions
      |
      v
Start Examination
      |
      v
AI-Assisted Monitoring
      |
      v
Answer Questions
      |
      v
Submit Examination
      |
      v
Submission Confirmation
      |
      v
Result / Status
Administrator Workflow
Administrator Login
        |
        v
Dashboard
        |
        v
Create Student
        |
        v
Create Examination
        |
        v
Add Questions
        |
        v
Monitor Active Examinations
        |
        v
Receive Monitoring Alert
        |
        v
Open Evidence
        |
        v
Review Evidence
        |
        +------> Confirm
        |
        +------> Dismiss
        |
        v
Administrative Action
        |
        v
Audit Record
Database Structure

The core database includes:

users
students
exams
questions
exam_sessions
student_answers
monitoring_rules
monitoring_events
evidence
admin_actions
system_logs
Main Relationships
User
 |
 +---- Student
 |
 +---- Administrator

Exam
 |
 +---- Questions
 |
 +---- Exam Sessions
          |
          +---- Student Answers
          |
          +---- Monitoring Events
                    |
                    +---- Evidence
                    |
                    +---- Admin Actions
Project Structure

The project follows a modular structure:

Exam-Nigahban/
│
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
│   └── tests/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── layouts/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── utils/
│   │   └── App.jsx
│   │
│   └── public/
│
├── ai/
│   ├── face/
│   ├── object/
│   ├── monitoring/
│   └── rules/
│
├── database/
│   ├── schema/
│   ├── seeds/
│   └── migrations/
│
├── docs/
│
├── evidence/
│
├── tests/
│
├── .env.example
├── .gitignore
├── CLAUDE.md
├── PROJECT_SPEC.md
├── TASKS.md
└── README.md

The exact repository structure may evolve during implementation while preserving the project's architectural boundaries.

Installation & Setup
Prerequisites

Install the following:

Python 3.12+
Node.js
npm
MySQL
Git
Google Chrome
Visual Studio Code
Backend Setup

Navigate to the backend directory:

cd backend

Create a Python virtual environment:

python -m venv .venv

Activate the environment on Windows:

.venv\Scripts\activate

Install backend dependencies:

pip install -r requirements.txt

Configure the environment variables using .env.

Example:

APP_NAME=Exam Nigahban API
APP_VERSION=1.0.0
ENVIRONMENT=development

DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_database_password
DB_NAME=exam_nigahban

SECRET_KEY=your_secure_secret_key

CORS_ORIGINS=http://localhost:5173

Never commit the real .env file.

Database Setup

Create the MySQL database:

CREATE DATABASE exam_nigahban;

Configure the database credentials in .env.

Run the backend initialization process according to the current project setup.

Verify the database connection before starting development.

Start Backend

From the backend directory:

uvicorn app.main:app --reload

The API should be available at:

http://127.0.0.1:8000

Health endpoint:

http://127.0.0.1:8000/health

Swagger documentation:

http://127.0.0.1:8000/docs
Frontend Setup

Navigate to the frontend directory:

cd frontend

Install dependencies:

npm install

Start the development server:

npm run dev

The frontend should normally be available at:

http://localhost:5173
Environment & Security

Sensitive configuration must never be committed to Git.

The project should use:

.env

for local secrets and:

.env.example

for safe configuration templates.

Never commit:

Database passwords
API keys
Secret keys
Authentication tokens
Private credentials
Sensitive evidence

Verify .gitignore before every public repository release.

Development Workflow

Development follows an incremental workflow:

Requirement
    |
    v
PROJECT_SPEC.md
    |
    v
TASKS.md
    |
    v
Claude Code
    |
    v
Implementation
    |
    v
Testing
    |
    v
Manual Verification
    |
    v
Git Checkpoint

The project uses:

PROJECT_SPEC.md — functional and technical specification
CLAUDE.md — Claude Code development instructions
TASKS.md — implementation task tracker
README.md — project overview and setup documentation

These documents should remain consistent with one another.

Development Principles

The project follows these principles:

Keep the architecture lightweight.
Avoid unnecessary dependencies.
Avoid over-engineering.
Reuse existing working components.
Implement features incrementally.
Test each major feature.
Keep security requirements mandatory.
Keep monitoring explainable.
Keep human review in the decision loop.
Do not continuously upload webcam video.
Do not expose sensitive student information.
Do not modify unrelated functionality.
Do not introduce architectural changes without justification.
Testing

The project should include:

Unit Testing
Authentication
Authorization
Examination services
Question services
Session services
Monitoring rules
Temporal rule engine
Evidence services
Integration Testing
Authentication APIs
Examination APIs
Session APIs
Monitoring APIs
Evidence APIs
WebSocket communication
End-to-End Testing

The complete workflow should be tested:

Admin Login
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
Camera Permission
    ↓
System Check
    ↓
Start Exam
    ↓
AI Monitoring
    ↓
Monitoring Event
    ↓
Evidence Generation
    ↓
Admin Alert
    ↓
Evidence Review
    ↓
Exam Submission
    ↓
Result
Current Development Priorities

Development should proceed in the following order:

Foundation verification
Authentication & authorization
Examination management
Student examination workflow
AI monitoring
Temporal monitoring rules
Evidence generation
Real-time administrator monitoring
Evidence review
Audit logging
UI/UX refinement
Security and performance review
End-to-end testing
Hackathon demo preparation

See TASKS.md for the detailed implementation checklist.

MVP Scope
Included
Secure authentication
Administrator-controlled accounts
Student management
Administrator management
Examination management
Question management
Examination sessions
Student answers
Camera permission
Pre-exam system check
AI-assisted monitoring
Head-pose monitoring
Looking-away detection
Face absence detection
Multiple-face detection
Mobile phone detection
Temporal monitoring rules
Evidence generation
Evidence storage
Real-time administrator alerts
Evidence review
Administrative actions
Audit logging
Professional responsive UI
Not Included in the MVP
Autonomous cheating decisions
Continuous webcam recording
Smartwatch detection
Digital camera detection
Laptop detection
Tablet detection
Facial identity recognition
Advanced biometric identification
Microservice architecture
Kubernetes
Redis
Large-scale distributed infrastructure
Mobile application
Unnecessary third-party integrations

Additional features require explicit approval before implementation.

Known Limitations

The MVP is an AI-assisted monitoring system rather than a perfect automated proctoring solution.

AI predictions may be affected by:

Lighting conditions
Camera quality
Camera positioning
Occlusion
Background conditions
Model confidence
Browser performance
Hardware limitations

Therefore, monitoring events are treated as evidence requiring human review.

Thresholds should be calibrated using realistic test scenarios before the final demonstration.

Documentation

The project documentation includes:

Document	Purpose
README.md	Project overview, setup and usage
PROJECT_SPEC.md	Functional and technical specification
CLAUDE.md	Claude Code development instructions
TASKS.md	Development task tracker
Hackathon Demonstration

The final demonstration should show the complete system flow:

Administrator
    ↓
Create Student
    ↓
Create Demo Examination
    ↓
Add Questions
    ↓
Student Login
    ↓
Terms & Conditions
    ↓
Camera Permission
    ↓
System Readiness Check
    ↓
Start Examination
    ↓
AI-Assisted Monitoring
    ↓
Trigger Monitoring Condition
    ↓
Generate Evidence
    ↓
Real-Time Administrator Alert
    ↓
Admin Reviews Evidence
    ↓
Confirm / Dismiss
    ↓
Audit Action
    ↓
Submit Examination
    ↓
Display Result / Status

The demonstration should emphasize:

AI-Assisted Monitoring + Explainable Evidence + Real-Time Alerts + Human Review

Final Objective

Exam Nigahban aims to provide a practical and professional online examination platform that combines:

Secure examination management
Browser-based AI monitoring
Temporal event evaluation
Evidence generation
Real-time administrator alerts
Human review
Auditability
Professional user experience

The system is designed to demonstrate how AI can assist examination monitoring while keeping final decisions under authorized human control.

License

This project is developed for educational, research, and hackathon purposes.

Project

Exam Nigahban

AI-Assisted Online Examination Monitoring & Evidence Generation Platform