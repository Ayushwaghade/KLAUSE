import datetime
import os
import pytz
import re
from typing import List, Dict, Any, Optional
from loguru import logger
from pymongo import MongoClient

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from app.config.config import settings
from app.automation.event_engine import Event, EventType, event_engine

try:
    import tzlocal
    DEFAULT_LOCAL_TZ = tzlocal.get_localzone()
except Exception:
    DEFAULT_LOCAL_TZ = pytz.timezone("Asia/Kolkata")


def human_readable_cron(cron_expr: str) -> str:
    """Converts a standard 5-part cron expression to a user-friendly English string."""
    if not cron_expr:
        return "Unscheduled"
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        return cron_expr
    minute, hour, dom, month, dow = parts

    days_map = {
        "0": "Sunday", "1": "Monday", "2": "Tuesday", "3": "Wednesday",
        "4": "Thursday", "5": "Friday", "6": "Saturday", "7": "Sunday"
    }

    def fmt_time(h_str, m_str):
        try:
            h = int(h_str)
            m = int(m_str)
            period = "PM" if h >= 12 else "AM"
            h12 = 12 if (h % 12 == 0) else (h % 12)
            return f"{h12}:{m:02d} {period}"
        except Exception:
            return f"{h_str}:{m_str}"

    if minute.startswith("*/") and hour == "*" and dom == "*" and month == "*" and dow == "*":
        return f"Every {minute[2:]} minutes"
    if minute == "*" and hour == "*" and dom == "*" and month == "*" and dow == "*":
        return "Every minute"
    if minute == "0" and hour == "*" and dom == "*" and month == "*" and dow == "*":
        return "Every hour on the hour"
    if minute == "0" and hour.startswith("*/") and dom == "*" and month == "*" and dow == "*":
        return f"Every {hour[2:]} hours"
    if "*" not in minute and "/" not in minute and "*" not in hour and "/" not in hour and dom == "*" and month == "*" and dow == "*":
        return f"Daily at {fmt_time(hour, minute)}"
    if "*" not in minute and "*" not in hour and dom == "*" and month == "*" and dow in ("1-5", "mon-fri", "MON-FRI"):
        return f"Every weekday (Mon-Fri) at {fmt_time(hour, minute)}"
    if "*" not in minute and "*" not in hour and dom == "*" and month == "*" and dow in days_map:
        return f"Every {days_map[dow]} at {fmt_time(hour, minute)}"

    return cron_expr


# Helper job function that runs when trigger fires
def _scheduled_job_executor(job_id: str, command: str):
    logger.info(f"Scheduled job '{job_id}' triggered. Executing command: '{command}'")
    
    # 1. Update task status to in_progress in db.tasks
    try:
        from app.memory.memory_manager import get_memory_manager
        mgr = get_memory_manager()
        mgr.db.tasks.update_one(
            {"job_id": job_id, "type": "scheduled"},
            {"$set": {"status": "in_progress", "last_run_started": datetime.datetime.utcnow()}}
        )
    except Exception as e:
        logger.debug(f"Could not update task to in_progress: {e}")

    # 2. Emit CRON_TRIGGERED event to EventEngine (in case rules bind to it)
    event_engine.publish(Event(
        event_type=EventType.CRON_TRIGGERED,
        source="scheduler",
        data={"job_id": job_id, "command": command}
    ))
    
    # 3. Run the actual tool or command via a separate thread
    import threading
    threading.Thread(
        target=_async_command_runner,
        args=(job_id, command),
        daemon=True
    ).start()


def _async_command_runner(job_id: str, command: str):
    from app.core.dispatcher import Dispatcher
    from app.core.context import context
    from app.memory.memory_manager import get_memory_manager
    
    # If KLAUSE is currently busy in an active turn, queue the rule prompt or wait
    if context.session_id and context.session_id != "default_session" and getattr(context, "_active_turn", False):
        logger.info(f"KLAUSE is busy. Execution of scheduled command '{command}' will queue or run silently.")
        
    dispatcher = Dispatcher()
    success = False
    result_text = ""
    error_text = None

    try:
        # Run terminal command (if project context exists), otherwise fallback to subprocess execution
        if context.current_project_path:
            observation = dispatcher.execute("run_terminal_command", {"command": command})
            success = observation.success
            result_text = str(observation.result or "")
            error_text = str(observation.error) if observation.error else None
            logger.info(f"Scheduled job '{job_id}' shell execution success: {success}")
        else:
            logger.info(f"No active project context for scheduled job '{job_id}'. Executing command directly via subprocess.")
            import subprocess
            res = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
            success = (res.returncode == 0)
            result_text = (res.stdout or res.stderr or "").strip()
            if not success:
                error_text = res.stderr.strip()
    except Exception as e:
        logger.error(f"Failed to execute command for scheduled job '{job_id}': {e}")
        success = False
        error_text = str(e)
        result_text = f"Execution error: {e}"

    # Sync task completion in MongoDB
    try:
        mgr = get_memory_manager()
        now = datetime.datetime.utcnow()

        # Update the main scheduled task back to 'pending' (ready for next run)
        mgr.db.tasks.update_one(
            {"job_id": job_id, "type": "scheduled"},
            {"$set": {
                "status": "pending",
                "last_run": now,
                "last_success": success,
                "last_result": result_text[:500] if result_text else (error_text or "Completed"),
                "updated_at": now
            }}
        )

        # Record this run as a completed task so it appears in the 'Done' column of Kanban
        run_title = f"Run: {job_id} ({datetime.datetime.now().strftime('%H:%M:%S')})"
        run_desc = f"Command: `{command}`\nResult: {result_text[:250] if result_text else (error_text or 'Done')}"
        mgr.db.tasks.insert_one({
            "project_id": "global",
            "title": run_title,
            "description": run_desc,
            "status": "done",
            "priority": "low" if success else "high",
            "type": "execution_log",
            "job_id": job_id,
            "command": command,
            "success": success,
            "created_at": now
        })
    except Exception as me:
        logger.warning(f"Failed to record scheduled execution in tasks collection: {me}")


class SchedulerWrapper:
    """
    Persistent background job scheduler using APScheduler and MongoDBJobStore.
    """
    def __init__(self):
        self.scheduler: Optional[BackgroundScheduler] = None
        self._lock = False
        self.local_tz = DEFAULT_LOCAL_TZ
        
    def start(self):
        if self.scheduler and self.scheduler.running:
            return
            
        mongo_uri = settings.memory.mongo_uri or "mongodb://localhost:27017/"
        mongo_db = settings.memory.mongo_db or "klause"
        
        logger.info(f"Initializing Scheduler with MongoDBJobStore on database '{mongo_db}'...")
        
        try:
            client = MongoClient(mongo_uri)
            jobstores = {
                'default': MongoDBJobStore(database=mongo_db, collection='scheduled_jobs', client=client)
            }
            
            self.scheduler = BackgroundScheduler(
                jobstores=jobstores,
                timezone=self.local_tz
            )
            self.scheduler.start()
            logger.info("Scheduler started successfully.")
        except Exception as e:
            logger.error(f"Failed to start Scheduler: {e}. Falling back to MemoryJobStore.")
            self.scheduler = BackgroundScheduler(timezone=self.local_tz)
            self.scheduler.start()

    def stop(self):
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler shut down cleanly.")

    def _sync_task_to_db(self, job_id: str, command: str, cron_expr: str, trigger=None):
        """Upserts a scheduled task record in MongoDB tasks collection so it appears on the Kanban Task page."""
        try:
            from app.memory.memory_manager import get_memory_manager
            mgr = get_memory_manager()
            human_desc = human_readable_cron(cron_expr)
            
            next_run_str = "Scheduled"
            if trigger:
                try:
                    next_fire = trigger.get_next_fire_time(None, datetime.datetime.now(self.local_tz))
                    if next_fire:
                        next_run_str = next_fire.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    pass

            mgr.db.tasks.update_one(
                {"job_id": job_id, "type": "scheduled"},
                {"$set": {
                    "project_id": "global",
                    "title": f"[Scheduled] {job_id}",
                    "description": f"Command: `{command}` | Schedule: {human_desc}",
                    "status": "pending",
                    "priority": "medium",
                    "type": "scheduled",
                    "job_id": job_id,
                    "command": command,
                    "schedule": cron_expr,
                    "human_schedule": human_desc,
                    "next_run": next_run_str,
                    "updated_at": datetime.datetime.utcnow()
                }, "$setOnInsert": {
                    "created_at": datetime.datetime.utcnow()
                }},
                upsert=True
            )
        except Exception as e:
            logger.warning(f"Failed to sync task '{job_id}' to db: {e}")

    def add_cron_job(self, job_id: str, command: str, cron_expr: str) -> str:
        """Adds a recurring cron job. Validates expression first."""
        if not self.scheduler:
            return "Error: Scheduler is not running."
            
        # Cron validation check
        from croniter import croniter
        try:
            base_time = datetime.datetime.now(self.local_tz)
            croniter(cron_expr, base_time)
        except Exception as ce:
            return f"Error: Invalid cron expression '{cron_expr}': {ce}"

        try:
            # If job already exists, remove it first to allow updates
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                
            trigger = CronTrigger.from_crontab(cron_expr, timezone=self.local_tz)
            self.scheduler.add_job(
                _scheduled_job_executor,
                trigger=trigger,
                args=[job_id, command],
                id=job_id,
                replace_existing=True
            )
            
            # Upsert into db.tasks
            self._sync_task_to_db(job_id, command, cron_expr, trigger)
            
            human_desc = human_readable_cron(cron_expr)
            return f"Successfully added scheduled task '{job_id}' ({human_desc})."
        except Exception as e:
            logger.error(f"Failed to add cron job: {e}")
            return f"Error adding cron job: {e}"

    def add_one_shot_job(self, job_id: str, command: str, run_at_utc: datetime.datetime) -> str:
        """Adds a one-shot job scheduled at a specific timestamp."""
        if not self.scheduler:
            return "Error: Scheduler is not running."
            
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        if run_at_utc <= now_utc:
            return f"Error: Scheduled time '{run_at_utc}' must be in the future (current UTC: {now_utc})."

        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                
            trigger = DateTrigger(run_date=run_at_utc, timezone=self.local_tz)
            self.scheduler.add_job(
                _scheduled_job_executor,
                trigger=trigger,
                args=[job_id, command],
                id=job_id,
                replace_existing=True
            )
            
            # Upsert into db.tasks
            self._sync_task_to_db(job_id, command, f"One-time at {run_at_utc.strftime('%Y-%m-%d %H:%M:%S')}", trigger)
            
            return f"Successfully scheduled one-shot job '{job_id}' at {run_at_utc} UTC."
        except Exception as e:
            logger.error(f"Failed to schedule job: {e}")
            return f"Error scheduling job: {e}"

    def run_job_now(self, job_id: str) -> bool:
        """Immediately executes a scheduled job on-demand in a background thread."""
        if not self.scheduler:
            return False
        job = self.scheduler.get_job(job_id)
        if not job:
            return False
        command = job.args[1] if len(job.args) > 1 else ""
        import threading
        threading.Thread(target=_scheduled_job_executor, args=(job_id, command), daemon=True).start()
        return True

    def list_jobs(self) -> List[Dict[str, Any]]:
        """Lists active scheduled jobs, converting runtime to local timezone with plain English schedule."""
        if not self.scheduler:
            return []

        local_tz = self.local_tz
        try:
            import tzlocal
            local_tz = tzlocal.get_localzone()
        except Exception:
            pass

        jobs_list = []
        for job in self.scheduler.get_jobs():
            # Get next run time
            next_run = job.next_run_time
            if next_run:
                # Convert to local timezone
                next_run_local = next_run.astimezone(local_tz)
                next_run_str = next_run_local.strftime("%Y-%m-%d %H:%M:%S %Z")
            else:
                next_run_str = "paused / idle"
                
            trigger_str = str(job.trigger)
            human_desc = "Scheduled"

            # If it's a CronTrigger, reconstruct the 5-part cron expression and convert to human English
            if isinstance(job.trigger, CronTrigger):
                try:
                    fd = {f.name: str(f) for f in job.trigger.fields}
                    cron_raw = f"{fd.get('minute', '*')} {fd.get('hour', '*')} {fd.get('day', '*')} {fd.get('month', '*')} {fd.get('day_of_week', '*')}"
                    human_desc = human_readable_cron(cron_raw)
                except Exception:
                    human_desc = trigger_str
            elif isinstance(job.trigger, DateTrigger):
                human_desc = f"One-shot at {next_run_str}"

            jobs_list.append({
                "job_id": job.id,
                "command": job.args[1] if len(job.args) > 1 else "",
                "trigger": trigger_str,
                "human_schedule": human_desc,
                "next_run_time_local": next_run_str,
                "timezone": getattr(self.local_tz, "zone", str(self.local_tz))
            })
        return jobs_list

    def remove_job(self, job_id: str) -> bool:
        if not self.scheduler:
            return False
        removed = False
        try:
            self.scheduler.remove_job(job_id)
            removed = True
        except Exception:
            pass
        # Remove from db.tasks collection as well
        try:
            from app.memory.memory_manager import get_memory_manager
            mgr = get_memory_manager()
            mgr.db.tasks.delete_many({"job_id": job_id})
            removed = True
        except Exception as e:
            logger.warning(f"Failed to remove task from db: {e}")
        return removed

    def pause_job(self, job_id: str) -> bool:
        if not self.scheduler:
            return False
        try:
            self.scheduler.pause_job(job_id)
            return True
        except Exception:
            return False

    def resume_job(self, job_id: str) -> bool:
        if not self.scheduler:
            return False
        try:
            self.scheduler.resume_job(job_id)
            return True
        except Exception:
            return False


# Singleton instance
scheduler = SchedulerWrapper()
