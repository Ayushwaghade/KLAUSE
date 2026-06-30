import os
import hashlib
import urllib.request
import re
from pathlib import Path
from loguru import logger

from app.memory.database import get_db
from app.memory.chroma_store import get_chroma_store

class KnowledgeBase:
    """
    Ingests and manages documents and URLs, chunking and indexing them in ChromaDB
    and MongoDB. Features full deduplication, fallback JS scraping, and file size limits.
    """
    def __init__(self):
        self.db = get_db()
        self.chroma = get_chroma_store()
        self.max_file_size_bytes = 10 * 1024 * 1024  # 10MB limit

    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> list:
        """Splits text into chunks of chunk_size with an overlap."""
        if not text:
            return []
        
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunks.append(text[start:end])
            start += chunk_size - overlap
            if start >= text_len or end == text_len:
                break
        return chunks

    def _get_file_hash(self, file_path: Path) -> str:
        """Generates SHA-256 hash of a file's content."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _delete_existing_by_source(self, source_key: str, source_val: str):
        """Finds and deletes any previously ingested research document by source metadata key."""
        try:
            existing = self.db.research.find({source_key: source_val})
            for doc in existing:
                doc_id = str(doc["_id"])
                logger.info(f"Deduplication: Removing existing document '{doc.get('title')}' (ID: {doc_id}) first.")
                self.delete_document(doc_id)
        except Exception as e:
            logger.error(f"Deduplication deletion failed: {e}")

    def add_document(self, file_path: str, tags: list, chunk_size: int = 1000, overlap: int = 200) -> str:
        """Parses and indexes a local file (.txt, .md, .pdf, .docx). Caps at 10MB."""
        path = Path(file_path).resolve()
        if not path.exists():
            return f"Error: File '{file_path}' does not exist."

        # File Size check
        size = path.stat().st_size
        if size > self.max_file_size_bytes:
            return f"Error: File exceeds the 10MB size limit (Size: {size / (1024*1024):.2f}MB)."

        # Extension check
        ext = path.suffix.lower()
        if ext not in (".txt", ".md", ".pdf", ".docx"):
            return f"Error: Unsupported file extension '{ext}'. Only .txt, .md, .pdf, and .docx are supported."

        try:
            # 1. Extract content
            content = ""
            if ext in (".txt", ".md"):
                content = path.read_text(encoding="utf-8", errors="ignore")
            elif ext == ".pdf":
                from pypdf import PdfReader
                reader = PdfReader(path)
                pages_text = []
                for p in reader.pages:
                    text = p.extract_text()
                    if text:
                        pages_text.append(text)
                content = "\n".join(pages_text)
            elif ext == ".docx":
                import docx
                doc = docx.Document(path)
                content = "\n".join([para.text for para in doc.paragraphs])

            if not content.strip():
                return f"Error: No readable text extracted from '{path.name}'."

            # 2. Content Hash Deduplication
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            self._delete_existing_by_source("content_hash", content_hash)
            self._delete_existing_by_source("file_path", str(path))

            # 3. Chunk and Ingest
            title = path.name
            return self._index_content(title, content, tags, chunk_size, overlap, metadata={
                "file_path": str(path),
                "content_hash": content_hash,
                "file_size": size
            })

        except Exception as e:
            logger.error(f"Failed to add document '{file_path}': {e}")
            return f"Error parsing document: {e}"

    def add_url(self, url: str, tags: list, chunk_size: int = 1000, overlap: int = 200) -> str:
        """Fetches, parses, and indexes a URL. Falls back to BrowserAgent if SPA/JS-heavy."""
        try:
            # Deduplicate by URL
            self._delete_existing_by_source("source_url", url)

            # 1. Fetch via requests/urllib first (lightweight)
            content = ""
            title = url
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    html = response.read().decode('utf-8', errors='ignore')
                    
                    # Extract page title
                    title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
                    if title_match:
                        title = title_match.group(1).strip()
                    
                    # Strip tags basic text parser
                    text_content = re.sub(r'<script.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
                    text_content = re.sub(r'<style.*?</style>', '', text_content, flags=re.DOTALL | re.IGNORECASE)
                    text_content = re.sub(r'<.*?>', ' ', text_content, flags=re.DOTALL)
                    text_content = re.sub(r'\s+', ' ', text_content).strip()
                    content = text_content
            except Exception as e:
                logger.warning(f"Lightweight request to {url} failed: {e}. Falling back to BrowserAgent...")

            # 2. BrowserAgent Fallback if content is empty or JS-dependent
            if len(content) < 300:
                logger.info(f"Content is sparse ({len(content)} chars). Falling back to Playwright BrowserAgent...")
                try:
                    from app.agents.browser_agent import BrowserAgent
                    agent = BrowserAgent()
                    # Execute in browser
                    page_text = agent.read_page(url)
                    if len(page_text) > len(content):
                        content = page_text
                        logger.info("Successfully fetched JS-rendered content via BrowserAgent.")
                except Exception as browser_err:
                    logger.error(f"BrowserAgent fallback failed: {browser_err}")

            if not content.strip():
                return f"Error: Failed to fetch any text content from URL '{url}'."

            # 3. Index Content
            return self._index_content(title, content, tags, chunk_size, overlap, metadata={
                "source_url": url
            })

        except Exception as e:
            logger.error(f"Failed to add URL '{url}': {e}")
            return f"Error indexing URL: {e}"

    def add_text(self, title: str, content: str, tags: list, chunk_size: int = 1000, overlap: int = 200) -> str:
        """Directly indexes arbitrary text content."""
        # Deduplicate by Title
        self._delete_existing_by_source("title", title)
        return self._index_content(title, content, tags, chunk_size, overlap, metadata={})

    def _index_content(self, title: str, content: str, tags: list, chunk_size: int, overlap: int, metadata: dict) -> str:
        """Internal helper to chunk and save data into MongoDB and ChromaDB."""
        # Parse tags
        tags_list = [t.strip().lower() for t in tags if t.strip()]
        
        # Save document info to MongoDB research collection
        import datetime
        research_doc = {
            "title": title,
            "tags": tags_list,
            "created_at": datetime.datetime.utcnow(),
            "chunk_ids": []
        }
        # Merge source metadata (e.g. source_url, file_path)
        research_doc.update(metadata)
        
        res = self.db.research.insert_one(research_doc)
        research_id = str(res.inserted_id)
        
        # Chunk text
        chunks = self.chunk_text(content, chunk_size, overlap)
        chunk_ids = []
        
        for idx, chunk in enumerate(chunks):
            chunk_id = f"{research_id}_chunk_{idx}"
            chunk_ids.append(chunk_id)
            
            # Index chunk in ChromaDB
            chroma_meta = {
                "parent_id": research_id,
                "title": title,
                "chunk_index": idx,
                "tags": ",".join(tags_list),
                "source_url": metadata.get("source_url", "none"),
                "file_path": metadata.get("file_path", "none"),
                "created_at": research_doc["created_at"].isoformat()
            }
            self.chroma.add_research(chunk_id, chunk, chroma_meta)
            
        # Update MongoDB doc with list of chunk IDs
        self.db.research.update_one(
            {"_id": res.inserted_id},
            {"$set": {"chunk_ids": chunk_ids}}
        )
        
        logger.info(f"Indexed document '{title}' (ID: {research_id}) in {len(chunks)} chunks.")
        return f"Success: Document '{title}' successfully ingested and indexed into {len(chunks)} chunks (ID: {research_id})."

    def delete_document(self, document_id: str) -> bool:
        """Deletes document from MongoDB and all corresponding chunks from ChromaDB."""
        from bson import ObjectId
        try:
            doc = self.db.research.find_one({"_id": ObjectId(document_id)})
            if not doc:
                # Try finding by string id if client connected to MockDB
                doc = self.db.research.find_one({"_id": document_id})
                
            if doc:
                chunk_ids = doc.get("chunk_ids", [])
                for cid in chunk_ids:
                    self.chroma.delete_research(cid)
                
                # Delete main document record
                self.db.research.delete_one({"_id": doc["_id"]})
                logger.info(f"Deleted research document ID: {document_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
        return False

    def clear_kb(self):
        """Purges all research documents and matching ChromaDB vectors."""
        try:
            # Delete all documents individually to clean ChromaDB too
            cursor = self.db.research.find({})
            count = 0
            for doc in cursor:
                doc_id = str(doc["_id"])
                if self.delete_document(doc_id):
                    count += 1
            logger.info(f"Knowledge Base cleared: {count} documents removed.")
            return f"Success: Cleared {count} documents from the Knowledge Base."
        except Exception as e:
            logger.error(f"Failed to clear KB: {e}")
            return f"Error: Failed to clear Knowledge Base: {e}"

    def search(self, query: str, limit: int = 5) -> list:
        """Performs a similarity search on ChromaDB for research chunks."""
        try:
            results = self.chroma.query_research(query, limit=limit)
            return results
        except Exception as e:
            logger.error(f"KB semantic query failed: {e}")
            return []

    def get_all_topics(self) -> list:
        """Retrieves all unique tags/topics across indexed research items."""
        try:
            cursor = self.db.research.find({})
            all_tags = set()
            for doc in cursor:
                tags = doc.get("tags", [])
                for t in tags:
                    all_tags.add(t.strip().lower())
            return sorted(list(all_tags))
        except Exception as e:
            logger.error(f"Failed to retrieve KB topics: {e}")
            return []


# Global instance
_kb_instance = None

def get_knowledge_base() -> KnowledgeBase:
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = KnowledgeBase()
    return _kb_instance
