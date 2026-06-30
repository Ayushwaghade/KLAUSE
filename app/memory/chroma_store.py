import os
import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
from google import genai
from loguru import logger
from app.config.config import settings

class GeminiEmbeddingFunction(EmbeddingFunction):
    """Custom embedding function utilizing Gemini models/text-embedding-004 API."""
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.client = None
        if self.api_key:
            try:
                self.client = genai.Client()
            except Exception as e:
                logger.warning(f"Failed to instantiate Gemini Client for embeddings: {e}")
        self.model = "models/text-embedding-004"
        if hasattr(settings, "ai") and settings.ai.embedding_model:
            self.model = settings.ai.embedding_model

    def __call__(self, input: Documents) -> Embeddings:
        if not self.client:
            logger.warning("Gemini Client not connected. Returning empty placeholder embeddings.")
            return [[0.0] * 768 for _ in input]
            
        embeddings = []
        try:
            for text in input:
                res = self.client.models.embed_content(
                    model=self.model,
                    contents=text
                )
                if res and res.embeddings:
                    embeddings.append(res.embeddings[0].values)
                else:
                    embeddings.append([0.0] * 768)
        except Exception as e:
            logger.error(f"Gemini embedding generation failed: {e}")
            return [[0.0] * 768 for _ in input]
        return embeddings

class MockChromaCollection:
    def __init__(self):
        self.documents = []
        self.metadatas = []
        self.ids = []

    def add(self, documents, metadatas, ids):
        self.documents.extend(documents)
        self.metadatas.extend(metadatas)
        self.ids.extend(ids)

    def delete(self, ids=None, where=None):
        if ids:
            for idx in reversed(range(len(self.ids))):
                if self.ids[idx] in ids:
                    self.ids.pop(idx)
                    self.documents.pop(idx)
                    self.metadatas.pop(idx)

    def query(self, query_texts, n_results=5):
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
            self.emb_fn = GeminiEmbeddingFunction()
            self.client = chromadb.PersistentClient(path=self.chroma_path)
            self.notes_collection = self.client.get_or_create_collection(
                name="notes",
                embedding_function=self.emb_fn
            )
            self.research_collection = self.client.get_or_create_collection(
                name="research",
                embedding_function=self.emb_fn
            )
            self.is_connected = True
            logger.info("ChromaDB collections 'notes' and 'research' successfully loaded/created with Gemini embeddings.")
        except Exception as e:
            logger.warning(f"Failed to initialize ChromaDB: {e}. Falling back to In-Memory Chroma client.")
            self.notes_collection = MockChromaCollection()
            self.research_collection = MockChromaCollection()

    def delete_note(self, note_id: str):
        logger.debug(f"Deleting note {note_id} from ChromaDB.")
        try:
            self.notes_collection.delete(ids=[note_id])
        except Exception as e:
            logger.warning(f"Failed to delete note {note_id} from ChromaDB: {e}")

    def delete_research(self, research_id: str):
        logger.debug(f"Deleting research {research_id} from ChromaDB.")
        try:
            self.research_collection.delete(ids=[research_id])
        except Exception as e:
            logger.warning(f"Failed to delete research {research_id} from ChromaDB: {e}")

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
