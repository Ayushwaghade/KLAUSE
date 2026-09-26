from pathlib import Path
import os
import yaml
from typing import Literal, Dict, Tuple, ClassVar
from pydantic import BaseModel, Field
from loguru import logger

# NOTE: DispositionConfig governs SOFT preferences only (tone, style suggestions).
# It has no Dispatcher-level enforcement. Anything safety-relevant (write permissions,
# destructive action gating) belongs in rules.md + Dispatcher checks, never here.

class ProactivitySettings(BaseModel):
    flag_code_smells: bool = Field(True, description="Point out code smells in modified or read files even if not explicitly asked.")
    suggest_unit_tests: bool = Field(True, description="Proactively suggest adding or updating unit tests when editing logic.")
    explain_architectural_decisions: bool = Field(True, description="Provide brief design notes justifying why a change is structured a certain way.")

class StyleSettings(BaseModel):
    code_philosophy: Literal["explicit_over_clever", "clever_hacks"] = Field("explicit_over_clever", description="Preferred programming style.")
    formatting_strictness: Literal["strict", "balanced", "lax"] = Field("balanced", description="Level of coding style enforcement.")

class PersonalitySettings(BaseModel):
    tone: Literal["hacker", "architect", "minimalist", "supportive"] = Field("hacker", description="Tone of responses.")
    brevity: Literal["concise", "verbose"] = Field("concise", description="Brevity level.")

class DispositionConfig(BaseModel):
    proactivity: ProactivitySettings = ProactivitySettings()
    style: StyleSettings = StyleSettings()
    personality: PersonalitySettings = PersonalitySettings()

    # Cache format: cache_key -> (global_mtime, ws_mtime, loaded_config)
    _cache: ClassVar[Dict[str, Tuple[float | None, float | None, "DispositionConfig"]]] = {}

    @classmethod
    def _deep_merge(cls, dict1: dict, dict2: dict) -> dict:
        merged = dict1.copy()
        for k, v in dict2.items():
            if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
                merged[k] = cls._deep_merge(merged[k], v)
            else:
                merged[k] = v
        return merged

    @classmethod
    def _get_file_mtime(cls, path: Path) -> float | None:
        try:
            return path.stat().st_mtime if path.exists() else None
        except Exception:
            return None

    @classmethod
    def _load_yaml_dict(cls, path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to parse YAML file at {path}: {e}")
            return {}

    @classmethod
    def load_from_workspace(cls, workspace_path: str | None = None) -> "DispositionConfig":
        cache_key = workspace_path or "global_only"
        
        project_root = Path(__file__).resolve().parent.parent.parent
        global_file = project_root / "disposition.yaml"
        
        ws_file = None
        if workspace_path:
            ws_file = Path(workspace_path) / ".agents" / "disposition.yaml"

        # Check modification times
        global_mtime = cls._get_file_mtime(global_file)
        ws_mtime = cls._get_file_mtime(ws_file) if ws_file else None

        # Check cache
        if cache_key in cls._cache:
            cached_global_mtime, cached_ws_mtime, cached_config = cls._cache[cache_key]
            if cached_global_mtime == global_mtime and cached_ws_mtime == ws_mtime:
                return cached_config

        # Load and merge dictionaries
        global_data = cls._load_yaml_dict(global_file)
        ws_data = cls._load_yaml_dict(ws_file) if ws_file else {}
        merged_data = cls._deep_merge(global_data, ws_data)

        # Parse into Pydantic model
        try:
            config = cls(**merged_data)
        except Exception as e:
            logger.warning(f"Validation error loading merged disposition data: {e}. Falling back to default settings.")
            config = cls()

        # Update cache
        cls._cache[cache_key] = (global_mtime, ws_mtime, config)
        return config
