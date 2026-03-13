# VoxPrompt

Voice-to-optimised-prompt pipeline. Speak → Transcribe → Optimise → Copy.

VoxPrompt captures your voice, transcribes it locally on your GPU with faster-whisper, sends the raw transcript to Claude for prompt optimisation, and copies the polished result to your clipboard — all from a clean terminal UI.

## Prerequisites

- **Python** 3.11+
- **NVIDIA GPU** with CUDA drivers installed (falls back to CPU if unavailable)
- **ffmpeg** installed and on PATH (required by faster-whisper)
- **Anthropic API key** set as environment variable `ANTHROPIC_API_KEY`
- A working **microphone**

## Setup

### Windows (recommended)

```bat
setup.bat
```

Or manually:

```bat
python -m venv .venv
.venv\Scripts\activate.bat
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

### Linux / WSL

```bash
chmod +x setup.sh
./setup.sh
```

## Usage

```bash
# Activate venv first
# Windows:  .venv\Scripts\activate.bat
# Linux:    source .venv/bin/activate

python -m voxprompt.main
```

On first run, the Whisper model (~1.5 GB) will download automatically.

### Keybindings

| Key     | Action         | Description                                      |
|---------|----------------|--------------------------------------------------|
| `SPACE` | Toggle Record  | Start/stop voice capture                         |
| `R`     | Re-optimise    | Re-run optimisation with a different approach     |
| `C`     | Copy           | Copy the optimised prompt to clipboard           |
| `E`     | Edit           | Edit the raw transcript, then re-optimise        |
| `S`     | Save           | Save session (raw + optimised) to JSON log       |
| `Q`     | Quit           | Exit the app                                     |

## Remapping Keybindings (Macro Keyboard)

All keybindings are defined in `voxprompt/config.py`:

```python
KEYBINDINGS = {
    "toggle_record": "space",
    "reoptimise": "r",
    "copy_output": "c",
    "edit_transcript": "e",
    "save_session": "s",
    "quit": "q",
}
```

To remap to a macro keyboard, change the key names. The app uses `pynput` which supports:

- Standard keys: `"a"`, `"space"`, `"enter"`, etc.
- Function keys: `"f1"` through `"f24"` (including `"f13"`–`"f24"` used by macro pads)
- Any key your OS recognises — pynput captures at the system level

Example for a 6-key macro pad mapped to F13–F18:

```python
KEYBINDINGS = {
    "toggle_record": "f13",
    "reoptimise": "f14",
    "copy_output": "f15",
    "edit_transcript": "f16",
    "save_session": "f17",
    "quit": "f18",
}
```

## Architecture

```
voxprompt/
├── main.py          # Entry point, app orchestration, keyboard event loop
├── audio.py         # Mic capture + Silero VAD (voice activity detection)
├── transcriber.py   # faster-whisper GPU transcription
├── optimiser.py     # Claude API prompt optimisation (streaming)
├── clipboard.py     # Copy-to-clipboard utility
├── config.py        # All settings + keybindings in one place
└── ui.py            # Rich-based terminal UI
```

**Flow:** Mic → VAD-gated recording → faster-whisper (GPU) → Claude API → clipboard

Session logs are saved to `./sessions/` as JSON files.
