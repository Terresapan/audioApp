#!/usr/bin/env python3
"""
Desktop YouTube Translator for Windows
=======================================
Captures Windows system audio via VB-Cable, translates English→Chinese,
and plays the translation through a specified audio output (e.g., Bluetooth earbuds).

Requirements:
1. VB-Audio Virtual Cable installed (https://vb-audio.com/Cable/)
2. Windows Sound Settings configured:
   - Default playback: "CABLE Input (VB-Audio Virtual Cable)"
   - Use "CABLE Output" as input source here
3. Bluetooth earbuds or headphones connected

Usage:
    python desktop_translator_windows.py
"""

import os
import asyncio
import io
import numpy as np
import sounddevice as sd
import pygame
from dotenv import load_dotenv

# AI Clients - same as server.py
from deepgram import AsyncDeepgramClient
from groq import AsyncGroq
import edge_tts

load_dotenv()

# Initialize clients
deepgram = AsyncDeepgramClient(api_key=os.getenv("DEEPGRAM_API_KEY"))
groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

# Audio settings
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_DURATION = 0.25  # seconds

# Translation chunking thresholds (Lecture Mode - optimized for accuracy)
# Larger chunks = better context for translation quality
MIN_WORDS_SENTENCE = 10    # Minimum words when sentence ends with . ! ?
MIN_WORDS_PAUSE = 25       # Minimum words on natural pause
FORCE_TRANSLATE_WORDS = 40 # Force translate at this many words

def list_audio_devices():
    """List all available audio input/output devices."""
    print("\n📢 Available Audio Devices:")
    print("-" * 60)
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        device_type = ""
        if device['max_input_channels'] > 0:
            device_type += "[INPUT] "
        if device['max_output_channels'] > 0:
            device_type += "[OUTPUT]"
        print(f"  {i}: {device['name']} {device_type}")
    print("-" * 60)
    return devices

def find_vbcable_device():
    """Find VB-Audio Virtual Cable device index."""
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        name_lower = device['name'].lower()
        if any(x in name_lower for x in ['cable output', 'vb-audio virtual cable']):
            if device['max_input_channels'] > 0:
                print(f"✅ Found VB-Cable input: {device['name']} (index {i})")
                return i
    return None

def find_output_device(name_contains=""):
    """Find an output device by name."""
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if device['max_output_channels'] > 0:
            if name_contains.lower() in device['name'].lower():
                print(f"✅ Found output device: {device['name']} (index {i})")
                return i
    return None

def select_input_device() -> int | None:
    """Interactively select input device."""
    devices = sd.query_devices()
    valid = []
    print("\n🎤 Available audio inputs:")
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            print(f"   [{i}] {device['name']}")
            valid.append(i)
    try:
        selection = input("\n👉 Enter the ID of your audio input (VB-Cable Output): ")
        device_id = int(selection)
        if device_id in valid:
            return device_id
        else:
            print("Invalid ID.")
            return None
    except ValueError:
        print("Invalid input.")
        return None

async def translate_text(text: str) -> str:
    """Translate English text to Chinese using Groq."""
    try:
        completion = await groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",  # Higher rate limits: 14.4K req/day, 500K tokens/day
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

async def speak_chinese(text: str, output_device: int = 1):
    """Convert Chinese text to speech and play to specific output device."""
    if not text:
        return
    
    try:
        print(f"🔊 Speaking: {text}")
        communicate = edge_tts.Communicate(text, "zh-CN-YunxiNeural")
        
        # Collect all audio chunks
        audio_buffer = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_buffer += chunk["data"]
        
        if audio_buffer:
            # Save to temp file and play with pygame to specific device
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                f.write(audio_buffer)
                temp_file = f.name
            
            # Use pygame for playback
            pygame.mixer.init()
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            
            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
                
            pygame.mixer.quit()
            
            # Clean up temp file
            import os
            os.unlink(temp_file)
            
            print(f"✅ Finished speaking")
            
    except Exception as e:
        print(f"❌ TTS Error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main function to run the desktop translator."""
    print("=" * 60)
    print("🎬 Dad's YouTube Translator - Windows Desktop Version")
    print("=" * 60)
    
    # List devices
    list_audio_devices()
    
    # Find VB-Cable input
    vbcable_device = find_vbcable_device()
    if vbcable_device is None:
        print("\n⚠️ VB-Cable not auto-detected!")
        print("   Please install from: https://vb-audio.com/Cable/")
        print("   Or select your audio input device manually:")
        vbcable_device = select_input_device()
        if vbcable_device is None:
            print("❌ No input device selected. Exiting.")
            return
    
    print("\n🎧 Instructions:")
    print("   1. In Windows Sound Settings:")
    print("      - Set 'CABLE Input (VB-Audio)' as default playback device")
    print("   2. Connect Dad's Bluetooth earbuds")
    print("   3. Play a YouTube video in English")
    print("   4. Dad will hear Chinese translation!")
    
    print("\n📚 Lecture Mode (optimized for accuracy)")
    print(f"   Min words (sentence): {MIN_WORDS_SENTENCE}")
    print(f"   Min words (pause): {MIN_WORDS_PAUSE}")
    print(f"   Force translate at: {FORCE_TRANSLATE_WORDS} words")
    print("\nPress Ctrl+C to stop.\n")
    
    # Buffer for accumulating transcription
    sentence_buffer = []
    
    try:
        # Create Deepgram connection
        from deepgram.core.events import EventType
        from deepgram.extensions.types.sockets import ListenV1ResultsEvent
        
        print("🔌 Connecting to Deepgram...")
        
        async with deepgram.listen.v1.connect(
            model="nova-3",           # Upgraded: 54% lower WER, better for noisy audio
            language="en-US",
            smart_format="true",
            punctuate="true",
            interim_results="true",
            endpointing=500,          # 500ms silence triggers speech_final (default 10ms too fast)
            utterance_end_ms=1500,    # 1.5s word gap for UtteranceEnd (ignores background noise)
            encoding="linear16",
            sample_rate="16000",
            channels="1"
        ) as dg_connection:
            
            print("✅ Deepgram connected!")
            
            # Debug event handlers
            def on_open(data):
                print("🟢 Deepgram WebSocket OPEN")
            
            def on_close(data):
                print("🔴 Deepgram WebSocket CLOSED")
            
            def on_error(data):
                print(f"❌ Deepgram Error: {data}")
            
            dg_connection.on(EventType.OPEN, on_open)
            dg_connection.on(EventType.CLOSE, on_close)
            dg_connection.on(EventType.ERROR, on_error)
            
            async def on_message(result):
                nonlocal sentence_buffer
                
                # Handle UtteranceEnd event (triggered by utterance_end_ms)
                # This fires when there's a 1.5s gap in words - useful in noisy environments
                if hasattr(result, 'type') and getattr(result, 'type', None) == 'UtteranceEnd':
                    if sentence_buffer:
                        full_text = " ".join(sentence_buffer)
                        word_count = len(full_text.split())
                        # Skip short utterances - often garbage STT from noise
                        if word_count < 8:
                            print(f"\n⏭️ Skipped short UtteranceEnd ({word_count} words): {full_text}")
                            sentence_buffer = []
                            return
                        print(f"\n🔇 UtteranceEnd ({word_count} words): {full_text}")
                        sentence_buffer = []
                        translation = await translate_text(full_text)
                        if translation:
                            print(f"🧠 Translated: {translation}")
                            await speak_chinese(translation)
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
                            
                            # Use fixed thresholds for chunking (Lecture Mode)
                            should_translate = (has_ending and word_count >= MIN_WORDS_SENTENCE) or (is_speech_final and word_count >= MIN_WORDS_PAUSE) or word_count >= FORCE_TRANSLATE_WORDS
                            
                            if should_translate:
                                print(f"\n👂 Heard ({word_count} words): {full_text}")
                                sentence_buffer = []
                                translation = await translate_text(full_text)
                                if translation:
                                    print(f"🧠 Translated: {translation}")
                                    await speak_chinese(translation)
            
            dg_connection.on(EventType.MESSAGE, on_message)
            
            # Start listening
            listen_task = asyncio.create_task(dg_connection.start_listening())
            
            # Stream audio from VB-Cable to Deepgram
            print("🎤 Listening to system audio...")
            
            # Store event loop reference for the callback thread
            loop = asyncio.get_running_loop()
            audio_chunk_count = [0]  # Use list to allow modification in callback
            
            def audio_callback(indata, frames, time_info, status):
                if status:
                    print(f"Audio status: {status}")
                
                # Debug: show audio level periodically
                audio_chunk_count[0] += 1
                if audio_chunk_count[0] % 40 == 0:  # Every ~10 seconds
                    level = np.abs(indata).max()
                    print(f"📊 Audio level: {level:.4f} (chunks: {audio_chunk_count[0]})")
                
                # Convert to bytes and send to Deepgram
                audio_bytes = (indata * 32767).astype(np.int16).tobytes()
                asyncio.run_coroutine_threadsafe(
                    dg_connection._send(audio_bytes),
                    loop  # Use the stored loop reference
                )
            
            with sd.InputStream(
                device=vbcable_device,
                channels=CHANNELS,
                samplerate=SAMPLE_RATE,
                dtype=np.float32,
                callback=audio_callback,
                blocksize=int(SAMPLE_RATE * CHUNK_DURATION)
            ):
                # Keep running until Ctrl+C
                while True:
                    await asyncio.sleep(1)
                    
    except KeyboardInterrupt:
        print("\n\n👋 Stopping translator...")
        # Send CloseStream to flush any buffered audio before closing
        try:
            import json
            await dg_connection._send(json.dumps({"type": "CloseStream"}))
            await asyncio.sleep(0.5)  # Brief wait for final response
            print("✅ CloseStream sent - audio flushed")
        except:
            pass  # Connection may already be closed
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
