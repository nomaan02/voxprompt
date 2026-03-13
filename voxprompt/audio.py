"""Microphone capture with Silero VAD for end-of-speech detection."""

import threading
import time

import numpy as np
import sounddevice as sd
import torch

from . import config


def _load_vad_model():
    """Load Silero VAD model via torch.hub."""
    model, utils = torch.hub.load(
        repo_or_dir="snakers4/silero-vad",
        model="silero_vad",
        force_reload=False,
        trust_repo=True,
    )
    return model


class AudioRecorder:
    """Captures microphone audio and uses Silero VAD to detect end-of-speech."""

    def __init__(self, on_status=None):
        """
        Args:
            on_status: Optional callback(elapsed_seconds) called periodically
                       while recording so the UI can update the timer.
        """
        self._on_status = on_status
        self._vad_model = None
        self._recording = False
        self._chunks: list[np.ndarray] = []
        self._lock = threading.Lock()

    def load_vad(self):
        """Pre-load the VAD model (call once at startup)."""
        self._vad_model = _load_vad_model()

    # ── public API ──────────────────────────────────────────────────────

    def start_recording(self) -> np.ndarray | None:
        """
        Begin recording from the default mic.  Blocks until VAD detects
        end-of-speech or MAX_RECORDING_DURATION is reached.

        Returns the captured audio as a float32 numpy array (mono, 16 kHz),
        or None if nothing was captured.
        """
        if self._vad_model is None:
            self.load_vad()

        self._chunks = []
        self._recording = True
        speech_detected = False
        silence_start: float | None = None
        start_time = time.time()

        # VAD expects 512-sample frames at 16 kHz (32 ms)
        frame_size = 512

        try:
            with sd.InputStream(
                samplerate=config.SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=frame_size,
            ) as stream:
                while self._recording:
                    elapsed = time.time() - start_time

                    # Safety cap
                    if elapsed >= config.MAX_RECORDING_DURATION:
                        break

                    # Status callback for UI timer
                    if self._on_status:
                        self._on_status(elapsed)

                    # Read a frame from the mic
                    data, overflowed = stream.read(frame_size)
                    audio_frame = data[:, 0]  # mono

                    with self._lock:
                        self._chunks.append(audio_frame.copy())

                    # Run VAD on the frame
                    tensor = torch.from_numpy(audio_frame)
                    speech_prob = self._vad_model(
                        tensor, config.SAMPLE_RATE
                    ).item()

                    if speech_prob >= config.VAD_THRESHOLD:
                        speech_detected = True
                        silence_start = None
                    elif speech_detected:
                        # Speech was active, now silence
                        if silence_start is None:
                            silence_start = time.time()
                        elif (
                            time.time() - silence_start
                            >= config.END_OF_SPEECH_TIMEOUT
                        ):
                            # End-of-speech detected
                            break

        except sd.PortAudioError as exc:
            raise RuntimeError(
                f"Microphone error: {exc}\n"
                f"Available devices:\n{sd.query_devices()}"
            ) from exc

        self._recording = False

        # Reset VAD state for next recording
        self._vad_model.reset_states()

        with self._lock:
            if not self._chunks:
                return None
            return np.concatenate(self._chunks)

    def stop_recording(self):
        """Signal the recording loop to stop early (e.g. user pressed key again)."""
        self._recording = False
