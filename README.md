# JARVIS — Joint Autonomous Reasoning & Vision Inspection System

**Group No. 12**
*Adib Sajjad Patel* (Roll No. 59 | Enrollment No. 24211320284)
*Rudra Sujit Sagar*
*Abhishek Chavan*
*Rasiklal M. Dhariwal Institute of Technology*
*Diploma in Computer Engineering | 5th Semester*

---

## 1. Project Overview

**JARVIS** is an agentic, multi-modal industrial monitoring platform designed for modern manufacturing floors. It bridges the gap between passive computer-vision detection and active autonomous reasoning.

Rather than functioning as a standard alarm system that merely flags objects, JARVIS actively interprets environmental input, determines the operational severity of an event, proposes corrective actions, and strictly gates execution behind a human-in-the-loop approval process. Every step of this pipeline is securely logged in a cryptographic hash-chained database, providing an immutable audit trail for compliance and safety investigations.

## 2. Problem Statement

Modern manufacturing and industrial environments face several critical monitoring challenges:

- **Delayed Detection:** Human operators cannot continuously monitor all zones without fatigue, leading to delayed responses to fire/smoke hazards or mechanical failures.
- **PPE Non-Compliance:** Workers improperly wearing Personal Protective Equipment (PPE) are difficult to track manually on a bustling plant floor.
- **Alert Fatigue:** Basic vision systems flag every detection as an "alarm," overwhelming supervisors without providing actionable context.
- **Lack of Accountability:** When safety incidents occur or equipment is halted, there is often no structured, tamper-evident history explaining *why* the decision was made or *who* approved it.

## 3. Core Concept: Why JARVIS is "Agentic"

A basic **Detection-Only System** follows a rigid pipeline:
`Input → Detection (YOLO) → Alert`

JARVIS follows an **Agentic Reasoning Pipeline**, empowering it to understand context rather than just bounding boxes:

```text
Observe (Input Image/Video)
   ↓
Detect (Perception via YOLOv8/YOLO26)
   ↓
Understand (Event generation & Telemetry extraction)
   ↓
Reason (Agentic determination of operational severity and category)
   ↓
Propose (Formulation of a specific human-readable corrective action)
   ↓
Human Approval (Supervisor/Manager explicitly authorizes or denies)
   ↓
Simulate Action (Updating the software state-machine of the factory floor)
   ↓
Record (Immutable hash-chained database entry)
```

By separating *perception* from *reasoning* and strictly requiring *human approval*, JARVIS acts as an intelligent assistant that significantly reduces cognitive load on plant managers while preserving human accountability for critical decisions.

## 4. Implemented Features

- **Multi-Modal Vision Inspection (PPE & Fire/Smoke):**
  JARVIS accepts uploaded industrial images and frame-by-frame video sequences. It utilizes custom-trained YOLO models (`best_ppe.pt`, `best_fire.pt`) to detect safety gear compliance (helmets, vests, gloves) and imminent physical hazards (fire, smoke).
- **Conveyor Status Simulation:**
  JARVIS features a software state-machine simulating a physical industrial conveyor line. It tracks commanded operational states (`running`, `stopped`) and handles unplanned injected faults (e.g., `mechanical_jam`, `sensor_misalignment`).
- **Autonomous Reasoning Engine:**
  A deterministic rule-based engine evaluates detected incidents, assigns a severity rating (`low`, `medium`, `high`, `critical`), and proposes exact operational resolutions (e.g., "Halt Line 1 and alert maintenance").
- **Human-in-the-Loop Approval Gate:**
  All autonomous proposals that modify plant state or require intervention are placed in a 'Pending' queue, enforcing strict managerial sign-off before being marked as resolved.
- **Tamper-Evident Audit Logging:**
  Events are committed to an SQLite database utilizing SHA-256 cryptographic hash-chaining (`record_hash` + `prev_hash`), ensuring the historical event log cannot be secretly altered.
- **Interactive Industrial Dashboard:**
  An 8-page, monochrome "Swiss Design" Streamlit dashboard acts as the central command center, offering real-time telemetry feeds, digital twin layout mapping, and violation trend analytics.
- **Automated Shift Handover Report:**
  JARVIS utilizes advanced Large Language Models (LLMs) via API to autonomously summarize incidents from the past shift, providing a plain-English briefing for oncoming supervisors. If cloud endpoints fail, it gracefully degrades to a deterministic local rule engine to ensure zero downtime.

## 5. System Architecture

```text
                    ┌──────────────────────┐
                    │       INPUTS         │
                    │ Uploaded Images /    │
                    │ Video / UI Commands  │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │   PERCEPTION LAYER   │
                    │ PPE (YOLO) / Fire /  │
                    │ Conveyor Simulation  │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │    EVENT PROCESSING  │
                    │ Detection → SQLite   │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │   REASONING LAYER    │
                    │ Rule-Based Severity &│
                    │ Action Proposals     │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │   APPROVAL GATE      │
                    │ Supervisor Sign-off  │
                    │ (Approve / Deny)     │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │ ACTION / SIMULATION  │
                    │ (Update DB State)    │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │   PRESENTATION UI    │
                    │ Dashboard / Analytics│
                    │ Shift Handover / CSV │
                    └──────────────────────┘
```

## 6. Technology Stack

| Component                 | Technology              | Purpose                                              |
| :------------------------ | :---------------------- | :--------------------------------------------------- |
| **User Interface**  | Streamlit (Python)      | High-performance, monochrome reactive dashboard      |
| **Computer Vision** | Ultralytics YOLO26/v8   | High-speed object detection for PPE and Fire         |
| **Data Layer**      | SQLite (WAL Mode)       | Lightweight, persistent, transactional event storage |
| **Cryptography**    | SHA-256 (hashlib)       | Tamper-evident hash-chaining for audit logs          |
| **Reasoning (NLP)** | OpenAI API / NVIDIA NIM | LLM generation for Shift Handover summaries          |
| **Data Processing** | Pandas / OpenCV / NumPy | DataFrame manipulation, video frame extraction       |

## 7. Repository Structure

```text
jarvis/
├── agent/
│   ├── reasoner.py         # Evaluates detections, assigns severity, proposes actions
│   └── shift_report.py     # LLM integration & deterministic fallback for shift summaries
├── dashboard/
│   └── app.py              # Main 8-page Streamlit UI application
├── database/
│   ├── db.py               # SQLite Data Access Layer & SHA-256 hashing logic
│   └── jarvis.db           # Live SQLite database file (auto-generated)
├── detection/
│   ├── models/
│   │   ├── best_fire.pt    # Custom-trained YOLO model (Fire/Smoke)
│   │   └── best_ppe.pt     # Custom-trained YOLO model (11-class PPE)
│   ├── test_inputs/        # Sample images/videos for evaluation
│   ├── fire_detector.py    # Fire/Smoke inference logic (Image & Video)
│   ├── ppe_detector.py     # PPE compliance inference logic (Image & Video)
│   └── pipeline.py         # Orchestrator routing inputs to detectors & reasoner
├── reports/
│   └── export.py           # Pandas utility to convert SQLite events to CSV format
├── simulation/
│   └── conveyor.py         # Software state machine simulating Line 1 status & faults
├── .env.example            # Template for LLM API Keys (NVIDIA NIM/OpenAI/OpenRouter)
├── README.md               # Detailed project documentation (this file)
└── requirements.txt        # Python dependency manifest
```

## 8. Installation & Setup

### Prerequisites

- Python 3.9 - 3.11 installed.
- Git installed.
- A virtual environment (recommended).

### Step-by-Step Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/adibcopilot/jarvis.git
   cd jarvis
   ```
2. **Set Up Virtual Environment:**

   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```
3. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```
4. **Environment Configuration (Optional but Recommended):**
   To enable the LLM-powered Shift Handover report, duplicate the `.env.example` file and rename it to `.env`.

   ```bash
   cp .env.example .env
   ```

   Open `.env` and insert your API key for NVIDIA NIM, OpenRouter, or OpenAI. If no key is provided, the system gracefully falls back to a deterministic local rule engine.
5. **Launch the Dashboard:**

   ```bash
   streamlit run dashboard/app.py --server.port 8501
   ```

   The dashboard will automatically initialize the SQLite database if it does not exist.

## 9. Dashboard Walkthrough

JARVIS is operated through a central Streamlit application containing 8 core pages:

1. **📊 Dashboard:**
   The primary control center. Displays high-level metric cards, a real-time 'Live Incident Feed' table, and a deep-dive 'Event Inspection Panel' that reveals the cryptographic hash of any selected event.
2. **📤 Upload & Detect:**
   The interface for the Computer Vision perception layer. Users can upload images or video files (`.mp4`, `.jpg`). The asset is processed frame-by-frame by the chosen YOLO pipeline (PPE or Fire/Smoke), outputting annotated visuals, detection counts, and the agent's reasoning chain.
3. **⚙️ Conveyor Control:**
   The interface for the simulation layer. Users can execute standard operating commands ("Run", "Manual Stop") which do not trigger incidents, or inject unplanned faults ("Mechanical Jam", "Thermal Overload") which immediately trigger critical events requiring managerial sign-off.
4. **🌐 Digital Twin:**
   A high-level topology board mapping the operational status of three virtual factory zones: Zone 1 (Conveyor Line 1), Zone 2 (PPE Inspection), and Zone 3 (Fire/Smoke Monitor).
5. **📈 Violation Trends:**
   A visual analytics page plotting historical distributions of incidents categorized by severity and domain (safety vs. mechanical) using interactive bar charts.
6. **📋 Shift Handover:**
   Allows a supervisor to select a time window (e.g., "Last 8 Hours") and autonomously generate a plain-English briefing analyzing all incidents, downtime, and safety recommendations via LLM APIs.
7. **✅ Approval Queue:**
   The human-in-the-loop governance interface. All incidents with an action proposal sit in a "Pending" state here until a supervisor explicitly clicks "Approve" or "Deny," resolving the event and storing the authorized outcome.
8. **📜 Event Log:**
   The master audit trail. Displays the entire database history in filterable expander blocks containing the full JSON detection payload and SHA-256 chains. Includes a **"📥 Export CSV"** button for compliance reporting.

## 10. Technical Workflows

### PPE & Fire Detection Workflow

1. **Input:** User uploads an image or video via the **Upload & Detect** page.
2. **Detection:** The asset is routed via `pipeline.py` to `ppe_detector.py` or `fire_detector.py`. YOLO runs inference, generating bounding boxes, labels, and confidence scores.
3. **Event Generation:** The pipeline parses the detections into a JSON payload and calls `database/db.py` to record the event in SQLite.
4. **Reasoning:** `agent/reasoner.py` evaluates the JSON payload. (e.g., Missing helmet = HIGH severity). It generates a proposed action ("Issue warning to worker(s): Missing PPE helmet").
5. **Approval:** The event appears in the **Approval Queue** as pending. A manager reviews the annotated image and the proposed action, clicking "Approve."
6. **History:** The event is updated in the database with `resolved_at` and `approved_by` timestamps.

### Simulated Conveyor Workflow

*Note: JARVIS operates entirely through software simulation. No physical PLCs, real motors, or hardware conveyors are integrated.*

1. **State Machine:** `simulation/conveyor.py` holds the virtual state (`running`, `stopped`, `faulted`) for Line 1.
2. **Commanded Action:** If a user clicks "Manual Stop", the state updates cleanly without generating an incident, as this is planned operational behavior.
3. **Fault Injection:** If a user clicks "Inject Fault: mechanical_jam", the state immediately transitions to `faulted`.
4. **Agent Response:** The system registers an unplanned mechanical event, assigns it CRITICAL severity, and proposes a maintenance inspection, routing it to the Approval Gate.

## 11. Database Schema

The system uses a robust SQLite database operating in WAL (Write-Ahead Logging) mode. The core entity is the `events` table:

| Column              | Type     | Purpose                                           |
| :------------------ | :------- | :------------------------------------------------ |
| `event_id`        | INTEGER  | Primary Key.                                      |
| `timestamp`       | DATETIME | When the event was recorded.                      |
| `event_type`      | TEXT     | E.g.,`ppe`, `fire`, `conveyor`.             |
| `source_file`     | TEXT     | Originating image or video filename.              |
| `detections_json` | TEXT     | Complete array of YOLO bounding boxes and labels. |
| `severity`        | TEXT     | `low`, `medium`, `high`, or `critical`.   |
| `category`        | TEXT     | `safety`, `mechanical`, or `technical`.     |
| `proposed_action` | TEXT     | Agent's human-readable recommendation.            |
| `approval_status` | TEXT     | `pending`, `approved`, or `denied`.         |
| `approved_by`     | TEXT     | The authorizing user (defaults to 'Manager').     |
| `record_hash`     | TEXT     | SHA-256 hash of the row payload +`prev_hash`.   |
| `prev_hash`       | TEXT     | SHA-256 hash of the immediately preceding event.  |

This cryptographic chaining mechanism acts similarly to a blockchain, guaranteeing that if a historical event is modified directly via a SQL editor, the `record_hash` of all subsequent rows will break, instantly revealing the tampering.
