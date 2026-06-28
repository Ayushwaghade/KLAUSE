from loguru import logger

class SessionContext:
    def __init__(self):
        self._current_project_path = None

    @property
    def current_project_path(self) -> str | None:
        return self._current_project_path

    @current_project_path.setter
    def current_project_path(self, path: str | None):
        logger.info(f"SessionContext: Switching project path to: {path}")
        self._current_project_path = path

# Global singleton context
context = SessionContext()
