# ============================================================
# ai_client.py — Groq API client thread for interview answers
# ============================================================

import threading
import queue
import logging
from groq import Groq

from config import (
    GROQ_API_KEY, GROQ_KEY_FILE,
    GROQ_INTERVIEW_MODEL, GROQ_INTERVIEW_MAX_TOKENS,
    GROQ_TEMPERATURE, GROQ_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


def load_api_key() -> str:
    """Load Groq API key from file or config."""
    import os
    if GROQ_API_KEY.strip():
        return GROQ_API_KEY.strip()
    try:
        if os.path.exists(GROQ_KEY_FILE):
            key = open(GROQ_KEY_FILE, "r").read().strip()
            if key:
                return key
    except Exception:
        pass
    return ""


class AIClientThread(threading.Thread):

    def __init__(self, transcript_queue: queue.Queue, answer_queue: queue.Queue,
                 status_callback, error_callback):
        super().__init__(daemon=True, name="AIClientThread")
        self.transcript_queue = transcript_queue
        self.answer_queue     = answer_queue
        self._status  = status_callback
        self._error   = error_callback
        self._resume  = ""
        self._running = True
        self._client  = None
        self._init_client()

    def _init_client(self):
        key = load_api_key()
        if key:
            self._client = Groq(api_key=key)
            logger.info("Groq client initialised.")
        else:
            logger.warning("Groq API key not set — AI answers disabled until key is provided.")

    def set_api_key(self, key: str):
        """Hot-update the API key."""
        self._client = Groq(api_key=key)
        # Save to file
        try:
            with open(GROQ_KEY_FILE, "w") as f:
                f.write(key.strip())
        except Exception as e:
            logger.warning(f"Could not save API key: {e}")
        logger.info("Groq API key updated.")

    def set_resume(self, text: str):
        self._resume = text.strip()
        logger.info(f"Resume context updated ({len(self._resume)} chars)")

    def _build_prompt(self, question: str) -> str:
        system = GROQ_SYSTEM_PROMPT
        if self._resume:
            system += f"\n\nCANDIDATE PROFILE:\n{self._resume}"
        return system

    def run(self):
        logger.info("AIClientThread: Started. Waiting for transcripts...")
        while self._running:
            try:
                question = self.transcript_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            if not question:
                continue

            logger.info(f"AIClientThread: Got question → {question[:80]}")
            self._status(f"🤖 Thinking... ({GROQ_INTERVIEW_MODEL})")

            if not self._client:
                self._error("Groq API key not set. Please enter it in Settings.")
                continue

            try:
                response = self._client.chat.completions.create(
                    model=GROQ_INTERVIEW_MODEL,
                    messages=[
                        {"role": "system",  "content": self._build_prompt(question)},
                        {"role": "user",    "content": question},
                    ],
                    max_tokens=GROQ_INTERVIEW_MAX_TOKENS,
                    temperature=GROQ_TEMPERATURE,
                    stream=False,
                )
                answer = response.choices[0].message.content.strip()
                logger.info(f"AIClientThread: Answer received ({len(answer)} chars)")
                self.answer_queue.put(answer)
                self._status("✅ Done — click START LISTENING for the next question.")
            except Exception as e:
                logger.error(f"Groq API error: {e}")
                self._error(f"Groq API error: {e}")

    def shutdown(self):
        self._running = False
