# JARVIS — Project Structure, File Directory & Dependencies Guide

This document provides a comprehensive, file-by-file and package-by-package technical reference for the **JARVIS** (Joint Autonomous Reasoning & Vision Inspection System) project. It details why every dependency exists, where it is consumed in the codebase, which backend architecture is implemented and why, and the exact purpose of every file and directory in the repository.

---

## Table of Contents

1. [Backend Architecture: Selection and Rationale](#1-backend-architecture-selection-and-rationale)
2. [Python Dependencies (`requirements.txt`)](#2-python-dependencies-requirementstxt)
   - [Object Detection (YOLO)](#object-detection-yolo)
   - [Face Recognition](#face-recognition)
   - [Dashboard &amp; UI](#dashboard--ui)
   - [Computer Vision Utilities](#computer-vision-utilities)
   - [AI &amp; LLM Reasoning Agent](#ai--llm-reasoning-agent)
   - [Alerts &amp; Notifications](#alerts--notifications)
   - [Simulation &amp; Data Generation](#simulation--data-generation)
   - [Reports &amp; Exports](#reports--exports)
   - [System &amp; Environment Utilities](#system--environment-utilities)
   - [API &amp; Web Server](#api--web-server)
3. [Complete Repository Directory and File Breakdown](#3-complete-repository-directory-and-file-breakdown)
   - [Root Files](#root-files)
   - [`api/` — Backend REST API](#api--backend-rest-api)
   - [`frontend/` — Web Application Client](#frontend--web-application-client)
   - [`agent/` — Autonomous Reasoning &amp; Reporting](#agent--autonomous-reasoning--reporting)
   - [`database/` — SQLite &amp; Cryptographic Audit Trail](#database--sqlite--cryptographic-audit-trail)
   - [`detection/` — Computer Vision &amp; YOLO Inference](#detection--computer-vision--yolo-inference)
   - [`guardrails/` — Policy Enforcement &amp; Validation](#guardrails--policy-enforcement--validation)
   - [`simulation/` — Industrial Conveyor State Machine](#simulation--industrial-conveyor-state-machine)
   - [`reports/` — Compliance Export Utilities](#reports--compliance-export-utilities)
   - [`alerts/` — Escalation &amp; Notification Package](#alerts--escalation--notification-package)
   - [`dashboard/` — Legacy / Prototype Streamlit UI](#dashboard--legacy--prototype-streamlit-ui)
   - [`.streamlit/` — Streamlit Configuration](#streamlit--streamlit-configuration)
4. [System Data Flow Summary](#4-system-data-flow-summary)

---

## 1. Backend Architecture: Selection and Rationale

### Which Backend is Used?

JARVIS uses **FastAPI + Python** served by **Uvicorn** (ASGI server) as its primary backend and REST API engine.

```text
┌──────────────────────────────────────────────┐
│             FRONTEND (Browser)               │
│          HTML5 + CSS3 + JavaScript           │
└──────────────────────┬───────────────────────┘
                       │ HTTP / REST / JSON
                       ▼
┌──────────────────────────────────────────────┐
│           BACKEND (Port 8000)                │
│             FastAPI + Python                 │
│          Served via Uvicorn ASGI             │
└──────────────────────┬───────────────────────┘
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
┌──────────────┐┌──────────────┐┌──────────────┐
│  AI / Vision ││  Simulation  ││ SQLite WAL   │
│ YOLO/DeepFace││ State Machine││ Hash-Chained │
└──────────────┘└──────────────┘└──────────────┘
```

### Why FastAPI is Used for the Backend

1. **Decoupled Client-Server Architecture:**
   - Early prototypes of JARVIS relied on Streamlit, where UI rendering and Python execution are coupled in a single monolithic process that reruns from top to bottom on every user action.
   - FastAPI decouples the user interface from backend execution. The frontend is a standalone, lightweight HTML5/CSS3/JavaScript single-page application (SPA). The backend functions as an independent, stateless REST API.
2. **High Asynchronous Performance (ASGI):**
   - Built on top of **Starlette** and **Pydantic**, FastAPI is one of the fastest Python frameworks available. Its native asynchronous event loop (`async`/`await`) allows JARVIS to handle concurrent client polling, simulation heartbeats, and image processing without blocking worker threads.
3. **Strict Data Validation & Type Safety:**
   - FastAPI leverages Pydantic schemas (e.g., `ApprovalRequest`, `TriggerRequest`, `AIConfigTestRequest`) to automatically validate incoming JSON payloads, reject malformed requests with standard HTTP 422 errors, and serialize Python dictionaries into predictable JSON structures.
4. **Direct Python AI Ecosystem Integration:**
   - Computer vision and deep learning models (PyTorch, Ultralytics YOLO, DeepFace, OpenCV) require a Python runtime. FastAPI allows direct, in-memory model invocation without requiring complex inter-process communication (IPC) bridges between a separate backend language (like Node.js or Go) and the Python ML pipeline.
5. **Interactive OpenAPI Documentation:**
   - FastAPI automatically generates interactive OpenAPI/Swagger documentation at `/docs` and ReDoc at `/redoc`, facilitating transparent API testing, endpoint inspection, and evaluation for academic defense and team collaboration.
6. **Cross-Origin Resource Sharing (CORS):**
   - Built-in `CORSMiddleware` enables secure cross-origin communication between the frontend client (e.g., served on `http://127.0.0.1:3000`) and the API server (`http://127.0.0.1:8000`).

---

## 2. Python Dependencies (`requirements.txt`)

Below is the complete breakdown of every package specified in `requirements.txt`, explaining **why** it is used and **where** it is referenced in the project.

### Object Detection (YOLO)

#### `ultralytics`

* **Purpose & Justification:** Provides the official library for training, loading, and performing real-time object detection inference using Ultralytics YOLO models (including YOLOv8, YOLOv11, and YOLO26 architectures). It handles model weight initialization, bounding box tensor decoding, Non-Maximum Suppression (NMS), and visual label plotting.
* **Where Used in Codebase:**
  - `detection/ppe_detector.py` (loads `detection/models/best_ppe.pt` to detect 11 PPE classes).
  - `detection/fire_detector.py` (loads `detection/models/best_fire.pt` to detect fire, smoke, and persons).
  - `detection/pipeline.py` (manages detector instances).
  - `detection/yolo_image_test.py`, `detection/yolo_video_test.py`, `detection/run_tests.py`, `detection/test_all_inputs.py` (automated model verification scripts).

---

### Face Recognition

#### `deepface`

* **Purpose & Justification:** A lightweight face recognition and facial attribute analysis framework. In the JARVIS system, it is designated to identify worker identity from facial features in captured camera frames, enabling per-worker violation tracking and probation record management.
* **Where Used in Codebase:**
  - Listed in project requirements and architecture specifications for worker identification and facial verification in the Worker Records module.

#### `tf-keras`

* **Purpose & Justification:** Provides legacy TensorFlow Keras interfaces required by DeepFace when loading pre-trained neural network backbones (such as VGG-Face, FaceNet, and OpenFace) under modern TensorFlow environments.
* **Where Used in Codebase:**
  - Serves as the required runtime dependency for `deepface` deep learning backend computations.

---

### Dashboard & UI

#### `streamlit`

* **Purpose & Justification:** A Python-based rapid UI prototyping framework. Built in early sprints to establish a functioning prototype of the dashboard (`dashboard/app.py`) before migrating to the production-ready HTML5/CSS3/JavaScript SPA. Retained in the repository for legacy evaluation, rapid local testing, and Python-only standalone demonstrations.
* **Where Used in Codebase:**
  - `dashboard/app.py` (8-page prototype dashboard including upload, conveyor control, approval queue, and event logs).
  - `.streamlit/config.toml` (sets monochrome theme tokens for Streamlit).

#### `plotly`

* **Purpose & Justification:** An interactive graphing library used to generate dynamic charts and distribution graphs.
* **Where Used in Codebase:**
  - `dashboard/app.py` (renders violation trend distribution bar charts and severity breakdowns in the Streamlit interface).

---

### Computer Vision Utilities

#### `opencv-python` (`cv2`)

* **Purpose & Justification:** The industry-standard computer vision library. Used for video decoding, frame-by-frame extraction, video writing, bounding box annotations, matrix conversions, and image preprocessing.
* **Where Used in Codebase:**
  - `detection/ppe_detector.py` (reads video streams, resizes frames, encodes annotated frames).
  - `detection/fire_detector.py` (processes video streams and draws fire bounding boxes).
  - `detection/image_input_test.py` and `detection/video_input_test.py` (standalone visual verification scripts).

#### `Pillow` (`PIL`)

* **Purpose & Justification:** Python Imaging Library. Used for opening, verifying, saving, and format-converting image files before feeding them to YOLO or rendering them in web buffers.
* **Where Used in Codebase:**
  - `detection/pipeline.py` (validates image dimensions and file formats).
  - `dashboard/app.py` (renders uploaded inspection images).

---

### AI & LLM Reasoning Agent

#### `openai`

* **Purpose & Justification:** Official OpenAI client SDK. Used by the JARVIS reasoning agent to query Large Language Models (GPT-4o, OpenAI-compatible NVIDIA NIM endpoints, or OpenRouter endpoints) to generate plain-English shift briefings and incident analyses.
* **Where Used in Codebase:**
  - `agent/shift_report.py` (executes LLM calls in `generate_shift_report()` to summarize incidents over selected shift intervals).
  - `api/main.py` (manages AI gateway status and configuration).

#### `langchain`

* **Purpose & Justification:** Framework for orchestrating LLM chains, agent prompts, and tool execution boundaries. Used for structured prompt assembly and agentic reasoning pipelines.
* **Where Used in Codebase:**
  - Integrated into the agent layer specifications for structured decision chains.

#### `langchain-openai`

* **Purpose & Justification:** Integration package providing standard LangChain chat model abstractions for OpenAI and compatible inference endpoints.
* **Where Used in Codebase:**
  - Pairs with `langchain` and `openai` for structured agent invocations.

---

### Alerts & Notifications

#### `plyer`

* **Purpose & Justification:** A cross-platform Python library for native system features. Used in JARVIS to trigger local desktop push notifications when critical safety violations (fire or mechanical jams) occur.
* **Where Used in Codebase:**
  - `alerts/` package (triggers instant supervisor desktop notifications on critical alerts).

#### `twilio`

* **Purpose & Justification:** Official Twilio API client. Provides optional SMS and WhatsApp alert capabilities to escalate unresolved critical emergencies directly to plant manager mobile phones.
* **Where Used in Codebase:**
  - Integrated into the `alerts/` subsystem for off-site supervisor dispatch.

---

### Simulation & Data Generation

#### `faker`

* **Purpose & Justification:** Generates realistic mock data (synthetic employee names, worker badge IDs, timestamps, and equipment serial numbers) for simulation runs, synthetic stress tests, and automated compliance demonstrations.
* **Where Used in Codebase:**
  - Mock data generation for worker records, test events, and synthetic handover logs.

#### `numpy`

* **Purpose & Justification:** The fundamental package for scientific computing in Python. Used for tensor manipulation, bounding box coordinate math, confidence array indexing, and numeric aggregations.
* **Where Used in Codebase:**
  - `detection/ppe_detector.py`, `detection/fire_detector.py` (handling bounding box arrays).
  - `detection/pipeline.py` (confidence filtering and score averaging).

#### `pandas`

* **Purpose & Justification:** High-performance tabular data manipulation library. Used for querying event datasets, grouping violations by department or shift, computing rolling statistics, and formatting data tables.
* **Where Used in Codebase:**
  - `reports/export.py` (converts SQLite query results into pandas DataFrames and exports CSV files).
  - `dashboard/app.py` (manipulates event logs and renders tabular metric views).

---

### Reports & Exports

#### `fpdf2`

* **Purpose & Justification:** Lightweight, pure-Python PDF generation library. Used to compile structured shift incident logs and safety audit records into formal, downloadable PDF compliance documents.
* **Where Used in Codebase:**
  - `reports/` module for generating formatted PDF safety compliance documents.

#### `openpyxl`

* **Purpose & Justification:** An Excel spreadsheet reader/writer. Used to generate `.xlsx` audit reports containing event histories, approval timestamps, and worker compliance metrics.
* **Where Used in Codebase:**
  - `reports/` export utility for Excel-formatted audit archives.

#### `jinja2`

* **Purpose & Justification:** Fast and extensible HTML templating engine. Used to render structured HTML report templates and email notifications with dynamic incident tables and severity badges.
* **Where Used in Codebase:**
  - Generating dynamic HTML reports and email alert layouts.

---

### System & Environment Utilities

#### `python-dotenv`

* **Purpose & Justification:** Loads environment variables from the `.env` file into `os.environ`. Keeps private credentials (API keys, ports, secrets) out of source control.
* **Where Used in Codebase:**
  - `agent/shift_report.py` (reads `OPENAI_API_KEY`, `NVIDIA_API_KEY`, `OPENROUTER_API_KEY`).
  - `api/main.py` (reads `AI_PROVIDER`, `AI_MODEL`).

#### `loguru`

* **Purpose & Justification:** Advanced, zero-configuration Python logging library. Replaces standard `print()` statements with structured, colorized, timestamped, and thread-safe log entries for pipeline tracing and debugging.
* **Where Used in Codebase:**
  - Logging pipeline transitions, database transactions, and model inference steps across backend modules.

#### `requests`

* **Purpose & Justification:** Standard synchronous HTTP client library. Used for external API health pings, downloading remote test datasets, and querying cloud endpoints.
* **Where Used in Codebase:**
  - `detection/download_ppe_dataset.py` (fetches sample dataset ZIP archives).
  - External health checks and webhook dispatches.

#### `schedule`

* **Purpose & Justification:** In-process, human-readable job scheduler. Used to trigger recurring maintenance routines, such as generating an automated shift handover briefing every 8 hours or refreshing compliance rollups.
* **Where Used in Codebase:**
  - Periodic background job execution for report scheduling.

#### `tqdm`

* **Purpose & Justification:** Fast, extensible progress bar utility for console loops.
* **Where Used in Codebase:**
  - `detection/download_ppe_dataset.py` (visual download progress).
  - Video processing loops iterating through frame sequences.

---

### API & Web Server

#### `fastapi`

* **Purpose & Justification:** Modern, high-performance web API framework. Serves as the primary REST API backend for the entire JARVIS web application, handling HTTP routing, request validation, authentication, and state reporting.
* **Where Used in Codebase:**
  - `api/main.py` (defines endpoints: `/api/health`, `/api/status`, `/api/events`, `/api/events/pending`, `/api/approvals`, `/api/simulation/trigger`, `/api/machines`, `/api/ai/config`, `/api/ai/reason`).

#### `uvicorn`

* **Purpose & Justification:** Ultra-fast ASGI (Asynchronous Server Gateway Interface) web server implementation for Python. Used to run and host the FastAPI application in production and development environments.
* **Where Used in Codebase:**
  - Command-line runner for hosting `api.main:app` on `http://127.0.0.1:8000`.

---

## 3. Complete Repository Directory and File Breakdown

Below is an exhaustive inventory of every directory and file in `jarvis/`, explaining **why** it was created and **what** it is used for.

```text
jarvis/
├── .env.example
├── .gitignore
├── execution_log.md
├── presentation_notes.md
├── README.md
├── requirements.txt
├── test_pipeline.py
├── yolo26n.pt
├── yolov8n.pt
├── .streamlit/
│   └── config.toml
├── agent/
│   ├── __init__.py
│   ├── reasoner.py
│   └── shift_report.py
├── alerts/
│   └── __init__.py
├── api/
│   └── main.py
├── dashboard/
│   ├── __init__.py
│   └── app.py
├── database/
│   ├── __init__.py
│   ├── db.py
│   └── jarvis.db
├── detection/
│   ├── __init__.py
│   ├── check_yolo26.py
│   ├── download_ppe_dataset.py
│   ├── fire_detector.py
│   ├── image_input_test.py
│   ├── pipeline.py
│   ├── ppe_detector.py
│   ├── run_tests.py
│   ├── test_all_inputs.py
│   ├── video_input_test.py
│   ├── yolo_download_test.py
│   ├── yolo_image_test.py
│   ├── yolo_video_test.py
│   ├── models/
│   │   ├── best_fire.pt
│   │   └── best_ppe.pt
│   └── test_inputs/
│       ├── fire_smoke/
│       └── ppe/
├── frontend/
│   ├── index.html
│   ├── css/
│   │   ├── components.css
│   │   ├── layout.css
│   │   ├── reset.css
│   │   └── tokens.css
│   └── js/
│       ├── api.js
│       └── app.js
├── guardrails/
│   ├── __init__.py
│   ├── config.yaml
│   ├── policy.py
│   ├── rules.py
│   └── validator.py
├── reports/
│   ├── __init__.py
│   └── export.py
└── simulation/
    ├── __init__.py
    └── conveyor.py
```

---

### Root Files

#### `.env.example`

* **Why Created:** Security best practice. Serves as a version-controlled template documenting all required environment variables without leaking real secrets.
* **What Used For:** Developers copy this to `.env` to configure API keys for OpenAI, NVIDIA NIM, or OpenRouter, and set server ports.

#### `.gitignore`

* **Why Created:** Keeps the Git repository clean, compact, and secure.
* **What Used For:** Excludes virtual environments (`venv/`), Python bytecode (`__pycache__/`, `*.pyc`), secret files (`.env`), transient runtime logs, generated export files (`reports/*.pdf`, `reports/*.csv`), and operating system artifacts (`.DS_Store`, `Thumbs.db`).

#### `execution_log.md`

* **Why Created:** Serves as a chronological development ledger documenting all implementation updates, test executions, bug fixes, and milestones.
* **What Used For:** Provides academic evaluators and teammates with proof of progress across project sprints (Updates 1 through 13).

#### `presentation_notes.md`

* **Why Created:** Prepared for project evaluation, panel presentations, and technical defense.
* **What Used For:** Contains the 30-second elevator pitch, clear breakdowns of real vs. simulated system boundaries, answers to difficult panel questions, and a structured 2-minute live demo script.

#### `README.md`

* **Why Created:** The primary public entry point and documentation hub for the GitHub repository.
* **What Used For:** Explains the project purpose, architecture, technology stack, setup commands, data flows, database schema, and academic author details.

#### `requirements.txt`

* **Why Created:** Standard Python package dependency manifest.
* **What Used For:** Allows anyone cloning the repository to install all required libraries with a single command (`pip install -r requirements.txt`).

#### `test_pipeline.py`

* **Why Created:** Automated end-to-end integration test runner.
* **What Used For:** Verifies the full system loop: running sample images through YOLO detection, evaluating detections with the reasoning agent, testing conveyor state transitions, inserting records into SQLite, and validating SHA-256 cryptographic hash chaining.

#### `yolo26n.pt` & `yolov8n.pt`

* **Why Created:** Pre-trained nano base model weights provided by Ultralytics.
* **What Used For:** Used as baseline checkpoints for benchmarking, general person detection, and testing Ultralytics library compatibility before applying custom fine-tuned weights.

---

### `api/` — Backend REST API

#### `api/main.py`

* **Why Created:** Houses the FastAPI backend application that powers the modern JARVIS web interface.
* **What Used For:** Exposes REST endpoints consumed by the frontend:
  - `GET /` — API root information.
  - `GET /api/health` — Health check endpoint queried by the frontend header indicator.
  - `GET /api/status` — Aggregated operational status (overall state, active alert counts, pending approvals, conveyor state).
  - `GET /api/events` — Retrieves recent event history from SQLite.
  - `GET /api/events/pending` — Retrieves events awaiting human supervisor sign-off.
  - `POST /api/approvals` — Processes manager decisions (`APPROVE` or `DENY`) and commits resolution timestamps to SQLite.
  - `POST /api/simulation/trigger` — Injects simulated incidents (PPE violations, fire hazards, conveyor jams) into the active database and pipeline.
  - `GET /api/machines` — Returns digital twin telemetry and state for facility machines (Primary Conveyor, Assembly Arm, Packaging Station).
  - `GET /api/ai/config` — Returns public AI provider and model metadata without exposing secret keys.
  - `POST /api/ai/test` — Validates connection parameters to AI endpoints.
  - `POST /api/ai/reason` — Passes proposed AI actions through the Guardrail Validator to enforce safety constraints.

---

### `frontend/` — Web Application Client

The modern frontend is built with pure **HTML5, CSS3, and Vanilla JavaScript**, providing a responsive, high-performance Single Page Application (SPA) that communicates with the FastAPI backend over HTTP/JSON.

#### `frontend/index.html`

* **Why Created:** The central HTML entry point and UI layout for the entire web dashboard.
* **What Used For:** Declares the global header, live navigation bar, system status indicator, and markup containers for all 12 operational views:
  1. **Floor View (`#floor-view`):** Real-time spatial topology map of facility machines, live conveyor telemetry, active alert badges, and system guardrail rules.
  2. **Trigger Console (`#trigger-console`):** Interactive testing cockpit allowing supervisors to simulate violations (PPE, Fire, Conveyor Jams) and test system responses.
  3. **Reasoning Trail (`#reasoning-trail`):** Step-by-step visual trace of the agentic decision pipeline (Observe → Detect → Reason → Propose → Approve → Record).
  4. **Pending Actions (`#pending-actions`):** Human-in-the-loop approval interface where supervisors review and sign off on proposed actions.
  5. **Worker Records (`#worker-records`):** Tabular roster of workers, safety compliance ratings, incident counts, and probation statuses.
  6. **Audit Reports (`#audit-reports`):** Catalog of generated quarterly and monthly compliance reports with PDF export actions.
  7. **Risk Trends (`#risk-trends`):** Safety analytics overview highlighting 30-day violation trends and risk distributions.
  8. **Ask JARVIS (`#ask-jarvis`):** Natural-language conversational interface with built-in guardrail advisory blocks.
  9. **Upload & Inspect (`#upload-inspect`):** Manual media inspection portal for uploading and analyzing plant images and videos.
  10. **Shift Handover (`#shift-handover`):** Automated shift summarization briefing and sign-off panel for oncoming supervisors.
  11. **Audit Verification (`#audit-verification`):** Cryptographic verification table displaying SHA-256 hash chains (`record_hash` + `prev_hash`) proving audit trail immutability.
  12. **Alert Setup (`#alert-setup`):** Notification routing matrix for configuring desktop push, email, and SMS alerts.

#### `frontend/css/reset.css`

* **Why Created:** Normalizes default browser styling across platforms (Chrome, Firefox, Edge).
* **What Used For:** Resets margins, padding, box-sizing (`border-box`), and font inheritance.

#### `frontend/css/tokens.css`

* **Why Created:** Design system foundation declaring design tokens as CSS Custom Properties (`:root`).
* **What Used For:** Defines the warm ivory and dark slate color palette, semantic status colors (critical red, warning amber, normal green), typography scales, spacing units, border radii, and z-index layers.

#### `frontend/css/layout.css`

* **Why Created:** Governs macroscopic application layout and positioning.
* **What Used For:** Styles the fixed top navigation header, page container widths, view switching rules (`.app-view.active`), grid configurations, and responsive media queries.

#### `frontend/css/components.css`

* **Why Created:** Reusable component styling across all dashboard views.
* **What Used For:** Styles summary stat cards, facility map cards, machine status badges, approval buttons, modal overlays, data tables, and the chat conversation container.

#### `frontend/js/api.js`

* **Why Created:** Reusable HTTP client module isolating network operations.
* **What Used For:** Wraps native browser `fetch` calls into clean helper methods (`api.get()`, `api.post()`, `api.health()`) targeting `http://127.0.0.1:8000/api`. Handles response parsing and error propagation.

#### `frontend/js/app.js`

* **Why Created:** Core client-side application logic and controller.
* **What Used For:**
  - **SPA Router:** Listens to `hashchange` events on `window.location.hash` to toggle views without full page reloads.
  - **Health Polling:** Polls `/api/health` and `/api/ai/config` every 15 seconds to update the header `API` indicator.
  - **Telemetry Refresh:** Polls `/api/status` and `/api/machines` every 5 seconds to update summary metrics and facility map states.
  - **Approval Queue Handling:** Fetches pending events, renders action cards, and sends `POST /api/approvals` on manager click.
  - **Simulation Console:** Binds trigger buttons to `POST /api/simulation/trigger` to inject test events.
  - **Chat Simulation:** Manages the Ask JARVIS chat interface and displays guardrail enforcement responses.

---

### `agent/` — Autonomous Reasoning & Reporting

#### `agent/__init__.py`

* **Why Created:** Standard Python package marker.
* **What Used For:** Exposes agent functions for clean imports across the project.

#### `agent/reasoner.py`

* **Why Created:** Encapsulates the core agentic reasoning logic of JARVIS.
* **What Used For:**
  - Evaluates raw detection payloads from YOLO or conveyor simulation.
  - Determines operational category (`safety`, `mechanical`, `technical`).
  - Assigns severity levels (`low`, `medium`, `high`, `critical`).
  - Formulates clear, human-readable action proposals (e.g., *"Halt Line 1: Mechanical jam detected; dispatch technician"*).
  - Employs deterministic rule engines to guarantee predictable, explainable behavior.

#### `agent/shift_report.py`

* **Why Created:** Automates shift handover briefings between departing and oncoming factory supervisors.
* **What Used For:** Queries recent events from SQLite, constructs a structured prompt, queries LLM APIs (OpenAI, NVIDIA NIM, or OpenRouter), and generates executive summaries. Includes **graceful local degradation** to deterministic rules if no API key is configured.

---

### `database/` — SQLite & Cryptographic Audit Trail

#### `database/__init__.py`

* **Why Created:** Package marker.
* **What Used For:** Enables imports of database helpers (`from database.db import ...`).

#### `database/db.py`

* **Why Created:** The Data Access Layer (DAL) for all persistent storage operations.
* **What Used For:**
  - Automatically initializes `database/jarvis.db` with WAL (Write-Ahead Logging) mode.
  - Manages the `events` table (recording timestamps, event types, raw YOLO detection JSON, severity, proposed actions, approval status, and timestamps).
  - Manages the `conveyor_state` table.
  - Implements **SHA-256 cryptographic hash-chaining**: computes `record_hash = sha256(payload + prev_hash)` for every row, making the historical audit trail tamper-evident.
  - Provides query functions: `get_all_events()`, `get_pending_events()`, `get_event_stats()`, `update_approval()`.

#### `database/jarvis.db`

* **Why Created:** The active SQLite database file.
* **What Used For:** Stores all runtime event logs, conveyor states, and approval records. Auto-generated if not present.

---

### `detection/` — Computer Vision & YOLO Inference

#### `detection/__init__.py`

* **Why Created:** Package marker.
* **What Used For:** Enables package imports for vision detectors and pipeline runners.

#### `detection/models/best_ppe.pt`

* **Why Created:** Custom-trained YOLO neural network weights.
* **What Used For:** Detects 11 safety classes: `helmet`, `gloves`, `vest`, `boots`, `goggles`, `none`, `Person`, `no_helmet`, `no_goggle`, `no_gloves`, `no_boots`.

#### `detection/models/best_fire.pt`

* **Why Created:** Custom-trained YOLO neural network weights for hazard detection.
* **What Used For:** Detects 6 classes: `fire`, `smoke`, `person`, `with helmet`, `with ppe`, `without helmet`.

#### `detection/ppe_detector.py`

* **Why Created:** High-level inference class (`PPEDetector`) for PPE compliance.
* **What Used For:** Ingests image or video frames, runs YOLO inference, filters by confidence threshold, extracts violations, and returns structured dictionaries and annotated frames.

#### `detection/fire_detector.py`

* **Why Created:** High-level inference class (`FireSmokeDetector`) for hazard detection.
* **What Used For:** Ingests images or video frames, detects flame/smoke instances, assesses confidence, and outputs hazard detections.

#### `detection/pipeline.py`

* **Why Created:** Pipeline orchestrator unifying perception, reasoning, and data logging.
* **What Used For:** Accepts an image path or event input, routes it to `PPEDetector` or `FireSmokeDetector`, forwards results to `agent/reasoner.py` for severity classification, and commits the resulting record to SQLite via `database/db.py`.

#### `detection/test_inputs/`

* **Why Created:** Curated test media directory.
* **What Used For:** Contains sample images and video files (`ppe/` and `fire_smoke/`) used for regression testing, validation, and dashboard demonstrations.

#### Verification & Test Scripts:

* `detection/check_yolo26.py` — Validates YOLO model loading and architecture metadata.
* `detection/download_ppe_dataset.py` — Utility script to download public benchmark PPE datasets.
* `detection/image_input_test.py` — Tests OpenCV image reading and display.
* `detection/video_input_test.py` — Tests OpenCV video playback and frame reading.
* `detection/yolo_download_test.py` — Tests automatic downloading of pre-trained Ultralytics weights.
* `detection/yolo_image_test.py` — Runs single-image YOLO inference and saves an annotated test output.
* `detection/yolo_video_test.py` — Runs video-frame YOLO inference and displays real-time tracking.
* `detection/run_tests.py` — Automated batch runner evaluating both PPE and Fire detectors across all test media.
* `detection/test_all_inputs.py` — Comprehensive evaluation script generating detection summaries and confidence metrics.

---

### `guardrails/` — Policy Enforcement & Validation

#### `guardrails/__init__.py`

* **Why Created:** Package marker.
* **What Used For:** Exposes guardrail validator classes and policy exceptions.

#### `guardrails/config.yaml`

* **Why Created:** Declarative configuration file for safety boundaries.
* **What Used For:** Defines blocked action keywords, restricted operations, and maximum automated authority thresholds.

#### `guardrails/policy.py`

* **Why Created:** Formulates formal safety policies.
* **What Used For:** Defines immutable constraints (e.g., AI agents cannot modify physical actuators directly, drop database tables, or alter user permissions).

#### `guardrails/rules.py`

* **Why Created:** Concrete rule logic evaluated during validation.
* **What Used For:** Contains string matching and pattern checking rules that detect hazardous or out-of-scope actions proposed by AI models.

#### `guardrails/validator.py`

* **Why Created:** The enforcement gatekeeper.
* **What Used For:** Intercepts proposed actions before execution; raises `GuardrailException` and returns a `BLOCKED` status if an action violates configured policies.

---

### `simulation/` — Industrial Conveyor State Machine

#### `simulation/__init__.py`

* **Why Created:** Package marker.
* **What Used For:** Enables imports of simulation controllers.

#### `simulation/conveyor.py`

* **Why Created:** Stand-in software simulation for industrial machinery (Line 1).
* **What Used For:**
  - Maintains the operational state machine (`running`, `stopped`, `faulted`).
  - Distinguishes commanded actions (`run()`, `manual_stop()`) which do not generate alarms from unplanned faults (`trigger_fault("mechanical_jam")`) which immediately trigger critical incident logging and require supervisor sign-off.
  - Persists state changes to the `conveyor_state` table in SQLite.

---

### `reports/` — Compliance Export Utilities

#### `reports/__init__.py`

* **Why Created:** Package marker.
* **What Used For:** Exposes reporting and export functions.

#### `reports/export.py`

* **Why Created:** Compliance and data portability utility.
* **What Used For:** Connects to SQLite, extracts event records into a pandas DataFrame, and exports data into timestamped CSV files for safety audits and regulatory reporting.

---

### `alerts/` — Escalation & Notification Package

#### `alerts/__init__.py`

* **Why Created:** Package marker for the multi-tier notification system.
* **What Used For:** Houses notification hooks for desktop push alerts (`plyer`), email alerts (`smtplib`), and mobile dispatch (`twilio`).

---

### `dashboard/` — Legacy / Prototype Streamlit UI

#### `dashboard/__init__.py`

* **Why Created:** Package marker.
* **What Used For:** Allows module resolution inside the dashboard directory.

#### `dashboard/app.py`

* **Why Created:** Built during initial development as an all-in-one Python prototype.
* **What Used For:** Retained as an alternative, standalone Python UI for local demonstration, quick script inspection, and fallback testing. Operates 8 views via Streamlit widgets.

---

### `.streamlit/` — Streamlit Configuration

#### `.streamlit/config.toml`

* **Why Created:** Customization file for Streamlit runtime.
* **What Used For:** Enforces dark theme settings (`backgroundColor="#0a0a0a"`, `textColor="#f5f5f5"`) when running the prototype `dashboard/app.py`.

---

## 4. System Data Flow Summary

The diagram below illustrates how components interact during live operation:

```text
               ┌──────────────────────────────┐
               │    User Browser (Client)     │
               │   HTML5 + CSS3 + JavaScript  │
               └──────────────┬───────────────┘
                              │ HTTP / REST / JSON
                              ▼
               ┌──────────────────────────────┐
               │    FastAPI Backend Server    │
               │         api/main.py          │
               └──────┬───────┬────────┬──────┘
                      │       │        │
        ┌─────────────┘       │        └─────────────┐
        ▼                     ▼                      ▼
┌──────────────┐      ┌──────────────┐       ┌──────────────┐
│  Perception  │      │  Simulation  │       │  Guardrails  │
│  YOLO Models │      │ StateMachine │       │  & Validator │
└──────┬───────┘      └──────┬───────┘       └──────┬───────┘
       │                     │                      │
       └──────────────┬──────┴──────────────────────┘
                      ▼
               ┌──────────────┐
               │  Reasoning   │
               │ Agent/LLM/DB │
               └──────┬───────┘
                      ▼
               ┌──────────────┐
               │  SQLite WAL  │
               │ SHA-256 Hash │
               └──────────────┘
```

This architecture ensures complete separation of concerns: the **frontend** handles presentation, spatial topology rendering, and user interactions; the **FastAPI backend** enforces API contracts, business logic, and security; and the **underlying services** handle vision inference, state simulation, deterministic reasoning, and tamper-evident audit persistence.
