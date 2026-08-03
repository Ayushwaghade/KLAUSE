import os
import re
import json
import datetime
from pathlib import Path
from loguru import logger

from app.memory.database import get_db
from app.memory.obsidian_connector import ObsidianConnector, set_obsidian_vault_path

def sanitize_filename(name: str) -> str:
    # Remove invalid characters for Windows paths
    clean = re.sub(r'[\\/*?:"<>|]', " ", name)
    # Replace spaces with underscores
    clean = re.sub(r'\s+', "_", clean).strip("_ ")
    return clean if clean else "unnamed_document"

def migrate_data():
    db = get_db()
    vault_path = Path("E:/KLAUSE/knowledge_base")
    vault_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Starting data migration to Obsidian vault: {vault_path}")
    
    migrated_notes = 0
    migrated_research = 0
    
    # 1. Migrate Notes collection
    # Note schema: {"project_id": str, "content": str, "tags": list, "created_at": datetime}
    try:
        notes_cursor = db.notes.find({})
        for idx, note in enumerate(notes_cursor):
            content = note.get("content", "").strip()
            if not content:
                continue
                
            note_id = str(note["_id"])
            created_at = note.get("created_at")
            created_str = created_at.strftime("%Y-%m-%d %H:%M") if isinstance(created_at, datetime.datetime) else "Unknown"
            
            # Formulate title from first line or snippet
            first_line = content.split('\n')[0].strip()
            # Truncate first line to 40 chars
            title_snippet = sanitize_filename(first_line[:40]) if first_line else f"Note_{note_id}"
            if len(title_snippet) < 3:
                title_snippet = f"Note_{note_id}"
                
            tags = note.get("tags", [])
            if "klause-note" not in tags:
                tags.append("klause-note")
            if "migrated" not in tags:
                tags.append("migrated")
                
            # Write markdown note file
            note_file = vault_path / f"{title_snippet}.md"
            # Ensure unique filename to prevent overwrites
            counter = 1
            while note_file.exists():
                note_file = vault_path / f"{title_snippet}_{counter}.md"
                counter += 1
                
            frontmatter = (
                "---\n"
                f"note_id: {note_id}\n"
                f"project_id: {note.get('project_id', 'none')}\n"
                "tags:\n"
                + "\n".join([f"  - {t}" for t in tags]) + "\n"
                f"created: {created_str}\n"
                "---\n\n"
            )
            
            note_file.write_text(frontmatter + content, encoding="utf-8")
            migrated_notes += 1
            logger.debug(f"Migrated note '{title_snippet}' to file.")
            
    except Exception as e:
        logger.error(f"Error migrating notes collection: {e}")

    # 2. Migrate Research collection
    # Research schema: {"title": str, "tags": list, "created_at": datetime, "source_url": str, "file_path": str}
    try:
        research_cursor = db.research.find({})
        for doc in research_cursor:
            title = doc.get("title", "Untitled").strip()
            
            # Check if this document already exists as a file inside our vault path
            file_path = doc.get("file_path", "")
            if file_path and file_path.startswith(str(vault_path.resolve())):
                logger.debug(f"Skipping research document '{title}' as it is already in the vault path.")
                continue
                
            # Read content from ChromaDB if content is missing from Mongo research metadata
            # In our db, research documents in Mongo don't store full raw body, but Chroma stores chunks.
            # Let's search ChromaDB chunks for this document
            from app.memory.chroma_store import get_chroma_store
            chroma = get_chroma_store()
            
            doc_id = str(doc["_id"])
            chunk_ids = doc.get("chunk_ids", [])
            content_chunks = []
            
            if chunk_ids:
                # We can fetch chunks from Chroma by ID
                try:
                    # Chroma client query or get
                    results = chroma.research_collection.get(ids=chunk_ids)
                    if results and results.get("documents"):
                        content_chunks = results["documents"]
                except Exception as e:
                    logger.warning(f"Failed to fetch chunks from Chroma for doc {doc_id}: {e}")
                    
            content = "\n\n".join(content_chunks).strip()
            if not content:
                # Fallback: check if the Mongo doc itself has content field
                content = doc.get("content", "").strip()
                
            if not content:
                logger.warning(f"No content found for research doc '{title}' (ID: {doc_id}), skipping.")
                continue
                
            created_at = doc.get("created_at")
            created_str = created_at.strftime("%Y-%m-%d %H:%M") if isinstance(created_at, datetime.datetime) else "Unknown"
            
            tags = doc.get("tags", [])
            if "klause-research" not in tags:
                tags.append("klause-research")
            if "migrated" not in tags:
                tags.append("migrated")
                
            title_clean = sanitize_filename(title)
            research_file = vault_path / f"{title_clean}.md"
            
            # Unique filename
            counter = 1
            while research_file.exists():
                research_file = vault_path / f"{title_clean}_{counter}.md"
                counter += 1
                
            frontmatter = (
                "---\n"
                f"research_id: {doc_id}\n"
                f"source_url: {doc.get('source_url', 'none')}\n"
                "tags:\n"
                + "\n".join([f"  - {t}" for t in tags]) + "\n"
                f"created: {created_str}\n"
                "---\n\n"
            )
            
            research_file.write_text(frontmatter + content, encoding="utf-8")
            migrated_research += 1
            logger.debug(f"Migrated research document '{title}' to file.")
            
    except Exception as e:
        logger.error(f"Error migrating research collection: {e}")

    logger.info(f"Migration completed. Migrated {migrated_notes} notes and {migrated_research} research documents.")
    
    # Set the Obsidian vault path and trigger incremental sync to rebuild everything
    set_obsidian_vault_path(str(vault_path))
    connector = ObsidianConnector()
    sync_res = connector.scan_and_sync()
    logger.info(f"Re-sync complete: {sync_res}")
    
    print(json.dumps({
        "status": "success",
        "migrated_notes": migrated_notes,
        "migrated_research": migrated_research,
        "sync_total": sync_res.get("total_notes", 0)
    }))

if __name__ == "__main__":
    migrate_data()
