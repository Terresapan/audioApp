# import os
# import asyncio
# import uvicorn
# from fastapi import FastAPI, WebSocket, Request
# from fastapi.responses import HTMLResponse
# from fastapi.templating import Jinja2Templates
# from dotenv import load_dotenv

# # AI Clients - Deepgram SDK v5.3.0
# from deepgram import DeepgramClient, AsyncDeepgramClient
# from deepgram.core.events import EventType
# from deepgram.extensions.types.sockets import ListenV1ResultsEvent

# from groq import AsyncGroq
# import edge_tts

# load_dotenv()

# app = FastAPI()
# templates = Jinja2Templates(directory="templates")

# # Initialize Clients - v5.3.0 requires api_key as keyword argument
# deepgram = AsyncDeepgramClient(api_key=os.getenv("DEEPGRAM_API_KEY"))
# groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

# # --- 1. The HTML Page ---
# @app.get("/", response_class=HTMLResponse)
# async def get(request: Request):
#     return templates.TemplateResponse("index.html", {"request": request})

# # --- 2. The Translation Pipeline ---
# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     print(f"📱 Phone Connected from: {websocket.client.host}")

#     try:
#         # Create a WebSocket connection to Deepgram using v5.3.0 API
#         # Note: Browser sends audio/webm (opus codec), Deepgram auto-detects container formats
#         async with deepgram.listen.v1.connect(
#             model="nova-3",           # Upgraded: 54% lower WER, better accuracy
#             language="en-US",
#             smart_format="true",
#             punctuate="true",
#             interim_results="true"
#         ) as dg_connection:
            
#             # Buffer to accumulate text before translating
#             sentence_buffer = []
            
#             # Define what happens when we receive transcription results
#             async def on_message(result):
#                 nonlocal sentence_buffer
#                 if isinstance(result, ListenV1ResultsEvent):
#                     # Access the transcript from the result
#                     if result.channel and result.channel.alternatives:
#                         sentence = result.channel.alternatives[0].transcript
#                         if sentence and result.is_final:
#                             sentence_buffer.append(sentence)
                            
#                             full_text = " ".join(sentence_buffer)
#                             word_count = len(full_text.split())
                            
#                             # Check if this looks like a complete sentence
#                             has_ending = any(full_text.rstrip().endswith(p) for p in ['.', '!', '?'])
#                             is_speech_final = result.speech_final if result.speech_final is not None else False
                            
#                             # Only translate when we have:
#                             # 1. A sentence ending punctuation, OR
#                             # 2. A natural pause (speech_final) AND at least 10 words, OR
#                             # 3. Accumulated more than 20 words (force translate)
#                             should_translate = has_ending or (is_speech_final and word_count >= 10) or word_count >= 20
                            
#                             if should_translate:
#                                 print(f"👂 Heard ({word_count} words): {full_text}")
#                                 sentence_buffer = []  # Clear buffer
#                                 translation = await translate_text(full_text)
#                                 print(f"🧠 Translated: {translation}")
#                                 await generate_and_send_audio(translation, websocket)

#             # Register the message handler
#             dg_connection.on(EventType.MESSAGE, on_message)

#             # Start listening for messages in a background task
#             listen_task = asyncio.create_task(dg_connection.start_listening())

#             try:
#                 # Forward audio from client to Deepgram
#                 while True:
#                     data = await websocket.receive_bytes()
#                     await dg_connection._send(data)
#             except Exception as e:
#                 print(f"Loop ended: {e}")
#             finally:
#                 listen_task.cancel()

#     except Exception as e:
#         print(f"Connection Error: {e}")

# # --- Helper Functions ---

# async def translate_text(text: str):
#     try:
#         completion = await groq_client.chat.completions.create(
#             model="llama-3.3-70b-versatile",
#             messages=[
#                 {
#                     "role": "system", 
#                     "content": """You are a professional simultaneous interpreter translating English to Chinese (Mandarin). 
# Rules:
# 1. Translate naturally as spoken Chinese, not formal written Chinese
# 2. Keep the same meaning and tone
# 3. Output ONLY the Chinese translation, nothing else
# 4. If the input is an incomplete fragment, translate it as naturally as possible"""
#                 },
#                 {"role": "user", "content": text}
#             ],
#             temperature=0.2,
#             max_tokens=1024,
#         )
#         result = completion.choices[0].message.content
#         return result if result else ""
#     except Exception as e:
#         print(f"❌ Translation Error: {e}")
#         return ""

# async def generate_and_send_audio(text: str, websocket: WebSocket):
#     if not text:
#         print("⚠️ No text to speak")
#         return
#     try:
#         # Voice: zh-CN-YunxiNeural (Male) or zh-CN-XiaoxiaoNeural (Female)
#         print(f"🔊 Generating audio for: {text}")
#         communicate = edge_tts.Communicate(text, "zh-CN-YunxiNeural")
        
#         # Collect ALL chunks into one complete audio buffer
#         audio_buffer = b""
#         async for chunk in communicate.stream():
#             if chunk["type"] == "audio":
#                 audio_buffer += chunk["data"]
        
#         # Send the complete audio as one piece
#         if audio_buffer:
#             await websocket.send_bytes(audio_buffer)
#             print(f"✅ Audio sent: {len(audio_buffer)} bytes")
#         else:
#             print(f"⚠️ No audio chunks generated")
#     except Exception as e:
#         print(f"❌ Audio Error: {e}")

# # --- Main Entry Point (Configured for Port 8080 with HTTPS) ---
# if __name__ == "__main__":
#     print("🚀 Starting Dad App with HTTPS...")
#     print(f"👉 On his phone, open: https://{os.getenv('HOST_IP', '0.0.0.0')}:8080")
#     print("⚠️  Accept the security warning on the phone to proceed")
#     # Note: We bind to 0.0.0.0 to allow external connections
#     # Using self-signed SSL certificates for HTTPS (required for microphone on mobile)
#     uvicorn.run(
#         app, 
#         host="0.0.0.0", 
#         port=8080,
#         ssl_keyfile="key.pem",
#         ssl_certfile="cert.pem"
#     )