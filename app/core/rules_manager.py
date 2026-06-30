import os
import re
from pathlib import Path
from loguru import logger

class RulesManager:
    """
    Manages loading, parsing, and caching KLAUSE universal rules from rules.md.
    Uses file modification timestamps (mtime) to avoid redundant disk reads.
    """

    def __init__(self):
        project_root = Path(__file__).resolve().parent.parent.parent
        self.rules_path = project_root / "rules.md"
        self._cached_rules = []
        self._last_modified = 0

    def _ensure_loaded(self):
        """Loads and parses rules.md if it changed on disk."""
        if not self.rules_path.exists():
            # Create default rules.md if missing
            self._create_default_rules()

        try:
            mtime = os.path.getmtime(self.rules_path)
            if mtime != self._last_modified:
                logger.info(f"RulesManager: rules.md modified. Reloading...")
                content = self.rules_path.read_text(encoding="utf-8")
                self._cached_rules = self._parse_rules(content)
                self._last_modified = mtime
        except Exception as e:
            logger.error(f"Failed to read/load rules.md: {e}")
            if not self._cached_rules:
                self._cached_rules = []

    def _create_default_rules(self):
        """Creates a default rules.md file."""
        default_content = (
            "# Last modified: 2026-06-29 17:00:00\n\n"
            "## [File] Rule 1: Session Data Folder\n"
            "- Store all session output files (downloads, generated text files, screenshots) within the active session folder.\n"
            "- If no active session folder is set, stop and ask Ayush to specify one before writing any files.\n"
            "- If you must write files outside the session folder, ask Ayush for permission first.\n\n"
            "## [General] Rule 2: Notes & Context Scanning\n"
            "- Before starting any task that explicitly references a project by name, read the notes file for that project if it exists.\n"
            "- Do not scan notes for simple one-off tasks (calculations, web searches, file conversions).\n"
        )
        try:
            self.rules_path.write_text(default_content, encoding="utf-8")
            logger.info("Created default rules.md at root.")
        except Exception as e:
            logger.error(f"Failed to create default rules.md: {e}")

    def _parse_rules(self, content: str) -> list:
        """Parses rules into structured blocks with tag categorizations."""
        # Find all rules defined by '##' headers
        rules = []
        # Split by ## headers, keeping headers
        parts = re.split(r'(?m)^(##\s+.*)$', content)
        
        # The first part is the header metadata
        header_meta = parts[0].strip()
        
        for idx in range(1, len(parts), 2):
            header = parts[idx].strip()
            body = parts[idx+1].strip() if idx + 1 < len(parts) else ""
            
            # Extract tag like [File], [Browser], [General]
            match = re.search(r'\[([a-zA-Z0-9_-]+)\]', header)
            tag = match.group(1).lower() if match else "general"
            
            rules.append({
                "header": header,
                "body": body,
                "tag": tag
            })
        return rules

    def get_rules(self, filter_tag: str = None) -> str:
        """
        Returns a formatted markdown string of rules matching [General] and the filter_tag.
        If filter_tag is None, returns all rules.
        """
        self._ensure_logged_in = self._ensure_loaded()  # Load fresh
        
        filter_tag_lower = filter_tag.lower() if filter_tag else None
        lines = []
        
        for r in self._cached_rules:
            tag = r["tag"]
            # Include if tag is general, or if no filter, or if matches filter
            if tag == "general" or not filter_tag_lower or tag == filter_tag_lower:
                lines.append(f"{r['header']}\n{r['body']}")
                
        return "\n\n".join(lines).strip()


# Global RulesManager instance
_rules_manager_inst = None

def get_rules_manager() -> RulesManager:
    global _rules_manager_inst
    if _rules_manager_inst is None:
        _rules_manager_inst = RulesManager()
    return _rules_manager_inst
