# ============================================================
# transcriber.py — Thread 2: faster-whisper transcription
# Quality-optimised: resampling, VAD, English lock, better beam
# ============================================================

import threading
import queue
import wave
import logging
import os
import numpy as np

from config import (
    AUDIO_FORMAT_BYTES,
    WHISPER_MODEL_SIZE, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE,
    WHISPER_LANGUAGE, WHISPER_BEAM_SIZE, WHISPER_VAD_FILTER,
    WHISPER_INITIAL_PROMPT, TEMP_WAV_PATH
)

logger = logging.getLogger(__name__)

TARGET_SAMPLE_RATE = 16000   # Whisper's native input rate


def _resample_audio(audio_np: np.ndarray, orig_rate: int, target_rate: int = TARGET_SAMPLE_RATE) -> np.ndarray:
    """
    Resample int16 audio from orig_rate to target_rate using linear interpolation.
    Works for any ratio (e.g. 48000→16000, 44100→16000).
    """
    if orig_rate == target_rate:
        return audio_np
    duration = len(audio_np) / orig_rate
    target_length = int(duration * target_rate)
    resampled = np.interp(
        np.linspace(0, len(audio_np) - 1, target_length),
        np.arange(len(audio_np)),
        audio_np.astype(np.float32),
    ).astype(np.int16)
    logger.info(f"Resampled: {orig_rate} Hz → {target_rate} Hz "
                f"({len(audio_np)} → {len(resampled)} samples)")
    return resampled


class TranscriberThread(threading.Thread):
    """
    Drains audio_queue on trigger, converts stereo→mono,
    resamples to 16 kHz, writes WAV, transcribes with faster-whisper.
    """

    def __init__(
        self,
        audio_queue: queue.Queue,
        transcript_queue: queue.Queue,
        trigger_event: threading.Event,
        audio_info: dict,
        status_callback=None,
        error_callback=None,
    ):
        super().__init__(daemon=True, name="TranscriberThread")
        self.audio_queue = audio_queue
        self.transcript_queue = transcript_queue
        self.trigger_event = trigger_event
        self.audio_info = audio_info
        self.status_callback = status_callback
        self.error_callback = error_callback
        self._shutdown = threading.Event()
        self._model = None

    # ── Model Loading ─────────────────────────────────────────────────────────

    def _load_model(self):
        try:
            from faster_whisper import WhisperModel
            logger.info(f"Loading Whisper '{WHISPER_MODEL_SIZE}'...")
            if self.status_callback:
                self.status_callback(f"Loading Whisper '{WHISPER_MODEL_SIZE}' model (may take a moment first time)...")
            self._model = WhisperModel(
                WHISPER_MODEL_SIZE,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE,
            )
            logger.info("Whisper model loaded successfully.")
            if self.status_callback:
                self.status_callback("✅ Ready — click START LISTENING to begin")
        except Exception as e:
            logger.error(f"Whisper model load failed: {e}")
            if self.error_callback:
                self.error_callback(f"Whisper model load failed: {e}")
            raise

    # ── Main Loop ─────────────────────────────────────────────────────────────

    def run(self):
        try:
            self._load_model()
        except Exception:
            return

        while not self._shutdown.is_set():
            triggered = self.trigger_event.wait(timeout=0.5)
            if not triggered:
                continue
            self.trigger_event.clear()
            self._process_audio()

    # ── Audio Processing ──────────────────────────────────────────────────────

    def _process_audio(self):
        # 1. Drain all queued audio
        frames = []
        while True:
            try:
                frames.append(self.audio_queue.get_nowait())
            except queue.Empty:
                break

        if not frames:
            logger.warning("No audio frames captured.")
            if self.status_callback:
                self.status_callback("⚠️ No audio captured — hold the button while speaking.")
            return

        # 2. Get format from capture thread (default safe fallbacks)
        orig_rate = self.audio_info.get("sample_rate", 48000)
        channels  = self.audio_info.get("channels", 2)

        # 3. Decode raw PCM bytes → numpy int16
        raw_bytes = b''.join(frames)
        audio_np = np.frombuffer(raw_bytes, dtype=np.int16)

        # 4. Stereo / multi-channel → Mono
        if channels > 1:
            try:
                audio_np = audio_np.reshape(-1, channels).mean(axis=1).astype(np.int16)
                logger.info(f"Converted {channels}ch → mono")
            except Exception as e:
                logger.warning(f"Stereo→mono failed: {e}")

        # 5. Resample to 16 kHz (Whisper's native rate)
        audio_np = _resample_audio(audio_np, orig_rate, TARGET_SAMPLE_RATE)

        # 6. Write 16 kHz mono WAV
        try:
            with wave.open(TEMP_WAV_PATH, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(AUDIO_FORMAT_BYTES)
                wf.setframerate(TARGET_SAMPLE_RATE)
                wf.writeframes(audio_np.tobytes())
        except Exception as e:
            logger.error(f"Failed to write WAV: {e}")
            if self.error_callback:
                self.error_callback(f"Failed to save audio: {e}")
            return

        # 7. Transcribe with quality settings
        self._transcribe()

    def _transcribe(self):
        try:
            if self.status_callback:
                self.status_callback("🔍 Transcribing...")

            segments, info = self._model.transcribe(
                TEMP_WAV_PATH,
                language=WHISPER_LANGUAGE,
                beam_size=WHISPER_BEAM_SIZE,
                vad_filter=WHISPER_VAD_FILTER,
                vad_parameters=dict(
                    threshold=0.35,               # Lower = more sensitive to speech
                    min_silence_duration_ms=800,  # Tolerates longer pauses in long questions
                    speech_pad_ms=600,            # Padding to avoid cutting end of sentence
                    min_speech_duration_ms=200,   # Ignore short noise bursts
                    max_speech_duration_s=60,     # Support up to 60 sec questions
                ),
                initial_prompt=WHISPER_INITIAL_PROMPT,
                temperature=0.0,
                no_speech_threshold=0.6,         # Ignore audio if model is <60% confident it's speech
                compression_ratio_threshold=2.4, # Reject garbage/repetitive output
                condition_on_previous_text=False,
                word_timestamps=False,
            )

            transcript = " ".join(seg.text.strip() for seg in segments).strip()
            logger.info(f"Detected language: {info.language} (confidence: {info.language_probability:.2f})")

            if transcript:
                logger.info(f"Transcript → {transcript}")
                self.transcript_queue.put(transcript)
            else:
                logger.warning("Empty transcript after VAD filtering.")
                if self.status_callback:
                    self.status_callback("⚠️ Nothing detected — try speaking louder or longer.")

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            if self.error_callback:
                self.error_callback(f"Transcription failed: {e}")
        finally:
            if os.path.exists(TEMP_WAV_PATH):
                try:
                    os.remove(TEMP_WAV_PATH)
                except Exception:
                    pass

    def shutdown(self):
        self._shutdown.set()
