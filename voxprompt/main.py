"""VoxPrompt entry point — app orchestration and TUI event loop."""

import json
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from pynput import keyboard

from . import config
from .audio import AudioRecorder
from .clipboard import copy_to_clipboard
from .optimiser import Optimiser
from .transcriber import Transcriber
from .ui import UI


class App:
    """Main application controller."""

    def __init__(self):
        self.ui = UI()
        self.recorder = AudioRecorder(on_status=self._on_recording_status)
        self.transcriber = Transcriber()
        self.optimiser: Optimiser | None = None

        # State
        self._is_recording = False
        self._last_raw_transcript: str = ""
        self._last_optimised_prompt: str = ""
        self._busy = False  # True while a pipeline stage is running

        # Build the key → action lookup from config
        self._key_action_map = self._build_key_map()

    # ── key mapping ─────────────────────────────────────────────────────

    @staticmethod
    def _build_key_map() -> dict:
        """Invert KEYBINDINGS so we can look up action by key press."""
        mapping: dict = {}
        for action, key_name in config.KEYBINDINGS.items():
            mapping[key_name.lower()] = action
        return mapping

    @staticmethod
    def _key_to_name(key) -> str | None:
        """Convert a pynput key event to a lowercase name string."""
        try:
            # Regular character keys
            return key.char.lower() if key.char else None
        except AttributeError:
            pass
        # Special keys
        name = getattr(key, "name", None)
        if name:
            return name.lower()
        # Function / media keys — use vk code
        vk = getattr(key, "vk", None) or getattr(key, "value", None)
        if vk:
            # F13-F24 have vk codes 124-135
            if hasattr(vk, "vk"):
                vk = vk.vk
            return f"<{vk}>"
        return None

    # ── keyboard handler ────────────────────────────────────────────────

    def _on_key_press(self, key):
        """pynput callback — runs in listener thread."""
        name = self._key_to_name(key)
        if name is None:
            return

        action = self._key_action_map.get(name)
        if action is None:
            return

        # Dispatch each action in its own thread so we don't block the listener
        if action == "quit":
            self._quit()
        elif action == "toggle_record":
            threading.Thread(target=self._toggle_record, daemon=True).start()
        elif action == "reoptimise":
            threading.Thread(target=self._reoptimise, daemon=True).start()
        elif action == "copy_output":
            self._copy_output()
        elif action == "edit_transcript":
            threading.Thread(target=self._edit_transcript, daemon=True).start()
        elif action == "save_session":
            self._save_session()

    # ── actions ─────────────────────────────────────────────────────────

    def _toggle_record(self):
        """Start or stop recording."""
        if self._is_recording:
            self.recorder.stop_recording()
            return

        if self._busy:
            self.ui.set_flash("Busy — please wait")
            return

        self._busy = True
        self._is_recording = True
        self.ui.set_status("LISTENING")
        self.ui.clear_flash()

        try:
            audio = self.recorder.start_recording()
        except RuntimeError as exc:
            self.ui.set_error(str(exc))
            self._is_recording = False
            self._busy = False
            self.ui.set_status("IDLE")
            return

        self._is_recording = False

        if audio is None or len(audio) < config.SAMPLE_RATE * 0.3:
            self.ui.set_flash("No speech detected — try again")
            self._busy = False
            self.ui.set_status("IDLE")
            return

        # Transcribe
        self.ui.set_status("TRANSCRIBING")
        try:
            transcript = self.transcriber.transcribe(audio)
        except Exception as exc:
            self.ui.set_error(f"Transcription error: {exc}")
            self._busy = False
            self.ui.set_status("IDLE")
            return

        if not transcript.strip():
            self.ui.set_flash("Transcript was empty — try speaking louder")
            self._busy = False
            self.ui.set_status("IDLE")
            return

        self._last_raw_transcript = transcript
        self.ui.set_raw_transcript(transcript)

        # Optimise
        self._run_optimisation(transcript)
        self._busy = False

    def _run_optimisation(self, transcript: str):
        """Run Claude optimisation (shared by record + reoptimise)."""
        self.ui.set_status("OPTIMISING")
        self.ui.set_optimised_prompt("")

        try:
            result = self.optimiser.optimise(
                transcript, on_token=self.ui.append_optimised_token
            )
        except Exception as exc:
            self.ui.set_error(f"Optimisation error: {exc}")
            self.ui.set_status("IDLE")
            return

        self._last_optimised_prompt = result
        self.ui.set_optimised_prompt(result)
        self.ui.set_status("DONE")

        # Auto-copy
        if copy_to_clipboard(result):
            self.ui.set_flash("✓ Copied to clipboard")
        else:
            self.ui.set_flash("Clipboard unavailable — copy manually")

    def _reoptimise(self):
        """Re-run optimisation on the last transcript with a different angle."""
        if self._busy:
            self.ui.set_flash("Busy — please wait")
            return
        if not self._last_raw_transcript:
            self.ui.set_flash("Nothing to re-optimise — record something first")
            return

        self._busy = True
        self.ui.set_status("OPTIMISING")
        self.ui.set_optimised_prompt("")

        try:
            result = self.optimiser.reoptimise(
                self._last_raw_transcript,
                on_token=self.ui.append_optimised_token,
            )
        except Exception as exc:
            self.ui.set_error(f"Optimisation error: {exc}")
            self.ui.set_status("IDLE")
            self._busy = False
            return

        self._last_optimised_prompt = result
        self.ui.set_optimised_prompt(result)
        self.ui.set_status("DONE")

        if copy_to_clipboard(result):
            self.ui.set_flash("✓ Copied to clipboard")
        else:
            self.ui.set_flash("Clipboard unavailable — copy manually")

        self._busy = False

    def _copy_output(self):
        """Copy the last optimised prompt to clipboard."""
        if not self._last_optimised_prompt:
            self.ui.set_flash("Nothing to copy yet")
            return
        if copy_to_clipboard(self._last_optimised_prompt):
            self.ui.set_flash("✓ Copied to clipboard")
        else:
            self.ui.set_flash("Clipboard unavailable — copy manually")

    def _edit_transcript(self):
        """Pause the live display, let the user edit the transcript, re-optimise."""
        if self._busy:
            self.ui.set_flash("Busy — please wait")
            return
        if not self._last_raw_transcript:
            self.ui.set_flash("Nothing to edit — record something first")
            return

        self._busy = True

        # Temporarily stop Live so we can use normal stdin
        self.ui.stop()

        print("\n── Edit Raw Transcript ──")
        print("Current transcript:")
        print(f"  {self._last_raw_transcript}")
        print()
        print("Type the corrected transcript (or press Enter to keep current):")

        try:
            edited = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            edited = ""

        if edited:
            self._last_raw_transcript = edited

        # Restart Live display
        self.ui.start()
        self.ui.set_raw_transcript(self._last_raw_transcript)

        # Re-optimise with the (possibly edited) transcript
        self._run_optimisation(self._last_raw_transcript)
        self._busy = False

    def _save_session(self):
        """Save the current session to a JSON log file."""
        if not self._last_raw_transcript and not self._last_optimised_prompt:
            self.ui.set_flash("Nothing to save yet")
            return

        log_dir = Path(config.SESSION_LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().isoformat(timespec="seconds")
        filename = timestamp.replace(":", "-") + ".json"
        filepath = log_dir / filename

        session_data = {
            "timestamp": timestamp,
            "raw_transcript": self._last_raw_transcript,
            "optimised_prompt": self._last_optimised_prompt,
            "model_used": config.CLAUDE_MODEL,
            "whisper_model": config.WHISPER_MODEL,
        }

        try:
            filepath.write_text(json.dumps(session_data, indent=2), encoding="utf-8")
            self.ui.set_flash(f"✓ Saved to {filepath}")
        except OSError as exc:
            self.ui.set_error(f"Save failed: {exc}")

    def _quit(self):
        """Clean shutdown."""
        self.ui.stop()
        os._exit(0)

    # ── recording status callback ───────────────────────────────────────

    def _on_recording_status(self, elapsed: float):
        """Called by AudioRecorder while recording to update the timer."""
        self.ui.set_recording_elapsed(elapsed)

    # ── startup ─────────────────────────────────────────────────────────

    def run(self):
        """Start the application."""
        # Pre-flight: check API key
        if not config.ANTHROPIC_API_KEY:
            print(
                "ERROR: ANTHROPIC_API_KEY environment variable is not set.\n"
                "Set it and restart VoxPrompt."
            )
            sys.exit(1)

        # Start UI
        self.ui.start()

        # Load models in background
        def _load_models():
            try:
                self.ui.set_loading("Loading Whisper model…")
                self.transcriber.load_model(
                    on_progress=lambda msg: self.ui.set_loading(msg)
                )

                self.ui.set_loading("Loading VAD model…")
                self.recorder.load_vad()

                self.ui.set_loading("Initialising Claude client…")
                self.optimiser = Optimiser()

                self.ui.set_status("IDLE")
                self.ui.set_flash("Ready — press SPACE to start recording")
            except Exception as exc:
                self.ui.set_error(f"Startup error: {exc}")

        threading.Thread(target=_load_models, daemon=True).start()

        # Start keyboard listener (blocks this thread via join)
        with keyboard.Listener(on_press=self._on_key_press) as listener:
            listener.join()


def main():
    """CLI entry point."""
    app = App()
    app.run()


if __name__ == "__main__":
    main()
