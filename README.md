# JARVIS — Joint Autonomous Reasoning & Vision Inspection System

**Group No. 12**  
*Adib Sajjad Patel* (Roll No. 26 | Enrollment No. 24211320284)  
*Rudra Sujit Sagar* (Roll No. 27 | Enrollment No. 24211320291)  
*Abhishek Sharadchandra Chavan* (Roll No. 24 | Enrollment No. 24211320226)  
*Rasiklal M. Dhariwal Institute of Technology*  
*Diploma in Computer Engineering | 5th Semester*  

---

## 1. Project Overview

**JARVIS** is an AI-based manufacturing monitoring web application designed for modern industrial floors. It bridges the gap between passive computer-vision detection and active autonomous reasoning. Built with a decoupled client-server architecture, JARVIS pairs a high-performance **HTML5/CSS3/JavaScript** single-page frontend with a robust **FastAPI + Python** REST API backend.

Rather than functioning as a standard alarm system that merely flags bounding boxes, JARVIS actively interprets multi-modal input, calculates operational severity, formulates structured corrective actions, and strictly gates all machine interventions behind a human-in-the-loop approval workflow. Every step of this pipeline is committed to an SQLite database with SHA-256 cryptographic hash-chaining, providing an immutable audit trail for safety and regulatory compliance.

> **Note on Implementation Boundaries:**  
> JARVIS is designed and demonstrated as a **software simulation**. It operates on sample industrial video/image feeds and software state machines; no physical industrial PLCs or hazardous factory hardware are directly wired to the system.

---

## 2. Problem Statement

Modern industrial and manufacturing facilities face persistent monitoring challenges:

- **Delayed Detection:** Human operators cannot monitor all plant zones continuously without fatigue, resulting in delayed responses to fire/smoke outbreaks or mechanical conveyor jams.
- **PPE Non-Compliance:** Manual auditing of safety equipment (helmets, vests, gloves, boots) across busy production shifts is inconsistent and error-prone.
- **Alert Fatigue:** Traditional sensor systems flood operators with raw alarms without contextual severity or recommended remediation.
- **Lack of Accountability:** When equipment is shut down or safety incidents occur, there is rarely a tamper-evident, verifiable record explaining *why* the decision was proposed and *which supervisor* authorized it.

---

## 3. Core Concept: Why JARVIS is "Agentic"

A basic **Detection-Only System** follows a passive, linear route:  
`Input → Detection (YOLO) → Trigger Alarm`

In contrast, JARVIS executes an **Agentic Reasoning Pipeline** that understands context and enforces human accountability:

```text
Observe (Uploaded image, video feed, or machine sensor telemetry)
   ↓
Detect (Perception via Ultralytics YOLO26/YOLOv8 & DeepFace)
   ↓
Understand (Extract telemetry, violation classes, and confidence scores)
   ↓
Reason (Deterministic rule engine evaluates severity: low, medium, high, critical)
   ↓
Propose (Formulates concrete operational recommendations)
   ↓
Human Approval (Supervisor reviews reasoning and clicks APPROVE or DENY)
   ↓
Simulate Action (Updates software state-machine of virtual factory lines)
   ↓
Record (Commits event with SHA-256 tamper-evident hash chaining to SQLite)
```

By separating *perception* from *reasoning* and strictly requiring *human authorization*, JARVIS acts as an intelligent co-pilot for plant supervisors.

---

## 4. Current System Architecture

The application is structured into three clean, decoupled layers:

```text
                    JARVIS WEB APPLICATION

┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND CLIENT                        │
│                 HTML5 + CSS3 + JavaScript                   │
│                                                             │
│   Floor View       Trigger Console      Reasoning Trail     │
│   Pending Actions  Worker Records       Audit Reports       │
│   Risk Trends      Ask JARVIS           Upload & Inspect    │
│   Shift Handover   Audit Verification   Alert Setup         │
└──────────────────────────────┬──────────────────────────────┘
                               │
                          HTTP / JSON
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND                         │
│                    FastAPI + Python                         │
│                                                             │
│   REST API Endpoints      Pydantic Request Validation       │
│   CORS Middleware         Simulation Event Triggering       │
│   Human Approval Engine   AI Gateway & Guardrail Validation │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     JARVIS SERVICES                         │
│                                                             │
│   YOLO26 / YOLOv8 Vision (PPE & Fire/Smoke Models)          │
│   DeepFace Facial Recognition & Attribution                 │
│   Deterministic Reasoning Engine (agent/reasoner.py)        │
│   LLM Shift Handover Summaries (OpenAI / NIM / OpenRouter)  │
│   Conveyor Finite State Machine (simulation/conveyor.py)    │
│   System Guardrail Validator (guardrails/validator.py)      │
│   Cryptographic Hash-Chained Database (SQLite WAL Mode)     │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Architectural Responsibilities

| Layer | Technology | Primary Responsibilities |
| :--- | :--- | :--- |
| **Frontend** | HTML5 | Page structure, semantic layouts, and DOM view containers |
| **Frontend** | CSS3 | Warm ivory/dark slate design system, tokens, spatial topology styling, and responsive layout |
| **Frontend** | JavaScript (ES6+) | Client-side SPA hash routing (`#floor-view`, etc.), dynamic polling, DOM rendering, and API communication |
| **Backend / API** | FastAPI + Python | High-performance REST endpoints, request validation (Pydantic), CORS, state aggregation, and error handling |
| **Web Server** | Uvicorn (ASGI) | Asynchronous HTTP server hosting the FastAPI backend on port 8000 |
| **Computer Vision** | Ultralytics YOLO26 / v8 | Object detection for safety PPE compliance (`best_ppe.pt`) and fire/smoke hazard analysis (`best_fire.pt`) |
| **Recognition** | DeepFace + TF-Keras | Facial detection and worker identity verification |
| **Reasoning** | Rule Engine + LLMs | Deterministic severity categorization (`low` to `critical`), action proposals, and LLM shift briefings |
| **Simulation** | Python State Machine | Stand-in simulation for Line 1 conveyor states (`running`, `stopped`, `faulted`) |
| **Guardrails** | Python Validator | Policy enforcement layer ensuring AI recommendations cannot bypass human safety gates |
| **Database** | SQLite (WAL Mode) | Persistent transactional storage with SHA-256 hash-chained audit logging |
| **Prototype UI** | Streamlit (Python) | *Historical/alternative prototype dashboard* (`dashboard/app.py`) retained for Python-only local testing |

---

## 6. Technology Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend UI** | HTML5, CSS3, JavaScript | Modern, responsive Single Page Application (SPA) |
| **Backend API** | FastAPI (Python 3.11) | High-speed ASGI REST API server |
| **ASGI Web Server**| Uvicorn | Asynchronous server hosting the FastAPI application |
| **Computer Vision**| Ultralytics YOLO26 / v8 | Custom neural networks for PPE and Fire/Smoke detection |
| **Face Recognition**| DeepFace + TF-Keras | Worker identification and profile attribution |
| **Database** | SQLite (WAL Mode) | Transactional event database with SHA-256 hash chains |
| **Cryptography** | SHA-256 (`hashlib`) | Tamper-evident cryptographic chaining (`record_hash` + `prev_hash`) |
| **AI / LLM Integration** | OpenAI / NVIDIA NIM / OpenRouter | LLM-powered shift summaries with deterministic local fallback |
| **Data Processing**| Pandas, NumPy, OpenCV | Bounding box processing, image manipulation, and tabular aggregations |
| **Reporting** | fpdf2, openpyxl, CSV | Formatted compliance downloads (PDF, Excel, CSV) |

For an exhaustive analysis of every dependency and repository file, refer to [PROJECT_STRUCTURE_AND_DEPENDENCIES.md](PROJECT_STRUCTURE_AND_DEPENDENCIES.md).

---

## 7. Frontend Application Walkthrough

The web frontend operates as a client-side Single Page Application (SPA) driven by hash-based routing (`window.location.hash`). It features 12 dedicated views:

1. **Floor View (`#floor-view`):**  
   The primary operational command center. Displays overall system health, active alert counts, pending approval tallies, an interactive 2D facility topology map with live machine telemetry (Primary Conveyor, Assembly Arm, Packaging Station), and active safety guardrail policies.
2. **Trigger Console (`#trigger-console`):**  
   Testing and simulation cockpit. Enables operators to inject simulated incidents (Missing Helmet, Fire Outbreak, Conveyor Mechanical Jam) to test the end-to-end response pipeline in real time.
3. **Reasoning Trail (`#reasoning-trail`):**  
   Visual step-by-step breakdown illustrating the agentic decision workflow: Observe → Detect → Reason → Propose → Approve → Record.
4. **Pending Actions (`#pending-actions`):**  
   Human-in-the-loop governance interface. Displays queued autonomous proposals requiring manager sign-off, featuring **APPROVE** and **DENY** actions that immediately update the database and machine states.
5. **Worker Records (`#worker-records`):**  
   Roster of floor personnel tracking safety incident records, compliance rates, and probation statuses.
6. **Audit Reports (`#audit-reports`):**  
   Catalog of quarterly and monthly safety compliance reports with downloadable document actions.
7. **Risk Trends (`#risk-trends`):**  
   Analytics dashboard displaying rolling 30-day percentage trends in safety violations, mechanical faults, and risk distributions.
8. **Ask JARVIS (`#ask-jarvis`):**  
   Chat interface for natural-language inquiries, featuring an active guardrail advisory block enforcing authorization policies.
9. **Upload & Inspect (`#upload-inspect`):**  
   Visual media upload portal allowing users to submit images and video recordings for inspection by the YOLO vision pipelines.
10. **Shift Handover (`#shift-handover`):**  
    Autonomous shift summarization view providing oncoming supervisors with an executive briefing of incidents, equipment downtime, and safety recommendations.
11. **Audit Verification (`#audit-verification`):**  
    Cryptographic verification inspector displaying SHA-256 hash chains (`record_hash` + `prev_hash`) to verify audit trail immutability.
12. **Alert Setup (`#alert-setup`):**  
    Notification matrix for toggling desktop push alerts, emergency SMS dispatch, and automated email digests.

### Header API Status Indicator

The top navigation header features an `API` indicator badge (`#nav-ai-config`):
- **Green (`is-connected`):** The frontend has verified that the FastAPI backend is online and the AI provider endpoint is configured.
- **Gray:** The backend is either unreachable or running without external AI credentials configured (system operates in deterministic local mode).
- The status is dynamically evaluated via real-time health pings to `/api/health` and `/api/ai/config`.

---

## 8. Backend REST API Endpoints

The FastAPI backend (`api/main.py`) exposes the following REST endpoints:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | API service root banner |
| `GET` | `/api/health` | Health check probe queried by frontend client |
| `GET` | `/api/status` | System operational summary (overall status, alerts, approvals, conveyor telemetry) |
| `GET` | `/api/events` | Retrieves list of recorded safety and machine events (`limit` parameter supported) |
| `GET` | `/api/events/pending` | Retrieves all incidents awaiting human supervisor sign-off |
| `POST`| `/api/approvals` | Processes supervisor decision (`APPROVE` or `DENY`) with user attribution |
| `POST`| `/api/simulation/trigger` | Injects simulated events (PPE, fire, conveyor faults) into the live database |
| `GET` | `/api/machines` | Returns digital twin telemetry and operating states for facility machinery |
| `GET` | `/api/ai/config` | Returns public AI provider and model metadata without leaking secrets |
| `POST`| `/api/ai/test` | Validates connection credentials to remote AI inference providers |
| `POST`| `/api/ai/reason` | Evaluates proposed actions against system safety guardrails before execution |

Interactive OpenAPI documentation is accessible at `http://127.0.0.1:8000/docs`.

---

## 9. Repository Structure

```text
jarvis/
├── agent/
│   ├── reasoner.py         # Evaluates detections, assigns severity, proposes actions
│   └── shift_report.py     # LLM shift summarization with deterministic local fallback
├── alerts/
│   └── __init__.py         # Notification dispatch hooks (desktop push, SMS, email)
├── api/
│   └── main.py             # FastAPI backend REST API server
├── dashboard/
│   └── app.py              # Historical / alternative prototype Streamlit dashboard
├── database/
│   ├── db.py               # SQLite Data Access Layer & SHA-256 hash-chaining logic
│   └── jarvis.db           # Active SQLite database file (auto-generated)
├── detection/
│   ├── models/
│   │   ├── best_fire.pt    # Custom fine-tuned YOLO weights (Fire/Smoke)
│   │   └── best_ppe.pt     # Custom fine-tuned YOLO weights (11-class PPE)
│   ├── test_inputs/        # Sample images & videos for testing
│   ├── fire_detector.py    # Hazard inference class (Image & Video)
│   ├── ppe_detector.py     # PPE compliance inference class (Image & Video)
│   ├── pipeline.py         # Orchestrator routing inputs to detectors & reasoner
│   └── run_tests.py        # Automated test suite for vision models
├── frontend/
│   ├── index.html          # Main Single Page Application HTML shell
│   ├── css/
│   │   ├── components.css  # Component styles (cards, tables, badges, buttons)
│   │   ├── layout.css      # Header, navigation, and SPA view layout
│   │   ├── reset.css       # Cross-browser CSS reset
│   │   └── tokens.css      # CSS custom property design tokens
│   └── js/
│       ├── api.js          # Reusable HTTP client wrapping fetch calls
│       └── app.js          # SPA router, polling timers, and event handlers
├── guardrails/
│   ├── config.yaml         # Guardrail boundary definitions
│   ├── policy.py           # Safety policy definitions
│   ├── rules.py            # Concrete rule validation logic
│   └── validator.py        # Guardrail interceptor & enforcement engine
├── reports/
│   └── export.py           # Pandas utility exporting SQLite events to CSV
├── simulation/
│   └── conveyor.py         # Software state machine simulating Line 1 conveyor
├── .env.example            # Environment variable template for API keys
├── PROJECT_STRUCTURE_AND_DEPENDENCIES.md # Comprehensive file & dependency guide
├── README.md               # Repository documentation (this file)
├── requirements.txt        # Python dependency manifest
└── test_pipeline.py        # End-to-end automated pipeline test script
```

---

## 10. Installation & Running

### Prerequisites

- Python 3.9 - 3.11 installed.
- Git installed.
- Modern web browser (Chrome, Edge, Firefox, Safari).

### 1. Clone & Set Up Environment

```bash
git clone https://github.com/adibcopilot/jarvis.git
cd jarvis

# Create and activate virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables (Optional)

To enable cloud LLM-assisted shift summaries, duplicate `.env.example` to `.env`:

```bash
cp .env.example .env
```

Add your API key for NVIDIA NIM, OpenRouter, or OpenAI. If no key is provided, the system automatically uses its local deterministic rule engine.

### 3. Start the FastAPI Backend Server

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

The API will initialize the database schema and be available at:  
- API Root: `http://127.0.0.1:8000`  
- Swagger Docs: `http://127.0.0.1:8000/docs`  

### 4. Launch the Web Frontend

In a separate terminal, serve the frontend directory:

```bash
python -m http.server --directory frontend 3000
```

Open your browser and navigate to:  
**`http://127.0.0.1:3000`**

*(Alternatively, you can open `frontend/index.html` directly in your browser).*

### 5. Running the Legacy Streamlit Prototype (Alternative)

If you wish to inspect the earlier standalone Python prototype:

```bash
streamlit run dashboard/app.py --server.port 8501
```

---

## 11. Database Schema & Tamper-Evident Audit Trail

JARVIS operates an SQLite database in WAL (Write-Ahead Logging) mode. The core ledger table is `events`:

| Column | Type | Description |
| :--- | :--- | :--- |
| `event_id` | INTEGER | Primary Key (autoincrementing) |
| `timestamp` | DATETIME | ISO timestamp of event recording |
| `event_type` | TEXT | Category: `ppe`, `fire`, or `conveyor` |
| `source_file` | TEXT | Originating image, video filename, or simulated line ID |
| `detections_json` | TEXT | Raw JSON array of bounding boxes, labels, and confidences |
| `severity` | TEXT | Severity assessment: `low`, `medium`, `high`, `critical` |
| `category` | TEXT | Operational domain: `safety`, `mechanical`, `technical` |
| `proposed_action` | TEXT | Recommendation generated by the reasoning agent |
| `approval_status` | TEXT | Governance state: `pending`, `approved`, `denied` |
| `approved_by` | TEXT | Authorizing supervisor identity |
| `record_hash` | TEXT | SHA-256 hash of `(timestamp + event_type + severity + proposed_action + prev_hash)` |
| `prev_hash` | TEXT | Cryptographic hash of the immediately preceding database row |

### Cryptographic Chaining
Every event incorporates the hash of the preceding record (`prev_hash`). If any past record is tampered with directly via a database client, the cryptographic signature chain breaks for all subsequent rows, instantly flagging unauthorized manipulation during compliance verification.

---

## 12. Verification & Testing

Run the automated test suite to verify end-to-end system health:

```bash
python test_pipeline.py
```

This tests:
1. PPE detection on sample test inputs.
2. Fire & smoke detection inference.
3. Conveyor finite state transitions and fault injection.
4. Agent severity classification and recommendation generation.
5. SQLite event insertion and SHA-256 cryptographic hash chaining.
