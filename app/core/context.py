import threading
import uuid
from typing import Dict, Tuple, Set, Optional
from loguru import logger

class SessionContext:
    def __init__(self):
        self._current_project_path = None
        self._session_data_folder = None
        self._session_id = "default_session"
        self._current_task = None
        self._last_tool_used = None
        self._last_error = None
        self._voice_active = False

        # Canvas connection tracking for Obsidian
        self._created_notes: list = []
        self._referenced_urls: list = []
        self._retrieved_notes: list = []

        # Session-specific thread-safe communication structures
        # Map: session_id -> (WebSocket, asyncio.AbstractEventLoop)
        self._active_connections: Dict[str, Tuple[any, any]] = {}
        
        # Map: session_id -> (request_id, threading.Event)
        self._confirmation_events: Dict[str, Tuple[str, threading.Event]] = {}
        
        # Map: request_id -> approved (bool)
        self._confirmation_responses: Dict[str, bool] = {}
        
        # Set of interrupted session_ids
        self._interrupted_sessions: Set[str] = set()

    @property
    def current_project_path(self) -> str | None:
        return self._current_project_path

    @current_project_path.setter
    def current_project_path(self, path: str | None):
        logger.info(f"SessionContext: Switching project path to: {path}")
        self._current_project_path = path

    @property
    def session_data_folder(self) -> str | None:
        return self._session_data_folder

    @session_data_folder.setter
    def session_data_folder(self, path: str | None):
        logger.info(f"SessionContext: Switching session data folder to: {path}")
        self._session_data_folder = path

    @property
    def session_id(self) -> str:
        return self._session_id

    @session_id.setter
    def session_id(self, val: str):
        logger.info(f"SessionContext: Setting active session_id to: {val}")
        self._session_id = val

    @property
    def current_task(self) -> str | None:
        return self._current_task

    @current_task.setter
    def current_task(self, val: str | None):
        logger.debug(f"SessionContext: current_task -> {val}")
        self._current_task = val

    @property
    def last_tool_used(self) -> str | None:
        return self._last_tool_used

    @last_tool_used.setter
    def last_tool_used(self, val: str | None):
        logger.debug(f"SessionContext: last_tool_used -> {val}")
        self._last_tool_used = val

    @property
    def last_error(self) -> str | None:
        return self._last_error

    @last_error.setter
    def last_error(self, val: str | None):
        logger.debug(f"SessionContext: last_error -> {val}")
        self._last_error = val

    @property
    def voice_active(self) -> bool:
        return self._voice_active

    @voice_active.setter
    def voice_active(self, val: bool):
        logger.debug(f"SessionContext: voice_active -> {val}")
        self._voice_active = val

    # --- Canvas Connection Tracking ---

    def track_created_note(self, note_title: str):
        """Track a note created during the current turn."""
        if note_title and note_title not in self._created_notes:
            self._created_notes.append(note_title)

    def track_referenced_url(self, url: str):
        """Track a URL referenced during the current turn."""
        if url and url not in self._referenced_urls:
            self._referenced_urls.append(url)

    def track_retrieved_note(self, note_title: str):
        """Track a note retrieved as RAG context during the current turn."""
        if note_title and note_title not in self._retrieved_notes:
            self._retrieved_notes.append(note_title)

    def get_canvas_tracking(self) -> dict:
        """Return and clear all tracked canvas connection data for this turn."""
        data = {
            "created_notes": list(self._created_notes),
            "referenced_urls": list(self._referenced_urls),
            "retrieved_notes": list(self._retrieved_notes)
        }
        self._created_notes.clear()
        self._referenced_urls.clear()
        self._retrieved_notes.clear()
        return data

    # --- Connection and Interrupt Management ---

    def set_connection(self, session_id: str, ws: any, loop: any):
        logger.info(f"SessionContext: Registering connection for session {session_id}")
        self._active_connections[session_id] = (ws, loop)

    def remove_connection(self, session_id: str):
        logger.info(f"SessionContext: Removing connection for session {session_id}")
        self._active_connections.pop(session_id, None)

    def interrupt_session(self, session_id: str):
        logger.warning(f"SessionContext: Interrupt requested for session {session_id}")
        self._interrupted_sessions.add(session_id)
        
        # Automatically resolve any waiting confirmations as False (cancel/deny)
        self.resolve_confirmation(session_id, approved=False)

    def is_interrupted(self, session_id: str) -> bool:
        return session_id in self._interrupted_sessions

    def clear_interrupt(self, session_id: str):
        if session_id in self._interrupted_sessions:
            logger.info(f"SessionContext: Clearing interrupt for session {session_id}")
            self._interrupted_sessions.remove(session_id)

    # --- Synchronous Confirmation Bridge ---

    def request_confirmation(self, session_id: str, prompt: str) -> bool:
        req_id = str(uuid.uuid4())
        event = threading.Event()
        
        self._confirmation_events[session_id] = (req_id, event)
        
        conn = self._active_connections.get(session_id)
        if conn:
            ws, loop = conn
            import asyncio
            asyncio.run_coroutine_threadsafe(
                ws.send_json({
                    "type": "request_confirmation",
                    "request_id": req_id,
                    "prompt": prompt
                }),
                loop
            )
            logger.info(f"SessionContext: Dispatched confirmation prompt to session {session_id}: {prompt}")
        else:
            logger.warning(f"SessionContext: No active WebSocket connection for session {session_id}. Denying permission.")
            return False

        # Wait up to 5 minutes for user reply
        completed = event.wait(timeout=300.0)
        
        # Clean up structures
        self._confirmation_events.pop(session_id, None)
        approved = self._confirmation_responses.pop(req_id, False)
        
        logger.info(f"SessionContext: Confirmation resolved for session {session_id} with result approved={approved} (timeout={not completed})")
        return approved

    def resolve_confirmation(self, session_id: str, approved: bool):
        pair = self._confirmation_events.get(session_id)
        if pair:
            req_id, event = pair
            logger.info(f"SessionContext: Resolving confirmation {req_id} for session {session_id} as approved={approved}")
            self._confirmation_responses[req_id] = approved
            event.set()
            return True
        return False

    def has_active_confirmation(self, session_id: str) -> bool:
        return session_id in self._confirmation_events

# Global singleton context
context = SessionContext()
