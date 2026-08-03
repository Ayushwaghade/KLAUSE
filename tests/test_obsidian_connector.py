import os
import shutil
import tempfile
from pathlib import Path
import pytest

from app.memory.obsidian_connector import parse_markdown_note, ObsidianConnector, set_obsidian_vault_path, get_obsidian_vault_path
from app.memory.database import get_db
from app.memory.knowledge_base import get_knowledge_base

def test_parse_markdown_note():
    # Test YAML frontmatter parsing and stripping
    raw_content = (
        "---\n"
        "title: Test Note\n"
        "tags:\n"
        "  - programming\n"
        "  - python\n"
        "---\n\n"
        "This is the body of the note.\n"
        "It contains some text and #inline-tag and #another_tag.\n"
    )
    meta, body, tags = parse_markdown_note(raw_content)
    
    assert meta.get("title") == "Test Note"
    assert "programming" in tags
    assert "python" in tags
    assert "inline-tag" in tags
    assert "another_tag" in tags
    assert "This is the body of the note." in body
    assert "---" not in body  # Strip frontmatter

def test_obsidian_sync_lifecycle():
    # Setup temporary directory as mock vault
    temp_dir = tempfile.mkdtemp()
    try:
        # Create a sample note file
        note_path = Path(temp_dir) / "Ingress.md"
        note_content = (
            "---\n"
            "tags:\n"
            "  - test-vault\n"
            "---\n"
            "Hello Obsidian vault context! This is a test chunk."
        )
        note_path.write_text(note_content, encoding="utf-8")
        
        # Save vault path settings
        original_vault = get_obsidian_vault_path()
        set_obsidian_vault_path(temp_dir)
        
        try:
            # Sync
            connector = ObsidianConnector()
            res = connector.scan_and_sync()
            
            assert res.get("status") == "success"
            assert res.get("total_notes") == 1
            assert res.get("added") == 1
            
            # Verify file exists in database
            db = get_db()
            doc = db.research.find_one({"file_path": str(note_path.resolve())})
            assert doc is not None
            assert "test-vault" in doc.get("tags", [])
            assert "obsidian" in doc.get("tags", [])
            
            # Delete the note file and sync again (testing deletion cleanup)
            note_path.unlink()
            res_delete = connector.scan_and_sync()
            assert res_delete.get("status") == "success"
            assert res_delete.get("deleted") == 1
            assert res_delete.get("total_notes") == 0
            
            # Verify file is deleted in database
            doc_deleted = db.research.find_one({"file_path": str(note_path.resolve())})
            assert doc_deleted is None
            
        finally:
            # Revert vault path setting
            set_obsidian_vault_path(original_vault)
            
    finally:
        # Clean up temporary dir
        shutil.rmtree(temp_dir)

def test_canvas_generation():
    """Test that update_connections_canvas creates valid canvas JSON."""
    import json
    temp_dir = tempfile.mkdtemp()
    try:
        # Create a mock note file in the vault
        note_path = Path(temp_dir) / "Big_Data_Overview.md"
        note_path.write_text("# Big Data\nSome content about big data.", encoding="utf-8")

        original_vault = get_obsidian_vault_path()
        set_obsidian_vault_path(temp_dir)

        try:
            connector = ObsidianConnector()

            # Call canvas update with sample data
            connector.update_connections_canvas(
                query="What is big data?",
                created_notes=["New_Research_Note"],
                referenced_urls=["https://en.wikipedia.org/wiki/Big_data"],
                retrieved_notes=["Big_Data_Overview"]
            )

            # Verify canvas file was created
            canvas_file = Path(temp_dir) / "KLAUSE_Connections.canvas"
            assert canvas_file.exists(), "Canvas file was not created"

            # Parse and validate structure
            canvas = json.loads(canvas_file.read_text(encoding="utf-8"))
            assert "nodes" in canvas
            assert "edges" in canvas

            # Should have 4 nodes: 1 chat query + 1 created note + 1 retrieved note + 1 URL
            assert len(canvas["nodes"]) == 4, f"Expected 4 nodes, got {len(canvas['nodes'])}"

            # Verify node types
            node_types = [n["type"] for n in canvas["nodes"]]
            assert node_types.count("text") == 2  # chat query + URL
            assert node_types.count("file") == 2  # created note + retrieved note

            # Should have 3 edges: created, read context, referenced
            assert len(canvas["edges"]) == 3, f"Expected 3 edges, got {len(canvas['edges'])}"

            edge_labels = [e.get("label") for e in canvas["edges"]]
            assert "created" in edge_labels
            assert "read context" in edge_labels
            assert "referenced" in edge_labels

            # Verify chat node is at X=0
            chat_node = [n for n in canvas["nodes"] if "Query" in n.get("text", "")][0]
            assert chat_node["x"] == 0

        finally:
            set_obsidian_vault_path(original_vault)

    finally:
        shutil.rmtree(temp_dir)
