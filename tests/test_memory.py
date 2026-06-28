import pytest
from app.memory.database import get_db, MockDatabase
from app.memory.chroma_store import get_chroma_store, MockChromaCollection
from app.memory.memory_manager import get_memory_manager

def test_database_fallback():
    """
    Verify get_db returns a working database instance (either MongoDB or MockDatabase).
    """
    db = get_db()
    assert db is not None
    # Verify that standard collections are attributes of the returned db
    assert hasattr(db, "conversations")
    assert hasattr(db, "notes")
    assert hasattr(db, "research")

def test_chroma_store_fallback():
    """
    Verify ChromaStore is initialized and has working collection objects.
    """
    store = get_chroma_store()
    assert store is not None
    assert store.notes_collection is not None
    assert store.research_collection is not None

def test_memory_manager_save_and_retrieve_history():
    """
    Test save_conversation and get_conversation_history.
    """
    import uuid
    mgr = get_memory_manager()
    session_id = f"test-session-{uuid.uuid4()}"
    
    # Save a couple of messages
    mgr.save_conversation(session_id, "user", "Hello KLAUSE")
    mgr.save_conversation(session_id, "assistant", "Hello! How can I help you?")
    
    # Retrieve
    history = mgr.get_conversation_history(session_id, limit=5)
    assert len(history) >= 2
    
    # Chronological check
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello KLAUSE"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Hello! How can I help you?"

def test_memory_manager_save_note_and_search():
    """
    Test save_note and semantic searching.
    """
    mgr = get_memory_manager()
    
    # Save notes
    note_id_1 = mgr.save_note(project_id="test-proj", content="The capital of France is Paris.", tags="geography, france")
    note_id_2 = mgr.save_note(project_id="test-proj", content="Python is a dynamic programming language.", tags="coding, python")
    
    assert note_id_1 is not None
    assert note_id_2 is not None
    
    # Perform semantic query (since Mock fallback returns all documents, we test that combined results are returned)
    results = mgr.search_semantic_memories(query="Paris", limit=5)
    assert len(results) > 0
    # Confirm result structure contains distance and content
    assert "content" in results[0]
    assert "distance" in results[0]
    assert "type" in results[0]

def test_memory_manager_save_research():
    """
    Test save_research.
    """
    mgr = get_memory_manager()
    research_id = mgr.save_research(
        title="Vector Search Architectures",
        content="This document details FAISS and ChromaDB architectures.",
        source_url="https://example.com/vector-search",
        tags="embeddings, database"
    )
    assert research_id is not None
