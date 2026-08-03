import os
import hashlib
from pathlib import Path
from loguru import logger

from app.memory.obsidian_connector import parse_markdown_note, ObsidianConnector, get_obsidian_vault_path

def deduplicate():
    vault_path = get_obsidian_vault_path()
    if not vault_path:
        print("Error: No vault path configured.")
        return
        
    vault_root = Path(vault_path).resolve()
    print(f"Scanning vault for duplicate note contents: {vault_root}")
    
    unique_contents = {}  # hash -> first_seen_filepath
    duplicates_deleted = 0
    
    for root, _, files in os.walk(vault_root):
        for file in files:
            if file.endswith(".md"):
                file_path = Path(root) / file
                
                # Skip manual empty files
                if file.lower().startswith("untitled"):
                    continue
                    
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    
                    # Parse YAML frontmatter and get clean body
                    _, body, _ = parse_markdown_note(content)
                    
                    # Clean whitespaces for robust body matching
                    body_clean = body.strip().lower()
                    if not body_clean:
                        # Delete empty files (another form of junk)
                        print(f"Deleting empty/bodyless note: {file}")
                        file_path.unlink()
                        duplicates_deleted += 1
                        continue
                        
                    body_hash = hashlib.md5(body_clean.encode("utf-8")).hexdigest()
                    
                    if body_hash in unique_contents:
                        # Already saw this note content! Delete this duplicate file.
                        original = unique_contents[body_hash]
                        print(f"Deleting duplicate note: '{file}' (Duplicate of '{original.name}')")
                        file_path.unlink()
                        duplicates_deleted += 1
                    else:
                        unique_contents[body_hash] = file_path
                        
                except Exception as e:
                    logger.error(f"Error checking file {file}: {e}")
                    
    print(f"Deduplication complete. Deleted {duplicates_deleted} duplicate files.")
    
    # Sync vault to clean up database records
    connector = ObsidianConnector()
    sync_res = connector.scan_and_sync()
    print(f"Re-sync complete: {sync_res}")

if __name__ == "__main__":
    deduplicate()
