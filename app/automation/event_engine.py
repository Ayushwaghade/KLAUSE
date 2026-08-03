import time
import datetime
import threading
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Any, Optional
from loguru import logger
import pygetwindow as gw

from app.config.config import settings

class EventType(Enum):
    WINDOW_FOCUSED = "window_focused"
    FILE_CHANGED = "file_changed"
    PROCESS_TERMINATED = "process_terminated"
    CRON_TRIGGERED = "cron_triggered"


@dataclass
class Event:
    event_type: EventType
    source: str
    timestamp: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    data: Dict[str, Any] = field(default_factory=dict)


class EventMonitorThread(threading.Thread):
    """
    Background daemon thread that polls OS state (active window)
    and KLAUSE background subprocesses to emit events.
    """
    def __init__(self, engine: "EventEngine"):
        super().__init__(name="KLAUSE_EventMonitorThread", daemon=True)
        self.engine = engine
        self.stop_event = threading.Event()
        
        # Window focus tracking state
        self.last_window_title = ""
        self.pending_window_title = ""
        self.pending_window_start_time = 0.0

    def stop(self):
        self.stop_event.set()

    def run(self):
        logger.info("EventMonitorThread started.")
        
        # Load configurable automation settings
        interval = getattr(settings.automation, "polling_interval_seconds", 0.5)
        debounce_time = getattr(settings.automation, "debounce_interval_seconds", 0.3)
        
        while not self.stop_event.is_set():
            try:
                # 1. Track active window focus changes with debouncing
                self._poll_active_window(debounce_time)
                
                # 2. Track background process termination
                self._poll_background_processes()
                
            except Exception as e:
                logger.error(f"Error in EventMonitorThread polling loop: {e}")
                
            time.sleep(interval)
            
        logger.info("EventMonitorThread stopped.")

    def _poll_active_window(self, debounce_time: float):
        try:
            active_win = gw.getActiveWindow()
            active_title = active_win.title if active_win else ""
        except Exception as e:
            logger.debug(f"Failed to get active window: {e}")
            active_title = ""

        # If the window title has changed from our last verified one
        if active_title != self.last_window_title:
            # If we don't have a pending title change or it matches a new window
            if active_title != self.pending_window_title:
                self.pending_window_title = active_title
                self.pending_window_start_time = time.time()
            else:
                # We have a pending title, check if it has stabilized (debounced)
                elapsed = time.time() - self.pending_window_start_time
                if elapsed >= debounce_time:
                    # Stabilized! Emit the event
                    logger.info(f"Active window stabilized: '{active_title}' after {debounce_time}s debounce.")
                    self.last_window_title = active_title
                    self.pending_window_title = ""
                    
                    self.engine.publish(Event(
                        event_type=EventType.WINDOW_FOCUSED,
                        source="pygetwindow",
                        data={"title": active_title}
                    ))
        else:
            # Reset pending window if it reverts to the current verified one
            self.pending_window_title = ""

    def _poll_background_processes(self):
        # Explicit import of running_processes to avoid cyclic dependencies
        from app.tools.terminal_tools import running_processes
        
        terminated_pids = []
        
        # Safe iteration over running processes
        for pid in list(running_processes.keys()):
            info = running_processes.get(pid)
            if not info:
                continue
            proc = info.get("process")
            if proc is None:
                continue
                
            # If poll() is not None, the process has exited
            exit_code = proc.poll()
            if exit_code is not None:
                logger.info(f"Background command with PID {pid} exited with code: {exit_code}")
                terminated_pids.append((pid, info, exit_code))
                
        # Clean up and notify
        for pid, info, exit_code in terminated_pids:
            # Remove from terminal tools registry
            if pid in running_processes:
                del running_processes[pid]
                
            # Emit event
            self.engine.publish(Event(
                event_type=EventType.PROCESS_TERMINATED,
                source="terminal_tools",
                data={
                    "pid": pid,
                    "command": info.get("command", ""),
                    "started_at": info.get("started_at", ""),
                    "exit_code": exit_code
                }
            ))


class EventEngine:
    """
    Central Pub/Sub event dispatcher for KLAUSE.
    """
    def __init__(self):
        self._listeners: Dict[EventType, List[Callable[[Event], Any]]] = {
            t: [] for t in EventType
        }
        self._monitor_thread: Optional[EventMonitorThread] = None
        self._lock = threading.Lock()

    def start(self):
        with self._lock:
            # If enabled in configuration, launch background polling
            if getattr(settings.automation, "enabled", True):
                if self._monitor_thread is None or not self._monitor_thread.is_alive():
                    self._monitor_thread = EventMonitorThread(self)
                    self._monitor_thread.start()
                    logger.info("EventEngine monitor thread started.")

    def stop(self):
        with self._lock:
            if self._monitor_thread:
                self._monitor_thread.stop()
                self._monitor_thread.join(timeout=3)
                self._monitor_thread = None
                logger.info("EventEngine monitor thread shut down.")

    def subscribe(self, event_type: EventType, callback: Callable[[Event], Any]):
        with self._lock:
            if callback not in self._listeners[event_type]:
                self._listeners[event_type].append(callback)
                logger.debug(f"Registered subscriber for event {event_type.value}")

    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], Any]):
        with self._lock:
            if callback in self._listeners[event_type]:
                self._listeners[event_type].remove(callback)
                logger.debug(f"Unregistered subscriber for event {event_type.value}")

    def publish(self, event: Event):
        # Safeguard call execution inside callback to prevent blocking event loop
        listeners = self._listeners.get(event.event_type, [])
        for callback in listeners:
            try:
                # Trigger callback in a separate thread to prevent handler delay blocking event loop
                threading.Thread(
                    target=self._safe_execute_callback,
                    args=(callback, event),
                    daemon=True
                ).start()
            except Exception as e:
                logger.error(f"Failed to spawn callback thread: {e}")

    def _safe_execute_callback(self, callback: Callable[[Event], Any], event: Event):
        try:
            callback(event)
        except Exception as e:
            logger.error(f"Error executing callback for event {event.event_type.value}: {e}")


# Singleton instance
event_engine = EventEngine()
