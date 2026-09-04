import os
import json
import base64
import time
import ssl
import urllib.request
import urllib.parse
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from db import add_reminder, list_reminders

app = FastAPI()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Unverified SSL context to bypass missing local OpenSSL certificates
ssl_ctx = ssl._create_unverified_context()

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_reminder",
            "description": "Add a task reminder with a specific time",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "The task to remember"},
                    "time": {"type": "string", "description": "When the task is due"}
                },
                "required": ["task", "time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_reminders",
            "description": "List all existing saved reminders",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]

def run_tool(name: str, arguments: dict) -> str:
    if name == "add_reminder":
        return add_reminder(arguments.get("task", ""), arguments.get("time", ""))
    elif name == "list_reminders":
        return list_reminders()
    return "Unknown tool."

def transcribe_audio_api(audio_bytes: bytes) -> str:
    boundary = "----WebKitFormBoundaryVoiceAssist"
    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(b'Content-Disposition: form-data; name="model"\r\n\r\nwhisper-1\r\n')
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(b'Content-Disposition: form-data; name="file"; filename="audio.wav"\r\nContent-Type: audio/wav\r\n\r\n')
    body.extend(audio_bytes)
    body.extend(f"\r\n--{boundary}--\r\n".encode())

    req = urllib.request.Request(
        "https://api.openai.com/v1/audio/transcriptions",
        data=body,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        }
    )
    with urllib.request.urlopen(req, context=ssl_ctx) as resp:
        res = json.loads(resp.read().decode())
        return res.get("text", "")

def llm_chat_completion(messages: list, use_tools: bool = True) -> dict:
    payload = {
        "model": "gpt-4o-mini",
        "messages": messages
    }
    if use_tools:
        payload["tools"] = TOOLS
        payload["tool_choice"] = "auto"

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
    )
    with urllib.request.urlopen(req, context=ssl_ctx) as resp:
        return json.loads(resp.read().decode())

def tts_generate_api(text: str) -> bytes:
    payload = {
        "model": "tts-1",
        "voice": "alloy",
        "input": text
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/audio/speech",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
    )
    with urllib.request.urlopen(req, context=ssl_ctx) as resp:
        return resp.read()

@app.websocket("/ws")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            if payload.get("type") == "interrupt":
                continue

            if payload.get("type") == "audio_input":
                t_start = time.time()
                audio_bytes = base64.b64decode(payload.get("data"))

                # 1. STT
                user_text = transcribe_audio_api(audio_bytes)
                stt_latency = round((time.time() - t_start) * 1000, 2)
                
                await websocket.send_json({
                    "type": "transcript",
                    "text": user_text,
                    "latency_stt_ms": stt_latency
                })

                # 2. LLM + Function Calling
                llm_start = time.time()
                messages = [
                    {"role": "system", "content": "You are a concise voice assistant. Give 1-2 sentence direct answers."},
                    {"role": "user", "content": user_text}
                ]
                
                llm_res = llm_chat_completion(messages)
                msg = llm_res["choices"][0]["message"]
                
                if msg.get("tool_calls"):
                    for tool in msg["tool_calls"]:
                        args = json.loads(tool["function"]["arguments"])
                        tool_out = run_tool(tool["function"]["name"], args)
                        messages.append(msg)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool["id"],
                            "content": tool_out
                        })
                    second_res = llm_chat_completion(messages, use_tools=False)
                    reply_text = second_res["choices"][0]["message"]["content"]
                else:
                    reply_text = msg.get("content", "")

                llm_latency = round((time.time() - llm_start) * 1000, 2)

                # 3. TTS
                tts_start = time.time()
                tts_bytes = tts_generate_api(reply_text)
                tts_latency = round((time.time() - tts_start) * 1000, 2)
                total_latency = round((time.time() - t_start) * 1000, 2)

                await websocket.send_json({
                    "type": "audio_output",
                    "audio": base64.b64encode(tts_bytes).decode("utf-8"),
                    "text": reply_text,
                    "metrics": {
                        "stt_ms": stt_latency,
                        "llm_ms": llm_latency,
                        "tts_ms": tts_latency,
                        "total_ms": total_latency
                    }
                })

    except WebSocketDisconnect:
        pass

@app.get("/")
async def get_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())
