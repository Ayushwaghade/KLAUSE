import os
from pathlib import Path
from typing import Optional
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class KlauseSettings(BaseModel):
    name: str = "KLAUSE"
    version: str = "0.1.0"
    wake_word: str = "klause"
    personality: str = "supportive"

class AISettings(BaseModel):
    gemini_model: str = "gemini-3.1-flash-lite-preview"
    embedding_model: str = "models/embedding-001"
    max_tokens: int = 8192
    max_steps: int = 10

class MemorySettings(BaseModel):
    mongo_uri: str = "mongodb://localhost:27017/"
    mongo_db: str = "klause"
    chroma_path: str = "./data/chroma"
    max_conversation_history: int = 50

class LiveTyperSettings(BaseModel):
    hotkey: str = "ctrl+shift+v"
    chunk_seconds: int = 2
    max_duration_seconds: int = 300

class VoiceSettings(BaseModel):
    enabled: bool = False
    trigger_mode: str = "push_to_talk"
    hotkey: str = "ctrl+space"
    stt_engine: str = "whisper"
    tts_engine: str = "sapi"
    max_spoken_sentences: int = 3
    speaking_rate: int = 0
    live_typer: LiveTyperSettings = LiveTyperSettings()

class PathSettings(BaseModel):
    knowledge_base: str = "./knowledge_base"
    projects: str = "./projects"
    logs: str = "./logs"

class StateMachineSettings(BaseModel):
    enabled: bool = True
    capture_clipboard: bool = True
    max_visible_windows: int = 10

class BrowserSettings(BaseModel):
    prefer: str = "chrome"  # chrome | brave | msedge | firefox
    profile_directory: Optional[str] = None  # e.g., "Default" or "Profile 1"

class AutomationSettings(BaseModel):
    enabled: bool = True
    polling_interval_seconds: float = 0.5
    debounce_interval_seconds: float = 0.3
    max_rules: int = 50

class AppConfig(BaseSettings):
    klause: KlauseSettings = KlauseSettings()
    ai: AISettings = AISettings()
    memory: MemorySettings = MemorySettings()
    voice: VoiceSettings = VoiceSettings()
    paths: PathSettings = PathSettings()
    state_machine: StateMachineSettings = StateMachineSettings()
    automation: AutomationSettings = AutomationSettings()
    browser: BrowserSettings = BrowserSettings()
    allowed_applications: dict[str, str] = Field(default_factory=dict)
    google_search_api_key: Optional[str] = Field(None, validation_alias="GOOGLE_SEARCH_API_KEY")
    google_search_cx: Optional[str] = Field(None, validation_alias="GOOGLE_SEARCH_CX")
    serper_api_key: Optional[str] = Field(None, validation_alias="SERPER_API_KEY")

    # Environment variables mapped from .env
    gemini_api_key: Optional[str] = Field(None, validation_alias="GEMINI_API_KEY")
    local_only: bool = Field(False, validation_alias="LOCAL_ONLY")
    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")
    mongo_uri: Optional[str] = Field(None, validation_alias="MONGO_URI")
    mongo_db: Optional[str] = Field(None, validation_alias="MONGO_DB")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True
    )

    @classmethod
    def load_config(cls, yaml_path: str = "config.yaml") -> "AppConfig":
        yaml_data = {}
        if os.path.exists(yaml_path):
            with open(yaml_path, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f) or {}

        # Resolve paths to absolute paths relative to project root
        project_root = Path(__file__).resolve().parent.parent.parent
        
        # Let's read config from yaml, and let Pydantic Settings handle environment overrides
        # We pass yaml_data. Settings loaded from environment/env_file override config.yaml
        config = cls(**yaml_data)

        # Make paths absolute
        config.paths.knowledge_base = str((project_root / config.paths.knowledge_base).resolve())
        config.paths.projects = str((project_root / config.paths.projects).resolve())
        config.paths.logs = str((project_root / config.paths.logs).resolve())
        config.memory.chroma_path = str((project_root / config.memory.chroma_path).resolve())
        
        # Ensure log, project, and chroma dirs exist
        os.makedirs(config.paths.logs, exist_ok=True)
        os.makedirs(config.paths.projects, exist_ok=True)
        os.makedirs(os.path.dirname(config.memory.chroma_path), exist_ok=True)
        
        return config

# Global config instance
settings = AppConfig.load_config()
