import pytest
import subprocess
from unittest.mock import MagicMock, patch
from app.core.context import context
from app.tools.terminal_tools import (
    run_terminal_command,
    run_terminal_command_async,
    list_running_commands,
    kill_running_command,
    running_processes
)
from app.tools.git_tools import git_status, git_diff, git_log, git_add, git_commit

@pytest.fixture(autouse=True)
def reset_context_and_registry():
    """
    Reset singleton context and background process registry before each test.
    """
    context.current_project_path = None
    running_processes.clear()
    yield
    context.current_project_path = None
    running_processes.clear()

def test_git_status_fails_without_project_context():
    """
    Verify that git_status returns a clear context-error when project path is not set.
    """
    res = git_status()
    assert "No project context" in res

def test_run_terminal_command_fails_without_project_context():
    """
    Verify that run_terminal_command returns a clear context-error when project path is not set.
    """
    res = run_terminal_command("echo test")
    assert "No project context" in res

def test_run_terminal_command_blocklist():
    """
    Verify blocklist safety intercepts dangerous commands.
    """
    context.current_project_path = "C:\\dummy_project"
    res = run_terminal_command("rm -rf /usr/local")
    assert "blocked due to security restrictions" in res

@patch("subprocess.run")
def test_run_terminal_command_timeout(mock_run):
    """
    Verify timeouts are handled gracefully.
    """
    context.current_project_path = "C:\\dummy_project"
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="sleep 100", timeout=30)
    
    res = run_terminal_command("sleep 100")
    assert "timed out after 30 seconds" in res

@patch("subprocess.run")
def test_git_status_success(mock_run):
    """
    Verify git_status succeeds with mocked subprocess execution output.
    """
    context.current_project_path = "C:\\dummy_project"
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = " M app/core/brain.py\n?? tests/test_dev_tools.py"
    mock_process.stderr = ""
    mock_run.return_value = mock_process
    
    res = git_status()
    assert "Observation:" in res
    assert "M app/core/brain.py" in res
    assert "tests/test_dev_tools.py" in res

@patch("subprocess.run")
def test_git_diff_success(mock_run):
    """
    Verify git_diff returns uncommitted changes correctly.
    """
    context.current_project_path = "C:\\dummy_project"
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = "-oldline\n+newline"
    mock_run.return_value = mock_process
    
    res = git_diff()
    assert "newline" in res

@patch("subprocess.run")
def test_git_commit_no_autostage(mock_run):
    """
    Verify git_commit does not stage files.
    """
    context.current_project_path = "C:\\dummy_project"
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = "[main abcd123] Test commit"
    mock_run.return_value = mock_process
    
    res = git_commit("Test commit")
    # Verify git commit was called, not git add
    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    assert "commit" in args[0]
    assert "-m" in args[0]
    assert "git add" not in args[0]

def test_list_background_processes_cleanup():
    """
    Verify list_running_commands prunes dead background processes from registry.
    """
    # Register a running mock process
    mock_proc_alive = MagicMock()
    mock_proc_alive.poll.return_value = None  # None = Running
    
    # Register a dead mock process
    mock_proc_dead = MagicMock()
    mock_proc_dead.poll.return_value = 0  # 0 = Completed
    mock_proc_dead.returncode = 0
    
    running_processes[1001] = {
        "process": mock_proc_alive,
        "command": "python -m http.server",
        "started_at": "2026-06-28 12:00:00"
    }
    running_processes[1002] = {
        "process": mock_proc_dead,
        "command": "echo done",
        "started_at": "2026-06-28 12:00:00"
    }
    
    res = list_running_commands()
    
    # Dead process should be pruned
    assert 1002 not in running_processes
    assert 1001 in running_processes
    assert "http.server" in res
    assert "echo done" not in res
