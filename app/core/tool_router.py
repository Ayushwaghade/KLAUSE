"""
Tool Router — classifies user requests and returns relevant tool groups.
Reduces prompt noise by filtering 110 tools down to ~25-40 relevant ones.
"""
import re
from typing import List, Optional
from loguru import logger

# Tool group keyword mappings
GROUP_KEYWORDS = {
    "terminal": [
        "run", "execute", "terminal", "command", "shell", "git", "commit",
        "push", "pull", "branch", "merge", "build", "npm", "pip", "install",
        "compile", "deploy", "code", "vscode"
    ],
    "filesystem": [
        "file", "folder", "directory", "read", "write", "copy", "move",
        "delete", "rename", "create file", "clipboard", "paste"
    ],
    "browser": [
        "open", "search", "browse", "website", "url", "youtube", "google",
        "play", "watch", "navigate", "webpage", "link", "click", "fill",
        "login", "sign in", "tab", "instagram", "twitter", "github.com",
        "gmail", "web"
    ],
    "memory": [
        "save", "note", "remember", "research", "knowledge", "vault",
        "obsidian", "search memory", "recall", "what do you know",
        "sync vault", "document"
    ],
    "vision": [
        "screen", "screenshot", "ocr", "look at", "see", "read screen",
        "what's on", "capture", "visual", "monitor"
    ],
    "automation": [
        "schedule", "cron", "rule", "automate", "recurring", "timer",
        "every", "daily", "hourly", "skill"
    ],
    "window": [
        "window", "focus", "minimize", "maximize", "switch window",
        "bring up", "foreground", "app", "application", "launch"
    ],
}

# Fallback escalation chains: if tools in group A fail, inject group B
FALLBACK_CHAINS = {
    "browser": "vision",
    "terminal": "filesystem",
    "filesystem": "terminal",
}


def classify_request(user_input: str) -> List[str]:
    """
    Scans user input for keywords and returns matching tool group names.
    Always includes 'core'. Returns all groups if no specific match found.
    """
    text = user_input.lower()
    matched_groups = set()

    for group, keywords in GROUP_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                matched_groups.add(group)
                break

    # If no specific groups matched, include all groups (safety net)
    if not matched_groups:
        matched_groups = set(GROUP_KEYWORDS.keys())
        logger.debug(f"ToolRouter: No specific group matched for '{user_input[:50]}', including all groups.")
    else:
        logger.info(f"ToolRouter: Classified request into groups: {sorted(matched_groups)}")

    # Always include core
    matched_groups.add("core")
    return sorted(matched_groups)


def escalate_group(failed_group: str) -> Optional[str]:
    """
    Returns the fallback group name for a group whose tools are failing.
    Returns None if no fallback chain exists.
    """
    fallback = FALLBACK_CHAINS.get(failed_group)
    if fallback:
        logger.info(f"ToolRouter: Escalating from '{failed_group}' → '{fallback}'")
    return fallback


def get_tool_group(tool_name: str) -> str:
    """
    Returns the group name for a given tool.
    """
    from app.tools.base import tool_registry
    tool_inst = tool_registry.get(tool_name)
    if tool_inst:
        return tool_inst.group
    return "core"
