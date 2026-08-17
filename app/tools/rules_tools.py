import os
from pathlib import Path
from loguru import logger
from app.tools.base import tool

@tool(
    name="modify_rules",
    group="core",
    description=(
        "Safely modifies the workspace rules.md file. "
        "Allows adding or removing rules. Backs up the current rules to rules.md.bak before editing. "
        "Arguments: action (str - either 'add' or 'remove'), rule_text (str)."
    ),
    destructive=True
)
def modify_rules(action: str, rule_text: str) -> str:
    """Modify KLAUSE rules."""
    project_root = Path(__file__).resolve().parent.parent.parent
    rules_path = project_root / "rules.md"
    backup_path = project_root / "rules.md.bak"

    action_lower = action.lower()
    if action_lower not in ("add", "remove"):
        return "Error: Action parameter must be either 'add' or 'remove'."

    if not rules_path.exists():
        return "Error: rules.md does not exist at root."

    try:
        current_content = rules_path.read_text(encoding="utf-8")
        
        # 1. Create backup rules.md.bak
        backup_path.write_text(current_content, encoding="utf-8")
        logger.info("Created backup rules.md.bak.")

        # 2. Modify content
        if action_lower == "add":
            new_content = current_content.strip() + f"\n\n{rule_text.strip()}\n"
            diff_summary = f"+++ Add rule:\n{rule_text}"
        else: # remove
            # Try exact match or substring match to strip rule
            target = rule_text.strip()
            if target in current_content:
                new_content = current_content.replace(target, "").strip() + "\n"
                diff_summary = f"--- Remove rule:\n{target}"
            else:
                # Try finding matching lines
                lines = current_content.splitlines()
                matching_lines = [l for l in lines if target in l]
                if matching_lines:
                    new_content = "\n".join([l for l in lines if target not in l]) + "\n"
                    diff_summary = f"--- Remove matching lines containing '{target}':\n" + "\n".join(matching_lines)
                else:
                    return f"Error: Could not find any rule matching '{target}' in rules.md."

        # 3. Update 'Last modified' timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Update or add modified header
        if new_content.startswith("# Last modified:"):
            first_line, rest = new_content.split("\n", 1)
            new_content = f"# Last modified: {timestamp}\n{rest}"
        else:
            new_content = f"# Last modified: {timestamp}\n\n{new_content}"

        # 4. Write new content to disk
        rules_path.write_text(new_content, encoding="utf-8")
        logger.info("rules.md updated successfully.")

        # Notify the rules manager to reload next time
        from app.core.rules_manager import get_rules_manager
        get_rules_manager()._last_modified = 0 # Force cache invalidation

        return (
            f"Observation: Successfully modified rules.md.\n"
            f"Diff Summary:\n{diff_summary}\n"
            f"Backup created at: rules.md.bak"
        )

    except Exception as e:
        logger.error(f"Failed to modify rules.md: {e}")
        return f"Error: Failed to edit rules: {e}"
