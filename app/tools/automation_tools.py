import datetime
from typing import Optional, Callable, Dict, Any
from loguru import logger
import pytz

from app.tools.base import tool, tool_registry
from app.automation.scheduler import scheduler
from app.automation.rule_engine import rule_engine, RuleModel
from app.automation.event_engine import EventType


@tool(
    name="schedule_add_cron",
    description="Registers a recurring cron job that runs a terminal command or workflow. Cron expressions should have 5 fields (minute hour day month day_of_week). Arguments: job_id (str), command (str), cron_expression (str).",
    destructive=False
)
def schedule_add_cron(job_id: str, command: str, cron_expression: str) -> str:
    """Add a recurring cron job."""
    return scheduler.add_cron_job(job_id, command, cron_expression)


@tool(
    name="schedule_add_one_shot",
    description="Schedules a one-shot terminal command or workflow at a specific future UTC date and time. Date format should be YYYY-MM-DD HH:MM:SS. Arguments: job_id (str), command (str), run_at_utc (str).",
    destructive=False
)
def schedule_add_one_shot(job_id: str, command: str, run_at_utc: str) -> str:
    """Schedule a one-shot job."""
    try:
        dt = datetime.datetime.strptime(run_at_utc, "%Y-%m-%d %H:%M:%S")
        dt = pytz.utc.localize(dt)
    except Exception as e:
        return f"Error: Invalid date format '{run_at_utc}'. Expected 'YYYY-MM-DD HH:MM:SS'. Error: {e}"
        
    return scheduler.add_one_shot_job(job_id, command, dt)


@tool(
    name="schedule_pause",
    description="Temporarily pauses a scheduled job. Arguments: job_id (str).",
    destructive=False
)
def schedule_pause(job_id: str) -> str:
    """Pause a scheduled job."""
    if scheduler.pause_job(job_id):
        return f"Successfully paused scheduled job '{job_id}'."
    return f"Error: Failed to pause job '{job_id}' (job might not exist)."


@tool(
    name="schedule_resume",
    description="Resumes a paused scheduled job. Arguments: job_id (str).",
    destructive=False
)
def schedule_resume(job_id: str) -> str:
    """Resume a scheduled job."""
    if scheduler.resume_job(job_id):
        return f"Successfully resumed scheduled job '{job_id}'."
    return f"Error: Failed to resume job '{job_id}' (job might not exist)."


@tool(
    name="schedule_list",
    description="Lists all currently active and paused scheduled jobs, showing their local timezone runtimes. No arguments required.",
    destructive=False
)
def schedule_list() -> str:
    """List scheduled jobs."""
    jobs = scheduler.list_jobs()
    if not jobs:
        return "Observation: No scheduled jobs found."
        
    lines = ["Active Scheduled Jobs:"]
    for j in jobs:
        lines.append(
            f"- Job ID: {j['job_id']} | Command: '{j['command']}' | "
            f"Trigger: {j['trigger']} | Next Run: {j['next_run_time_local']}"
        )
    return "\n".join(lines)


@tool(
    name="schedule_remove",
    description="Permanently deletes a scheduled job. Arguments: job_id (str).",
    destructive=True
)
def schedule_remove(job_id: str) -> str:
    """Remove a scheduled job."""
    if scheduler.remove_job(job_id):
        return f"Successfully removed scheduled job '{job_id}'."
    return f"Error: Failed to remove job '{job_id}' (job might not exist)."


@tool(
    name="rule_add",
    description=(
        "Registers an event-driven automation rule (e.g. executing a tool or triggering KLAUSE when a window is focused). "
        "Arguments: rule_id (str), event_type (str), action_type (str: 'tool_call'|'trigger_react'), "
        "action_payload (dict), filter_pattern (str - optional regex to match title/path/command)."
    ),
    destructive=True
)
def rule_add(
    rule_id: str,
    event_type: str,
    action_type: str,
    action_payload: Dict[str, Any],
    filter_pattern: Optional[str] = None,
    confirm_fn: Optional[Callable[[str], bool]] = None
) -> str:
    """Add an event-driven automation rule with security validations."""
    # 1. Validate event_type matching EventType name
    et_names = [et.name.lower() for et in EventType] + [et.value.lower() for et in EventType]
    if event_type.lower() not in et_names:
        valid_options = ", ".join(et.name for et in EventType)
        return f"Error: Invalid event_type '{event_type}'. Valid types are: {valid_options}."

    # Normalize event_type to match EventType value
    normalized_et = ""
    for et in EventType:
        if event_type.lower() in (et.name.lower(), et.value.lower()):
            normalized_et = et.value
            break

    # 2. Validate action_type
    if action_type not in ("tool_call", "trigger_react"):
        return "Error: Invalid action_type. Must be 'tool_call' or 'trigger_react'."

    # 3. Security Guard check for destructive actions
    if action_type == "tool_call":
        tool_name = action_payload.get("tool_name")
        if not tool_name:
            return "Error: action_payload must contain 'tool_name' for action_type 'tool_call'."
            
        if tool_name in tool_registry and tool_registry[tool_name].destructive:
            if confirm_fn:
                approved = confirm_fn(
                    f"Security Guard: Rule '{rule_id}' attempts to execute destructive tool '{tool_name}'. "
                    f"Allow registration of this rule?"
                )
                if not approved:
                    return "Rule registration cancelled by user (destructive tool guard)."
            else:
                return "Error: Cannot register rule executing destructive tool without user confirmation context."

    # Assemble rule model
    try:
        rule = RuleModel(
            rule_id=rule_id,
            event_type=normalized_et,
            filter_pattern=filter_pattern,
            action_type=action_type,
            action_payload=action_payload,
            enabled=True
        )
    except Exception as e:
        return f"Error: Schema validation failed: {e}"

    return rule_engine.add_rule(rule)


@tool(
    name="rule_list",
    description="Lists all registered automation rules. No arguments required.",
    destructive=False
)
def rule_list() -> str:
    """List automation rules."""
    rules = rule_engine.rules
    if not rules:
        return "Observation: No automation rules registered."
        
    lines = ["Registered Automation Rules:"]
    for r in rules:
        status = "enabled" if r.enabled else "disabled"
        filter_str = f" | Filter: '{r.filter_pattern}'" if r.filter_pattern else ""
        lines.append(
            f"- Rule ID: {r.rule_id} ({status}) | Event: {r.event_type}{filter_str} | "
            f"Action: {r.action_type} -> {r.action_payload}"
        )
    return "\n".join(lines)


@tool(
    name="rule_remove",
    description="Deletes an automation rule by its ID. Arguments: rule_id (str).",
    destructive=True
)
def rule_remove(rule_id: str) -> str:
    """Remove an automation rule."""
    if rule_engine.remove_rule(rule_id):
        return f"Successfully removed rule '{rule_id}'."
    return f"Error: Failed to remove rule '{rule_id}' (rule might not exist)."
