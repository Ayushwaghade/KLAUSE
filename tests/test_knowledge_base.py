import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.memory.knowledge_base import KnowledgeBase
from app.core.dispatcher import Dispatcher
from app.tools.kb_tools import kb_add_document, kb_add_url, kb_search, kb_delete, kb_clear


@pytest.fixture
def temp_kb_dir(tmp_path):
    """Fixture to mock chroma store paths and local testing files."""
    db_dir = tmp_path / "mock_chroma"
    db_dir.mkdir()
    return db_dir


def test_knowledge_base_unsupported_and_oversized_files(temp_kb_dir):
    kb = KnowledgeBase()
    
    # 1. Test unsupported extension
    bad_file = temp_kb_dir / "test.csv"
    bad_file.write_text("a,b,c", encoding="utf-8")
    
    res = kb.add_document(str(bad_file), ["test"])
    assert "Unsupported file extension" in res

    # 2. Test file size guard (>10MB)
    huge_file = temp_kb_dir / "large.txt"
    # mock stat st_size to be 11MB
    with patch.object(Path, "stat") as mock_stat:
        mock_stat.return_value.st_size = 12 * 1024 * 1024
        res2 = kb.add_document(str(huge_file), ["test"])
        assert "exceeds the 10MB size limit" in res2


def test_knowledge_base_chunking():
    kb = KnowledgeBase()
    text = "abcdefghij" # 10 chars
    # Chunk size 4, overlap 1 -> Expected:
    # 1. "abcd" (start 0, end 4)
    # 2. start = 4 - 1 = 3 -> "defg" (start 3, end 7)
    # 3. start = 7 - 1 = 6 -> "ghij" (start 6, end 10)
    chunks = kb.chunk_text(text, chunk_size=4, overlap=1)
    assert chunks == ["abcd", "defg", "ghij"]


@patch("app.memory.knowledge_base.urllib.request.urlopen")
@patch("app.agents.browser_agent.BrowserAgent")
def test_knowledge_base_js_fallback(mock_browser_agent_class, mock_urlopen, temp_kb_dir):
    kb = KnowledgeBase()
    
    # Mock normal urlopen to return empty page
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"<html></html>"
    mock_urlopen.return_value.__enter__.return_value = mock_resp
    
    # Mock BrowserAgent read_page to return rich text
    mock_agent = MagicMock()
    mock_agent.read_page.return_value = "This is rich content rendered by Playwright and JavaScript!"
    mock_browser_agent_class.return_value = mock_agent
    
    # Mock MongoDB and ChromaDB
    kb.db = MagicMock()
    kb.chroma = MagicMock()
    
    res = kb.add_url("https://example.com/dynamic-spa", ["js"])
    assert "Success" in res
    mock_browser_agent_class.assert_called_once()
    mock_agent.read_page.assert_called_once_with("https://example.com/dynamic-spa")


def test_knowledge_base_deduplication(temp_kb_dir):
    kb = KnowledgeBase()
    
    # Mock MongoDB and ChromaDB
    kb.db = MagicMock()
    kb.chroma = MagicMock()
    
    # Mock existing query to find a document
    kb.db.research.find.return_value = [
        {"_id": "old_doc_123", "title": "Duplicated Doc", "chunk_ids": ["c1", "c2"]}
    ]
    
    # Mock delete
    with patch.object(kb, "delete_document") as mock_delete:
        test_file = temp_kb_dir / "doc.txt"
        test_file.write_text("Hello duplicate context", encoding="utf-8")
        
        kb.add_document(str(test_file), ["dup"])
        
        # Verify it found and deleted the existing document first!
        mock_delete.assert_called_with("old_doc_123")


@patch("google.genai.Client")
def test_real_chromadb_embedding_integration(mock_genai_client, temp_kb_dir):
    """
    Integration test utilizing a real local persistent ChromaDB instance
    to verify actual embedding generation and similarity query recall.
    """
    # Setup mock Client response for embed_content
    mock_client = MagicMock()
    mock_embeddings = MagicMock()
    
    # Models generate a mock 768-dimension vector
    mock_embeddings.embeddings = [MagicMock()]
    mock_embeddings.embeddings[0].values = [0.1] * 768
    mock_client.models.embed_content.return_value = mock_embeddings
    mock_genai_client.return_value = mock_client

    # Initialize a clean local ChromaDB on temp path
    with patch("app.config.config.settings.memory.chroma_path", str(temp_kb_dir)):
        kb = KnowledgeBase()
        # Mock MongoDB
        kb.db = MagicMock()
        
        # Ingest text segments
        kb.add_text("Doc A", "The quick brown fox jumps over the lazy dog", ["animals"])
        kb.add_text("Doc B", "Malware analysis protocols for remote systems", ["cybersec"])
        
        # Search
        results = kb.search("lazy dog", limit=1)
        assert len(results) == 1
        assert results[0]["type"] == "research"
        assert results[0]["metadata"]["tags"] == "animals"
        assert results[0]["content"] == "The quick brown fox jumps over the lazy dog"
