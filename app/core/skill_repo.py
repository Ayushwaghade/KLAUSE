import subprocess
import json
import yaml
from pathlib import Path
from loguru import logger

# Paths inside the workspace
project_root = Path(__file__).resolve().parent.parent.parent
REPO_PATH = project_root / "data" / "cloned_skills_repo"
INDEX_PATH = project_root / "data" / "skills_index.json"
RELEVANT_DOMAINS = ["engineering", "engineering-team", "research", "productivity"]

def clone_or_update_repo(repo_url: str = "https://github.com/alirezarezvani/claude-skills") -> str:
    """Clones or pulls the GitHub skills repository."""
    try:
        if REPO_PATH.exists():
            logger.info("Updating existing skills repository...")
            subprocess.run(
                ["git", "-C", str(REPO_PATH), "pull"],
                check=True, capture_output=True, timeout=60
            )
            return "Repository updated successfully."
        else:
            logger.info(f"Cloning skills repository from {repo_url}...")
            REPO_PATH.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", repo_url, str(REPO_PATH)],
                check=True, capture_output=True, timeout=120
            )
            return "Repository cloned successfully."
    except FileNotFoundError:
        logger.error("Git binary was not found on system PATH.")
        return "Error: git is not installed or not in PATH."
    except subprocess.CalledProcessError as e:
        stderr_msg = e.stderr.decode(errors="ignore").strip()
        logger.error(f"Git command failed: {stderr_msg}")
        return f"Error: git command failed — {stderr_msg[:200]}"
    except subprocess.TimeoutExpired:
        logger.error("Git operation timed out.")
        return "Error: git operation timed out."

def build_skill_index() -> list[dict]:
    """Scans for SKILL.md files, parses frontmatter, and writes the JSON index."""
    index = []
    if not REPO_PATH.exists():
        logger.warning("Skills repository folder does not exist. Cannot build index.")
        return index

    for skill_md in REPO_PATH.rglob("SKILL.md"):
        # Check domain whitelist filter based on relative paths
        try:
            rel_parts = skill_md.relative_to(REPO_PATH).parts
            if not rel_parts:
                continue
            # First folder under cloned_skills_repo represents the domain
            domain = rel_parts[0]
            if domain not in RELEVANT_DOMAINS:
                continue
        except Exception:
            continue

        try:
            content = skill_md.read_text(encoding="utf-8")
            if not content.startswith("---"):
                continue

            # Split into frontmatter and body
            parts = content.split("---", 2)
            if len(parts) < 3:
                continue
            
            frontmatter = parts[1]
            meta = yaml.safe_load(frontmatter)
            if not meta:
                continue

            index.append({
                "name": meta.get("name", skill_md.parent.name),
                "description": meta.get("description", "")[:200],
                "path": str(skill_md.resolve()),
                "domain": domain
            })
        except Exception as e:
            logger.warning(f"Skipped parsing {skill_md}: {e}")
            continue

    try:
        INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        INDEX_PATH.write_text(json.dumps(index, indent=2), encoding="utf-8")
        logger.info(f"Built skills index with {len(index)} entries.")
    except Exception as e:
        logger.error(f"Failed to write skill index: {e}")

    return index

def load_skill_full_text(skill_name: str) -> str | None:
    """Loads the full content of a skill file, capped at 6000 characters."""
    if not INDEX_PATH.exists():
        return None
    try:
        index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        skill = next((s for s in index if s["name"].strip().lower() == skill_name.strip().lower()), None)
        if not skill:
            # Try to match folder name or title substring
            skill = next((s for s in index if skill_name.strip().lower() in s["name"].strip().lower()), None)
            
        if skill and "path" in skill:
            skill_path = Path(skill["path"])
            if skill_path.exists():
                return skill_path.read_text(encoding="utf-8")[:6000]
    except Exception as e:
        logger.error(f"Failed to load skill text for '{skill_name}': {e}")
    return None

def get_skill_summaries() -> str:
    """Returns a bulleted list of skill names and descriptions for prompt classification."""
    if not INDEX_PATH.exists():
        return ""
    try:
        index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        return "\n".join(f"- {s['name']}: {s['description']}" for s in index)
    except Exception as e:
        logger.warning(f"Failed to generate skill summaries: {e}")
        return ""
