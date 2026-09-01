# 🎙️ JARVIS — Evaluation & Presentation Defense Notes

**Project:** JARVIS (Joint Autonomous Reasoning & Vision Inspection System)  
**Candidate:** Adib Sajjad Patel | Diploma in Computer Engineering  
**Current Status:** ~65–70% Complete (12 of 18 Functional Requirements Implemented & Verified)

---

## 🎯 1. The 60-Second Elevator Pitch

> *"JARVIS is an autonomous monitoring and decision system for manufacturing units. Instead of being just another computer-vision alert script, JARVIS combines multi-modal perception (PPE compliance, fire/smoke hazard detection, and simulated conveyor fault monitoring) with a **permission-gated AI reasoning layer**. When an incident occurs, the AI classifies severity, formulates an action plan, and presents it to a human supervisor for approval before anything affects the physical line. All records are cryptographically hash-chained in an audit log to prevent tampering."*

---

## 🏗️ 2. What Is Real vs. What Is Simulated? (Be 100% Honest)

| Component | Status | How to explain to the panel |
|---|:---:|---|
| **Computer Vision (PPE & Fire)** | **REAL** | *"We run trained YOLO models (`best_ppe.pt` with 11 classes, and `best_fire.pt` with 6 classes) on real image and video files uploaded via the dashboard interface."* |
| **Reasoning Agent** | **REAL** | *"The decision engine (`agent/reasoner.py`) deterministically evaluates incident telemetry, differentiates commanded stops from unplanned mechanical faults, and computes severity and action proposals."* |
| **Conveyor Equipment** | **SIMULATED** | *"Since industrial factory hardware/PLCs are not accessible in a student lab, the conveyor line is simulated via a software state machine (`simulation/conveyor.py`) with scripted fault injection per Proposal Section 4."* |
| **Tamper-Evident Audit Log** | **REAL** | *"Each event in the SQLite database is linked using SHA-256 hash chaining (`record_hash` + `prev_hash`), ensuring retroactive edits break the verification chain."* |

---

## ❓ 3. Likely Panel Questions & Prepared Answers

### Q1: *"Why not just use an alert script when YOLO detects a missing helmet?"*
**Answer:**  
*"Standard detection tools only output raw bounding boxes. JARVIS adds an autonomous reasoning layer that understands context: a single missing glove is a low-severity notification, but multiple missing items escalate to high severity with supervisor floor intervention. More importantly, JARVIS handles multi-domain telemetry (fire emergencies, conveyor mechanical failures) through a unified human-in-the-loop approval workflow."*

### Q2: *"Why is there no webcam or live RTSP camera feed?"*
**Answer:**  
*"Per Project Proposal Section 4 and the SRS constraints, industrial inspection in this prototype is demonstrated via user-uploaded image and video files to ensure repeatable, deterministic evaluation without relying on unstable hardware or classroom webcams."*

### Q3: *"How does the system know if a conveyor stopped normally versus broke down?"*
**Answer:**  
*"The state machine tracks transition origin. When an operator clicks 'Manual Stop', it's flagged as a commanded change — normal operational state, no incident logged. When a sensor or mechanical fault is injected, `is_commanded_change()` returns `False`, which immediately triggers the reasoning agent to classify it as a HIGH severity mechanical fault requiring maintenance authorization."*

### Q4: *"What is currently complete versus what remains?"*
**Answer:**  
*"We have completed **12 of 18 Functional Requirements**: full PPE detection, fire/smoke detection, conveyor fault simulation, the reasoning agent, human approval gating, live telemetry dashboard, video inference, CSV audit export, digital twin status board, trend analytics, and tamper-evident hash chaining. The remaining 6 features (DeepFace worker recognition, Twilio SMS/SMTP alerts, full multi-user RBAC, and LLM natural-language queries) are planned for the next development phase."*

---

## 🎬 4. Step-by-Step Live Demo Script (2 Minutes)

1. **Open Dashboard (`http://localhost:8501`)**
   - Show the 5 stat cards and live incident feed.
2. **Demo 1 — PPE Compliance (`Upload & Detect`)**
   - Upload `detection/test_inputs/ppe/bo.jpg`.
   - Show YOLO annotations + Agent Decision (`Severity: MEDIUM`, `Action: Issue warning, missing safety vest`).
3. **Demo 2 — Fire Safety (`Upload & Detect`)**
   - Switch to Fire mode, upload `detection/test_inputs/fire_smoke/fire.jpg`.
   - Show flame detection (88.8% confidence) + Agent Decision (`Severity: CRITICAL`, `Action: Evacuate zone immediately`).
4. **Demo 3 — Conveyor Simulation (`Conveyor Control`)**
   - Click `Run Line`, then `Manual Stop` — point out that no fault is triggered.
   - Select `mechanical_jam` and click `Inject Unplanned Fault` — point out that an incident is immediately generated and dispatched to the approval queue.
5. **Demo 4 — Human Approval Gate (`Approval Queue`)**
   - Show the pending incident proposals.
   - Click `Approve` or `Deny` — show that status updates in real-time.
6. **Demo 5 — Audit Trail & Export (`Event Log`)**
   - Expand an event to show the SHA-256 cryptographic hash chain (`record_hash` / `prev_hash`).
   - Click `📥 Export CSV` to demonstrate one-click audit export for compliance reporting.
