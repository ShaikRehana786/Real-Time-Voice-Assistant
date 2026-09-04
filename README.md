# 🎙️ Hazir: Real-Time Full-Duplex Voice Assistant

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python_3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![WebSockets](https://img.shields.io/badge/WebSockets-Full--Duplex-4B8BBE?style=for-the-badge&logo=socketdotio&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)

A low-latency, full-duplex conversational voice agent engineered for real-time interaction, zero-friction barge-in interruption, and deterministic side-effect tool calling.

---

## ⚡ System Architecture

```text
        [ User Microphone ]                  [ Audio Output ]
                |                                    ^
                v                                    |
       +-----------------+                  +------------------+
       |  Web Speech STT |                  |  Web Speech TTS  |
       +--------+--------+                  +--------^---------+
                | (Streamed Transcripts)             | (Synthesized Audio)
                v                                    |
     +============================================================+
     |                     Browser Client                         |
     |  * WebSocket Duplex Client (index.html)                    |
     |  * Sub-1.5s Round-Trip Latency Telemetry                   |
     |  * Zero-Lag Barge-In Interruption Handler                  |
     +============================================================+
                                 ^ |
               WebSockets (ws://)| | JSON Payloads
                                 | v
     +============================================================+
     |                 FastAPI Asynchronous Backend               |
     |  * WebSocket Event Lifecycle Manager                       |
     |  * Concurrent Tool Dispatcher & Intent Classifier          |
     +============================================================+
                                 |
           +---------------------+---------------------+
           v                     v                     v
 +-------------------+ +-------------------+ +-------------------+
 |   Weather API     | |   Reminder Tool   | |   Database Tool   |
 |   (wttr.in API)   | |  (SQLite Storage) | |  (SQLite Storage) |
 +-------------------+ +-------------------+ +-------------------+
```

---

## 🚀 Key Highlights

* **Sub-1.5s Round-Trip Latency (RTT):** Monitored in real time via telemetry counters embedded directly in the frontend interface.
* **Instant Barge-In Protocol:** Immediately cancels ongoing TTS audio playback when user speech activity is detected.
* **Live Side-Effect Tool Invocations:**
  * `tool_weather`: Outbound async HTTP calls to retrieve real-time location-based weather metrics.
  * `tool_reminders`: Persistent task scheduling stored inside SQLite.
  * `tool_database`: Structured CRUD notes operations with query retention.

---

## 🛠️ Tool Calling Pipeline

| Tool | Purpose | Persistence Layer | External Integration |
| :--- | :--- | :--- | :--- |
| **`tool_weather`** | Live temperature and forecast lookups | In-memory cache | `wttr.in` REST API |
| **`tool_reminders`** | Schedule and list tasks | SQLite (`assistant.db`) | Local database engine |
| **`tool_database`** | Store and query personal notes | SQLite (`assistant.db`) | Local database engine |

---

## 📦 Setup & Execution

### 1. Installation
```bash
git clone https://github.com/ShaikRehana786/Real-Time-Voice-Assistant.git
cd Real-Time-Voice-Assistant
pip install -r requirements.txt
```

### 2. Start Server
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Open Assistant
Visit `http://127.0.0.1:8000` in Google Chrome or Microsoft Edge and enable microphone access when prompted.
