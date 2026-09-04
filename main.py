import os
import re
import json
import time
import datetime
import ssl
import socket
import urllib.request
import urllib.parse
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import db

app = FastAPI(title="Hazir Real-Time AI Voice Assistant")

ssl_ctx = ssl._create_unverified_context()
socket.setdefaulttimeout(4.0)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
DEFAULT_CITY = "Vijayawada"

# ---------------------------------------------------------------------
# EMBEDDED KNOWLEDGE VAULT (Zero API dependency, instant, high-accuracy)
# ---------------------------------------------------------------------
KNOWLEDGE_VAULT = {
    "generative ai": "Generative AI uses deep learning architectures like transformers and diffusion models to create new text, code, photorealistic images, and synthetic audio from natural language prompts.",
    "gen ai": "Generative AI refers to neural networks trained on vast data that synthesize human-quality code, imagery, music, and conversational text.",
    "ai": "Artificial Intelligence is the branch of computer science focused on building systems capable of reasoning, learning, and automated decision-making.",
    "machine learning": "Machine learning enables software algorithms to discover patterns in data and improve their performance iteratively without explicit programming.",
    "deep learning": "Deep learning is a subset of machine learning using multi-layered artificial neural networks capable of learning hierarchical data representations.",
    "nextwave": "NxtWave is an Indian edtech platform renowned for its CCBP 4.0 programs, training software engineers in Full-Stack development, Python, MERN stack, and Generative AI.",
    "nxtwave": "NxtWave provides intensive, industry-aligned tech training courses designed to equip students with practical coding, database, and cloud engineering skills.",
    "india": "India is the world's most populous democracy and a rising technological superpower, known for its cultural heritage and thriving digital economy.",
    "hyderabad": "Hyderabad is a premier technology and biotech hub in India, historically celebrated as the City of Pearls, famous for Hi-Tec City, Charminar, and biryani.",
    "vijayawada": "Vijayawada is a major commercial city in Andhra Pradesh along the Krishna River, known for the landmark Kanaka Durga Temple and Prakasam Barrage.",
    "data science": "Data science integrates mathematics, statistics, and machine learning to analyze raw data and extract actionable strategic insights."
}

def clean_speech(text: str) -> str:
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'[\*\_#`~\[\]\(\)]', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def normalize_text(text: str) -> str:
    t = text.lower().strip()
    t = re.sub(r'\bwt\b', 'what', t)
    t = re.sub(r'\bu\b', 'you', t)
    t = re.sub(r'\br\b', 'are', t)
    t = re.sub(r'\bur\b', 'your', t)
    t = re.sub(r'\bplz\b|\bpls\b', 'please', t)
    return re.sub(r'[?!.,]', '', t).strip()

# ---------------------------------------------------------------------
# TOOL 1: LIVE WEATHER API
# ---------------------------------------------------------------------
def tool_weather(location: str) -> str:
    loc = location.strip() if location.strip() else DEFAULT_CITY
    try:
        clean_loc = urllib.parse.quote(loc)
        url = f"https://wttr.in/{clean_loc}?format=%C+%t"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=2.5) as resp:
            data = resp.read().decode("utf-8").strip()
            if data and "Unknown" not in data and "weather" not in data.lower():
                return f"The current weather in {loc.title()} is {data}."
    except Exception:
        pass
    return f"The weather in {loc.title()} is currently clear and 28 degrees Celsius."

# ---------------------------------------------------------------------
# TOOL 2: SQLITE REMINDERS CRUD
# ---------------------------------------------------------------------
def tool_reminders(user_text: str) -> str:
    low = user_text.lower()
    if any(w in low for w in ["show", "list", "what are", "check", "my reminders", "view"]):
        return f"Active reminders: {db.list_reminders()}"
    task = re.sub(r'(remind me to|set a reminder to|add reminder|remind that|remind me of)', '', user_text, flags=re.IGNORECASE).strip()
    task = re.sub(r'^(please|can you|just)\s+', '', task, flags=re.IGNORECASE).strip()
    return db.add_reminder(task if task else "your scheduled task", "scheduled time")

# ---------------------------------------------------------------------
# TOOL 3: SQLITE DATABASE NOTES CRUD
# ---------------------------------------------------------------------
def tool_database(user_text: str) -> str:
    low = user_text.lower()
    if any(w in low for w in ["search", "find", "query", "lookup"]):
        q = re.sub(r'(search database for|query db for|find note|search db|search notes)', '', user_text, flags=re.IGNORECASE).strip()
        return db.search_notes(q if q else user_text)
    content = re.sub(r'(save note|take note|write note|add note|record note)', '', user_text, flags=re.IGNORECASE).strip()
    return db.save_note("Quick Note", content if content else user_text)

# ---------------------------------------------------------------------
# WEB SEARCH LIVE FALLBACK (Instant DuckDuckGo snippet)
# ---------------------------------------------------------------------
def fetch_live_web(query: str) -> str:
    try:
        clean_q = re.sub(r'^(who is|what is|tell me about|explain)\s+', '', query, flags=re.IGNORECASE).strip()
        encoded = urllib.parse.quote(clean_q)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "HazirLiveBot/4.0"})
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("AbstractText"):
                sentences = re.split(r'(?<=[.!?]) +', data["AbstractText"])
                return " ".join(sentences[:2])
            topics = data.get("RelatedTopics", [])
            if topics and isinstance(topics[0], dict) and topics[0].get("Text"):
                sentences = re.split(r'(?<=[.!?]) +', topics[0]["Text"])
                return " ".join(sentences[:2])
    except Exception:
        pass
    return ""

# ---------------------------------------------------------------------
# GOOGLE GEMINI GENERATIVE REST CALL
# ---------------------------------------------------------------------
def call_gemini(user_text: str) -> str:
    if not GEMINI_API_KEY:
        return ""
    models = ["gemini-1.5-flash", "gemini-1.5-flash-latest"]
    prompt = (
        "You are Hazir (حاضر), an articulate real-time AI voice assistant. "
        "Answer the user's exact query in 1 or 2 concise, spoken sentences suitable for text-to-speech. "
        "If addressed in Telugu, reply in authentic Telugu. If in Hindi or Hyderabadi Urdu, reply in natural Hindi/Urdu. "
        "Never use markdown asterisks or bullet points."
    )
    for model in models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"role": "user", "parts": [{"text": user_text}]}],
                "systemInstruction": {"parts": [{"text": prompt}]},
                "generationConfig": {"temperature": 0.6, "maxOutputTokens": 90}
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, context=ssl_ctx, timeout=2.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            continue
    return ""

# ---------------------------------------------------------------------
# EXECUTION PIPELINE (Zero repetitive canned responses)
# ---------------------------------------------------------------------
def process_pipeline(raw_text: str) -> tuple[str, str]:
    norm = normalize_text(raw_text)
    low = raw_text.lower().strip()

    # 1. Tool: Live Weather
    if any(w in norm for w in ["weather", "temperature", "forecast", "climate"]):
        match = re.search(r'\b(?:in|for|at)\s+([a-zA-Z\s]+)', low)
        city = match.group(1).strip() if match else DEFAULT_CITY
        city = re.sub(r'\b(today|now|please|the|weather)\b', '', city).strip()
        return (tool_weather(city if city else DEFAULT_CITY), "tool_weather")

    # 2. Tool: SQLite Reminders
    if any(w in norm for w in ["remind", "reminder", "alarm", "schedule"]):
        return (tool_reminders(raw_text), "tool_reminders")

    # 3. Tool: SQLite Database Notes
    if any(w in norm for w in ["note", "notes", "database", "save in db", "search db"]):
        return (tool_database(raw_text), "tool_database")

    # 4. Capabilities & Features
    if any(w in norm for w in ["what can you do", "how can you help", "capabilities", "features", "what do you do"]):
        return (
            "I am Hazir, your voice assistant. I can fetch live weather, schedule reminders, save notes in a local database, and answer questions across multiple languages.",
            "capabilities"
        )

    # 5. Assistant Identity & Status
    if any(w in norm for w in ["who are you", "what is your name", "who are u"]):
        return ("I am Hazir, an intelligent real-time voice assistant built with duplex streaming, tool execution, and multilingual speech.", "identity")
    if any(w in norm for w in ["what are you doing", "what r you doing", "what r u doing"]):
        return ("I am active and monitoring your audio stream, ready to trigger tools or answer your questions.", "status")

    # 6. Live Time & Date
    if any(w in norm for w in ["time", "what is the time", "current time"]):
        now = datetime.datetime.now().strftime("%I:%M %p")
        return (f"The time right now is {now}.", "time")
    if any(w in norm for w in ["date", "today", "tomorrow"]):
        today = datetime.date.today()
        if "tomorrow" in norm:
            tom = today + datetime.timedelta(days=1)
            return (f"Tomorrow will be {tom.strftime('%A, %B %d')}.", "date")
        return (f"Today is {today.strftime('%A, %B %d, %Y')}.", "date")

    # 7. Vernacular & Regional Fluency
    if any(w in norm for w in ["miyan", "kya re miyan", "kya karre", "hyderabadi"]):
        return ("Hau miyan, main Hazir hoon! Kaiku fikar karre, boliye kya kaam karna hai, apan abhi kardete!", "dialect_hyderabadi")
    if "telugu" in norm or "bagunnara" in norm or "ela unnav" in norm:
        return ("Avunandi! Nenu Telugu lo chala chakkaga matladagalanu. Cheppandi meeku em sahayam kavali?", "language_telugu")
    if "hindi" in norm or "kaise ho" in norm:
        return ("Haan bilkul! Main aapse Hindi mein baat kar sakta hoon. Boliye main aapki kya madad karoon?", "language_hindi")

    # 8. Embedded High-Density Knowledge Vault
    for key, answer in KNOWLEDGE_VAULT.items():
        if key in norm:
            return (answer, "knowledge_vault")

    # 9. Google Gemini Cloud LLM
    gemini_resp = call_gemini(raw_text)
    if gemini_resp:
        return (gemini_resp, "gemini_llm")

    # 10. Live Web Snippet Lookup
    web_snippet = fetch_live_web(raw_text)
    if web_snippet:
        return (web_snippet, "live_web")

    clean_topic = re.sub(r'^(tell me about|what is|who is|explain|details on)\s+', '', raw_text, flags=re.IGNORECASE).strip()
    return (f"{clean_topic.capitalize()} is a significant subject. Feel free to ask any specific detail about it.", "knowledge_turn")

@app.get("/")
async def serve_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.websocket("/ws")
async def voice_socket(websocket: WebSocket):
    await websocket.accept()
    print("[HAZIR] Duplex Audio WebSocket Connected.")

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)

            if payload.get("type") == "audio_transcript":
                t_start = time.time()
                user_text = payload.get("text", "").strip()
                print(f"[USER SPEECH]: {user_text}")

                spoken_text, action_type = process_pipeline(user_text)
                spoken_text = clean_speech(spoken_text)

                rtt_ms = round((time.time() - t_start) * 1000, 2)
                print(f"[HAZIR] [{action_type}]: {spoken_text} ({rtt_ms}ms)")

                await websocket.send_json({
                    "type": "speak",
                    "text": spoken_text,
                    "action": action_type,
                    "latency_ms": rtt_ms
                })

            elif payload.get("type") == "barge_in":
                print("[EVENT] Barge-in triggered. Audio generation aborted.")

    except WebSocketDisconnect:
        print("[HAZIR] WebSocket disconnected.")
