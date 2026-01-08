"""
Audio Bridge for Windows - Captures VB-Cable audio, sends to server, and plays translations.

This script runs on the Windows host (not in Docker) because Docker 
cannot access Windows audio devices.

Prerequisites:
    - VB-Audio Virtual Cable installed (https://vb-audio.com/Cable/)
    - Windows Sound Settings configured to route audio through VB-Cable
    - web_server.py running on port 5050

Usage:
    python audio_bridge_windows.py
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


def find_vbcable_device() -> int | None:
    """Find VB-Audio Virtual Cable device index."""
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        name_lower = device['name'].lower()
        # Look for VB-Cable Output (this is the input source for capturing)
        if any(x in name_lower for x in ['cable output', 'vb-audio virtual cable']):
            if device['max_input_channels'] > 0:
                print(f"✅ Found VB-Cable: {device['name']} (index {i})")
                return i
    return None


def list_input_devices():
    """List all available audio input devices."""
    print("\n🎤 Available audio inputs:")
    devices = sd.query_devices()
    valid = []
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            print(f"   [{i}] {device['name']}")
            valid.append(i)
    return valid


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


def select_input_device() -> int | None:
    """Interactively select input device if VB-Cable not found."""
    valid_devices = list_input_devices()
    try:
        selection = input("\n👉 Enter the ID of your audio input (VB-Cable Output): ")
        device_id = int(selection)
        if device_id in valid_devices:
            return device_id
        else:
            print("Invalid ID.")
            return None
    except ValueError:
        print("Invalid input.")
        return None


def select_output_device() -> int | None:
    """Interactively select output device."""
    valid_devices = list_output_devices()
    try:
        selection = input("\n👉 Enter the ID of your Earbuds/Headphones: ")
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


async def audio_sender(input_device: int):
    """Capture VB-Cable audio and send to server."""
    print(f"🎤 Audio Sender connecting (input: device [{input_device}])...")
    
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
                device=input_device,
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
    print("🎤 Audio Bridge for Windows - With Translation Playback")
    print("=" * 60)
    
    # 1. Find VB-Cable for input
    vbcable_device = find_vbcable_device()
    if vbcable_device is None:
        print("\n⚠️ VB-Cable not auto-detected. Please select manually:")
        print("   (Install from: https://vb-audio.com/Cable/)")
        vbcable_device = select_input_device()
        if vbcable_device is None:
            print("❌ No input device selected. Exiting.")
            return
    print(f"\n✅ Input: Device [{vbcable_device}]")
    
    # 2. Select output device for translations (Earbuds/Headphones)
    output_device = select_output_device()
    if output_device is None:
        print("❌ No output device selected. Exiting.")
        return
    print(f"✅ Output: Device [{output_device}]")
    
    print("\n🎧 Instructions:")
    print("   1. In Windows Sound Settings:")
    print("      - Set 'CABLE Input (VB-Audio)' as default playback device")
    print("      - This routes all system audio through VB-Cable")
    print("   2. Play a YouTube video in your browser")
    print("   3. Translations will play through your selected output device")
    print("\nPress Ctrl+C to stop.\n")
    
    # 3. Run both sender and receiver concurrently
    print("🚀 Starting Bridge...")
    await asyncio.gather(
        audio_sender(vbcable_device),
        tts_receiver(output_device)
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Stopping audio bridge...")
