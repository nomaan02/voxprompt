"""Rich-based terminal UI rendering."""

import threading

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from . import config

# Status name → Rich colour style
STATUS_STYLES = {
    "IDLE": "dim white",
    "LISTENING": "bold red",
    "TRANSCRIBING": "bold yellow",
    "OPTIMISING": "bold blue",
    "DONE": "bold green",
    "LOADING": "bold magenta",
    "ERROR": "bold red",
}


class UI:
    """Manages the Rich Live terminal dashboard."""

    def __init__(self):
        self.console = Console()
        self._live: Live | None = None
        self._lock = threading.Lock()

        # Display state
        self.status: str = "LOADING"
        self.raw_transcript: str = "(waiting for voice input)"
        self.optimised_prompt: str = "(will appear after optimisation)"
        self.flash_message: str = ""
        self.recording_elapsed: float = 0.0
        self.error_message: str = ""
        self.loading_message: str = ""

    # ── rendering ───────────────────────────────────────────────────────

    def _build_keybinding_legend(self) -> str:
        """Build the keybinding legend from config."""
        kb = config.KEYBINDINGS
        key_display = {
            "toggle_record": "Record",
            "reoptimise": "Re-optimise",
            "copy_output": "Copy",
            "edit_transcript": "Edit",
            "save_session": "Save",
            "quit": "Quit",
        }
        parts = []
        for action, label in key_display.items():
            key = kb.get(action, "?").upper()
            parts.append(f"[bold][{key}][/bold] {label}")
        row1 = "  ".join(parts[:3])
        row2 = "  ".join(parts[3:])
        return f"{row1}\n{row2}"

    def _build_status_text(self) -> Text:
        """Build the status indicator."""
        style = STATUS_STYLES.get(self.status, "white")
        label = self.status
        if self.status == "LISTENING":
            secs = int(self.recording_elapsed)
            label = f"● LISTENING  {secs}s"
        elif self.status == "LOADING" and self.loading_message:
            label = f"LOADING — {self.loading_message}"
        text = Text(label, style=style)
        return text

    def _render(self) -> Table:
        """Build the full dashboard as a Rich renderable."""
        # Header
        header_table = Table.grid(expand=True)
        header_table.add_column(ratio=1)
        header_table.add_column(justify="right")
        header_table.add_row(
            Text("VoxPrompt", style="bold white"),
            self._build_status_text(),
        )

        # Raw transcript panel
        raw_content = self.raw_transcript or "(waiting for voice input)"
        raw_panel = Panel(
            raw_content,
            title="RAW TRANSCRIPT",
            title_align="left",
            border_style="dim",
            padding=(1, 2),
        )

        # Optimised prompt panel
        opt_content = self.optimised_prompt or "(will appear after optimisation)"
        opt_panel = Panel(
            opt_content,
            title="OPTIMISED PROMPT",
            title_align="left",
            border_style="green" if self.status == "DONE" else "dim",
            padding=(1, 2),
        )

        # Flash / error messages
        messages = ""
        if self.flash_message:
            messages = f"[bold green]{self.flash_message}[/bold green]"
        if self.error_message:
            messages = f"[bold red]{self.error_message}[/bold red]"

        # Keybinding legend
        legend = self._build_keybinding_legend()

        # Assemble into a vertical layout via a grid table
        grid = Table.grid(expand=True)
        grid.add_column()
        grid.add_row(Panel(header_table, style="bold"))
        grid.add_row(raw_panel)
        grid.add_row(opt_panel)
        if messages:
            grid.add_row(Text.from_markup(f"  {messages}"))
        grid.add_row(Panel(Text.from_markup(legend), border_style="dim"))

        return grid

    # ── live display control ────────────────────────────────────────────

    def start(self):
        """Start the Rich Live display (call from main thread)."""
        self._live = Live(
            self._render(),
            console=self.console,
            refresh_per_second=8,
            screen=True,
        )
        self._live.start()

    def stop(self):
        """Stop the Rich Live display."""
        if self._live:
            self._live.stop()
            self._live = None

    def refresh(self):
        """Force a UI refresh."""
        with self._lock:
            if self._live:
                self._live.update(self._render())

    # ── convenience setters (thread-safe) ───────────────────────────────

    def set_status(self, status: str):
        self.status = status
        self.refresh()

    def set_raw_transcript(self, text: str):
        self.raw_transcript = text
        self.refresh()

    def set_optimised_prompt(self, text: str):
        self.optimised_prompt = text
        self.refresh()

    def append_optimised_token(self, token: str):
        """Append a streamed token to the optimised prompt display."""
        if self.optimised_prompt == "(will appear after optimisation)":
            self.optimised_prompt = ""
        self.optimised_prompt += token
        self.refresh()

    def set_flash(self, message: str):
        self.flash_message = message
        self.error_message = ""
        self.refresh()

    def set_error(self, message: str):
        self.error_message = message
        self.flash_message = ""
        self.refresh()

    def clear_flash(self):
        self.flash_message = ""
        self.error_message = ""
        self.refresh()

    def set_loading(self, message: str):
        self.loading_message = message
        self.status = "LOADING"
        self.refresh()

    def set_recording_elapsed(self, seconds: float):
        self.recording_elapsed = seconds
        self.refresh()
