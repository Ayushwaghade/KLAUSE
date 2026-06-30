from app.tools.base import tool
from app.core import skill_repo

@tool(
    name="import_skills_repo",
    description="Clones or updates the GitHub skills repository (claude-skills) and rebuilds the metadata index. Arguments: repo_url (str - optional)."
)
def import_skills_repo(repo_url: str = "https://github.com/alirezarezvani/claude-skills") -> str:
    """Import and index expert skills repository."""
    result = skill_repo.clone_or_update_repo(repo_url)
    if "Error" in result:
        return result
    index = skill_repo.build_skill_index()
    return f"Observation: {result} Indexed {len(index)} relevant domain skills."

@tool(
    name="load_skill",
    description="Loads the complete instruction guide for a specific expert skill. Arguments: skill_name (str)."
)
def load_skill(skill_name: str) -> str:
    """Load skill instructions."""
    content = skill_repo.load_skill_full_text(skill_name)
    if not content:
        return f"Observation: No expert skill found matching '{skill_name}'. Use list_skills to see available options."
    return f"Observation: Loaded expert skill '{skill_name}' instructions:\n\n{content}"

@tool(
    name="list_skills",
    description="Lists all currently available expert skills with their descriptions. Argument: none."
)
def list_skills() -> str:
    """List expert skills."""
    summaries = skill_repo.get_skill_summaries()
    if not summaries.strip():
        return "Observation: No expert skills indexed. Please run import_skills_repo first."
    return f"Observation: Available expert skills:\n\n{summaries}"
