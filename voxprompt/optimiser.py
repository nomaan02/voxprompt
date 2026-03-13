"""Claude API prompt optimisation with streaming."""

from anthropic import Anthropic

from . import config


class Optimiser:
    """Sends raw transcripts to Claude for prompt optimisation."""

    def __init__(self):
        if not config.ANTHROPIC_API_KEY:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not set. "
                "Set it as an environment variable before running VoxPrompt."
            )
        self._client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def optimise(self, transcript: str, on_token=None) -> str:
        """
        Optimise a raw transcript into a polished prompt.

        Args:
            transcript: The raw spoken text.
            on_token:   Optional callback(token: str) called for each streamed
                        token so the UI can display incremental output.

        Returns the complete optimised prompt.
        """
        return self._stream_completion(
            user_message=transcript,
            on_token=on_token,
        )

    def reoptimise(self, transcript: str, on_token=None) -> str:
        """
        Re-optimise the same transcript with a different structural approach.

        Args:
            transcript: The raw spoken text (same as before).
            on_token:   Optional callback(token: str) for streaming.

        Returns the new optimised prompt.
        """
        user_message = (
            f"{transcript}\n\n"
            "[Note: Try a different structural approach to this prompt. "
            "Vary the formatting, emphasis, or organisation compared to "
            "a previous attempt.]"
        )
        return self._stream_completion(
            user_message=user_message,
            on_token=on_token,
        )

    def _stream_completion(self, user_message: str, on_token=None) -> str:
        """Stream a completion from Claude and return the full text."""
        result_parts: list[str] = []

        with self._client.messages.stream(
            model=config.CLAUDE_MODEL,
            max_tokens=config.CLAUDE_MAX_TOKENS,
            temperature=config.CLAUDE_TEMPERATURE,
            system=config.OPTIMISER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                result_parts.append(text)
                if on_token:
                    on_token(text)

        return "".join(result_parts)
