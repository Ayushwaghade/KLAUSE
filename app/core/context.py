from loguru import logger

class SessionContext:
    def __init__(self):
        self._current_project_path = None
        self._session_data_folder = None
        self._session_id = "default_session"

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

# Global singleton context
context = SessionContext()
