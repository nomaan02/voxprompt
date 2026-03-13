"""faster-whisper GPU transcription."""

import sys

import numpy as np
from faster_whisper import WhisperModel

from . import config


class Transcriber:
    """Wraps faster-whisper for single-call transcription."""

    def __init__(self):
        self._model: WhisperModel | None = None

    def load_model(self, on_progress=None):
        """
        Load the Whisper model.  Call once at startup.

        Args:
            on_progress: Optional callback(message: str) for status updates
                         (e.g. first-run download progress).
        """
        device = config.WHISPER_DEVICE
        compute_type = config.WHISPER_COMPUTE_TYPE

        # CUDA availability check — fall back to CPU gracefully
        try:
            import torch

            if device == "cuda" and not torch.cuda.is_available():
                if on_progress:
                    on_progress(
                        "CUDA not available — falling back to CPU "
                        "(transcription will be slower)"
                    )
                device = "cpu"
                compute_type = "int8"
        except ImportError:
            device = "cpu"
            compute_type = "int8"

        if on_progress:
            on_progress(
                f"Loading Whisper model '{config.WHISPER_MODEL}' on {device}…"
            )

        self._model = WhisperModel(
            config.WHISPER_MODEL,
            device=device,
            compute_type=compute_type,
        )

        if on_progress:
            on_progress("Whisper model loaded.")

    def transcribe(self, audio: np.ndarray) -> str:
        """
        Transcribe a float32 mono 16 kHz audio array to text.

        Returns the full transcript as a single string.
        """
        if self._model is None:
            raise RuntimeError("Whisper model not loaded — call load_model() first")

        segments, _info = self._model.transcribe(
            audio,
            beam_size=config.WHISPER_BEAM_SIZE,
            language="en",
            vad_filter=True,
        )

        return " ".join(seg.text.strip() for seg in segments).strip()
