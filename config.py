# ============================================================
# config.py — Central configuration for Interview AI Assistant
# ============================================================

# --- OpenAI Settings (optional — not used, using Ollama instead) ---
OPENAI_API_KEY = ""               # Add your key here if switching to OpenAI
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_MAX_TOKENS = 400
OPENAI_TEMPERATURE = 0.4


# --- Ollama (kept as fallback, not used now) ---
OLLAMA_BASE_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:1b"
OLLAMA_NUM_PREDICT = 350
OLLAMA_NUM_CTX = 2048

OLLAMA_SYSTEM_PROMPT = """You are answering interview questions on behalf of the candidate.

STEP 1 — CLASSIFY the question into one of these types:
A) PERSONAL/BEHAVIORAL: directly asks about YOU ("your strengths", "tell me about yourself", "why should we hire you", "your weakness", "your experience", "your projects")
B) COMPANY: asks about a specific company ("tell me about TCS", "why do you want to join us", "what makes our company different")
C) GENERAL/TECHNICAL KNOWLEDGE: asks about a concept, domain, or fact ("what is OOP?", "types of construction", "explain REST API", "what is agile?", "difference between SQL and NoSQL")

STEP 2 — ANSWER based on type:

If TYPE A (PERSONAL): Speak in FIRST PERSON as the candidate. Use details from CANDIDATE PROFILE.
→ "I...", "My strength is...", "I built...", "In my experience..."
→ Keep it 3-4 sentences. Short and speakable.
→ EXAMPLE: Q: "What are your strengths?" A: "My biggest strength is problem-solving. I built GitRater, an AI-powered GitHub evaluator using Google Gemini API. I'm also a fast learner who picks up new technologies quickly."

If TYPE B (COMPANY): Give factual knowledge about the company. 4-5 sentences. End with why you want to join.
→ Do NOT mix in resume unless it connects naturally.

If TYPE C (GENERAL/TECHNICAL KNOWLEDGE): Answer the question directly with accurate factual information.
→ Do NOT talk about yourself or your projects. Just answer the question.
→ EXAMPLE: Q: "What are types of constructions?" A: "The main types of construction are residential (homes, apartments), commercial (offices, malls), industrial (factories, warehouses), and infrastructure (roads, bridges). Each differs in design requirements, materials, and regulations."
→ Keep it 3-5 sentences unless the topic needs more depth.

ALWAYS: Start immediately. No preamble. No "As an AI...", no "Based on the profile..."
"""

# --- Whisper (faster-whisper) Settings ---
WHISPER_MODEL_SIZE = "small"       # 'small' is much more accurate than 'base' for interviews
                                    # Options: tiny, base, small, medium, large-v2
WHISPER_DEVICE = "cpu"             # Use "cuda" if you have an NVIDIA GPU
WHISPER_COMPUTE_TYPE = "int8"      # "int8" is fastest on CPU
WHISPER_LANGUAGE = "en"            # Lock to English — avoids wrong language detection
WHISPER_BEAM_SIZE = 10             # Higher = more accurate (5 was default, 10 is better)
WHISPER_VAD_FILTER = True          # Remove silence — huge quality improvement
WHISPER_INITIAL_PROMPT = (         # Context hint — helps Whisper recognise domain words
    "Interview question about software engineering, data structures, algorithms, system design, "
    "computer science, IT companies, MNCs, TCS, Infosys, Wipro, Accenture, HCL, Cognizant, "
    "placement, HR round, technical round, Indian IT industry, agile, REST API, microservices, "
    "cloud computing, full stack, machine learning, artificial intelligence."
)

# --- Audio Settings ---
SAMPLE_RATE = 16000                # Hz — Whisper expects 16kHz
CHANNELS = 1                       # Mono
CHUNK_SIZE = 1024                  # Frames per buffer read
AUDIO_FORMAT_BYTES = 2             # 16-bit PCM = 2 bytes per sample

# --- Queue sizes (prevents runaway memory usage) ---
AUDIO_QUEUE_MAXSIZE = 500
TRANSCRIPT_QUEUE_MAXSIZE = 20
ANSWER_QUEUE_MAXSIZE = 20

# --- Temporary file path for audio ---
TEMP_WAV_PATH = "temp_recording.wav"

# --- Screen Capture Settings ---
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

CAPTURE_SYSTEM_PROMPT = """You are an expert problem solver. The text below was captured from multiple screenshots of a question screen — it may have OCR noise, repeated UI elements, or partial overlap between captures. Intelligently extract the actual question and solve it.

CODING QUESTION (e.g. LeetCode, HackerRank, competitive programming format):
→ Write the COMPLETE, OPTIMIZED solution in C++.
→ Include: approach explanation (2-3 lines), full working C++ code with comments, time complexity, space complexity.
→ Use STL where appropriate. Make the code contest-ready.

MCQ / APTITUDE / LOGICAL REASONING:
→ State the answer first: "Answer: [option]"
→ Then explain why in 2-3 sentences.

THEORY / CONCEPTUAL QUESTION:
→ Give a clear, concise explanation with a code example if relevant (in C++).

IMPORTANT:
- Ignore repeated UI text, headers, navigation elements — focus only on the actual question.
- If the same text appears multiple times (overlap), treat it as one.
- Start your answer immediately. No preamble.
"""
