# 🤖 JARVIS — AI Surveillance & Alert System

> An end-to-end AI system for real-time object detection, face recognition, intelligent alerting, and automated reporting.

---

## 📁 Project Structure

```
jarvis/
├── detection/       # YOLOv8/v11 object & person detection
├── simulation/      # Data simulation & test scenario generation
├── agent/           # LLM-powered decision-making agent (GPT-4o)
├── alerts/          # Desktop, email & SMS notification system
├── dashboard/       # Streamlit live monitoring dashboard
├── reports/         # Auto-generated PDF / Excel / HTML reports
├── venv/            # Python virtual environment (not committed)
├── requirements.txt # All Python dependencies
├── .env             # API keys & secrets (not committed)
└── .gitignore
```

---

## 🚀 Setup

### 1. Clone the repo
```bash
git clone <your-repo-url>
cd jarvis
```

### 2. Create & activate virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure secrets
Create a `.env` file in the root:
```
OPENAI_API_KEY=sk-...
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
ALERT_EMAIL=you@example.com
```

---

## 🧩 Modules

| Module | Technology | Purpose |
|---|---|---|
| `detection/` | YOLOv8, OpenCV | Real-time object & person detection |
| `simulation/` | Faker, NumPy | Synthetic data for testing |
| `agent/` | LangChain, GPT-4o | AI decision-making & reasoning |
| `alerts/` | Plyer, Twilio, SMTP | Multi-channel alert delivery |
| `dashboard/` | Streamlit, Plotly | Live monitoring UI |
| `reports/` | FPDF2, OpenPyXL | Automated report generation |

---

## 🛠 Tech Stack

- **Python 3.10+**
- **YOLOv8 / Ultralytics** — object detection
- **DeepFace** — face recognition & emotion analysis
- **Streamlit** — dashboard
- **LangChain + OpenAI** — AI agent
- **Plotly** — data visualisation

---

## 📌 Status

🔨 In active development — Final Year Project
