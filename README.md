# 🎙️ Interview AI Assistant

A **free, local, real-time AI assistant** that listens to your interview audio, transcribes the question, and gives you a smart answer — all running 100% on your machine. No subscriptions, no internet required (after setup).

> **Built for:** Online interviews on Zoom, Google Meet, Microsoft Teams, etc.
> **Stealth mode:** Window is invisible to screen sharing software.

---

## ✨ Features

- 🎧 **System audio capture** — listens to your headphones/speakers (WASAPI loopback)
- 🗣️ **Local transcription** — uses `faster-whisper` (offline, fast, accurate)
- 🤖 **AI answers** — powered by Ollama (free, local LLM)
- 📋 **Resume-aware** — paste your resume once, AI personalises every answer
- 🔒 **Stealth mode** — invisible to Zoom, Meet, Teams screen sharing
- ⌨️ **Hotkey** — `Ctrl+\` to show/hide the window instantly
- 🏷️ **Hidden from taskbar** — window disguised as "System Performance Monitor"

---

## 🖥️ Requirements

- Windows 10 (build 2004+) or Windows 11
- Python 3.9+
- ~2 GB free disk space (for Ollama model)
- Internet only for first-time model downloads

---

## 🚀 Setup Guide

### Step 1 — Install Ollama

1. Download from **[ollama.com](https://ollama.com/download)** and install
2. After install, open a terminal and pull the AI model:
```bash
ollama pull llama3.2:1b
```
> `llama3.2:1b` is ~750 MB and runs well on CPU. For better quality (slower), use `ollama pull llama3.2`.

### Step 2 — Clone the repository

```bash
git clone https://github.com/Viveknegi384/interview.git
cd interview
```

### Step 3 — Create a virtual environment

```bash
python -m venv venv
```

Activate it:
- **Windows:** `venv\Scripts\activate`
- **Mac/Linux:** `source venv/bin/activate`

### Step 4 — Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `pyaudiowpatch` requires Windows for WASAPI loopback support.

---

## ▶️ Running the App

You need **two terminals**:

**Terminal 1 — Start Ollama server:**
```bash
ollama serve
```

**Terminal 2 — Run the app:**
```bash
venv\Scripts\activate
python main.py
```

---

## 🧭 How to Use

1. **Start the app** — it loads the Whisper model (first run takes ~10 sec)
2. **Paste your resume** in the yellow text area at the top and click **💾 Save**
3. When the interviewer asks a question, click **⏺ START LISTENING**
4. When the question is done, click **⏹ STOP LISTENING**
5. The app transcribes the question and shows an AI answer in ~5-10 seconds

### Hotkeys
| Key | Action |
|-----|--------|
| `Ctrl+\` | Show / hide the window |

### Tips
- Press **STOP** only after the interviewer finishes speaking (wait 1-2 sec after last word)
- Make sure audio is coming through your headphones before clicking START
- The `X` button **hides** the window (not close) — use **✕ Quit App** to fully exit

---

## 📁 Project Structure

```
interview/
├── main.py           # UI + app entry point (stealth window)
├── audio_capture.py  # WASAPI loopback audio capture thread
├── transcriber.py    # faster-whisper transcription thread
├── ai_client.py      # Ollama AI response thread
├── config.py         # All settings (model, Whisper, audio)
├── requirements.txt  # Python dependencies
└── README.md
```

---

## ⚙️ Configuration (`config.py`)

| Setting | Default | Description |
|---------|---------|-------------|
| `OLLAMA_MODEL` | `llama3.2:1b` | AI model — change to `llama3.2` for better quality |
| `WHISPER_MODEL_SIZE` | `small` | Transcription model — `tiny` (faster) / `medium` (more accurate) |
| `OLLAMA_NUM_PREDICT` | `350` | Max tokens in answer |
| `WHISPER_LANGUAGE` | `en` | Lock to English |

---

## 🆓 Storing Ollama Models on a Different Drive

If your C: drive is low on space, store models on D: drive:

```powershell
# PowerShell (run as admin)
[System.Environment]::SetEnvironmentVariable("OLLAMA_MODELS", "D:\ollama_models\models", "User")
```

Then restart Ollama.

---

## 📦 Dependencies

```
faster-whisper      # Local speech-to-text
pyaudiowpatch       # WASAPI loopback audio capture (Windows)
requests            # Ollama API communication
numpy               # Audio processing
keyboard            # Global hotkey support
```

---

## ⚠️ Disclaimer

This tool is intended as a **personal learning and practice aid**. Use responsibly and in accordance with your interview platform's terms of service.

---

## 🤝 Contributing

PRs welcome! Ideas for improvement:
- GPU acceleration (CUDA support for Whisper)
- Multiple language support
- Auto-detect question end (no button needed)
- System tray icon
