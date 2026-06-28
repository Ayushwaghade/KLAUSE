import pytest
from unittest.mock import MagicMock, patch
from app.tools.base import tool_registry
from app.core.dispatcher import Dispatcher
from app.core.brain import Brain
from app.models.agent import ToolObservation

def test_tool_registration():
    # Verify that Phase 1 tools are successfully registered
    assert "read_file" in tool_registry
    assert "write_file" in tool_registry
    assert "web_search" in tool_registry

def test_dispatcher_confirm_callback():
    confirm_called = []
    def dummy_confirm(prompt: str) -> bool:
        confirm_called.append(prompt)
        return True

    dispatcher = Dispatcher(confirm_fn=dummy_confirm)
    
    # Case A: Writing to a new file (should NOT trigger confirmation)
    with patch("os.path.exists", return_value=False):
        with patch("builtins.open", MagicMock()):
            obs = dispatcher.execute("write_file", {"path": "new_file.txt", "content": "hello"})
            assert obs.success is True
            assert len(confirm_called) == 0

    # Case B: Overwriting an existing file (should trigger confirmation)
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", MagicMock()):
            obs = dispatcher.execute("write_file", {"path": "existing_file.txt", "content": "hello"})
            assert obs.success is True
            assert len(confirm_called) == 1
            assert "already exists" in confirm_called[0]

def test_brain_react_loop():
    # Setup mock dispatcher
    mock_dispatcher = MagicMock(spec=Dispatcher)
    mock_dispatcher.execute.return_value = ToolObservation(
        tool_name="write_file",
        success=True,
        result="Success: Content written to test.txt"
    )

    # Setup mock responses for Gemini
    mock_gemini_client = MagicMock()
    
    # Step 1: Brain decides to write file
    res1 = MagicMock()
    res1.text = '{"thought": "I need to write to the file.", "action": "write_file", "params": {"path": "test.txt", "content": "hello"}, "response": null}'
    
    # Step 2: Brain determines task is completed
    res2 = MagicMock()
    res2.text = '{"thought": "File is written. I will respond to the user.", "action": "FINAL", "params": {}, "response": "I successfully created the file test.txt."}'
    
    mock_gemini_client.models.generate_content.side_effect = [res1, res2]

    # Patch the Client class initialization to return our mocked client
    with patch("app.core.brain.genai.Client", return_value=mock_gemini_client):
        brain = Brain(dispatcher=mock_dispatcher)
        # Force connected state for unit testing
        brain.is_connected = True
        brain.client = mock_gemini_client
        
        response = brain.think("Create file test.txt containing hello")
        
        assert response == "I successfully created the file test.txt."
        mock_dispatcher.execute.assert_called_once_with("write_file", {"path": "test.txt", "content": "hello"})
        assert mock_gemini_client.models.generate_content.call_count == 2

def test_brain_self_healing_parameters():
    mock_dispatcher = MagicMock(spec=Dispatcher)
    mock_dispatcher.execute.return_value = ToolObservation(
        tool_name="write_file",
        success=True,
        result="Success: Content written to test.txt"
    )

    mock_gemini_client = MagicMock()
    
    # Step 1: Brain outputs arguments at the ROOT level of JSON (missing params block)
    res1 = MagicMock()
    res1.text = '{"thought": "I need to write.", "action": "write_file", "path": "test.txt", "content": "hello"}'
    
    res2 = MagicMock()
    res2.text = '{"thought": "Done.", "action": "FINAL", "params": {}, "response": "Finished"}'
    
    mock_gemini_client.models.generate_content.side_effect = [res1, res2]

    with patch("app.core.brain.genai.Client", return_value=mock_gemini_client):
        brain = Brain(dispatcher=mock_dispatcher)
        brain.is_connected = True
        brain.client = mock_gemini_client
        
        response = brain.think("Create file test.txt containing hello")
        
        assert response == "Finished"
        mock_dispatcher.execute.assert_called_once_with("write_file", {"path": "test.txt", "content": "hello"})
        assert mock_gemini_client.models.generate_content.call_count == 2
