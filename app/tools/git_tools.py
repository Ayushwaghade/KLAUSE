import subprocess
from loguru import logger
from app.tools.base import tool
from app.core.context import context

MAX_OUTPUT_LENGTH = 4000

def _truncate(output: str) -> str:
    """
    Truncates output strings to a maximum character length for Gemini context safety.
    """
    if len(output) > MAX_OUTPUT_LENGTH:
        return output[:MAX_OUTPUT_LENGTH] + f"\n... [truncated, {len(output)} chars total]"
    return output

def _run_git_cmd(args: list[str]) -> str:
    """
    Run a git command in the active project directory, returning output.
    """
    cwd = context.current_project_path
    if not cwd:
        return "Error: No project context is active. Please open a project first."
        
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=15,
            cwd=cwd
        )
        if result.returncode != 0:
            err = result.stderr or ""
            return f"Error running git {' '.join(args)}:\n{err}"
            
        out = result.stdout or ""
        if not out:
            return "Command completed successfully with no output."
        return _truncate(out)
    except subprocess.TimeoutExpired:
        return "Error: Git command timed out after 15 seconds."
    except Exception as e:
        return f"Error: Failed to execute git command: {e}"

@tool(
    name="git_status",
    description="Shows the status of files in the active git repository. Returns a concise list of modifications.",
    destructive=False
)
def git_status() -> str:
    """
    Retrieves the git status of the active project.
    """
    logger.info("Git Tool: Querying status.")
    res = _run_git_cmd(["status", "-s"])
    # If the folder is not a git repo, subprocess might return non-zero
    if "Error running git status -s" in res:
        return "Observation: Directory is not initialized as a Git repository, or git is not installed."
    return f"Observation:\n{res}"


@tool(
    name="git_diff",
    description="Shows uncommitted diffs. Argument: file_path (str, optional - to diff a specific file).",
    destructive=False
)
def git_diff(file_path: str = None) -> str:
    """
    Shows uncommitted diffs inside the active project.
    """
    logger.info(f"Git Tool: Querying diff for file_path: {file_path}")
    args = ["diff"]
    if file_path:
        args += ["--", file_path]
    res = _run_git_cmd(args)
    return f"Observation:\n{res}"


@tool(
    name="git_log",
    description="Shows the recent commit logs. Arguments: limit (int, default=5), oneline (bool, default=True).",
    destructive=False
)
def git_log(limit: int = 5, oneline: bool = True) -> str:
    """
    Shows the git log of the active project.
    """
    logger.info(f"Git Tool: Querying log (limit={limit}, oneline={oneline}).")
    args = ["log", f"-n {limit}"]
    if oneline:
        args += ["--oneline"]
    res = _run_git_cmd(args)
    return f"Observation:\n{res}"


@tool(
    name="git_add",
    description="Stages changes to files in the git repository. Argument: paths (list of str, optional - if empty or None, stages all changes using '.').",
    destructive=True
)
def git_add(paths: list[str] = None) -> str:
    """
    Stages file changes inside the active project directory.
    """
    logger.info(f"Git Tool: Staging paths: {paths}")
    args = ["add"]
    if paths:
        # Extend arguments list with specific file paths
        args += paths
    else:
        args += ["."]
    res = _run_git_cmd(args)
    return f"Observation: staged changes. Details: {res}"


@tool(
    name="git_commit",
    description="Commits staged files in the git repository. Argument: message (str). Note: Stages nothing; files must already be added.",
    destructive=True
)
def git_commit(message: str) -> str:
    """
    Commits staged changes. Does NOT perform auto-staging.
    """
    logger.info(f"Git Tool: Committing with message: {message}")
    res = _run_git_cmd(["commit", "-m", message])
    return f"Observation: committed changes. Details: {res}"
