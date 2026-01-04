"""
Audio Bridge - Captures BlackHole audio, sends to server, and plays translations.

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
import ssl
import json
import miniaudio

# Configuration
WS_AUDIO_URL = "wss://localhost:5050/ws/audio?encoding=linear16"
WS_BROWSER_URL = "wss://localhost:5050/ws/browser"
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_DURATION = 0.25  # 250ms chunks

# Global volume setting (can be updated via WebSocket)
current_volume = 4.0  # Default: 4x boost

# Create SSL context to trust self-signed certificate
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


def find_blackhole_device() -> int | None:
    """Find BlackHole audio device index."""
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if 'blackhole' in device['name'].lower():
            if device['max_input_channels'] > 0:
                return i
    return None


def list_output_devices():
    """List all available audio output devices."""
    print("\n🔊 Available audio outputs:")
    devices = sd.query_devices()
    valid = []
    for i, device in enumerate(devices):
        if device['max_output_channels'] > 0:
            print(f"   [{i}] {device['name']}")
            valid.append(i)
    return valid


def select_output_device() -> int | None:
    """Interactively select output device."""
    valid_devices = list_output_devices()
    try:
        selection = input("\n👉 Enter the ID of your Earbuds (e.g. 2): ")
        device_id = int(selection)
        if device_id in valid_devices:
            return device_id
        else:
            print("Invalid ID.")
            return None
    except ValueError:
        print("Invalid input.")
        return None


def decode_mp3_to_pcm(mp3_bytes: bytes) -> tuple[np.ndarray, int, int]:
    """Decode MP3 bytes to PCM samples using miniaudio."""
    global current_volume
    decoded = miniaudio.decode(mp3_bytes, output_format=miniaudio.SampleFormat.SIGNED16)
    samples = np.frombuffer(decoded.samples, dtype=np.int16)
    # Convert to float32 for sounddevice (range -1 to 1)
    samples_float = samples.astype(np.float32) / 32768.0
    # Apply volume boost and clip to prevent distortion
    samples_float = np.clip(samples_float * current_volume, -1.0, 1.0)
    # Reshape to (frames, channels) if stereo
    if decoded.nchannels > 1:
        samples_float = samples_float.reshape(-1, decoded.nchannels)
    return samples_float, decoded.sample_rate, decoded.nchannels


async def tts_receiver(output_device_id: int):
    """Receive TTS audio from server and play to selected device."""
    print(f"🎧 TTS Receiver connecting (output: device [{output_device_id}])...")
    
    try:
        async with websockets.connect(WS_BROWSER_URL, ssl=ssl_context, ping_interval=None) as ws:
            print("✅ TTS Receiver connected!")
            
            while True:
                message = await ws.recv()
                
                if isinstance(message, bytes):
                    # MP3 audio data - decode and play
                    try:
                        samples, sample_rate, nchannels = decode_mp3_to_pcm(message)
                        frames = len(samples) if nchannels == 1 else len(samples)
                        print(f"🔈 Playing {frames} frames @ {sample_rate}Hz ({nchannels}ch) to device [{output_device_id}]")
                        # Non-blocking play - don't wait, let it overlap if needed
                        sd.play(samples, samplerate=sample_rate, device=output_device_id)
                        # Use asyncio.sleep instead of sd.wait() to avoid blocking
                        # Approximate duration
                        duration = len(samples) / sample_rate if nchannels == 1 else len(samples) / sample_rate
                        await asyncio.sleep(duration + 0.1)  # Small buffer
                    except Exception as e:
                        print(f"❌ Decode/play error: {e}")
                else:
                    # JSON message (translation text, status, volume)
                    try:
                        global current_volume
                        data = json.loads(message)
                        if data.get('type') == 'translation':
                            print(f"\n🧠 翻译: {data['translation']}")
                        elif data.get('type') == 'volume':
                            current_volume = data.get('value', 2.0)
                            print(f"🔊 Volume updated to: {current_volume}x")
                    except:
                        pass
                        
    except Exception as e:
        print(f"❌ TTS Receiver error: {e}")


async def audio_sender(blackhole_device: int):
    """Capture BlackHole audio and send to server."""
    print(f"🎤 Audio Sender connecting (input: BlackHole [{blackhole_device}])...")
    
    try:
        async with websockets.connect(WS_AUDIO_URL, ssl=ssl_context) as ws:
            print("✅ Audio Sender connected!")
            
            loop = asyncio.get_running_loop()
            chunk_count = [0]
            
            def audio_callback(indata, frames, time_info, status):
                if status:
                    print(f"Status: {status}")
                
                chunk_count[0] += 1
                if chunk_count[0] % 40 == 0:
                    level = np.abs(indata).max()
                    print(f"📊 Audio level: {level:.4f} (chunks: {chunk_count[0]})")
                
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
                    
    except Exception as e:
        print(f"❌ Audio Sender error: {e}")


async def main():
    print("=" * 60)
    print("🎤 Audio Bridge - With Translation Playback")
    print("=" * 60)
    
    # 1. Find BlackHole for input
    blackhole_device = find_blackhole_device()
    if blackhole_device is None:
        print("❌ BlackHole not found! Install with: brew install blackhole-2ch")
        return
    print(f"\n✅ Input: BlackHole [{blackhole_device}]")
    
    # 2. Select output device for translations (Earbuds)
    output_device = select_output_device()
    if output_device is None:
        print("❌ No output device selected. Exiting.")
        return
    print(f"✅ Output: Device [{output_device}]")
    
    print("\n🎧 Instructions:")
    print("   1. Set Mac output to 'YouTube Translator' (Multi-Output)")
    print("   2. Mute the browser tab (optional - to avoid double audio)")
    print("   3. Play a YouTube video")
    print("\nPress Ctrl+C to stop.\n")
    
    # 3. Run both sender and receiver concurrently
    print("🚀 Starting Bridge...")
    await asyncio.gather(
        audio_sender(blackhole_device),
        tts_receiver(output_device)
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Stopping audio bridge...")
