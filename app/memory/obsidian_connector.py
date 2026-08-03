import os
import re
import json
import hashlib
import datetime
from pathlib import Path
from loguru import logger

from app.memory.database import get_db
from app.memory.knowledge_base import get_knowledge_base

def get_obsidian_settings_path() -> Path:
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / "data" / "session_settings.json"

def get_obsidian_vault_path() -> str:
    path = get_obsidian_settings_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("obsidian_vault_path", "")
        except Exception as e:
            logger.error(f"Failed to read obsidian vault path: {e}")
    return ""

def set_obsidian_vault_path(vault_path: str):
    path = get_obsidian_settings_path()
    data = {"sessions": {}, "last_used_data_folder": None}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read obsidian settings for write: {e}")
    
    # Resolve to absolute path
    abs_path = os.path.abspath(vault_path) if vault_path else ""
    data["obsidian_vault_path"] = abs_path
    
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Obsidian vault path updated to: {abs_path}")
    except Exception as e:
        logger.error(f"Failed to save obsidian settings: {e}")


def parse_markdown_note(content: str) -> tuple[dict, str, list]:
    """
    Parses YAML frontmatter, strips it from the note body, and extracts tags.
    """
    metadata = {}
    body = content
    tags = []

    # 1. Parse YAML frontmatter
    yaml_pattern = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL | re.MULTILINE)
    match = yaml_pattern.match(content)
    if match:
        frontmatter_text = match.group(1)
        body = content[match.end():]
        try:
            import yaml
            parsed = yaml.safe_load(frontmatter_text)
            if isinstance(parsed, dict):
                metadata = parsed
        except Exception as e:
            logger.warning(f"Failed to parse YAML frontmatter: {e}")

    # 2. Extract tags from frontmatter
    fm_tags = metadata.get("tags", [])
    if isinstance(fm_tags, list):
        tags.extend([str(t).strip().lower() for t in fm_tags])
    elif isinstance(fm_tags, str):
        tags.extend([t.strip().lower() for t in re.split(r'[,\s]+', fm_tags) if t.strip()])

    # 3. Extract inline tags (e.g. #work, #personal)
    inline_tags = re.findall(r'(?:^|\s)#([a-zA-Z][a-zA-Z0-9_\-\/]*)', body)
    tags.extend([t.strip().lower() for t in inline_tags])

    # Deduplicate and filter tags
    tags = list(set([t for t in tags if t.strip()]))
    return metadata, body, tags


class ObsidianConnector:
    def __init__(self):
        self.db = get_db()
        self.kb = get_knowledge_base()

    def scan_and_sync(self) -> dict:
        """
        Scans the registered Obsidian Vault path for markdown files,
        syncs new/modified files, and cleans up deleted files.
        """
        vault_path = get_obsidian_vault_path()
        if not vault_path:
            logger.warning("Obsidian Sync: No vault path configured.")
            return {"status": "error", "message": "No vault path configured"}

        vault_root = Path(vault_path).resolve()
        if not vault_root.exists() or not vault_root.is_dir():
            logger.error(f"Obsidian Sync: Vault path '{vault_path}' does not exist or is not a directory.")
            return {"status": "error", "message": f"Vault path '{vault_path}' does not exist"}

        logger.info(f"Obsidian Sync: Starting scan on '{vault_root}'")
        
        # 1. Discover all current markdown files in the vault
        current_files = {}
        for root, _, files in os.walk(vault_root):
            for file in files:
                if file.endswith(".md"):
                    file_path = Path(root) / file
                    abs_path = str(file_path.resolve())
                    try:
                        mtime = os.path.getmtime(abs_path)
                        current_files[abs_path] = mtime
                    except Exception as e:
                        logger.warning(f"Obsidian Sync: Failed to check stats for {file}: {e}")

        # 2. Query existing sync records from DB
        sync_records = {}
        try:
            for rec in self.db.obsidian_sync.find():
                sync_records[rec["file_path"]] = {
                    "last_modified": rec.get("last_modified", 0.0),
                    "document_id": rec.get("document_id"),
                    "content_hash": rec.get("content_hash", "")
                }
        except Exception as e:
            logger.error(f"Obsidian Sync: Failed to retrieve sync records from DB: {e}")

        added_count = 0
        updated_count = 0
        deleted_count = 0

        # 3. Synchronize additions and edits
        for abs_path, mtime in current_files.items():
            record = sync_records.get(abs_path)
            
            # Check if file has changed
            is_new = record is None
            is_modified = record is not None and mtime != record["last_modified"]
            
            if is_new or is_modified:
                try:
                    rel_path = str(Path(abs_path).relative_to(vault_root))
                    content = Path(abs_path).read_text(encoding="utf-8", errors="ignore")
                    
                    # Deduplicate contents by computing hash
                    content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
                    if record and record["content_hash"] == content_hash:
                        # Modified timestamp but identical content hash - just update timestamp in db
                        self.db.obsidian_sync.update_one(
                            {"file_path": abs_path},
                            {"$set": {"last_modified": mtime}}
                        )
                        continue
                        
                    # Parse markdown file metadata, body, and tags
                    _, body, tags = parse_markdown_note(content)
                    
                    # Dedup in KnowledgeBase
                    self.kb._delete_existing_by_source("file_path", abs_path)
                    
                    # Add to tags "obsidian" to clearly classify vault notes
                    if "obsidian" not in tags:
                        tags.append("obsidian")
                    
                    title = Path(abs_path).stem
                    
                    # Index note content
                    self.kb._index_content(
                        title=title,
                        content=body,
                        tags=tags,
                        chunk_size=800,
                        overlap=150,
                        metadata={
                            "file_path": abs_path,
                            "content_hash": content_hash,
                            "source_type": "obsidian",
                            "relative_path": rel_path
                        }
                    )
                    
                    # Find inserted ID
                    doc = self.db.research.find_one({"file_path": abs_path})
                    doc_id = str(doc["_id"]) if doc else ""
                    
                    # Update sync state in DB
                    self.db.obsidian_sync.update_one(
                        {"file_path": abs_path},
                        {"$set": {
                            "last_modified": mtime,
                            "content_hash": content_hash,
                            "document_id": doc_id,
                            "relative_path": rel_path
                        }},
                        upsert=True
                    )
                    
                    if is_new:
                        added_count += 1
                        logger.debug(f"Obsidian Sync: Added new note '{title}'")
                    else:
                        updated_count += 1
                        logger.debug(f"Obsidian Sync: Updated note '{title}'")
                        
                except Exception as e:
                    logger.error(f"Obsidian Sync: Failed to sync file {abs_path}: {e}")

        # 4. Clean up deletions (files in DB but no longer on disk)
        for abs_path, rec in sync_records.items():
            if abs_path not in current_files:
                doc_id = rec.get("document_id")
                try:
                    if doc_id:
                        self.kb.delete_document(doc_id)
                    self.db.obsidian_sync.delete_one({"file_path": abs_path})
                    deleted_count += 1
                    logger.info(f"Obsidian Sync: Removed deleted note reference '{abs_path}'")
                except Exception as e:
                    logger.error(f"Obsidian Sync: Failed to clean deleted file reference {abs_path}: {e}")

        logger.info(f"Obsidian Sync complete: Added {added_count}, Updated {updated_count}, Deleted {deleted_count} notes.")
        
        # Save sync timestamp
        self.db.settings.update_one(
            {"key": "obsidian_sync_info"},
            {"$set": {
                "last_sync": datetime.datetime.utcnow().isoformat(),
                "total_notes": len(current_files)
            }},
            upsert=True
        )

        return {
            "status": "success",
            "added": added_count,
            "updated": updated_count,
            "deleted": deleted_count,
            "total_notes": len(current_files)
        }

    def write_note(self, title: str, content: str, folder: str = "") -> str:
        """
        Creates or overwrites a note in the Obsidian Vault.
        """
        vault_path = get_obsidian_vault_path()
        if not vault_path:
            return "Error: Obsidian vault path is not configured."
            
        vault_root = Path(vault_path).resolve()
        
        # Sanitize title
        clean_title = re.sub(r'[\\/*?:"<>|]', "", title).strip()
        if not clean_title:
            return "Error: Invalid note title."
            
        target_dir = vault_root
        if folder:
            # Prevent directory traversal
            clean_folder = folder.replace("..", "").strip("/\\")
            target_dir = vault_root / clean_folder
            
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            note_file = target_dir / f"{clean_title}.md"
            
            # Format note with automatic Obsidian frontmatter tags
            note_content = content
            if not content.startswith("---"):
                # Add default KLAUSE tag
                note_content = (
                    "---\n"
                    "tags:\n"
                    "  - klause\n"
                    "  - agent-note\n"
                    f"created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                    "---\n\n"
                    f"{content}"
                )
                
            note_file.write_text(note_content, encoding="utf-8")
            logger.info(f"Obsidian Connector: Successfully wrote note '{clean_title}' at '{note_file}'")
            
            # Trigger quick incremental sync to immediate index it
            self.scan_and_sync()
            
            return f"Success: Note '{clean_title}' written to Obsidian vault folder."
        except Exception as e:
            logger.error(f"Obsidian Connector: Failed to write note: {e}")
            return f"Error writing note to vault: {e}"

    def append_note(self, title: str, content: str) -> str:
        """
        Appends content to an existing note in the Obsidian Vault.
        """
        vault_path = get_obsidian_vault_path()
        if not vault_path:
            return "Error: Obsidian vault path is not configured."
            
        vault_root = Path(vault_path).resolve()
        
        # Search for note file recursively
        note_file = None
        for root, _, files in os.walk(vault_root):
            for file in files:
                if file.endswith(".md") and Path(file).stem.lower() == title.lower().strip():
                    note_file = Path(root) / file
                    break
            if note_file:
                break
                
        if not note_file:
            # Fallback: create note in root
            return self.write_note(title, content)
            
        try:
            existing_content = note_file.read_text(encoding="utf-8", errors="ignore")
            # Append content with spacing
            separator = "\n\n---\n### Append from KLAUSE Agent\n"
            updated = f"{existing_content}{separator}{content}\n"
            
            note_file.write_text(updated, encoding="utf-8")
            logger.info(f"Obsidian Connector: Appended content to '{note_file.name}'")
            
            # Index changes
            self.scan_and_sync()
            return f"Success: Content appended to note '{title}'."
        except Exception as e:
            logger.error(f"Obsidian Connector: Failed to append note: {e}")
            return f"Error appending content: {e}"

    def update_connections_canvas(self, query: str, created_notes: list, referenced_urls: list, retrieved_notes: list):
        """
        Updates the KLAUSE_Connections.canvas file in the vault root.
        Creates nodes for chat queries, created notes, retrieved RAG notes, and referenced URLs,
        and draws edges between them.
        """
        vault_path = get_obsidian_vault_path()
        if not vault_path:
            logger.warning("Canvas update skipped: No vault path configured.")
            return

        # Skip if there's nothing to map
        if not created_notes and not referenced_urls and not retrieved_notes:
            logger.debug("Canvas update skipped: No connections to map.")
            return

        vault_root = Path(vault_path).resolve()
        canvas_file = vault_root / "KLAUSE_Connections.canvas"

        # Load existing canvas or create new
        canvas_data = {"nodes": [], "edges": []}
        if canvas_file.exists():
            try:
                raw = canvas_file.read_text(encoding="utf-8")
                canvas_data = json.loads(raw)
            except Exception as e:
                logger.warning(f"Canvas: Failed to load existing canvas, creating new: {e}")
                canvas_data = {"nodes": [], "edges": []}

        import uuid as _uuid

        # Calculate Y position for the new chat node (below the lowest existing node)
        lowest_y = 0
        for node in canvas_data["nodes"]:
            node_bottom = node.get("y", 0) + node.get("height", 100)
            if node_bottom > lowest_y:
                lowest_y = node_bottom
        chat_y = lowest_y + 80  # Gap between rows

        # Build a lookup of existing file nodes by their label/file path to reuse them
        existing_file_nodes = {}
        for node in canvas_data["nodes"]:
            if node.get("type") == "file":
                existing_file_nodes[node.get("file", "")] = node["id"]
            elif node.get("type") == "text" and node.get("text", "").startswith("🌐"):
                existing_file_nodes[node.get("text", "")] = node["id"]

        # 1. Create Chat Query Node
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        chat_node_id = str(_uuid.uuid4())[:8]
        chat_node = {
            "id": chat_node_id,
            "type": "text",
            "text": f"💬 **Query** ({timestamp})\n{query[:120]}",
            "x": 0,
            "y": chat_y,
            "width": 300,
            "height": 80,
            "color": "4"
        }
        canvas_data["nodes"].append(chat_node)

        node_x_offset = 0

        # 2. Created Notes → right side
        for idx, note_title in enumerate(created_notes):
            # Find the .md file relative path in the vault
            rel_path = f"{note_title}.md"
            for root, _, files in os.walk(vault_root):
                for f in files:
                    if f.lower() == f"{note_title.lower()}.md":
                        rel_path = str(Path(root, f).relative_to(vault_root))
                        break

            file_node_id = existing_file_nodes.get(rel_path)
            if not file_node_id:
                file_node_id = str(_uuid.uuid4())[:8]
                file_node = {
                    "id": file_node_id,
                    "type": "file",
                    "file": rel_path,
                    "x": 400,
                    "y": chat_y + (idx * 120),
                    "width": 280,
                    "height": 60
                }
                canvas_data["nodes"].append(file_node)
                existing_file_nodes[rel_path] = file_node_id

            edge = {
                "id": str(_uuid.uuid4())[:8],
                "fromNode": chat_node_id,
                "fromSide": "right",
                "toNode": file_node_id,
                "toSide": "left",
                "label": "created"
            }
            canvas_data["edges"].append(edge)

        # 3. Retrieved RAG Notes → right side (arrows point FROM note TO chat)
        for idx, note_title in enumerate(retrieved_notes):
            rel_path = f"{note_title}.md"
            for root, _, files in os.walk(vault_root):
                for f in files:
                    if f.lower() == f"{note_title.lower()}.md":
                        rel_path = str(Path(root, f).relative_to(vault_root))
                        break

            file_node_id = existing_file_nodes.get(rel_path)
            if not file_node_id:
                file_node_id = str(_uuid.uuid4())[:8]
                file_node = {
                    "id": file_node_id,
                    "type": "file",
                    "file": rel_path,
                    "x": 400,
                    "y": chat_y - 100 - (idx * 120),
                    "width": 280,
                    "height": 60
                }
                canvas_data["nodes"].append(file_node)
                existing_file_nodes[rel_path] = file_node_id

            edge = {
                "id": str(_uuid.uuid4())[:8],
                "fromNode": file_node_id,
                "fromSide": "left",
                "toNode": chat_node_id,
                "toSide": "right",
                "label": "read context"
            }
            canvas_data["edges"].append(edge)

        # 4. Referenced URLs → left side
        for idx, url in enumerate(referenced_urls):
            url_label = f"🌐 {url[:60]}"
            url_node_id = existing_file_nodes.get(url_label)
            if not url_node_id:
                url_node_id = str(_uuid.uuid4())[:8]
                url_node = {
                    "id": url_node_id,
                    "type": "text",
                    "text": url_label,
                    "x": -400,
                    "y": chat_y + (idx * 100),
                    "width": 280,
                    "height": 50,
                    "color": "6"
                }
                canvas_data["nodes"].append(url_node)
                existing_file_nodes[url_label] = url_node_id

            edge = {
                "id": str(_uuid.uuid4())[:8],
                "fromNode": chat_node_id,
                "fromSide": "left",
                "toNode": url_node_id,
                "toSide": "right",
                "label": "referenced"
            }
            canvas_data["edges"].append(edge)

        # Write canvas file
        try:
            canvas_file.write_text(json.dumps(canvas_data, indent=2), encoding="utf-8")
            logger.info(f"Canvas: Updated KLAUSE_Connections.canvas with {len(canvas_data['nodes'])} nodes, {len(canvas_data['edges'])} edges.")
        except Exception as e:
            logger.error(f"Canvas: Failed to write canvas file: {e}")
