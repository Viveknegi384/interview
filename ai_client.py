# ============================================================
# ai_client.py — Thread 3: Ollama AI answer generation (speed-optimised)
# ============================================================

import threading
import queue
import requests
import json
import logging

from config import (
    OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_NUM_PREDICT, OLLAMA_NUM_CTX,
    OLLAMA_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


class AIClientThread(threading.Thread):
    """
    Watches transcript_queue. Sends each question to local Ollama.
    Streams the response and puts final answer into answer_queue.
    Supports dynamic resume context injected via set_resume().
    """

    def __init__(
        self,
        transcript_queue: queue.Queue,
        answer_queue: queue.Queue,
        status_callback=None,
        error_callback=None,
    ):
        super().__init__(daemon=True, name="AIClientThread")
        self.transcript_queue = transcript_queue
        self.answer_queue = answer_queue
        self.status_callback = status_callback
        self.error_callback = error_callback
        self._shutdown = threading.Event()
        self._resume_text = ""
        self._resume_lock = threading.Lock()

    def set_resume(self, resume_text: str):
        """Thread-safe update of resume context."""
        with self._resume_lock:
            self._resume_text = resume_text.strip()
        logger.info(f"Resume context updated ({len(self._resume_text)} chars)")

    def _build_system_prompt(self) -> str:
        with self._resume_lock:
            resume = self._resume_text
        if resume:
            return OLLAMA_SYSTEM_PROMPT + f"\n\nCANDIDATE PROFILE (use for personal questions ONLY):\n{resume}"
        return OLLAMA_SYSTEM_PROMPT

    def run(self):
        logger.info("AIClientThread: Started. Waiting for transcripts...")
        while not self._shutdown.is_set():
            try:
                transcript = self.transcript_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            logger.info(f"AIClientThread: Got question → {transcript}")
            self._ask_ollama(transcript)

    def _ask_ollama(self, question: str):
        if self.status_callback:
            self.status_callback("🤖 Asking Ollama AI...")

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": question,
            "system": self._build_system_prompt(),
            "stream": True,
            "options": {
                "num_predict": OLLAMA_NUM_PREDICT,
                "num_ctx": OLLAMA_NUM_CTX,
                "temperature": 0.4,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
            },
        }

        try:
            response = requests.post(
                OLLAMA_BASE_URL,
                json=payload,
                stream=True,
                timeout=60,
            )
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            msg = "Cannot connect to Ollama. Open a new terminal and run: ollama serve"
            logger.error(msg)
            if self.error_callback:
                self.error_callback(msg)
            return
        except Exception as e:
            msg = f"Ollama request failed: {e}"
            logger.error(msg)
            if self.error_callback:
                self.error_callback(msg)
            return

        full_answer = []
        try:
            for line in response.iter_lines():
                if self._shutdown.is_set():
                    break
                if line:
                    chunk = json.loads(line.decode("utf-8"))
                    full_answer.append(chunk.get("response", ""))
                    if chunk.get("done", False):
                        break
        except Exception as e:
            logger.error(f"Stream read error: {e}")
            if self.error_callback:
                self.error_callback(f"AI stream error: {e}")
            return

        answer_text = "".join(full_answer).strip()
        if answer_text:
            logger.info(f"AIClientThread: Answer received ({len(answer_text)} chars)")
            self.answer_queue.put(answer_text)
        else:
            logger.warning("AIClientThread: Empty answer from Ollama.")
            if self.error_callback:
                self.error_callback("Ollama returned empty response. Is the model loaded?")

    def shutdown(self):
        self._shutdown.set()
