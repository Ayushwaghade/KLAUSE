import chromadb
from loguru import logger
from app.config.config import settings

class MockChromaCollection:
    def __init__(self):
        self.documents = []
        self.metadatas = []
        self.ids = []

    def add(self, documents, metadatas, ids):
        self.documents.extend(documents)
        self.metadatas.extend(metadatas)
        self.ids.extend(ids)

    def query(self, query_texts, n_results=5):
        # Return all documents up to n_results
        limit = min(n_results, len(self.ids))
        return {
            "ids": [self.ids[:limit]],
            "documents": [self.documents[:limit]],
            "metadatas": [self.metadatas[:limit]],
            "distances": [[0.0] * limit]
        }

class ChromaStore:
    def __init__(self):
        self.chroma_path = settings.memory.chroma_path
        self.is_connected = False
        logger.info(f"Initializing local persistent ChromaDB client at: {self.chroma_path}")
        
        try:
            self.client = chromadb.PersistentClient(path=self.chroma_path)
            self.notes_collection = self.client.get_or_create_collection(name="notes")
            self.research_collection = self.client.get_or_create_collection(name="research")
            self.is_connected = True
            logger.info("ChromaDB collections 'notes' and 'research' successfully loaded/created.")
        except Exception as e:
            logger.warning(f"Failed to initialize ChromaDB: {e}. Falling back to In-Memory Chroma client.")
            self.notes_collection = MockChromaCollection()
            self.research_collection = MockChromaCollection()

    def add_note(self, note_id: str, content: str, metadata: dict):
        logger.debug(f"Adding note {note_id} to ChromaDB semantic index.")
        self.notes_collection.add(
            documents=[content],
            metadatas=[metadata],
            ids=[note_id]
        )

    def add_research(self, research_id: str, content: str, metadata: dict):
        logger.debug(f"Adding research {research_id} to ChromaDB semantic index.")
        self.research_collection.add(
            documents=[content],
            metadatas=[metadata],
            ids=[research_id]
        )

    def query_notes(self, query: str, limit: int = 5) -> list:
        logger.debug(f"Querying ChromaDB 'notes' with semantic search: {query}")
        results = self.notes_collection.query(
            query_texts=[query],
            n_results=limit
        )
        return self._format_results(results, "note")

    def query_research(self, query: str, limit: int = 5) -> list:
        logger.debug(f"Querying ChromaDB 'research' with semantic search: {query}")
        results = self.research_collection.query(
            query_texts=[query],
            n_results=limit
        )
        return self._format_results(results, "research")

    def _format_results(self, raw_results, doc_type: str) -> list:
        formatted = []
        if not raw_results or "ids" not in raw_results or not raw_results["ids"]:
            return formatted
            
        ids = raw_results["ids"][0]
        documents = raw_results["documents"][0]
        metadatas = raw_results["metadatas"][0]
        distances = raw_results["distances"][0] if "distances" in raw_results else [0.0] * len(ids)
        
        for idx in range(len(ids)):
            formatted.append({
                "id": ids[idx],
                "type": doc_type,
                "content": documents[idx],
                "metadata": metadatas[idx],
                "distance": distances[idx]
            })
        return formatted

# Global Chroma Store client instance
_chroma_store_inst = None

def get_chroma_store():
    global _chroma_store_inst
    if _chroma_store_inst is None:
        _chroma_store_inst = ChromaStore()
    return _chroma_store_inst
