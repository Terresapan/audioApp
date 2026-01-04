"""
Audio Bridge - Captures BlackHole audio and sends to web server.

This script runs on the Mac host (not in Docker) because Docker 
cannot access macOS audio devices.

Usage:
    python audio_bridge.py

Prerequisites:
    - BlackHole 2ch installed
    - Multi-Output Device configured in Audio MIDI Setup
    - web_server.py running on port 5050
"""

import asyncio
import numpy as np
import sounddevice as sd
import websockets

# Configuration
WS_URL = "ws://localhost:5050/ws/audio"
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_DURATION = 0.25  # 250ms chunks


def find_blackhole_device() -> int | None:
    """Find BlackHole audio device index."""
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if 'blackhole' in device['name'].lower():
            if device['max_input_channels'] > 0:
                return i
    return None


def list_audio_devices():
    """List all available audio devices."""
    print("\n🔊 Available audio devices:")
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            marker = "👈" if 'blackhole' in device['name'].lower() else ""
            print(f"   [{i}] {device['name']} {marker}")


async def main():
    print("=" * 60)
    print("🎤 Audio Bridge - BlackHole → Web Server")
    print("=" * 60)
    
    list_audio_devices()
    
    blackhole_device = find_blackhole_device()
    if blackhole_device is None:
        print("\n❌ BlackHole not found!")
        print("   Install: brew install blackhole-2ch")
        print("   Then reboot your Mac")
        return
    
    print(f"\n✅ Using BlackHole device [{blackhole_device}]")
    print(f"🔌 Connecting to {WS_URL}...")
    
    try:
        async with websockets.connect(WS_URL) as ws:
            print("✅ Connected to web server!")
            print("\n🎧 Instructions:")
            print("   1. Set Mac output to 'Multi-Output Device'")
            print("   2. Open http://localhost:5050 in browser")
            print("   3. Play a YouTube video")
            print("\nPress Ctrl+C to stop.\n")
            
            loop = asyncio.get_running_loop()
            audio_chunk_count = [0]
            
            def audio_callback(indata, frames, time_info, status):
                if status:
                    print(f"Audio status: {status}")
                
                audio_chunk_count[0] += 1
                if audio_chunk_count[0] % 40 == 0:
                    level = np.abs(indata).max()
                    print(f"📊 Audio level: {level:.4f} (chunks: {audio_chunk_count[0]})")
                
                # Convert to 16-bit PCM bytes
                audio_bytes = (indata * 32767).astype(np.int16).tobytes()
                asyncio.run_coroutine_threadsafe(ws.send(audio_bytes), loop)
            
            with sd.InputStream(
                device=blackhole_device,
                channels=CHANNELS,
                samplerate=SAMPLE_RATE,
                dtype=np.float32,
                callback=audio_callback,
                blocksize=int(SAMPLE_RATE * CHUNK_DURATION)
            ):
                print("🎤 Capturing system audio...")
                while True:
                    await asyncio.sleep(1)
                    
    except ConnectionRefusedError:
        print(f"\n❌ Cannot connect to {WS_URL}")
        print("   Make sure web_server.py is running first!")
    except websockets.exceptions.ConnectionClosed:
        print("\n🔌 Connection to server closed")
    except KeyboardInterrupt:
        print("\n\n👋 Stopping audio bridge...")


if __name__ == "__main__":
    asyncio.run(main())
