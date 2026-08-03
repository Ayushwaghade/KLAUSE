# app/tools package init
from app.tools.base import tool_registry, get_tool_definitions
import app.tools.system_tools     # Phase 1
import app.tools.memory_tools     # Phase 2
import app.tools.terminal_tools   # Phase 3
import app.tools.git_tools        # Phase 3
import app.tools.vscode_tools     # Phase 3
import app.tools.project_tools    # Phase 3
import app.tools.clipboard_tools  # Phase 4
import app.tools.filesystem_tools # Phase 4
import app.tools.app_tools        # Phase 4
import app.tools.window_tools     # Phase 4
import app.tools.browser_tools    # Phase 6
import app.tools.automation_tools # Phase 9 Event Engine & Scheduler
import app.tools.session_tools    # Universal Rules Integration
import app.tools.rules_tools      # Universal Rules Integration
import app.tools.kb_tools         # Phase 7 Knowledge Base
import app.tools.vision_tools     # Phase 8 Vision
import app.tools.skill_repo_tools  # Expert Skills Ingest
import app.tools.obsidian_tools    # Obsidian Integration

