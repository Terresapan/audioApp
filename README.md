# Dad's YouTube Translator / Audio App

A real-time audio translation application designed to bridge language barriers. This project provides tools to translate computer audio (like YouTube videos) or live conversations from English to Chinese (and vice versa) using state-of-the-art AI services.

## Features

- **Real-time Audio Translation**: Captures system audio (or microphone input) and translates it on the fly.
- **Web Interface**:
  - Broadcasts translations to connected browsers.
  - **Conversation Mode**: Bidirectional translation (English <-> Chinese) for face-to-face conversations using a phone and desktop.
- **Desktop Mode**: A standalone CLI tool for background translation of system audio.
- **AI Integration**:
  - **Deepgram**: Fast and accurate Speech-to-Text (STT).
  - **Groq (Llama 3)**: Low-latency translation.
  - **Edge TTS**: Natural-sounding Text-to-Speech (TTS).

---

## Prerequisites

- **Python 3.12+**
- **Deepgram API Key** (for STT)
- **Groq API Key** (for Translation)
- **Virtual Audio Driver**: [BlackHole 2ch](https://github.com/ExistentialAudio/BlackHole) (Required for capturing system audio on macOS).
- **SSL Certificates** (`cert.pem` and `key.pem`) for secure WebSocket connections.

## Project Components

1.  **`web_server.py`**: The main FastAPI backend. Handles WebSocket connections, orchestrates AI services, and serves the web UI.
2.  **`audio_bridge.py`**: A helper script used when running `web_server.py` (especially in Docker). It captures local system audio via BlackHole and sends it to the web server over WebSockets.
3.  **`desktop_translator.py`**: A standalone version that runs entirely locally without the web server. Useful for a simple "set and forget" translation experience.

---

## Installation & Setup

### 1. Install System Dependencies

**macOS (for Audio Capture):**
```bash
brew install blackhole-2ch
# After installing, configure a "Multi-Output Device" in Audio MIDI Setup
# that includes both your speakers/headphones and BlackHole 2ch.
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```env
DEEPGRAM_API_KEY=your_deepgram_key_here
GROQ_API_KEY=your_groq_key_here
```

### 3. Generate SSL Certificates
The server requires SSL for secure WebSocket connections (WSS). Generate self-signed certs:

```bash
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365 -subj "/CN=localhost"
```

---

## Usage

### Option A: Web Server Mode (Docker)

This is the robust way to run the full application.

1.  **Start the Server**:
    ```bash
    docker-compose up --build
    ```

2.  **Start the Audio Bridge (Local Host)**:
    Since Docker cannot access macOS system audio directly, run the bridge script on your host machine to feed audio to the container.
    ```bash
    # Install dependencies for the bridge first
    pip install sounddevice numpy websockets miniaudio

    python audio_bridge.py
    ```

3.  **Access the UI**:
    Open `https://localhost:5050` in your browser. Note: You may need to accept the self-signed certificate warning.

### Option B: Web Server Mode (Local)

Run everything directly on your machine without Docker.

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the Server**:
    ```bash
    python web_server.py
    ```
    The server listens on `0.0.0.0:5050`.

### Option C: Standalone Desktop Translator

For a simple CLI experience without the web UI.

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the Translator**:
    ```bash
    python desktop_translator.py
    ```
    Follow the on-screen prompts to select your input (BlackHole) and output (Headphones) devices.

---

## Audio Setup Guide (macOS)
To translate YouTube or system audio:
1.  Open **Audio MIDI Setup** on macOS.
2.  Create a **Multi-Output Device**.
3.  Select your **Headphones** (Master Device) and **BlackHole 2ch**.
4.  In your System Settings -> Sound, select this Multi-Output Device as your output.
5.  Run the translator app (Desktop or Web+Bridge) and select **BlackHole 2ch** as the input source when prompted.

---

## License
[MIT](LICENSE)
