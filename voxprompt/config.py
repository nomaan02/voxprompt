"""VoxPrompt configuration — all tuneable values in one place."""

import os

# Audio
SAMPLE_RATE = 16000
VAD_THRESHOLD = 0.5
END_OF_SPEECH_TIMEOUT = 1.5  # seconds of silence to stop recording
MAX_RECORDING_DURATION = 120  # seconds

# Transcription
WHISPER_MODEL = "medium.en"
WHISPER_DEVICE = "cuda"
WHISPER_COMPUTE_TYPE = "float16"
WHISPER_BEAM_SIZE = 5

# Optimisation
CLAUDE_MODEL = "claude-sonnet-4-20250514"
CLAUDE_MAX_TOKENS = 4096
CLAUDE_TEMPERATURE = 0.3

# Keybindings (remappable for macro keyboard)
KEYBINDINGS = {
    "toggle_record": "space",
    "reoptimise": "r",
    "copy_output": "c",
    "edit_transcript": "e",
    "save_session": "s",
    "quit": "q",
}

# Paths
SESSION_LOG_DIR = "./sessions"

# Claude system prompt for optimisation
OPTIMISER_SYSTEM_PROMPT = """\
You are a prompt engineering specialist. Your job is to take raw, spoken-aloud text \
from a developer and transform it into a clear, well-structured prompt that will get \
the best results from an AI coding assistant (like Claude Code or Cursor Agent).

Rules:
- Preserve the user's INTENT completely — do not add scope or change what they're asking for
- Fix spoken artefacts: filler words (um, uh, like, you know), false starts, repetitions, trailing thoughts
- Add structure: if the request is multi-part, break it into numbered steps or clear sections
- Add specificity: if the user implies technical context (e.g. "fix the thing" when they clearly \
mean a specific file/function), make it explicit based on context clues
- Add constraints: if the user hasn't specified output format, language, or framework but it's \
implied, state it
- Keep the developer's voice and tone — don't make it robotic or overly formal
- If the spoken text is already clear and concise, make minimal changes — don't over-engineer \
simple requests
- Output ONLY the optimised prompt, no preamble, no explanation, no meta-commentary

Format: Output the optimised prompt as clean text, using markdown formatting (headers, bullets, \
code blocks) ONLY if the complexity warrants it. Simple requests should stay as simple text."""

# API key (read from environment)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
