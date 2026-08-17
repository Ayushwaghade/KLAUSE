from app.tools.base import tool
from app.memory.obsidian_connector import (
    get_obsidian_vault_path,
    set_obsidian_vault_path,
    ObsidianConnector
)
from app.memory.knowledge_base import get_knowledge_base

@tool(
    name="configure_obsidian_vault",
    group="memory",
    description="Registers or updates the directory path to the user's local Obsidian note vault. Arguments: vault_path (str)."
)
def configure_obsidian_vault(vault_path: str) -> str:
    """Configures the Obsidian Vault path."""
    try:
        set_obsidian_vault_path(vault_path)
        connector = ObsidianConnector()
        res = connector.scan_and_sync()
        if res.get("status") == "success":
            return (
                f"Success: Obsidian vault path set to '{vault_path}'. "
                f"Indexed {res.get('total_notes')} markdown notes."
            )
        else:
            return f"Obsidian vault path updated, but sync failed: {res.get('message')}"
    except Exception as e:
        return f"Error configuring vault path: {e}"


@tool(
    name="sync_obsidian_vault",
    group="memory",
    description="Manually triggers a scan and sync of the configured Obsidian note vault, importing any new/edited files and clearing deleted files. Arguments: none."
)
def sync_obsidian_vault() -> str:
    """Triggers an Obsidian vault synchronization check."""
    try:
        connector = ObsidianConnector()
        res = connector.scan_and_sync()
        if res.get("status") == "success":
            return (
                f"Sync successful. Added: {res['added']}, "
                f"Updated: {res['updated']}, Deleted: {res['deleted']}. "
                f"Total notes in vault: {res['total_notes']}"
            )
        else:
            return f"Sync failed: {res.get('message')}"
    except Exception as e:
        return f"Error during vault synchronization: {e}"


@tool(
    name="search_obsidian_notes",
    group="memory",
    description="Semantically searches all indexed notes inside the user's Obsidian Vault for related concepts. Arguments: query (str)."
)
def search_obsidian_notes(query: str) -> str:
    """Searches indexed Obsidian notes semantically."""
    try:
        kb = get_knowledge_base()
        # Query ChromaDB (which searches the research collection containing obsidian notes)
        results = kb.search(query, limit=5)
        
        # Filter results that belong to the obsidian vault source_type
        notes = []
        for r in results:
            meta = r.get("metadata") or {}
            # Check if this chunk is from obsidian
            if meta.get("source_type") == "obsidian" or "obsidian" in meta.get("tags", "").split(","):
                notes.append(r)
                
        if not notes:
            return "Observation: No matching notes found in the Obsidian Vault."
            
        out = "Matching Obsidian Notes:\n"
        for idx, note in enumerate(notes):
            meta = note.get("metadata") or {}
            out += f"[{idx+1}] Note: {meta.get('title')} (Path: {meta.get('relative_path')})\n"
            out += f"Content: {note.get('content')}\n\n"
        return out
    except Exception as e:
        return f"Error searching obsidian notes: {e}"


@tool(
    name="create_obsidian_note",
    group="memory",
    description="Creates a new markdown note in the Obsidian Vault. You can write task guides, research, code walktroughs, and daily logs here. Arguments: title (str), content (str), folder (str, optional)."
)
def create_obsidian_note(title: str, content: str, folder: str = "") -> str:
    """Creates a new note file inside the Obsidian Vault."""
    try:
        connector = ObsidianConnector()
        res = connector.write_note(title, content, folder)
        # Track created note for Obsidian Canvas connections
        if "Success" in res:
            from app.core.context import context
            context.track_created_note(title)
        return f"Observation: {res}"
    except Exception as e:
        return f"Error creating obsidian note: {e}"


@tool(
    name="append_obsidian_note",
    group="memory",
    description="Appends text content to an existing Obsidian note. This is useful for building up logs or appending new sections to existing files. Arguments: title (str), content (str)."
)
def append_obsidian_note(title: str, content: str) -> str:
    """Appends content to an existing Obsidian note."""
    try:
        connector = ObsidianConnector()
        res = connector.append_note(title, content)
        return f"Observation: {res}"
    except Exception as e:
        return f"Error appending to obsidian note: {e}"
