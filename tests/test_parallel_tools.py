import pytest
from unittest.mock import MagicMock, patch
from app.core.dispatcher import Dispatcher
from app.core.brain import Brain
from app.models.agent import ToolObservation, AgentAction, ToolCall

def test_dispatcher_execute_parallel_success():
    dispatcher = Dispatcher()
    
    # Mock execute for two tools
    with patch.object(dispatcher, "execute") as mock_exec:
        mock_exec.side_effect = lambda action, params: ToolObservation(
            tool_name=action,
            success=True,
            result=f"Result of {action} with {params}"
        )
        
        tool_calls = [
            {"action": "read_file", "params": {"path": "a.txt"}},
            {"action": "read_file", "params": {"path": "b.txt"}},
            {"action": "git_status", "params": {}}
        ]
        
        results = dispatcher.execute_parallel(tool_calls)
        assert len(results) == 3
        assert results[0].tool_name == "read_file"
        assert "a.txt" in results[0].result
        assert results[1].tool_name == "read_file"
        assert "b.txt" in results[1].result
        assert results[2].tool_name == "git_status"
        assert all(r.success for r in results)

def test_dispatcher_execute_parallel_partial_failure():
    dispatcher = Dispatcher()
    
    def side_effect(action, params):
        if action == "failing_tool":
            return ToolObservation(tool_name=action, success=False, result="", error="Tool crashed")
        return ToolObservation(tool_name=action, success=True, result="OK")

    with patch.object(dispatcher, "execute", side_effect=side_effect):
        tool_calls = [
            {"action": "good_tool_1", "params": {}},
            {"action": "failing_tool", "params": {}},
            {"action": "good_tool_2", "params": {}}
        ]
        results = dispatcher.execute_parallel(tool_calls)
        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[1].error == "Tool crashed"
        assert results[2].success is True

def test_brain_parallel_tool_calling():
    brain = Brain()
    
    # Mock LLM generation: turn 1 returns parallel actions, turn 2 returns FINAL
    turn_1_json = (
        '{\n'
        '  "thought": "I will read both files in parallel.",\n'
        '  "actions": [\n'
        '    {"action": "read_file", "params": {"path": "file1.txt"}},\n'
        '    {"action": "read_file", "params": {"path": "file2.txt"}}\n'
        '  ],\n'
        '  "response": null\n'
        '}'
    )
    turn_2_json = (
        '{\n'
        '  "thought": "Both files read. I am done.",\n'
        '  "action": "FINAL",\n'
        '  "params": {},\n'
        '  "response": "Here is the summary of both files."\n'
        '}'
    )
    
    with patch.object(brain, "_generate_plan", return_value=""), \
         patch.object(brain, "_maybe_load_relevant_skill", return_value=""), \
         patch.object(brain, "_generate_text_or_json", side_effect=[turn_1_json, turn_2_json]), \
         patch.object(brain.dispatcher, "execute_parallel") as mock_parallel:
        
        mock_parallel.return_value = [
            ToolObservation(tool_name="read_file", success=True, result="Content of file1"),
            ToolObservation(tool_name="read_file", success=True, result="Content of file2")
        ]
        
        callback_events = []
        def step_cb(event):
            callback_events.append(event)
            
        final_resp = brain.think("Analyze file1 and file2", session_id="test_parallel", step_callback=step_cb)
        
        assert "summary of both files" in final_resp
        assert mock_parallel.called
        assert len(mock_parallel.call_args[0][0]) == 2
        
        # Verify callback caught the parallel execution
        parallel_cb = next((e for e in callback_events if e.get("type") == "thought" and "PARALLEL" in e.get("action", "")), None)
        assert parallel_cb is not None
        assert len(parallel_cb["actions"]) == 2

def test_tool_call_root_param_absorption():
    # Direct dictionary with root-level parameters
    data = {"action": "web_search", "query": "Transformers research", "max_results": 5}
    tc = ToolCall.model_validate(data)
    assert tc.action == "web_search"
    assert tc.params == {"query": "Transformers research", "max_results": 5}

    # Tool alias instead of action
    alias_data = {"tool": "web_search", "query": "GANs"}
    tc2 = ToolCall.model_validate(alias_data)
    assert tc2.action == "web_search"
    assert tc2.params == {"query": "GANs"}

def test_brain_parallel_tool_calling_with_root_params():
    brain = Brain()
    turn_1_json = (
        '{\n'
        '  "thought": "I will search both topics in parallel.",\n'
        '  "actions": [\n'
        '    {"action": "web_search", "query": "Transformers research"},\n'
        '    {"action": "web_search", "query": "GANs research"}\n'
        '  ]\n'
        '}'
    )
    turn_2_json = (
        '{\n'
        '  "thought": "Got all search results.",\n'
        '  "action": "FINAL",\n'
        '  "response": "Here is the combined research."\n'
        '}'
    )
    with patch.object(brain, "_generate_plan", return_value=""), \
         patch.object(brain, "_maybe_load_relevant_skill", return_value=""), \
         patch.object(brain, "_generate_text_or_json", side_effect=[turn_1_json, turn_2_json]), \
         patch.object(brain.dispatcher, "execute_parallel") as mock_parallel:

        mock_parallel.return_value = [
            ToolObservation(tool_name="web_search", success=True, result="Transformers info"),
            ToolObservation(tool_name="web_search", success=True, result="GANs info")
        ]

        final_resp = brain.think("Research Transformers and GANs", session_id="test_root_params")
        assert "combined research" in final_resp
        assert mock_parallel.called
        calls = mock_parallel.call_args[0][0]
        assert len(calls) == 2
        assert calls[0]["params"] == {"query": "Transformers research"}
        assert calls[1]["params"] == {"query": "GANs research"}

