import subprocess
import os
import datetime
from loguru import logger
from app.tools.base import tool
from app.core.context import context

MAX_OUTPUT_LENGTH = 4000
BLOCKLIST = ["rm -rf /", "format c:", "del /s", "del /f", "rmdir /s", "mkfs", "dd if="]

# Global background process registry
# { pid (int): { "process": Popen, "command": str, "started_at": str } }
running_processes = {}

def _truncate(output: str) -> str:
    """
    Truncates output strings to a maximum character length for Gemini context safety.
    """
    if len(output) > MAX_OUTPUT_LENGTH:
        return output[:MAX_OUTPUT_LENGTH] + f"\n... [truncated, {len(output)} chars total]"
    return output

def _is_blocked(command: str) -> bool:
    """
    Validates command against the dangerous commands blocklist.
    """
    cmd_lower = command.lower()
    for pattern in BLOCKLIST:
        if pattern in cmd_lower:
            return True
    return False

@tool(
    name="run_terminal_command",
    description="Runs a shell command synchronously inside the active project directory. Argument: command (str).",
    destructive=True
)
def run_terminal_command(command: str) -> str:
    """
    Runs a terminal command synchronously. Requires active project context and enforces safety policies.
    """
    cwd = context.current_project_path
    if not cwd:
        return "Error: No project context is active. Please open a project first."

    if _is_blocked(command):
        logger.warning(f"Command blocked due to safety policy: {command}")
        return "Error: Command blocked due to security restrictions (high-risk pattern detected)."

    logger.info(f"Terminal Tool: Running command synchronously: {command} in CWD: {cwd}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=cwd
        )
        stdout_str = result.stdout or ""
        stderr_str = result.stderr or ""
        
        output = ""
        if stdout_str:
            output += f"STDOUT:\n{stdout_str}\n"
        if stderr_str:
            output += f"STDERR:\n{stderr_str}\n"
            
        if not output:
            output = "Command completed with no terminal output."
            
        return _truncate(output)
    except subprocess.TimeoutExpired:
        logger.warning(f"Command timed out: {command}")
        return "Error: Command timed out after 30 seconds. For long-running servers/tasks, please use run_terminal_command_async instead."
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        return f"Error: Failed to run command: {e}"


@tool(
    name="run_terminal_command_async",
    description="Launches a shell command in the background (asynchronous) inside the active project directory. Argument: command (str).",
    destructive=True
)
def run_terminal_command_async(command: str) -> str:
    """
    Launches a command in the background and registers its PID.
    """
    cwd = context.current_project_path
    if not cwd:
        return "Error: No project context is active. Please open a project first."

    if _is_blocked(command):
        logger.warning(f"Async command blocked due to safety policy: {command}")
        return "Error: Command blocked due to security restrictions (high-risk pattern detected)."

    logger.info(f"Terminal Tool: Running command asynchronously: {command} in CWD: {cwd}")
    try:
        # Start background process
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        pid = process.pid
        running_processes[pid] = {
            "process": process,
            "command": command,
            "started_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        logger.info(f"Command launched in background with PID: {pid}")
        return f"Observation: Command successfully started in background with PID: {pid}."
    except Exception as e:
        logger.error(f"Failed to launch command in background: {e}")
        return f"Error: Failed to run background command: {e}"


@tool(
    name="list_running_commands",
    description="Lists all active background terminal commands launched by KLAUSE.",
    destructive=False
)
def list_running_commands() -> str:
    """
    Inspects running processes, purges dead background tasks, and reports alive ones.
    """
    logger.info("Terminal Tool: Listing active background processes.")
    alive = {}
    
    # Check status of each tracked process
    for pid, info in running_processes.items():
        proc = info["process"]
        # poll() returns None if process is running
        if proc.poll() is None:
            alive[pid] = info
        else:
            logger.info(f"Pruning dead background process with PID {pid} (Exit code: {proc.returncode})")
            
    # Swap global dict with alive processes
    running_processes.clear()
    running_processes.update(alive)
    
    if not running_processes:
        return "Observation: No background commands are currently running."
        
    lines = ["Observation: Currently running background commands:"]
    for pid, info in running_processes.items():
        lines.append(f"- PID: {pid} | Command: '{info['command']}' | Started: {info['started_at']}")
        
    return "\n".join(lines)


@tool(
    name="kill_running_command",
    description="Terminates an active background command. Argument: pid (int).",
    destructive=True
)
def kill_running_command(pid: int) -> str:
    """
    Terminates a registered background process by PID.
    """
    logger.info(f"Terminal Tool: Terminating PID: {pid}")
    if pid not in running_processes:
        return f"Error: PID {pid} is not registered or is no longer running."
        
    try:
        info = running_processes[pid]
        proc = info["process"]
        # Terminate process tree
        proc.terminate()
        # Wait up to 2 seconds for clean exit, otherwise force kill
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            
        del running_processes[pid]
        return f"Observation: Process with PID {pid} has been terminated."
    except Exception as e:
        logger.error(f"Failed to terminate process {pid}: {e}")
        return f"Error: Failed to terminate process: {e}"
