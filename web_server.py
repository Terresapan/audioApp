"""
Dad's YouTube Translator - Web Server
FastAPI server that broadcasts translations to connected browsers.

Usage:
    python web_server.py

Then open: http://localhost:5050
"""

import os
import asyncio
import json
from typing import Set
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# AI Clients
from deepgram import AsyncDeepgramClient
from deepgram.core.events import EventType
from deepgram.extensions.types.sockets import ListenV1ResultsEvent
from groq import AsyncGroq
import edge_tts

load_dotenv()

# Configuration
PORT = 5050
MIN_WORDS_SENTENCE = 10
MIN_WORDS_PAUSE = 25
FORCE_TRANSLATE_WORDS = 40
MIN_WORDS_UTTERANCE_END = 8

# Initialize AI Clients
deepgram = AsyncDeepgramClient(api_key=os.getenv("DEEPGRAM_API_KEY"))
groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))


# --- Connection Manager for Broadcasting ---
class ConnectionManager:
    """Manages WebSocket connections for broadcasting translations."""
    
    def __init__(self):
        self.browser_connections: Set[WebSocket] = set()
        self.audio_source: WebSocket | None = None
        self.sentence_buffer: list = []
        self.dg_connection = None
    
    async def connect_browser(self, websocket: WebSocket):
        await websocket.accept()
        self.browser_connections.add(websocket)
        print(f"🌐 Browser connected ({len(self.browser_connections)} total)")
    
    def disconnect_browser(self, websocket: WebSocket):
        self.browser_connections.discard(websocket)
        print(f"🌐 Browser disconnected ({len(self.browser_connections)} total)")
    
    async def broadcast_text(self, text: str, translation: str):
        """Send translation to all connected browsers."""
        message = json.dumps({
            "type": "translation",
            "original": text,
            "translation": translation
        })
        disconnected = set()
        for ws in self.browser_connections:
            try:
                await ws.send_text(message)
            except:
                disconnected.add(ws)
        self.browser_connections -= disconnected
    
    async def broadcast_audio(self, audio_bytes: bytes):
        """Send TTS audio to all connected browsers."""
        disconnected = set()
        for ws in self.browser_connections:
            try:
                await ws.send_bytes(audio_bytes)
            except:
                disconnected.add(ws)
        self.browser_connections -= disconnected
    
    async def broadcast_status(self, status: str):
        """Send status update to all browsers."""
        message = json.dumps({"type": "status", "message": status})
        for ws in self.browser_connections:
            try:
                await ws.send_text(message)
            except:
                pass


manager = ConnectionManager()


# --- App Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 Dad's Translator starting on http://localhost:{PORT}")
    print(f"📱 Mobile access: http://<your-mac-ip>:{PORT}")
    yield
    print("👋 Shutting down...")


app = FastAPI(lifespan=lifespan)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- Routes ---
@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/mobile")
async def mobile():
    return FileResponse("templates/index.html")


@app.websocket("/ws/browser")
async def browser_websocket(websocket: WebSocket):
    """WebSocket endpoint for browser clients to receive translations."""
    await manager.connect_browser(websocket)
    try:
        while True:
            # Browser can send commands (e.g., start/stop)
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif msg.get("type") == "stop":
                # Stop the audio source connection
                print("⏹️ Stop command received from browser")
                if manager.audio_source:
                    try:
                        await manager.audio_source.close()
                    except:
                        pass
                    manager.audio_source = None
                await manager.broadcast_status("⏹️ Translation stopped by user")
    except WebSocketDisconnect:
        manager.disconnect_browser(websocket)


@app.websocket("/ws/audio")
async def audio_websocket(websocket: WebSocket):
    """WebSocket endpoint for audio input (from audio_bridge.py or mobile mic)."""
    await websocket.accept()
    manager.audio_source = websocket  # Store reference for stop command
    
    # Check if this is a mobile client (vs audio_bridge)
    # Audio bridge sends linear16 param. Mobile sends default/webm.
    # If mobile, add to browser_connections so it receives the translations back!
    encoding_param = websocket.query_params.get("encoding")
    is_mobile = encoding_param != "linear16"
    
    if is_mobile:
        manager.browser_connections.add(websocket)
        print("📱 Mobile client connected (receiving translations)")
    else:
        print("🎤 Audio bridge connected (input only)")
    
    await manager.broadcast_status("🎤 Audio source connected")
    
    sentence_buffer = []
    
    # Determine Deepgram options based on client type
    # audio_bridge.py sends raw PCM (linear16), Mobile sends WebM/Opus (auto-detect)
    encoding_param = websocket.query_params.get("encoding")
    
    deepgram_options = {
        "model": "nova-3",
        "language": "en-US",
        "smart_format": "true",
        "punctuate": "true",
        "interim_results": "true",
        "endpointing": 500,
        "utterance_end_ms": 1500,
        "channels": "1"
    }
    
    if encoding_param == "linear16":
        deepgram_options["encoding"] = "linear16"
        deepgram_options["sample_rate"] = "16000"
    
    try:
        # Create Deepgram connection
        async with deepgram.listen.v1.connect(**deepgram_options) as dg_connection:
            
            async def on_message(result):
                nonlocal sentence_buffer
                
                # Handle UtteranceEnd event
                if hasattr(result, 'type') and getattr(result, 'type', None) == 'UtteranceEnd':
                    if sentence_buffer:
                        full_text = " ".join(sentence_buffer)
                        word_count = len(full_text.split())
                        if word_count < MIN_WORDS_UTTERANCE_END:
                            print(f"⏭️ Skipped short UtteranceEnd ({word_count} words)")
                            sentence_buffer = []
                            return
                        print(f"🔇 UtteranceEnd ({word_count} words): {full_text}")
                        sentence_buffer = []
                        await process_translation(full_text)
                    return
                
                if isinstance(result, ListenV1ResultsEvent):
                    if result.channel and result.channel.alternatives:
                        sentence = result.channel.alternatives[0].transcript
                        if sentence and result.is_final:
                            sentence_buffer.append(sentence)
                            
                            full_text = " ".join(sentence_buffer)
                            word_count = len(full_text.split())
                            
                            has_ending = any(full_text.rstrip().endswith(p) for p in ['.', '!', '?'])
                            is_speech_final = result.speech_final if result.speech_final is not None else False
                            
                            should_translate = (
                                (has_ending and word_count >= MIN_WORDS_SENTENCE) or 
                                (is_speech_final and word_count >= MIN_WORDS_PAUSE) or 
                                word_count >= FORCE_TRANSLATE_WORDS
                            )
                            
                            if should_translate:
                                print(f"👂 Heard ({word_count} words): {full_text}")
                                sentence_buffer = []
                                await process_translation(full_text)
            
            dg_connection.on(EventType.MESSAGE, on_message)
            listen_task = asyncio.create_task(dg_connection.start_listening())
            
            try:
                # Receive audio from client
                while True:
                    audio_data = await websocket.receive_bytes()
                    await dg_connection._send(audio_data)
            except WebSocketDisconnect:
                pass
            finally:
                listen_task.cancel()
                
    except Exception as e:
        print(f"❌ Audio connection error: {e}")
    finally:
        print("🎤 Audio source disconnected")
        if is_mobile:
            manager.disconnect_browser(websocket)
        await manager.broadcast_status("🎤 Audio source disconnected")


async def process_translation(text: str):
    """Translate text and broadcast to all browsers."""
    translation = await translate_text(text)
    if translation:
        print(f"🧠 Translated: {translation}")
        await manager.broadcast_text(text, translation)
        
        # Generate and send TTS audio
        audio_bytes = await generate_audio(translation)
        if audio_bytes:
            await manager.broadcast_audio(audio_bytes)


async def translate_text(text: str) -> str:
    """Translate English to Chinese using Groq."""
    try:
        completion = await groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system", 
                    "content": """You are a professional simultaneous interpreter translating English to Chinese (Mandarin). 
Rules:
1. Translate naturally as spoken Chinese, not formal written Chinese
2. Keep the same meaning and tone
3. Output ONLY the Chinese translation, nothing else
4. If the input is an incomplete fragment, translate it as naturally as possible"""
                },
                {"role": "user", "content": text}
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        result = completion.choices[0].message.content
        return result if result else ""
    except Exception as e:
        print(f"❌ Translation Error: {e}")
        return ""


async def generate_audio(text: str) -> bytes | None:
    """Generate TTS audio for Chinese text."""
    if not text:
        return None
    try:
        communicate = edge_tts.Communicate(text, "zh-CN-YunxiNeural")
        audio_buffer = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_buffer += chunk["data"]
        return audio_buffer if audio_buffer else None
    except Exception as e:
        print(f"❌ TTS Error: {e}")
        return None


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT, ssl_keyfile="key.pem", ssl_certfile="cert.pem")
