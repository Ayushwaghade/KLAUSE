import time
import datetime
import pytest
import pytz
from unittest.mock import patch, MagicMock, AsyncMock

from app.automation.event_engine import Event, EventType, EventEngine, EventMonitorThread
from app.automation.rule_engine import RuleEngine, RuleModel
from app.automation.scheduler import SchedulerWrapper


# ===========================================================================
# 1. Event Engine Tests
# ===========================================================================

def test_event_engine_subscribe_publish():
    engine = EventEngine()
    received_events = []

    def callback(event: Event):
        received_events.append(event)

    # Subscribe
    engine.subscribe(EventType.WINDOW_FOCUSED, callback)

    # Publish matching event
    test_event = Event(event_type=EventType.WINDOW_FOCUSED, source="test", data={"title": "VS Code"})
    engine.publish(test_event)

    # Yield time for async callback invocation thread
    time.sleep(0.1)

    assert len(received_events) == 1
    assert received_events[0].data["title"] == "VS Code"

    # Unsubscribe
    engine.unsubscribe(EventType.WINDOW_FOCUSED, callback)
    engine.publish(test_event)
    time.sleep(0.1)

    # Length remains 1
    assert len(received_events) == 1


@patch("pygetwindow.getActiveWindow")
def test_event_monitor_debounced_window_focus(mock_get_win):
    engine = EventEngine()
    received_events = []

    def callback(event: Event):
        received_events.append(event)

    engine.subscribe(EventType.WINDOW_FOCUSED, callback)

    # Create monitor thread
    monitor = EventMonitorThread(engine)

    # Mock window object
    mock_win = MagicMock()
    mock_win.title = "Notepad"
    mock_get_win.return_value = mock_win

    # 1. First poll with Notepad title
    monitor._poll_active_window(debounce_time=0.1)
    assert len(received_events) == 0  # Not stabilized yet (debounce is 0.1s)

    # 2. Wait 0.15s and poll again with same title
    time.sleep(0.15)
    monitor._poll_active_window(debounce_time=0.1)
    time.sleep(0.1)  # Yield for callback thread

    assert len(received_events) == 1
    assert received_events[0].data["title"] == "Notepad"

    # 3. Change title to Chrome
    mock_win2 = MagicMock()
    mock_win2.title = "Chrome"
    mock_get_win.return_value = mock_win2

    monitor._poll_active_window(debounce_time=0.1)
    assert len(received_events) == 1  # Chrome not stabilized yet

    # 4. Change window title immediately before stabilization (reset debounce)
    mock_win3 = MagicMock()
    mock_win3.title = "VS Code"
    mock_get_win.return_value = mock_win3
    monitor._poll_active_window(debounce_time=0.1)
    
    # Wait 0.05s (less than 0.1s debounce)
    time.sleep(0.05)
    monitor._poll_active_window(debounce_time=0.1)
    assert len(received_events) == 1  # VS Code not stabilized yet

    # 5. Wait 0.12s (stabilized!)
    time.sleep(0.12)
    monitor._poll_active_window(debounce_time=0.1)
    time.sleep(0.1)  # Yield for callback thread

    assert len(received_events) == 2
    assert received_events[1].data["title"] == "VS Code"


# ===========================================================================
# 2. Rule Engine Tests
# ===========================================================================

def test_rule_validation():
    # Valid rule
    rule_data = {
        "rule_id": "test_rule_1",
        "event_type": "window_focused",
        "filter_pattern": ".*VS Code.*",
        "action_type": "tool_call",
        "action_payload": {
            "tool_name": "list_running_commands",
            "params": {}
        },
        "enabled": True
    }
    rule = RuleModel.model_validate(rule_data)
    assert rule.rule_id == "test_rule_1"
    assert rule.event_type == "window_focused"

    # Invalid rule (missing payload)
    bad_rule_data = {
        "rule_id": "test_rule_2",
        "event_type": "window_focused",
        "action_type": "tool_call"
    }
    with pytest.raises(Exception):
        RuleModel.model_validate(bad_rule_data)


def test_rule_matching():
    rules = [
        RuleModel(
            rule_id="r1",
            event_type="window_focused",
            filter_pattern="notepad",
            action_type="trigger_react",
            action_payload={"prompt": "Notepad focused"}
        ),
        RuleModel(
            rule_id="r2",
            event_type="window_focused",
            filter_pattern="vscode",
            action_type="trigger_react",
            action_payload={"prompt": "VS Code focused"}
        )
    ]

    engine = RuleEngine()
    engine.rules = rules

    # Match Notepad event
    notepad_event = Event(event_type=EventType.WINDOW_FOCUSED, source="test", data={"title": "My Notepad Document"})
    matches = engine.match_event(notepad_event)
    assert len(matches) == 1
    assert matches[0].rule_id == "r1"

    # Match VS Code event
    vscode_event = Event(event_type=EventType.WINDOW_FOCUSED, source="test", data={"title": "workspace - vscode"})
    matches = engine.match_event(vscode_event)
    assert len(matches) == 1
    assert matches[0].rule_id == "r2"

    # Match generic title (no matches)
    generic_event = Event(event_type=EventType.WINDOW_FOCUSED, source="test", data={"title": "Calculator"})
    matches = engine.match_event(generic_event)
    assert len(matches) == 0


@patch("app.core.dispatcher.Dispatcher.execute")
def test_rule_tool_call_execution(mock_dispatcher_execute):
    rule = RuleModel(
        rule_id="r1",
        event_type="window_focused",
        filter_pattern="notepad",
        action_type="tool_call",
        action_payload={
            "tool_name": "list_running_commands",
            "params": {}
        }
    )
    
    mock_obs = MagicMock()
    mock_obs.success = True
    mock_dispatcher_execute.return_value = mock_obs

    engine = RuleEngine()
    engine.rules = [rule]

    notepad_event = Event(event_type=EventType.WINDOW_FOCUSED, source="test", data={"title": "notepad"})
    engine.handle_event(notepad_event)

    time.sleep(0.1)  # Yield for safe execution thread
    mock_dispatcher_execute.assert_called_once_with("list_running_commands", {})


# ===========================================================================
# 3. Scheduler Tests
# ===========================================================================

def test_cron_expression_validation():
    scheduler_wrapper = SchedulerWrapper()
    # Mock BackgroundScheduler
    scheduler_wrapper.scheduler = MagicMock()

    # Valid cron
    res1 = scheduler_wrapper.add_cron_job("j1", "dir", "*/5 * * * *")
    assert "Successfully added" in res1

    # Invalid cron
    res2 = scheduler_wrapper.add_cron_job("j2", "dir", "invalid_cron_expr * *")
    assert "Error: Invalid cron expression" in res2


def test_scheduler_timezone_display():
    scheduler_wrapper = SchedulerWrapper()
    scheduler_wrapper.scheduler = MagicMock()

    # Create a mock job scheduled at a specific UTC time
    mock_job = MagicMock()
    mock_job.id = "test_job"
    # Scheduled for 2026-07-01 12:00:00 UTC
    mock_job.next_run_time = datetime.datetime(2026, 7, 1, 12, 0, 0, tzinfo=pytz.utc)
    mock_job.args = ["test_job", "echo hello"]
    mock_job.trigger = "cron[minute='*']"
    
    scheduler_wrapper.scheduler.get_jobs.return_value = [mock_job]

    # Explicitly mock local timezone to match test assertion (e.g. Asia/Kolkata +5:30)
    with patch("tzlocal.get_localzone", return_value=pytz.timezone("Asia/Kolkata")):
        jobs = scheduler_wrapper.list_jobs()
        assert len(jobs) == 1
        # 12:00:00 UTC + 5:30 = 17:30:00 local time
        assert "17:30:00" in jobs[0]["next_run_time_local"]
        assert "Asia/Kolkata" in jobs[0]["next_run_time_local"] or "IST" in jobs[0]["next_run_time_local"]
