# ============================================================
# main.py — Interview AI Assistant (Stealth Edition)
# Features: Hidden from screen share, taskbar, global hotkey
# ============================================================

import tkinter as tk
from tkinter import scrolledtext, messagebox
import queue
import threading
import logging
import sys
import os
import ctypes
import ctypes.wintypes

from config import AUDIO_QUEUE_MAXSIZE, TRANSCRIPT_QUEUE_MAXSIZE, ANSWER_QUEUE_MAXSIZE
from audio_capture import AudioCaptureThread
from transcriber import TranscriberThread
from ai_client import AIClientThread

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False

# ── Logging ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(threadName)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("interview_assistant.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

RESUME_FILE = "resume.txt"

# Windows Display Affinity constants
WDA_NONE               = 0x00000000
WDA_EXCLUDEFROMCAPTURE = 0x00000011   # Windows 10 2004+


def apply_stealth(hwnd: int):
    """
    Makes the window invisible to all screen capture software
    (Zoom, GMeet, Teams, OBS, etc.) while remaining visible on monitor.
    """
    try:
        result = ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
        if result:
            logger.info("✅ Stealth mode: window hidden from screen capture.")
        else:
            logger.warning("⚠️ SetWindowDisplayAffinity failed — Windows 10 build 2004+ required.")
    except Exception as e:
        logger.warning(f"Stealth mode unavailable: {e}")


# ══════════════════════════════════════════════════════════
#  Main Application
# ══════════════════════════════════════════════════════════
class InterviewAssistantApp:
    def __init__(self, root: tk.Tk):
        self.root = root

        # ── Stealth window setup ─────────────────────────
        # Disguised title — looks like a system utility
        self.root.title("System Performance Monitor")
        self.root.geometry("900x820")
        self.root.resizable(True, True)
        self.root.configure(bg="#1e1e2e")

        # Always on top of everything (only YOU see it)
        self.root.attributes('-topmost', True)

        # Hide from taskbar — won't appear in Alt+Tab or taskbar
        self.root.attributes('-toolwindow', True)

        # ── Queues ───────────────────────────────────────
        self.audio_queue      = queue.Queue(maxsize=AUDIO_QUEUE_MAXSIZE)
        self.transcript_queue = queue.Queue(maxsize=TRANSCRIPT_QUEUE_MAXSIZE)
        self.answer_queue     = queue.Queue(maxsize=ANSWER_QUEUE_MAXSIZE)

        # ── Shared audio info ─────────────────────────────
        self.audio_info = {}

        # ── State ────────────────────────────────────────
        self.is_listening = False
        self._audio_stop_event   = threading.Event()
        self._transcribe_trigger = threading.Event()
        self._active_audio_thread = None
        self._window_visible = True

        # ── Build UI ─────────────────────────────────────
        self._build_ui()

        # ── Apply screen capture stealth ─────────────────
        # Must be done AFTER window is drawn
        self.root.update()
        hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
        if hwnd == 0:
            hwnd = self.root.winfo_id()
        apply_stealth(hwnd)

        # ── Global hotkey: Ctrl+Shift+Space to show/hide ──
        self._register_hotkey()

        # ── Start background threads ─────────────────────
        self._start_background_threads()

        # ── Load saved resume ─────────────────────────────
        self._load_resume()

        # ── Poll answer queue ─────────────────────────────
        self._poll_answer_queue()

        # ── Shutdown ──────────────────────────────────────
        self.root.protocol("WM_DELETE_WINDOW", self._minimize_to_hidden)

    # ══════════════════════════════════════════════════════
    #  Stealth / Hotkey
    # ══════════════════════════════════════════════════════
    def _register_hotkey(self):
        if not KEYBOARD_AVAILABLE:
            logger.warning("keyboard library not available — hotkey disabled.")
            return
        try:
            keyboard.add_hotkey("ctrl+\\", self._toggle_visibility, suppress=False)
            logger.info("✅ Hotkey registered: Ctrl+\\ to show/hide window.")
        except Exception as e:
            logger.warning(f"Hotkey registration failed: {e}")

    def _toggle_visibility(self):
        """Show or hide the window — called by global hotkey."""
        self.root.after(0, self._do_toggle_visibility)

    def _do_toggle_visibility(self):
        if self._window_visible:
            self.root.withdraw()       # Hide completely (no taskbar, no screen)
            self._window_visible = False
            logger.info("Window hidden. Press Ctrl+Shift+Space to show.")
        else:
            self.root.deiconify()      # Show again
            self.root.lift()
            self.root.attributes('-topmost', True)
            self._window_visible = True
            logger.info("Window shown.")

    def _minimize_to_hidden(self):
        """Instead of closing, just hide the window."""
        self._do_toggle_visibility()

    # ══════════════════════════════════════════════════════
    #  UI Construction
    # ══════════════════════════════════════════════════════
    def _build_ui(self):
        BG        = "#1e1e2e"
        PANEL     = "#2a2a3e"
        ACCENT    = "#7c3aed"
        ACCENT_ON = "#dc2626"
        ACCENT_SAVE = "#059669"
        FG        = "#e2e8f0"
        FG_DIM    = "#94a3b8"
        ENTRY_BG  = "#12121e"

        self._colors = dict(
            bg=BG, panel=PANEL, accent=ACCENT,
            accent_on=ACCENT_ON, fg=FG, fg_dim=FG_DIM, entry_bg=ENTRY_BG,
        )

        # ── Header ───────────────────────────────────────
        header = tk.Frame(self.root, bg=BG, pady=8)
        header.pack(fill=tk.X, padx=20)

        tk.Label(
            header, text="🎙️ Interview AI Assistant",
            font=("Segoe UI", 15, "bold"), bg=BG, fg=FG,
        ).pack(side=tk.LEFT)

        tk.Label(
            header, text="🔒 Stealth Mode • Hidden from screen share",
            font=("Segoe UI", 8), bg=BG, fg="#4ade80",
        ).pack(side=tk.LEFT, padx=(10, 0), pady=(5, 0))

        # Hotkey hint label (top right)
        tk.Label(
            header, text="Ctrl+\\ → show/hide",
            font=("Segoe UI", 8), bg=BG, fg=FG_DIM,
        ).pack(side=tk.RIGHT)

        # ── Quit button (real quit, since X button now hides) ──
        quit_btn = tk.Button(
            self.root,
            text="✕ Quit App",
            font=("Segoe UI", 8),
            bg="#374151", fg=FG_DIM,
            relief=tk.FLAT, padx=6, pady=2,
            cursor="hand2",
            command=self._real_quit,
        )
        quit_btn.place(relx=1.0, rely=0.0, anchor="ne", x=-8, y=8)

        # ══════════════════════════════════════════════════
        # RESUME PANEL
        # ══════════════════════════════════════════════════
        resume_outer = tk.Frame(self.root, bg=PANEL, bd=1, relief=tk.RIDGE)
        resume_outer.pack(fill=tk.X, padx=20, pady=(0, 6))

        resume_header = tk.Frame(resume_outer, bg=PANEL)
        resume_header.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(
            resume_header,
            text="📋 My Resume / Profile",
            font=("Segoe UI", 9, "bold"), bg=PANEL, fg=FG_DIM,
        ).pack(side=tk.LEFT)

        self._save_btn = tk.Button(
            resume_header, text="💾 Save",
            font=("Segoe UI", 9),
            bg=ACCENT_SAVE, fg="white",
            activebackground="#047857", activeforeground="white",
            relief=tk.FLAT, padx=8, pady=2,
            cursor="hand2", command=self._save_resume,
        )
        self._save_btn.pack(side=tk.RIGHT)

        self._resume_visible = True
        self._toggle_btn = tk.Button(
            resume_header, text="▲ Collapse",
            font=("Segoe UI", 8), bg=PANEL, fg=FG_DIM,
            relief=tk.FLAT, padx=6, pady=2,
            cursor="hand2", command=self._toggle_resume_panel,
        )
        self._toggle_btn.pack(side=tk.RIGHT, padx=(0, 6))

        self._resume_frame = tk.Frame(resume_outer, bg=PANEL)
        self._resume_frame.pack(fill=tk.X, padx=10, pady=(0, 6))

        self.resume_box = scrolledtext.ScrolledText(
            self._resume_frame, height=6, wrap=tk.WORD,
            font=("Consolas", 10),
            bg=ENTRY_BG, fg="#fbbf24",
            insertbackground=FG,
            relief=tk.FLAT, padx=8, pady=5,
        )
        self.resume_box.pack(fill=tk.X)
        self.resume_box.insert(
            tk.END,
            "Paste your resume, skills, projects, and experience here...\n"
        )

        # ── Listen Button ─────────────────────────────────
        btn_frame = tk.Frame(self.root, bg=BG)
        btn_frame.pack(pady=(4, 4))

        self.listen_btn = tk.Button(
            btn_frame,
            text="⏺  START LISTENING",
            font=("Segoe UI", 13, "bold"),
            bg=ACCENT, fg="white",
            activebackground="#5b21b6", activeforeground="white",
            relief=tk.FLAT, bd=0,
            padx=26, pady=10,
            cursor="hand2",
            command=self._toggle_listen,
        )
        self.listen_btn.pack()

        self.recording_indicator = tk.Label(
            btn_frame, text="", font=("Segoe UI", 9),
            bg=BG, fg=ACCENT_ON,
        )
        self.recording_indicator.pack(pady=(3, 0))

        # ── Transcript Box ────────────────────────────────
        tk.Label(
            self.root, text="📝 Transcript:",
            font=("Segoe UI", 9, "bold"), bg=BG, fg=FG_DIM,
        ).pack(anchor=tk.W, padx=20)

        transcript_frame = tk.Frame(self.root, bg=PANEL, bd=1, relief=tk.SUNKEN)
        transcript_frame.pack(fill=tk.X, padx=20, pady=(2, 6))

        self.transcript_box = scrolledtext.ScrolledText(
            transcript_frame, height=3, wrap=tk.WORD,
            font=("Consolas", 10),
            bg=ENTRY_BG, fg=FG,
            relief=tk.FLAT, padx=8, pady=5,
            state=tk.DISABLED,
        )
        self.transcript_box.pack(fill=tk.X)

        # ── Answer Box ────────────────────────────────────
        tk.Label(
            self.root, text="🤖 AI Answer:",
            font=("Segoe UI", 9, "bold"), bg=BG, fg=FG_DIM,
        ).pack(anchor=tk.W, padx=20)

        answer_frame = tk.Frame(self.root, bg=PANEL, bd=1, relief=tk.SUNKEN)
        answer_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(2, 6))

        self.answer_box = scrolledtext.ScrolledText(
            answer_frame, height=10, wrap=tk.WORD,
            font=("Segoe UI", 12),
            bg=ENTRY_BG, fg="#86efac",
            insertbackground=FG,
            relief=tk.FLAT, padx=10, pady=8,
            state=tk.DISABLED,
        )
        self.answer_box.pack(fill=tk.BOTH, expand=True)

        # ── Bottom Buttons ────────────────────────────────
        btns = tk.Frame(self.root, bg=BG)
        btns.pack(fill=tk.X, padx=20, pady=(0, 4))

        tk.Button(
            btns, text="🗑  Clear",
            font=("Segoe UI", 9),
            bg="#374151", fg=FG,
            activebackground="#4b5563", activeforeground=FG,
            relief=tk.FLAT, padx=10, pady=4,
            cursor="hand2", command=self._clear_all,
        ).pack(side=tk.LEFT)

        # ── Status Bar ────────────────────────────────────
        self.status_var = tk.StringVar(value="⏳ Loading Whisper model...")
        tk.Label(
            self.root, textvariable=self.status_var,
            font=("Segoe UI", 9), bg="#12121e", fg=FG_DIM,
            anchor=tk.W, padx=10, pady=4,
        ).pack(fill=tk.X, side=tk.BOTTOM)

    # ══════════════════════════════════════════════════════
    #  Resume Panel
    # ══════════════════════════════════════════════════════
    def _toggle_resume_panel(self):
        if self._resume_visible:
            self._resume_frame.pack_forget()
            self._toggle_btn.config(text="▼ Expand")
            self._resume_visible = False
        else:
            self._resume_frame.pack(fill=tk.X, padx=10, pady=(0, 6))
            self._toggle_btn.config(text="▲ Collapse")
            self._resume_visible = True

    def _save_resume(self):
        text = self.resume_box.get("1.0", tk.END).strip()
        if not text or text.startswith("Paste your resume"):
            messagebox.showwarning("No Resume", "Please paste your resume text first.")
            return
        try:
            with open(RESUME_FILE, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            logger.warning(f"Could not save resume file: {e}")
        self._ai_client.set_resume(text)
        self._set_status("✅ Resume saved! AI will personalise answers to your profile.")
        self._resume_visible = True
        self._toggle_resume_panel()

    def _load_resume(self):
        if os.path.exists(RESUME_FILE):
            try:
                with open(RESUME_FILE, "r", encoding="utf-8") as f:
                    text = f.read().strip()
                if text:
                    self.resume_box.delete("1.0", tk.END)
                    self.resume_box.insert(tk.END, text)
                    self._ai_client.set_resume(text)
                    logger.info("Saved resume loaded from file.")
            except Exception as e:
                logger.warning(f"Could not load resume file: {e}")

    # ══════════════════════════════════════════════════════
    #  Thread Management
    # ══════════════════════════════════════════════════════
    def _start_background_threads(self):
        self._transcriber = TranscriberThread(
            audio_queue=self.audio_queue,
            transcript_queue=self.transcript_queue,
            trigger_event=self._transcribe_trigger,
            audio_info=self.audio_info,
            status_callback=self._set_status_safe,
            error_callback=self._show_error_safe,
        )
        self._transcriber.start()

        self._ai_client = AIClientThread(
            transcript_queue=self.transcript_queue,
            answer_queue=self.answer_queue,
            status_callback=self._set_status_safe,
            error_callback=self._show_error_safe,
        )
        self._ai_client.start()
        logger.info("Background threads started.")

    # ══════════════════════════════════════════════════════
    #  Listen Toggle
    # ══════════════════════════════════════════════════════
    def _toggle_listen(self):
        if not self.is_listening:
            self._start_listening()
        else:
            self._stop_listening()

    def _start_listening(self):
        self.is_listening = True
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

        self._audio_stop_event.clear()
        self._active_audio_thread = AudioCaptureThread(
            audio_queue=self.audio_queue,
            stop_event=self._audio_stop_event,
            audio_info=self.audio_info,
            error_callback=self._show_error_safe,
        )
        self._active_audio_thread.start()

        c = self._colors
        self.listen_btn.config(text="⏹  STOP LISTENING", bg=c["accent_on"], activebackground="#991b1b")
        self.recording_indicator.config(text="🔴 Recording system audio...")
        self._set_status("🎙️ Listening to headphones/speakers...")
        logger.info("Listening started.")

    def _stop_listening(self):
        self.is_listening = False
        self._audio_stop_event.set()

        c = self._colors
        self.listen_btn.config(text="⏺  START LISTENING", bg=c["accent"], activebackground="#5b21b6")
        self.recording_indicator.config(text="")
        self._set_status("⏳ Transcribing...")
        self._transcribe_trigger.set()
        logger.info("Listening stopped — transcription triggered.")

    # ══════════════════════════════════════════════════════
    #  Answer Queue Polling
    # ══════════════════════════════════════════════════════
    def _poll_answer_queue(self):
        try:
            answer = self.answer_queue.get_nowait()
            self._display_answer(answer)
            self._set_status("✅ Done — click START LISTENING for the next question.")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_answer_queue)

    # ══════════════════════════════════════════════════════
    #  Display Helpers
    # ══════════════════════════════════════════════════════
    def _display_answer(self, answer: str):
        self.answer_box.config(state=tk.NORMAL)
        self.answer_box.delete("1.0", tk.END)
        self.answer_box.insert(tk.END, answer)
        self.answer_box.see(tk.END)
        self.answer_box.config(state=tk.DISABLED)
        logger.info("Answer displayed in UI.")

    def _update_transcript_display(self, text: str):
        self.transcript_box.config(state=tk.NORMAL)
        self.transcript_box.delete("1.0", tk.END)
        self.transcript_box.insert(tk.END, text)
        self.transcript_box.config(state=tk.DISABLED)

    def _clear_all(self):
        for box in [self.transcript_box, self.answer_box]:
            box.config(state=tk.NORMAL)
            box.delete("1.0", tk.END)
            box.config(state=tk.DISABLED)
        self._set_status("✅ Cleared.")

    # ══════════════════════════════════════════════════════
    #  Thread-safe callbacks
    # ══════════════════════════════════════════════════════
    def _set_status(self, msg: str):
        self.status_var.set(msg)

    def _set_status_safe(self, msg: str):
        self.root.after(0, lambda: self.status_var.set(msg))

    def _show_error_safe(self, msg: str):
        logger.error(f"UI Error: {msg}")
        self.root.after(0, lambda: (
            self._set_status(f"❌ {msg}"),
            messagebox.showerror("Error", msg),
        ))

    # ══════════════════════════════════════════════════════
    #  Shutdown
    # ══════════════════════════════════════════════════════
    def _real_quit(self):
        """Actually quit the application."""
        logger.info("Shutting down...")
        self._audio_stop_event.set()
        self._transcriber.shutdown()
        self._ai_client.shutdown()
        if KEYBOARD_AVAILABLE:
            try:
                keyboard.remove_all_hotkeys()
            except Exception:
                pass
        self.root.destroy()

    def _minimize_to_hidden(self):
        """X button hides instead of closing."""
        self._do_toggle_visibility()


# ══════════════════════════════════════════════════════════
#  Entry Point
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    root = tk.Tk()
    app = InterviewAssistantApp(root)

    # Patch transcript queue to also update UI display
    _orig_put = app._transcriber.transcript_queue.put
    def _ui_put(item):
        app.root.after(0, lambda: app._update_transcript_display(item))
        return _orig_put(item)
    app._transcriber.transcript_queue.put = _ui_put

    root.mainloop()
