# Hazir • Real-Time AI Voice Assistant (Project 5)

A low-latency, full-duplex streaming AI voice assistant that processes spoken natural language, triggers real tools (live weather, SQLite reminders, local database notes), articulates responses via text-to-speech, and handles barge-in interruptions gracefully.

## Architecture
- **Transport**: Full-duplex WebSockets over FastAPI (/ws).
- **Speech Pipeline**: Native streaming STT and TTS with regional Indian voice routing (en-IN, hi-IN, te-IN).
- **Tool Automation**:
  - tool_weather: Real-time weather and temperature via HTTP endpoints.
  - tool_reminders: Structured SQLite task persistence in assistant.db.
  - tool_database: Structured SQLite notes search and storage in assistant.db.
- **Knowledge Core**: Embedded multi-domain technical knowledge vault with instant web search fallback and Gemini LLM gateway.
- **Interruption (Barge-In)**: Instant cancellation frame execution on mic activation or manual stop trigger.

## Setup Instructions
```bash
pip install fastapi uvicorn
uvicorn main:app --host 127.0.0.1 --port 8000
```
Open http://127.0.0.1:8000 in Google Chrome or Microsoft Edge.
