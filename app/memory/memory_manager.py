import datetime
from bson import ObjectId
from loguru import logger
from app.memory.database import get_db
from app.memory.chroma_store import get_chroma_store

class MemoryManager:
    def __init__(self):
        try:
            self.db = get_db()
            self.chroma = get_chroma_store()
            logger.info("MemoryManager successfully coordinated.")
        except Exception as e:
            logger.error(f"Failed to initialize MemoryManager components: {e}")
            raise

    # --- Conversations ---
    def save_conversation(self, session_id: str, role: str, content: str, project_id: str = None):
        """
        Save a chat message to the MongoDB conversations collection.
        """
        logger.debug(f"Saving conversation message for session {session_id}.")
        msg = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.utcnow(),
            "project_id": project_id
        }
        try:
            self.db.conversations.insert_one(msg)
        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")

    def get_conversation_history(self, session_id: str, limit: int = 20) -> list:
        """
        Retrieve chronologically sorted conversation history for a session.
        """
        logger.debug(f"Retrieving conversation history for session {session_id}.")
        try:
            cursor = self.db.conversations.find(
                {"session_id": session_id}
            ).sort([("timestamp", -1), ("_id", -1)]).limit(limit)
            
            history = []
            for doc in cursor:
                # Convert ObjectId to string for compatibility
                doc["_id"] = str(doc["_id"])
                history.append(doc)
            
            # Reverse history to restore chronological order
            history.reverse()
            return history
        except Exception as e:
            logger.error(f"Failed to retrieve conversation history: {e}")
            return []

    # --- Notes ---
    def save_note(self, project_id: str, content: str, tags: str = "") -> str:
        """
        Save a note to MongoDB and index it in ChromaDB for semantic search.
        """
        logger.info("Saving note to memory.")
        tags_list = [t.strip() for t in tags.split(",") if t.strip()]
        note_doc = {
            "project_id": project_id,
            "content": content,
            "tags": tags_list,
            "created_at": datetime.datetime.utcnow()
        }
        
        try:
            # Save to MongoDB first to get ID
            res = self.db.notes.insert_one(note_doc)
            note_id = str(res.inserted_id)
            
            # Index in ChromaDB
            chroma_meta = {
                "project_id": project_id or "none",
                "tags": ",".join(tags_list),
                "created_at": note_doc["created_at"].isoformat()
            }
            self.chroma.add_note(note_id, content, chroma_meta)
            logger.info(f"Note successfully saved and indexed with ID: {note_id}")
            return note_id
        except Exception as e:
            logger.error(f"Failed to save note: {e}")
            return f"Error saving note: {e}"

    # --- Research ---
    def save_research(self, title: str, content: str, source_url: str = "", tags: str = "") -> str:
        """
        Save a research document to MongoDB and index it in ChromaDB.
        """
        logger.info(f"Saving research to memory: {title}")
        tags_list = [t.strip() for t in tags.split(",") if t.strip()]
        research_doc = {
            "title": title,
            "content": content,
            "source_url": source_url,
            "tags": tags_list,
            "created_at": datetime.datetime.utcnow()
        }
        
        try:
            # Save to MongoDB first
            res = self.db.research.insert_one(research_doc)
            research_id = str(res.inserted_id)
            
            # Index in ChromaDB
            chroma_meta = {
                "title": title,
                "source_url": source_url or "none",
                "tags": ",".join(tags_list),
                "created_at": research_doc["created_at"].isoformat()
            }
            self.chroma.add_research(research_id, content, chroma_meta)
            logger.info(f"Research document successfully saved and indexed with ID: {research_id}")
            return research_id
        except Exception as e:
            logger.error(f"Failed to save research: {e}")
            return f"Error saving research: {e}"

    # --- Semantic Search ---
    def search_semantic_memories(self, query: str, limit: int = 5) -> list:
        """
        Semantically search both notes and research collections, returned sorted by distance.
        """
        logger.info(f"Performing combined semantic search for: {query}")
        try:
            notes_results = self.chroma.query_notes(query, limit=limit)
            research_results = self.chroma.query_research(query, limit=limit)
            
            # Combine and sort by distance (lowest distance is most similar)
            combined = notes_results + research_results
            combined.sort(key=lambda x: x["distance"])
            
            return combined[:limit]
        except Exception as e:
            logger.error(f"Combined semantic search failed: {e}")
            return []

    # --- Projects & Tasks ---
    def save_project(self, name: str, path: str, description: str = "", status: str = "active", tags: str = "") -> str:
        """
        Save/Register a new project metadata record.
        """
        tags_list = [t.strip() for t in tags.split(",") if t.strip()]
        project = {
            "name": name,
            "path": path,
            "description": description,
            "status": status,
            "tags": tags_list,
            "last_opened": datetime.datetime.utcnow()
        }
        try:
            self.db.projects.update_one(
                {"name": name},
                {"$set": project},
                upsert=True
            )
            logger.info(f"Project metadata registered/updated: {name}")
            return f"Success: Project '{name}' registered."
        except Exception as e:
            logger.error(f"Failed to save project: {e}")
            return f"Error saving project: {e}"

    def save_task(self, project_id: str, title: str, description: str = "", status: str = "pending", priority: str = "medium") -> str:
        """
        Save a task linked to a project.
        """
        task = {
            "project_id": project_id,
            "title": title,
            "description": description,
            "status": status,
            "priority": priority,
            "created_at": datetime.datetime.utcnow()
        }
        try:
            res = self.db.tasks.insert_one(task)
            task_id = str(res.inserted_id)
            logger.info(f"Task registered under project {project_id} with ID: {task_id}")
            return task_id
        except Exception as e:
            logger.error(f"Failed to save task: {e}")
            return f"Error saving task: {e}"

# Global MemoryManager instance
_memory_manager_inst = None

def get_memory_manager():
    global _memory_manager_inst
    if _memory_manager_inst is None:
        _memory_manager_inst = MemoryManager()
    return _memory_manager_inst
