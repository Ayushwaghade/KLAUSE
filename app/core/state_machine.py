"""
Live State Machine — collects real-time desktop, project, and session state
and formats it as a compact prompt block for Gemini injection.

Design:
  - Full state sent on the first turn of a session
  - Diff-only sent on subsequent turns (zero tokens if nothing changed)
  - Parallel collectors with 3-second timeout, fallback to last-known values
  - Clipboard sensitivity filter to prevent leaking secrets
"""

import re
import subprocess
import concurrent.futures
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import pyperclip
import pygetwindow as gw
from loguru import logger

from app.core.context import context
from app.config.config import settings


# ---------------------------------------------------------------------------
# Sensitivity filter patterns for clipboard content
# ---------------------------------------------------------------------------
SENSITIVE_PATTERNS = [
    r'(?i)(password|secret|token|key|bearer|authorization)\s*[:=]',
    r'eyJ[A-Za-z0-9_-]{20,}',                          # JWT tokens
    r'(?i)(ghp_|sk-|pk_|AKIA)[A-Za-z0-9_-]{10,}',     # GitHub / OpenAI / Stripe / AWS keys
]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class ProjectState:
    name: str
    path: str
    branch: str
    active_file: str                        # parsed from VS Code window title
    klause_spawned_processes: list[str]      # from running_processes registry
    last_commit: str


@dataclass
class DesktopState:
    active_window: str
    visible_windows: list[str]
    clipboard_preview: str                  # first 100 chars, sensitivity-filtered


@dataclass
class SystemState:
    timestamp: str
    active_project: Optional[ProjectState]
    desktop: DesktopState
    current_task: Optional[str]
    last_tool_used: Optional[str]
    voice_active: bool

    # ---- prompt serialisation ----

    def to_prompt_block(self, previous: Optional["SystemState"] = None) -> str:
        """First turn → full block.  Subsequent turns → diff only."""
        if previous is None:
            return self._full_block()

        changes = self._diff(previous)
        if not changes:
            return ""  # nothing changed — inject zero tokens
        return "STATE CHANGES:\n" + "\n".join(f"- {c}" for c in changes)

    def _full_block(self) -> str:
        lines = [f"CURRENT SYSTEM STATE ({self.timestamp}):"]
        lines.append(f"- Active window: {self.desktop.active_window}")
        
        visible = ", ".join(self.desktop.visible_windows) or "none"
        lines.append(f"- Visible windows: {visible}")

        if self.active_project:
            p = self.active_project
            lines.append(f"- Project: {p.name} ({p.path})")
            lines.append(f"- Git branch: {p.branch}")
            lines.append(f"- Active file: {p.active_file}")
            procs = ", ".join(p.klause_spawned_processes) or "none"
            lines.append(f"- KLAUSE-managed processes: {procs}")
            lines.append(f"- Last commit: {p.last_commit}")

        if self.desktop.clipboard_preview:
            lines.append(f'- Clipboard: "{self.desktop.clipboard_preview}"')

        if self.current_task:
            lines.append(f"- Current task: {self.current_task}")

        if self.last_tool_used:
            lines.append(f"- Last tool: {self.last_tool_used}")

        lines.append(f"- Voice active: {self.voice_active}")
        return "\n".join(lines)

    def _diff(self, prev: "SystemState") -> list[str]:
        changes: list[str] = []

        # Desktop-level diffs
        if self.desktop.active_window != prev.desktop.active_window:
            changes.append(f"Active window: {prev.desktop.active_window} → {self.desktop.active_window}")

        if self.desktop.visible_windows != prev.desktop.visible_windows:
            visible_prev = ", ".join(prev.desktop.visible_windows) or "none"
            visible_curr = ", ".join(self.desktop.visible_windows) or "none"
            changes.append(f"Visible windows: {visible_prev} → {visible_curr}")

        if self.desktop.clipboard_preview != prev.desktop.clipboard_preview:
            changes.append("Clipboard changed")

        # Project-level diffs
        cur_proj = self.active_project
        prev_proj = prev.active_project

        if cur_proj and prev_proj:
            if cur_proj.branch != prev_proj.branch:
                changes.append(f"Git branch: {prev_proj.branch} → {cur_proj.branch}")
            if cur_proj.active_file != prev_proj.active_file:
                changes.append(f"Active file: {prev_proj.active_file} → {cur_proj.active_file}")
            if cur_proj.last_commit != prev_proj.last_commit:
                changes.append(f"Last commit: {cur_proj.last_commit}")
            if cur_proj.klause_spawned_processes != prev_proj.klause_spawned_processes:
                changes.append(f"KLAUSE processes: {', '.join(cur_proj.klause_spawned_processes) or 'none'}")
        elif cur_proj and not prev_proj:
            changes.append(f"Project opened: {cur_proj.name} ({cur_proj.path})")
        elif not cur_proj and prev_proj:
            changes.append("Project closed")

        # Session-level diffs
        if self.current_task != prev.current_task:
            changes.append(f"Current task: {self.current_task or 'none'}")

        if self.last_tool_used != prev.last_tool_used:
            changes.append(f"Last tool: {self.last_tool_used or 'none'}")

        if self.voice_active != prev.voice_active:
            changes.append(f"Voice active: {self.voice_active}")

        return changes


# ---------------------------------------------------------------------------
# Collector
# ---------------------------------------------------------------------------
class StateMachine:
    def __init__(self):
        self._current: Optional[SystemState] = None
        self._previous: Optional[SystemState] = None

    def reset_history(self):
        """Reset state tracking to force a full block on the next turn."""
        self._current = None
        self._previous = None

    def refresh(self) -> SystemState:
        """Parallel-collects all state with 3 s timeout per collector."""
        self._previous = self._current

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            proj_future = pool.submit(self._collect_project_state)
            desk_future = pool.submit(self._collect_desktop_state)

            try:
                project = proj_future.result(timeout=3)
            except Exception:
                project = self._current.active_project if self._current else None

            try:
                desktop = desk_future.result(timeout=3)
            except Exception:
                desktop = (
                    self._current.desktop
                    if self._current
                    else DesktopState("unknown", [], "")
                )

        self._current = SystemState(
            timestamp=datetime.now().strftime("%H:%M"),
            active_project=project,
            desktop=desktop,
            current_task=context.current_task,
            last_tool_used=context.last_tool_used,
            voice_active=context.voice_active,
        )
        return self._current

    def get_prompt_block(self) -> str:
        """Returns full block on first call, diff on subsequent calls."""
        if self._current is None:
            return ""
        return self._current.to_prompt_block(self._previous)

    # ---- individual collectors ----

    def _collect_project_state(self) -> Optional[ProjectState]:
        if not context.current_project_path:
            return None
        path = Path(context.current_project_path)
        return ProjectState(
            name=path.name,
            path=str(path),
            branch=self._get_git_branch(path),
            active_file=self._get_active_file_from_window_title(),
            klause_spawned_processes=self._get_klause_processes(),
            last_commit=self._get_last_commit(path),
        )

    def _collect_desktop_state(self) -> DesktopState:
        try:
            active = gw.getActiveWindow()
            active_title = active.title if active else "unknown"
        except Exception:
            active_title = "unknown"

        return DesktopState(
            active_window=active_title,
            visible_windows=self._get_visible_windows(),
            clipboard_preview=self._safe_clipboard(),
        )

    # ---- helper methods ----

    @staticmethod
    def _get_git_branch(path: Path) -> str:
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=path, capture_output=True, text=True, timeout=3,
            )
            return result.stdout.strip() or "unknown"
        except Exception:
            return "unknown"

    @staticmethod
    def _get_last_commit(path: Path) -> str:
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-1"],
                cwd=path, capture_output=True, text=True, timeout=3,
            )
            return result.stdout.strip() or "none"
        except Exception:
            return "none"

    @staticmethod
    def _get_active_file_from_window_title() -> str:
        """Parse the active VS Code window title for the current filename.

        VS Code titles follow the pattern:
            <filename> — <project> — Visual Studio Code
        """
        try:
            active = gw.getActiveWindow()
            if not active or not active.title:
                return "unknown"
            title = active.title
            if "Visual Studio Code" not in title:
                return "unknown"
            # Split on em-dash " — " and take the first segment
            parts = title.split("\u2014")
            if parts:
                return parts[0].strip()
            return "unknown"
        except Exception:
            return "unknown"

    @staticmethod
    def _get_klause_processes() -> list[str]:
        try:
            from app.tools.terminal_tools import running_processes
            return [
                f"{info['command'][:30]} (PID {pid})"
                for pid, info in running_processes.items()
                if info["process"].poll() is None
            ]
        except Exception:
            return []

    @staticmethod
    def _get_visible_windows() -> list[str]:
        max_windows = getattr(
            getattr(settings, "state_machine", None), "max_visible_windows", 10
        )
        try:
            return [
                w.title
                for w in gw.getAllWindows()
                if w.title.strip() and w.visible
            ][:max_windows]
        except Exception:
            return []

    @staticmethod
    def _safe_clipboard() -> str:
        """Read clipboard with sensitivity filtering."""
        capture = getattr(
            getattr(settings, "state_machine", None), "capture_clipboard", True
        )
        if not capture:
            return ""
        try:
            clip = pyperclip.paste()[:100]
        except Exception:
            return ""
        if any(re.search(p, clip) for p in SENSITIVE_PATTERNS):
            return "[redacted — possible sensitive content]"
        return clip


# Global singleton
state_machine = StateMachine()
