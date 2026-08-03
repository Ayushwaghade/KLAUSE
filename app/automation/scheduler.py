import datetime
import os
import pytz
from typing import List, Dict, Any, Optional
from loguru import logger
from pymongo import MongoClient

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from app.config.config import settings
from app.automation.event_engine import Event, EventType, event_engine

# Helper job function that runs when trigger fires
def _scheduled_job_executor(job_id: str, command: str):
    logger.info(f"Scheduled job '{job_id}' triggered. Executing command: '{command}'")
    
    # 1. Emit CRON_TRIGGERED event to EventEngine (in case rules bind to it)
    event_engine.publish(Event(
        event_type=EventType.CRON_TRIGGERED,
        source="scheduler",
        data={"job_id": job_id, "command": command}
    ))
    
    # 2. Run the actual tool or command
    # For safety, execute commands via a separate thread utilizing KLAUSE Dispatcher
    import threading
    threading.Thread(
        target=_async_command_runner,
        args=(job_id, command),
        daemon=True
    ).start()

def _async_command_runner(job_id: str, command: str):
    from app.core.dispatcher import Dispatcher
    from app.core.context import context
    
    # Determine execution strategy
    # If it looks like a CLI/shell command, use run_terminal_command
    # Otherwise, it might be a tool action block.
    # Note: We must ensure active project context or check session bounds
    dispatcher = Dispatcher()
    
    # If KLAUSE is currently busy in an active turn, queue the rule prompt or wait
    if context.session_id and context.session_id != "default_session" and getattr(context, "_active_turn", False):
        logger.info(f"KLAUSE is busy. Execution of scheduled command '{command}' will queue or run silently.")
        
    try:
        # Run terminal command (if project context exists), otherwise fallback to general tool execution
        if context.current_project_path:
            observation = dispatcher.execute("run_terminal_command", {"command": command})
            logger.info(f"Scheduled job '{job_id}' shell execution success: {observation.success}")
        else:
            logger.warning(f"No active project context for scheduled job '{job_id}'. Executing command directly as subprocess.")
            import subprocess
            subprocess.run(command, shell=True, capture_output=True)
    except Exception as e:
        logger.error(f"Failed to execute command for scheduled job '{job_id}': {e}")


class SchedulerWrapper:
    """
    Persistent background job scheduler using APScheduler and MongoDBJobStore.
    """
    def __init__(self):
        self.scheduler: Optional[BackgroundScheduler] = None
        self._lock = False
        
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
                timezone=pytz.utc
            )
            self.scheduler.start()
            logger.info("Scheduler started successfully.")
        except Exception as e:
            logger.error(f"Failed to start Scheduler: {e}. Falling back to MemoryJobStore.")
            self.scheduler = BackgroundScheduler(timezone=pytz.utc)
            self.scheduler.start()

    def stop(self):
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler shut down cleanly.")

    def add_cron_job(self, job_id: str, command: str, cron_expr: str) -> str:
        """Adds a recurring cron job. Validates expression first."""
        if not self.scheduler:
            return "Error: Scheduler is not running."
            
        # Cron validation check
        from croniter import croniter
        try:
            # croniter expects 5 standard fields
            base_time = datetime.datetime.now(datetime.timezone.utc)
            croniter(cron_expr, base_time)
        except Exception as ce:
            return f"Error: Invalid cron expression '{cron_expr}': {ce}"

        try:
            # If job already exists, remove it first to allow updates
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                
            trigger = CronTrigger.from_crontab(cron_expr, timezone=pytz.utc)
            self.scheduler.add_job(
                _scheduled_job_executor,
                trigger=trigger,
                args=[job_id, command],
                id=job_id,
                replace_existing=True
            )
            return f"Successfully added cron job '{job_id}' with schedule '{cron_expr}'."
        except Exception as e:
            logger.error(f"Failed to add cron job: {e}")
            return f"Error adding cron job: {e}"

    def add_one_shot_job(self, job_id: str, command: str, run_at_utc: datetime.datetime) -> str:
        """Adds a one-shot job scheduled at a specific UTC timestamp."""
        if not self.scheduler:
            return "Error: Scheduler is not running."
            
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        if run_at_utc <= now_utc:
            return f"Error: Scheduled time '{run_at_utc}' must be in the future (current UTC: {now_utc})."

        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                
            trigger = DateTrigger(run_date=run_at_utc, timezone=pytz.utc)
            self.scheduler.add_job(
                _scheduled_job_executor,
                trigger=trigger,
                args=[job_id, command],
                id=job_id,
                replace_existing=True
            )
            return f"Successfully scheduled one-shot job '{job_id}' at {run_at_utc} UTC."
        except Exception as e:
            logger.error(f"Failed to schedule job: {e}")
            return f"Error scheduling job: {e}"

    def list_jobs(self) -> List[Dict[str, Any]]:
        """Lists active scheduled jobs, converting UTC runtime to local timezone."""
        if not self.scheduler:
            return []
            
        local_tz = pytz.timezone("Asia/Kolkata")  # Sensible default or detect local timezone
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
                # Convert UTC to local timezone
                next_run_local = next_run.astimezone(local_tz)
                next_run_str = next_run_local.strftime("%Y-%m-%d %H:%M:%S %Z")
            else:
                next_run_str = "paused / idle"
                
            # Extract trigger info
            trigger_str = str(job.trigger)
            
            jobs_list.append({
                "job_id": job.id,
                "command": job.args[1] if len(job.args) > 1 else "",
                "trigger": trigger_str,
                "next_run_time_local": next_run_str,
                "timezone": local_tz.zone
            })
        return jobs_list

    def remove_job(self, job_id: str) -> bool:
        if not self.scheduler:
            return False
        try:
            self.scheduler.remove_job(job_id)
            return True
        except Exception:
            return False

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
