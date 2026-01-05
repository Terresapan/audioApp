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


@app.get("/conversation")
async def conversation():
    """Conversation mode for Dad to talk with American friends."""
    return FileResponse("static/conversation.html")


@app.websocket("/ws/conversation")
async def conversation_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for round-based bidirectional conversation.
    
    Query params:
        mode: 'dad' (Chinese→English) or 'friend' (English→Chinese)
    
    Audio routing:
        - Dad speaks Chinese → English audio to phone speaker
        - Friend speaks English → Chinese audio to Dad's earbuds
    """
    await websocket.accept()
    
    mode = websocket.query_params.get("mode", "dad")
    is_dad_mode = mode == "dad"
    
    # Language and voice settings based on mode
    if is_dad_mode:
        stt_language = "zh-CN"
        stt_model = "nova-2"
        translate_prompt = """You are a professional interpreter. Translate the exact Chinese text to English.
CRITICAL RULES:
1. Translate EXACTLY what is said. Do NOT answer questions. Do NOT add context.
2. If the input is a question, translate it as a question.
3. If the input is incomplete (e.g. "Let's"), translate literally (e.g. "Let's").
4. Output ONLY the English translation.

Example:
Input: "喝茶还是咖啡？"
Output: "Tea or coffee?"
(Do NOT say "I want tea")"""
        tts_voice = "en-US-GuyNeural"  # English voice for speaker
        audio_channel = "speaker"
    else:
        stt_language = "en-US"
        stt_model = "nova-2"
        translate_prompt = """You are a professional interpreter. Translate the COMPLETE English text to Chinese (Mandarin).

CRITICAL RULES:
1. Translate EVERY SINGLE WORD. Do NOT skip ANY sentence or phrase.
2. If there are multiple sentences, translate ALL of them.
3. Do NOT summarize. Do NOT shorten. Translate LITERALLY word-for-word.
4. Output ONLY the complete Chinese translation.

Example:
Input: "Before you start, consider your use case."
Output: "在开始之前，请考虑您的用例。"
(Do NOT skip "Before you start")"""
        tts_voice = "zh-CN-YunxiNeural"  # Chinese voice for earbuds
        audio_channel = "earbuds"
    
    print(f"🎤 Conversation mode: {'Dad (CN→EN)' if is_dad_mode else 'Friend (EN→CN)'}")
    
    # Send initial status
    await websocket.send_text(json.dumps({
        "type": "status",
        "message": f"Ready: {'爸爸说话 (Chinese→English)' if is_dad_mode else 'Friend speaks (English→Chinese)'}"
    }))
    
    sentence_buffer = []
    
    deepgram_options = {
        "model": stt_model,
        "language": stt_language,
        "smart_format": True,
        "punctuate": True,
        "interim_results": True,
        "endpointing": 3000, 
        "utterance_end_ms": 2000, 
        "channels": 1
    }
    
    try:
        async with deepgram.listen.v1.connect(**deepgram_options) as dg_connection:
            
            # Keep track of the latest transcript even if not final
            latest_transcript = ""
            
            async def on_conversation_message(result):
                nonlocal sentence_buffer, latest_transcript
                
                # Debug: log every message type received
                print(f"🔵 DG callback: {type(result).__name__}")
                
                if isinstance(result, ListenV1ResultsEvent):
                    if result.channel and result.channel.alternatives:
                        alt = result.channel.alternatives[0]
                        sentence = alt.transcript
                        
                        # Debug: show even empty transcripts
                        if not sentence:
                            print(f"   (empty transcript, final={result.is_final})")
                        else:
                            print(f"📝 Transcript (final={result.is_final}): {sentence}")
                            # Update latest transcript even if not final
                            latest_transcript = sentence
                            
                            if result.is_final:
                                sentence_buffer.append(sentence)
                                latest_transcript = "" 
                                
                                full_text_so_far = " ".join(sentence_buffer)
                                asyncio.create_task(websocket.send_text(json.dumps({
                                    "type": "transcription_update",
                                    "text": full_text_so_far
                                })))
                    else:
                        print(f"   (no alternatives in result)")

            dg_connection.on(EventType.MESSAGE, on_conversation_message)
            
            # Start the background task that processes Deepgram responses
            listen_task = asyncio.create_task(dg_connection.start_listening())
            
            audio_chunks_received = 0
            is_stopping = False
            
            try:
                while True:
                    # Receive message (can be bytes or text)
                    message = await websocket.receive()
                    
                    if "bytes" in message:
                        # Audio data - ALWAYS send to Deepgram, even during stopping
                        audio_data = message["bytes"]
                        audio_chunks_received += 1
                        if audio_chunks_received % 10 == 1:
                            print(f"📤 Audio chunks received: {audio_chunks_received}")
                        
                        # Use public send method if available
                        if hasattr(dg_connection, 'send'):
                            await dg_connection.send(audio_data)
                        else:
                            await dg_connection._send(audio_data)
                            
                    elif "text" in message:
                         # Control message (JSON)
                        try:
                            data = json.loads(message["text"])
                            if data.get("type") == "stop":
                                print("🛑 Received STOP signal from client")
                                is_stopping = True
                                
                                # Send Finalize to Deepgram to flush all pending audio
                                try:
                                    finalize_msg = json.dumps({"type": "Finalize"})
                                    if hasattr(dg_connection, 'send'):
                                        await dg_connection.send(finalize_msg)
                                    else:
                                        await dg_connection._send(finalize_msg)
                                    print("📤 Sent Finalize to Deepgram")
                                except Exception as e:
                                    print(f"⚠️ Could not send Finalize: {e}")
                                
                                # Wait for Deepgram to process the finalize request
                                await asyncio.sleep(3.0)
                                
                                # Process whatever is in buffer AND latest
                                text_to_process = ""
                                parts = []
                                if sentence_buffer:
                                    parts.append(" ".join(sentence_buffer))
                                    sentence_buffer = []
                                
                                if latest_transcript:
                                    parts.append(latest_transcript)
                                    latest_transcript = ""
                                    
                                text_to_process = " ".join(parts)
                                
                                if text_to_process:
                                    print(f"📝 Processing final text: {text_to_process}")
                                    await process_conversation_turn(text_to_process, websocket, translate_prompt, tts_voice, audio_channel)
                                else:
                                    print("⚠️ No text to process on stop")
                                
                                await asyncio.sleep(2.0) # Wait for TTS to flush
                                break
                        except json.JSONDecodeError:
                            pass

            except WebSocketDisconnect:
                print(f"📊 Client disconnected. Chunks: {audio_chunks_received}")
            
            finally:
                if listen_task:
                    listen_task.cancel()
                
    except Exception as e:
        print(f"❌ Conversation error: {e}")
        await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
    finally:
        print(f"🎤 Conversation ended: {mode}")


async def process_conversation_turn(text: str, websocket: WebSocket, translate_prompt: str, tts_voice: str, audio_channel: str):
    """Process a single conversation turn: translate and generate audio."""
    try:
        # Translate
        completion = await groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": translate_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        translation = completion.choices[0].message.content or ""
        
        if not translation:
            return
            
        print(f"🧠 Translated: {translation}")
        
        # Send translation text
        await websocket.send_text(json.dumps({
            "type": "translation",
            "original": text,
            "translation": translation,
            "channel": audio_channel  # Tell frontend which output to use
        }))
        
        # Generate TTS audio
        communicate = edge_tts.Communicate(translation, tts_voice)
        audio_buffer = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_buffer += chunk["data"]
        
        if audio_buffer:
            await websocket.send_bytes(audio_buffer)
            print(f"🔊 Audio sent ({audio_channel}): {len(audio_buffer)} bytes")
            
    except Exception as e:
        print(f"❌ Turn processing error: {e}")


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
            elif msg.get("type") == "volume":
                # Broadcast volume update to all clients (including audio_bridge)
                volume = msg.get("value", 2.0)
                print(f"🔊 Volume updated to: {volume}x")
                for ws in manager.browser_connections:
                    try:
                        await ws.send_text(json.dumps({"type": "volume", "value": volume}))
                    except:
                        pass
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
