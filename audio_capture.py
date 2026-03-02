# ============================================================
# audio_capture.py — Thread 1: System Audio (Headphone) Loopback Capture
# Uses pyaudiowpatch for WASAPI loopback — captures what plays in headphones
# ============================================================

import threading
import queue
import logging

from config import CHUNK_SIZE, AUDIO_QUEUE_MAXSIZE

logger = logging.getLogger(__name__)


class AudioCaptureThread(threading.Thread):
    """
    Captures system audio (what you hear in headphones) via WASAPI loopback.
    Works with Zoom, Teams, GMeet, YouTube — anything playing through speakers.
    Puts raw PCM chunks into audio_queue.
    Also populates audio_info dict with actual sample_rate and channels.
    """

    def __init__(self, audio_queue: queue.Queue, stop_event: threading.Event,
                 audio_info: dict, error_callback=None):
        super().__init__(daemon=True, name="AudioCaptureThread")
        self.audio_queue = audio_queue
        self.stop_event = stop_event
        self.audio_info = audio_info      # filled with {'sample_rate': ..., 'channels': ...}
        self.error_callback = error_callback
        self._pa = None
        self._stream = None

    def run(self):
        try:
            import pyaudiowpatch as pyaudio
        except ImportError:
            msg = "pyaudiowpatch not installed. Run: pip install pyaudiowpatch"
            logger.error(msg)
            if self.error_callback:
                self.error_callback(msg)
            return

        try:
            self._pa = pyaudio.PyAudio()
            device_info = self._find_loopback_device(pyaudio)

            if device_info is None:
                msg = ("No WASAPI loopback device found. "
                       "Make sure audio is playing and your output device is active.")
                logger.error(msg)
                if self.error_callback:
                    self.error_callback(msg)
                return

            sample_rate = int(device_info["defaultSampleRate"])
            channels = int(device_info["maxInputChannels"])

            # Share actual audio format info with the transcriber
            self.audio_info["sample_rate"] = sample_rate
            self.audio_info["channels"] = channels
            self.audio_info["ready"] = True

            logger.info(
                f"AudioCaptureThread: Loopback device → '{device_info['name']}' "
                f"| {sample_rate} Hz | {channels}ch"
            )

            self._stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=sample_rate,
                input=True,
                input_device_index=int(device_info["index"]),
                frames_per_buffer=CHUNK_SIZE,
            )

            logger.info("AudioCaptureThread: Loopback capture started.")

            while not self.stop_event.is_set():
                try:
                    data = self._stream.read(CHUNK_SIZE, exception_on_overflow=False)
                    if not self.audio_queue.full():
                        self.audio_queue.put_nowait(data)
                    else:
                        # Drop oldest to prevent memory bloat
                        try:
                            self.audio_queue.get_nowait()
                        except queue.Empty:
                            pass
                        self.audio_queue.put_nowait(data)
                except OSError as e:
                    logger.warning(f"AudioCaptureThread: Read error (skipping): {e}")

        except Exception as e:
            logger.error(f"AudioCaptureThread: Fatal error — {e}")
            if self.error_callback:
                self.error_callback(f"Audio loopback error: {e}")
        finally:
            self._cleanup()

    def _find_loopback_device(self, pyaudio):
        """Find the WASAPI loopback device matching the default output (speakers/headphones)."""
        try:
            wasapi_info = self._pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_out_idx = wasapi_info.get("defaultOutputDevice", -1)
            if default_out_idx < 0:
                return None

            default_speakers = self._pa.get_device_info_by_index(default_out_idx)
            logger.info(f"Default output device: {default_speakers['name']}")

            # If the default device is already a loopback, use it
            if default_speakers.get("isLoopbackDevice", False):
                return default_speakers

            # Otherwise search for matching loopback device
            for loopback in self._pa.get_loopback_device_info_generator():
                if default_speakers["name"] in loopback["name"]:
                    logger.info(f"Found loopback device: {loopback['name']}")
                    return loopback

            # Fallback: return first available loopback
            for loopback in self._pa.get_loopback_device_info_generator():
                logger.info(f"Using fallback loopback: {loopback['name']}")
                return loopback

        except Exception as e:
            logger.error(f"AudioCaptureThread: Error finding loopback device — {e}")
            return None

    def _cleanup(self):
        try:
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
            if self._pa:
                self._pa.terminate()
            logger.info("AudioCaptureThread: Cleaned up resources.")
        except Exception as e:
            logger.warning(f"AudioCaptureThread: Cleanup error — {e}")
