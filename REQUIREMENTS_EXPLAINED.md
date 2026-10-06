# JARVIS — Requirements & File-by-File Breakdown

This document provides a detailed breakdown of **every Python dependency** in `requirements.txt`, **which backend is used and why**, and **every single folder and file** in the repository: why it was created, what it is used for, and where it connects.

---

## 1. Which Backend is Used and Why?

### The Backend: **FastAPI + Python (Served via Uvicorn ASGI)**

JARVIS uses **FastAPI** as its primary REST API backend, served asynchronously on port `8000` via **Uvicorn**.

```text
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND CLIENT                        │
│                 HTML5 + CSS3 + JavaScript                   │
│          (Floor View, Trigger Console, Reasoning, etc.)     │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / JSON REST
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND                         │
│             FastAPI + Python (Uvicorn Port 8000)            │
│               Request Validation & Controllers              │
└──────────────────────────────┬──────────────────────────────┘
                               │
       ┌───────────────────────┼───────────────────────┐
       ▼                       ▼                       ▼
┌──────────────┐       ┌──────────────┐        ┌──────────────┐
│  AI/Vision   │       │  Simulation  │        │ SQLite (WAL) │
│ YOLO/DeepFace│       │ StateMachine │        │ Hash-Chained │
└──────────────┘       └──────────────┘        └──────────────┘
```

### Why FastAPI was Chosen:

1. **Decoupled Client-Server Architecture:**
   - In early prototypes, Streamlit tightly coupled the UI and Python execution into a monolithic script that re-executed top-to-bottom on every user click.
   - FastAPI decouples the application into a pure client-side SPA (HTML5/CSS3/JavaScript) and a stateless, high-speed REST backend.
2. **Asynchronous High Performance (ASGI):**
   - Built on **Starlette** and **Pydantic**, FastAPI is one of the fastest Python frameworks available. Its native asynchronous event loop handles high-frequency client polling (status checks every 5 seconds) without blocking machine learning or simulation workloads.
3. **Direct Integration with Python AI Ecosystem:**
   - Deep learning frameworks (Ultralytics YOLO, PyTorch, DeepFace, OpenCV) require a Python runtime. FastAPI allows in-memory model execution without the overhead of inter-process communication (IPC) bridges.
4. **Automatic Request Validation & Type Safety:**
   - Pydantic models automatically validate incoming requests (`ApprovalRequest`, `TriggerRequest`, `AIConfigTestRequest`) and reject malformed payloads with descriptive HTTP 422 errors.
5. **Auto-Generated Interactive Documentation:**
   - Automatically provides OpenAPI/Swagger documentation at `http://127.0.0.1:8000/docs` and ReDoc at `http://127.0.0.1:8000/redoc`.
6. **Cross-Origin Resource Sharing (CORS):**
   - Built-in `CORSMiddleware` enables clean communication with browser clients running on different ports (e.g., frontend server on port 3000).

---

## 2. Requirements Breakdown (`requirements.txt`)

Below is the complete analysis of every library in `requirements.txt`:

| Package | Category | Why It Is Used | Where It Is Used |
| :--- | :--- | :--- | :--- |
| **`ultralytics`** | Computer Vision | YOLOv8 / YOLOv11 / YOLO26 framework for deep-learning object detection. Handles model loading, tensor inference, non-maximum suppression (NMS), and bounding box visualization. | `detection/ppe_detector.py`, `detection/fire_detector.py`, `detection/pipeline.py`, `detection/run_tests.py` |
| **`deepface`** | Face Recognition | Facial detection and recognition framework. Used to identify worker faces in camera frames to match safety infractions against employee profiles. | Worker identity verification and profile attribution in safety records. |
| **`tf-keras`** | Deep Learning Backend | Legacy Keras 3 / TensorFlow backend required by DeepFace to load pre-trained deep convolutional neural networks (VGG-Face, FaceNet). | Runtime dependency supporting `deepface`. |
| **`streamlit`** | Prototype UI | Rapid Python dashboard framework. Used in early development to build an initial 8-page prototype (`dashboard/app.py`). Maintained as an alternative Python-only local interface. | `dashboard/app.py`, `.streamlit/config.toml` |
| **`plotly`** | Data Visualization | Interactive graphing library. Used to render violation trend charts and distribution bar graphs in dashboard analytics. | `dashboard/app.py` |
| **`opencv-python`** (`cv2`) | Computer Vision | Foundational computer vision library. Handles video file decoding, frame-by-frame extraction, image resizing, matrix conversions, and drawing visual bounding box annotations. | `detection/ppe_detector.py`, `detection/fire_detector.py`, `detection/image_input_test.py`, `detection/video_input_test.py` |
| **`Pillow`** (`PIL`) | Image Utilities | Python Imaging Library. Opens, resizes, converts image formats, and loads image buffers for web display and inspection. | `detection/pipeline.py`, `dashboard/app.py` |
| **`openai`** | AI / LLM SDK | Official OpenAI Python SDK. Communicates with GPT-4o, NVIDIA NIM, or OpenRouter endpoints to generate natural-language shift handover briefings. | `agent/shift_report.py`, `api/main.py` |
| **`langchain`** | Agent Orchestration | Framework for chaining prompts, memory, tools, and agent workflows into structured execution paths. | Agent decision chain logic and structured reasoning workflows. |
| **`langchain-openai`** | LLM Integration | LangChain integration module providing standard chat model abstractions for OpenAI-compatible endpoints. | Agent orchestration layer. |
| **`plyer`** | Notifications | Cross-platform library for native OS features. Triggers immediate local desktop push notifications to plant supervisors when critical incidents occur. | `alerts/` notification hooks. |
| **`twilio`** | Mobile Alerts | Official Twilio REST API client. Sends automated SMS and WhatsApp emergency alerts to off-site plant managers for critical unresolved incidents. | `alerts/` mobile dispatch module. |
| **`faker`** | Data Generation | Synthetic data generator. Creates realistic worker names, employee IDs, machine serials, and test event histories for simulation runs. | Test data generation and simulation routines. |
| **`numpy`** | Scientific Computing | Fundamental package for numerical computing. Operates on image tensors, bounding box coordinates, and array metrics. | `detection/ppe_detector.py`, `detection/fire_detector.py`, `detection/pipeline.py` |
| **`pandas`** | Data Analysis | High-performance tabular data manipulation library. Aggregates event records, filters by date/shift, calculates risk distributions, and formats export tables. | `reports/export.py`, `dashboard/app.py` |
| **`fpdf2`** | Report Generation | Pure-Python PDF generation library. Compiles structured incident histories and shift handover briefings into formal, downloadable PDF audit documents. | `reports/` PDF generation. |
| **`openpyxl`** | Spreadsheet Export | Excel workbook reader/writer (`.xlsx`). Exports compliance logs and event records into spreadsheets for management auditing. | `reports/` Excel export utilities. |
| **`jinja2`** | HTML Templating | Fast, secure template engine. Renders dynamic HTML layouts for printable inspection reports and structured email notification alerts. | Report templating and email generation. |
| **`python-dotenv`** | Environment Config | Reads `.env` files and loads environment variables into `os.environ` so secret API keys and ports stay out of source control. | `agent/shift_report.py`, `api/main.py` |
| **`loguru`** | Logging | Modern, structured, colorized logging library. Replaces `print()` with timestamped, thread-safe log output for monitoring backend transactions. | Global logging across backend services. |
| **`requests`** | HTTP Client | Synchronous HTTP client library. Used for external API health probes, dataset downloading, and webhook dispatches. | `detection/download_ppe_dataset.py` |
| **`schedule`** | Task Scheduling | In-process job scheduler. Triggers periodic background jobs, such as generating an automated shift briefing every 8 hours. | Background shift report scheduling. |
| **`tqdm`** | Progress Bars | Extensible progress bar utility for console loops. Provides visual feedback during batch video frame processing and dataset downloads. | Batch vision test scripts and dataset downloaders. |
| **`fastapi`** | Web API Framework | The primary REST API framework powering the application. Defines routes, handles CORS, validates incoming schemas, and executes application logic. | `api/main.py` |
| **`uvicorn`** | ASGI Web Server | Lightning-fast ASGI web server implementation used to run and host the FastAPI application. | Running `uvicorn api.main:app --port 8000`. |

---

## 3. Every Folder & File: Why It Was Created & What It Is Used For

### Root Directory

* **`.env.example`**
  - *Why Created:* Version-controlled environment variable template.
  - *What Used For:* Shows required configuration keys (`OPENAI_API_KEY`, `NVIDIA_API_KEY`, `OPENROUTER_API_KEY`, `AI_PROVIDER`, `AI_MODEL`) without exposing private credentials.
* **`.gitignore`**
  - *Why Created:* Git exclusion manifest.
  - *What Used For:* Excludes `venv/`, `__pycache__/`, `.env`, temporary video outputs, and system cache files from Git.
* **`README.md`**
  - *Why Created:* Primary GitHub repository overview.
  - *What Used For:* Documents the web application architecture (HTML/CSS/JS frontend + FastAPI backend), technology stack, API endpoints, setup instructions, and database schema.
* **`PROJECT_STRUCTURE_AND_DEPENDENCIES.md`**
  - *Why Created:* Comprehensive file and package reference manual.
  - *What Used For:* In-depth explanation of every single dependency and file in the codebase.
* **`REQUIREMENTS_EXPLAINED.md`**
  - *Why Created:* Dedicated requirements explanation reference (this file).
  - *What Used For:* Details why every library was chosen, where it is consumed, and why FastAPI is the backend.
* **`execution_log.md`**
  - *Why Created:* Chronological engineering ledger.
  - *What Used For:* Tracks the historical record of project updates, test logs, bug fixes, and milestones across development sprints (Updates 1 to 13).
* **`presentation_notes.md`**
  - *Why Created:* Defense and panel preparation guide.
  - *What Used For:* Contains the project elevator pitch, real vs. simulated boundary breakdown, panel Q&A answers, and a 2-minute live demo script.
* **`requirements.txt`**
  - *Why Created:* Python dependency manifest.
  - *What Used For:* Enables reproducible installation of all project packages via `pip install -r requirements.txt`.
* **`test_pipeline.py`**
  - *Why Created:* Automated end-to-end integration test.
  - *What Used For:* Tests the full pipeline loop: image detection, reasoning classification, conveyor state transitions, SQLite insertion, and SHA-256 hash chaining.
* **`yolo26n.pt` & `yolov8n.pt`**
  - *Why Created:* Pretrained nano base model weights.
  - *What Used For:* Baseline models for general person/object detection and Ultralytics library verification.

---

### `api/` — Backend REST API
* **`api/main.py`**
  - *Why Created:* The core FastAPI backend application.
  - *What Used For:* Exposes REST endpoints (`/api/health`, `/api/status`, `/api/events`, `/api/events/pending`, `/api/approvals`, `/api/simulation/trigger`, `/api/machines`, `/api/ai/config`, `/api/ai/test`, `/api/ai/reason`), enforces CORS, parses Pydantic models, and interfaces with the database and simulation layers.

---

### `frontend/` — Web Application Client
* **`frontend/index.html`**
  - *Why Created:* The Single Page Application (SPA) HTML shell.
  - *What Used For:* Declares the global header, navigation bar, API status badge, and HTML containers for all 12 views: Floor View, Trigger Console, Reasoning Trail, Pending Actions, Worker Records, Audit Reports, Risk Trends, Ask JARVIS, Upload & Inspect, Shift Handover, Audit Verification, Alert Setup.
* **`frontend/css/reset.css`**
  - *Why Created:* Cross-browser style normalization.
  - *What Used For:* Resets default browser margins, padding, and box-sizing to ensure consistent rendering across browsers.
* **`frontend/css/tokens.css`**
  - *Why Created:* Design token definitions.
  - *What Used For:* Defines CSS custom properties (`:root`) for warm ivory/dark slate palettes, semantic status colors (critical, warning, normal), typography, and spacing.
* **`frontend/css/layout.css`**
  - *Why Created:* Structural application styling.
  - *What Used For:* Styles the top navigation header, page container widths, responsive grid layouts, and active SPA view toggling.
* **`frontend/css/components.css`**
  - *Why Created:* UI component stylesheets.
  - *What Used For:* Styles summary metric cards, facility map topology layout, machine status cards, approval buttons, modal overlays, data tables, and chat messages.
* **`frontend/js/api.js`**
  - *Why Created:* Reusable HTTP client module.
  - *What Used For:* Wraps native `fetch` into helper methods (`api.get()`, `api.post()`, `api.health()`) targeting `http://127.0.0.1:8000/api`.
* **`frontend/js/app.js`**
  - *Why Created:* Client-side application controller.
  - *What Used For:* Implements client-side hash routing (`window.location.hash`), polls `/api/status` every 5 seconds, polls `/api/health` every 15 seconds, handles approval actions, simulation triggers, and chat interactions.

---

### `agent/` — Autonomous Reasoning & Reporting
* **`agent/__init__.py`**
  - *Why Created:* Python package marker.
  - *What Used For:* Enables imports of reasoning functions.
* **`agent/reasoner.py`**
  - *Why Created:* Deterministic reasoning engine.
  - *What Used For:* Evaluates raw detection payloads from YOLO or conveyor faults; assigns operational category (`safety`, `mechanical`) and severity (`low`, `medium`, `high`, `critical`); generates human-readable corrective action proposals.
* **`agent/shift_report.py`**
  - *Why Created:* Automated shift briefing generator.
  - *What Used For:* Aggregates shift incidents from SQLite, constructs prompts, queries LLMs (OpenAI, NVIDIA NIM, OpenRouter), and generates executive summaries. Includes deterministic local fallback if no API key is provided.

---

### `database/` — SQLite & Cryptographic Audit Trail
* **`database/__init__.py`**
  - *Why Created:* Package marker.
* **`database/db.py`**
  - *Why Created:* SQLite Data Access Layer (DAL).
  - *What Used For:* Automatically creates the SQLite database and schemas (`events`, `conveyor_state`); implements SHA-256 cryptographic hash-chaining (`record_hash` + `prev_hash`); provides querying and approval update functions.
* **`database/jarvis.db`**
  - *Why Created:* Live SQLite database file.
  - *What Used For:* Persists all historical incident records, approval states, and conveyor telemetry.

---

### `detection/` — Computer Vision & YOLO Inference
* **`detection/__init__.py`**
  - *Why Created:* Package marker.
* **`detection/models/best_ppe.pt`**
  - *Why Created:* Custom fine-tuned YOLO model for PPE gear.
  - *What Used For:* Detects 11 classes: `helmet`, `gloves`, `vest`, `boots`, `goggles`, `none`, `Person`, `no_helmet`, `no_goggle`, `no_gloves`, `no_boots`.
* **`detection/models/best_fire.pt`**
  - *Why Created:* Custom fine-tuned YOLO model for hazards.
  - *What Used For:* Detects 6 classes: `fire`, `smoke`, `person`, `with helmet`, `with ppe`, `without helmet`.
* **`detection/ppe_detector.py`**
  - *Why Created:* PPE detection module.
  - *What Used For:* Loads `best_ppe.pt`, processes images and video streams frame-by-frame, identifies missing safety gear, and outputs annotated images.
* **`detection/fire_detector.py`**
  - *Why Created:* Hazard detection module.
  - *What Used For:* Loads `best_fire.pt`, detects fire and smoke hazards in images and video streams.
* **`detection/pipeline.py`**
  - *Why Created:* Unified detection and reasoning pipeline.
  - *What Used For:* Accepts media inputs, invokes the appropriate detector, passes results to `agent/reasoner.py`, and records the event into SQLite.
* **`detection/test_inputs/`**
  - *Why Created:* Test media repository.
  - *What Used For:* Contains sample industrial images and video sequences (`ppe/` and `fire_smoke/`) for testing and evaluation.
* **Test & Verification Scripts:**
  - `check_yolo26.py`, `download_ppe_dataset.py`, `image_input_test.py`, `video_input_test.py`, `yolo_download_test.py`, `yolo_image_test.py`, `yolo_video_test.py`, `run_tests.py`, `test_all_inputs.py`: Scripts created to download datasets, benchmark frame rates, and verify detector accuracy.

---

### `guardrails/` — Policy Enforcement & Safety Validation
* **`guardrails/__init__.py`**
  - *Why Created:* Package marker.
* **`guardrails/config.yaml`**
  - *Why Created:* Declarative guardrail rules configuration.
  - *What Used For:* Lists blocked action keywords, restricted system operations, and threshold limits.
* **`guardrails/policy.py`**
  - *Why Created:* Safety policy definitions.
  - *What Used For:* Formalizes immutable rules (e.g., AI cannot execute direct physical motor stops without human approval).
* **`guardrails/rules.py`**
  - *Why Created:* Rule evaluation logic.
  - *What Used For:* Pattern matching algorithms that check proposed actions against security policies.
* **`guardrails/validator.py`**
  - *Why Created:* Enforcement interceptor.
  - *What Used For:* Evaluates proposed actions before execution; raises `GuardrailException` and returns a `BLOCKED` status if an action violates safety policies.

---

### `simulation/` — Machinery Simulation
* **`simulation/__init__.py`**
  - *Why Created:* Package marker.
* **`simulation/conveyor.py`**
  - *Why Created:* Stand-in software state machine for Line 1 conveyor.
  - *What Used For:* Simulates operational states (`running`, `stopped`, `faulted`); handles commanded user actions (`run()`, `manual_stop()`) and injected faults (`mechanical_jam`, `sensor_misalignment`, `motor_overheat`); persists states to `conveyor_state` in SQLite.

---

### `reports/` — Compliance & Export
* **`reports/__init__.py`**
  - *Why Created:* Package marker.
* **`reports/export.py`**
  - *Why Created:* Audit export utility.
  - *What Used For:* Queries the SQLite event log into a pandas DataFrame and exports timestamped CSV reports for external compliance audits.

---

### `alerts/` — Escalation & Notifications
* **`alerts/__init__.py`**
  - *Why Created:* Notification dispatch package.
  - *What Used For:* Provides notification hooks for desktop push alerts (`plyer`), email notifications (`smtplib`), and mobile dispatch (`twilio`).

---

### `dashboard/` — Legacy / Prototype Streamlit UI
* **`dashboard/__init__.py`**
  - *Why Created:* Package marker.
* **`dashboard/app.py`**
  - *Why Created:* Early-phase all-in-one prototype dashboard.
  - *What Used For:* Maintained as an alternative, Python-only local interface for rapid testing and standalone demonstration.

---

### `.streamlit/` — Streamlit Configuration
* **`.streamlit/config.toml`**
  - *Why Created:* Runtime configuration file for Streamlit.
  - *What Used For:* Enforces a unified dark theme (`#0a0a0a`) when running the prototype `dashboard/app.py`.
