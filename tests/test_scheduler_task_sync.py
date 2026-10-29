import pytest
from unittest.mock import MagicMock, patch
from app.automation.scheduler import SchedulerWrapper, human_readable_cron
from app.api.server import list_tasks, create_task, delete_task, TaskCreate

def test_human_readable_cron_expressions():
    assert human_readable_cron("*/5 * * * *") == "Every 5 minutes"
    assert human_readable_cron("*/15 * * * *") == "Every 15 minutes"
    assert human_readable_cron("*/30 * * * *") == "Every 30 minutes"
    assert human_readable_cron("0 * * * *") == "Every hour on the hour"
    assert human_readable_cron("0 */2 * * *") == "Every 2 hours"
    assert human_readable_cron("0 */6 * * *") == "Every 6 hours"
    assert human_readable_cron("0 9 * * *") == "Daily at 9:00 AM"
    assert human_readable_cron("30 14 * * *") == "Daily at 2:30 PM"
    assert human_readable_cron("0 9 * * 1-5") == "Every weekday (Mon-Fri) at 9:00 AM"
    assert human_readable_cron("0 10 * * 1") == "Every Monday at 10:00 AM"

def test_scheduler_syncs_with_tasks_collection():
    mock_mgr = MagicMock()
    mock_db = MagicMock()
    mock_mgr.db = mock_db
    
    # Fake tasks collection find return
    fake_tasks = [
        {
            "_id": "64b0f1a23c4d5e6f7a8b9c0d",
            "job_id": "test_sync_job",
            "type": "scheduled",
            "title": "[Scheduled] test_sync_job",
            "description": "Command: `git status` | Schedule: Every 5 minutes",
            "status": "pending",
            "priority": "medium",
            "command": "git status"
        }
    ]
    mock_db.tasks.find.return_value.sort.return_value = fake_tasks
    
    with patch("app.api.server.get_memory_manager", return_value=mock_mgr), \
         patch("app.api.server.scheduler.list_jobs", return_value=[{
             "job_id": "test_sync_job",
             "command": "git status",
             "next_run_time_local": "2026-10-29 15:00:00",
             "human_schedule": "Every 5 minutes",
             "trigger": "cron"
         }]):
        
        tasks = list_tasks()
        assert len(tasks) == 1
        assert tasks[0]["id"] == "64b0f1a23c4d5e6f7a8b9c0d"
        assert tasks[0]["type"] == "scheduled"
        assert tasks[0]["job_id"] == "test_sync_job"
        assert tasks[0]["status"] == "pending"
        
        # Verify update_one was called to upsert the scheduled task into db.tasks
        mock_db.tasks.update_one.assert_called()

def test_create_and_delete_task():
    mock_mgr = MagicMock()
    mock_db = MagicMock()
    mock_mgr.db = mock_db
    
    insert_res = MagicMock()
    insert_res.inserted_id = "64b0f1a23c4d5e6f7a8b9c0e"
    mock_db.tasks.insert_one.return_value = insert_res
    
    with patch("app.api.server.get_memory_manager", return_value=mock_mgr):
        res = create_task(TaskCreate(
            title="Manual Task",
            description="Testing manual creation",
            priority="high",
            status="pending"
        ))
        assert res["status"] == "success"
        assert res["task"]["title"] == "Manual Task"
        assert res["task"]["id"] == "64b0f1a23c4d5e6f7a8b9c0e"
        
        # Test deletion
        del_res = delete_task("64b0f1a23c4d5e6f7a8b9c0e")
        assert del_res["status"] == "success"
        mock_db.tasks.delete_one.assert_called()
