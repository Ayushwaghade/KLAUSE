import os
from pathlib import Path
from typing import Optional, Union
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class KlauseSettings(BaseModel):
    name: str = "KLAUSE"
    user_name: str = "Ayush"
    version: str = "0.1.0"
    wake_word: str = "klause"
    personality: str = "supportive"

class AISettings(BaseModel):
    provider: str = "gemini"
    gemini_model: str = "gemini-3.1-flash-lite-preview"
    nvidia_model: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    embedding_model: str = "models/embedding-001"
    max_tokens: int = 8192
    max_steps: int = 10
    
    # Model routing settings
    routing_enabled: bool = False
    fast_provider: str = "gemini"
    fast_model: str = "gemini-3.1-flash-lite-preview"
    complex_provider: str = "nvidia"
    complex_model: str = "nvidia/nemotron-3-ultra-550b-a55b"

class MemorySettings(BaseModel):
    mongo_uri: str = "mongodb://localhost:27017/"
    mongo_db: str = "klause"
    chroma_path: str = "./data/chroma"
    max_conversation_history: int = 50

class LiveTyperSettings(BaseModel):
    hotkey: str = "ctrl+shift+v"
    chunk_seconds: int = 2
    max_duration_seconds: int = 300

class LiveVoiceSettings(BaseModel):
    model: str = "gemini-3.8-live"
    voice_name: str = "Puck"
    rotation_token_limit: int = 45000
    rotation_turn_limit: int = 40
    sample_rate_in: int = 16000
    sample_rate_out: int = 24000
    barge_in: bool = True

class VoiceSettings(BaseModel):
    enabled: bool = False
    mode: str = "live"  # "live" (Gemini 3.8 Live API) or "legacy" (Whisper STT + SAPI TTS)
    trigger_mode: str = "push_to_talk"
    hotkey: str = "ctrl+space"
    stt_engine: str = "whisper"
    tts_engine: str = "sapi"
    max_spoken_sentences: int = 3
    speaking_rate: int = 0
    live: LiveVoiceSettings = LiveVoiceSettings()
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

class DesktopMacroSettings(BaseModel):
    enabled: bool = False

class AppConfig(BaseSettings):
    klause: KlauseSettings = KlauseSettings()
    ai: AISettings = AISettings()
    memory: MemorySettings = MemorySettings()
    voice: VoiceSettings = VoiceSettings()
    paths: PathSettings = PathSettings()
    state_machine: StateMachineSettings = StateMachineSettings()
    automation: AutomationSettings = AutomationSettings()
    browser: BrowserSettings = BrowserSettings()
    desktop_macro: DesktopMacroSettings = DesktopMacroSettings()
    allowed_applications: dict[str, str] = Field(default_factory=dict)
    user_name: Optional[str] = Field(None, validation_alias="USER_NAME")
    google_search_api_key: Optional[str] = Field(None, validation_alias="GOOGLE_SEARCH_API_KEY")
    google_search_cx: Optional[str] = Field(None, validation_alias="GOOGLE_SEARCH_CX")
    serper_api_key: Optional[str] = Field(None, validation_alias="SERPER_API_KEY")

    # Environment variables mapped from .env
    gemini_api_key: Optional[str] = Field(None, validation_alias="GEMINI_API_KEY")
    nvidia_api_key: Optional[str] = Field(None, validation_alias="NVIDIA_API_KEY")
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

    @property
    def effective_user_name(self) -> str:
        """Returns the user name configured in config.yaml or .env, defaulting to 'User'."""
        if self.user_name and self.user_name.strip():
            return self.user_name.strip()
        if hasattr(self, "klause") and getattr(self.klause, "user_name", None):
            return self.klause.user_name.strip()
        return "User"

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


def get_config_yaml_path(yaml_path: str = "config.yaml") -> Path:
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / yaml_path


def get_yaml_config(yaml_path: str = "config.yaml") -> dict:
    """Reads config.yaml and returns both raw text and parsed dict."""
    file_path = get_config_yaml_path(yaml_path)
    raw_yaml = ""
    parsed = {}
    if file_path.exists():
        raw_yaml = file_path.read_text(encoding="utf-8")
        parsed = yaml.safe_load(raw_yaml) or {}
    return {
        "raw_yaml": raw_yaml,
        "config": parsed,
        "effective_user_name": settings.effective_user_name
    }


def reload_config(yaml_path: str = "config.yaml") -> AppConfig:
    """Reloads config from yaml_path and updates the global settings instance in-place."""
    global settings
    file_path = get_config_yaml_path(yaml_path)
    new_settings = AppConfig.load_config(str(file_path))
    for field in new_settings.model_fields.keys():
        if hasattr(new_settings, field):
            setattr(settings, field, getattr(new_settings, field))
    return settings


def save_yaml_config(data_or_yaml: Union[dict, str], yaml_path: str = "config.yaml") -> dict:
    """Validates and persists updated configuration to config.yaml, then reloads settings."""
    file_path = get_config_yaml_path(yaml_path)
    if isinstance(data_or_yaml, str):
        parsed = yaml.safe_load(data_or_yaml)
        if not isinstance(parsed, dict):
            raise ValueError("Provided YAML must represent a key-value mapping")
        raw_yaml = data_or_yaml
        file_path.write_text(raw_yaml, encoding="utf-8")
    else:
        parsed = data_or_yaml
        raw_yaml = yaml.dump(parsed, sort_keys=False, allow_unicode=True)
        file_path.write_text(raw_yaml, encoding="utf-8")

    reload_config(yaml_path)
    return {
        "raw_yaml": raw_yaml,
        "config": parsed,
        "effective_user_name": settings.effective_user_name
    }
