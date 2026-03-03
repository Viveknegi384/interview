# ============================================================
# config.py — Central configuration for Interview AI Assistant
# ============================================================

# --- Groq API Settings ---
GROQ_API_KEY = ""                      # Set here OR enter in the app on first launch
GROQ_INTERVIEW_MODEL = "llama-3.1-8b-instant"   # Fast — for voice interview Q&A
GROQ_CODING_MODEL    = "groq/compound"           # Groq's best — Llama 4 Scout + GPT-OSS 120B + code execution
GROQ_INTERVIEW_MAX_TOKENS = 400
GROQ_CODING_MAX_TOKENS    = 3000   # Qwen3 uses tokens for thinking + answer
GROQ_TEMPERATURE = 0.3

# --- Interview System Prompt ---
GROQ_SYSTEM_PROMPT = """You are answering interview questions on behalf of the candidate.

STEP 1 — CLASSIFY the question:
A) PERSONAL/BEHAVIORAL: asks about YOU ("your strengths", "tell me about yourself", "why should we hire you", "weakness", "your experience", "your projects")
B) COMPANY: asks about a specific company ("tell me about TCS", "why do you want to join us")
C) GENERAL/TECHNICAL KNOWLEDGE: asks about a concept or fact ("what is OOP?", "types of construction", "explain REST API")

STEP 2 — ANSWER:

If TYPE A (PERSONAL): Speak as the candidate in FIRST PERSON using CANDIDATE PROFILE.
→ "I...", "My strength is...", "I built..."
→ 3-4 sentences MAX. Short, natural, speakable.

If TYPE B (COMPANY): Give factual company knowledge. 4-5 sentences. End with why you want to join.

If TYPE C (GENERAL/TECHNICAL): Answer factually. Do NOT use the resume. Just answer the question directly.
→ 3-5 sentences.

RULES: No preamble. Start immediately. Never say "The candidate..." or "As an AI...".
"""

# --- Screen Capture / Coding System Prompt ---
GROQ_CAPTURE_PROMPT = """You are an expert competitive programmer. Solve the coding problem extracted from the screenshot.

Rules:
- Always provide the most optimized solution (best time and space complexity possible).
- Output ONLY the C++ solution code block, nothing else.
- No explanation, no problem restatement, no walkthrough.
- After the code block, output exactly one line: Time: O(...) | Space: O(...)
- Use STL freely (vector, map, set, priority_queue, etc.).
- Write complete, compilable, contest-ready C++ code.
- The input text may have OCR noise — extract the actual question intelligently.
- If MCQ/aptitude: output Answer: [option] and a single-line reason only.

Format:
```cpp
// solution here
```
Time: O(...) | Space: O(...)
"""

# --- Whisper (faster-whisper) Settings ---
WHISPER_MODEL_SIZE   = "small"
WHISPER_DEVICE       = "cpu"
WHISPER_COMPUTE_TYPE = "int8"
WHISPER_LANGUAGE     = "en"
WHISPER_BEAM_SIZE    = 10
WHISPER_VAD_FILTER   = True
WHISPER_INITIAL_PROMPT = (
    "Interview question about software engineering, data structures, algorithms, system design, "
    "computer science, IT companies, MNCs, TCS, Infosys, Wipro, Accenture, HCL, Cognizant, "
    "placement, HR round, technical round, Indian IT industry, agile, REST API, microservices, "
    "cloud computing, full stack, machine learning, artificial intelligence."
)

# --- Audio Settings ---
SAMPLE_RATE       = 16000
CHANNELS          = 1
CHUNK_SIZE        = 1024
AUDIO_FORMAT_BYTES = 2

# --- Queue sizes ---
AUDIO_QUEUE_MAXSIZE      = 500
TRANSCRIPT_QUEUE_MAXSIZE = 20
ANSWER_QUEUE_MAXSIZE     = 20

# --- Temp file ---
TEMP_WAV_PATH = "temp_recording.wav"

# --- Screen Capture ---
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# --- API key storage file ---
GROQ_KEY_FILE = "groq_key.txt"

# --- Hotkeys ---
# Ctrl+\      → show/hide window  (existing)
# Ctrl+Alt+L  → start/stop listening  (safe: not used by Chrome/Firefox/Edge/VS Code)
LISTEN_HOTKEY = "ctrl+alt+l"
