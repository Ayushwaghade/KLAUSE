import os
import json
import pytest
from unittest.mock import MagicMock, patch
from app.core.brain import Brain
from app.core.dispatcher import Dispatcher
from app.models.agent import ToolObservation

@pytest.fixture
def clean_continuation():
    session_id = "test_continuation_session"
    filepath = os.path.join("data", "continuations", f"{session_id}.json")
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception:
            pass
    yield session_id
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception:
            pass

def test_continuation_triggers():
    brain = Brain()
    # Positive triggers
    assert brain._is_continuation_trigger("continue") is True
    assert brain._is_continuation_trigger("Please continue") is True
    assert brain._is_continuation_trigger("go on") is True
    assert brain._is_continuation_trigger("keep going") is True
    assert brain._is_continuation_trigger("proceed") is True
    assert brain._is_continuation_trigger("resume") is True
    assert brain._is_continuation_trigger("carry on") is True
    assert brain._is_continuation_trigger("finish it") is True
    assert brain._is_continuation_trigger("yes") is True
    assert brain._is_continuation_trigger("sure") is True
    assert brain._is_continuation_trigger("ok") is True
    assert brain._is_continuation_trigger("continue researching the rust crates") is True

    # Negative triggers
    assert brain._is_continuation_trigger("stop") is False
    assert brain._is_continuation_trigger("don't continue") is False
    assert brain._is_continuation_trigger("cancel") is False
    assert brain._is_continuation_trigger("what is the weather today?") is False
    assert brain._is_continuation_trigger("open chrome and play music") is False

def test_continuation_disk_persistence(clean_continuation):
    session_id = clean_continuation
    brain = Brain()
    history = [
        {
            "thought": "Searching for zero knowledge proofs in Rust",
            "action": "web_search",
            "params": {"query": "rust zkp"},
            "observation": ToolObservation(tool_name="web_search", success=True, result="Found arkworks-rs, bellman")
        }
    ]

    brain._save_continuation(
        session_id=session_id,
        original_goal="Research Rust ZKP libraries",
        history=history,
        provider="nvidia",
        model_name="nvidia/nemotron-3-ultra-550b-a55b",
        is_complex=True,
        active_groups=["research", "core"],
        plan_str="1. Search crates\n2. Summarize"
    )

    # Verify file written to disk
    filepath = brain._get_continuation_filepath(session_id)
    assert os.path.exists(filepath)

    # Clear in-memory dictionary to force reading from disk
    brain._continuation_states.clear()
    state = brain._get_continuation(session_id)
    assert state is not None
    assert state["original_goal"] == "Research Rust ZKP libraries"
    assert state["provider"] == "nvidia"
    assert state["model_name"] == "nvidia/nemotron-3-ultra-550b-a55b"
    assert state["is_complex"] is True
    assert len(state["history"]) == 1
    assert "arkworks-rs" in state["history"][0]["observation"]["result"]

    # Clear continuation removes disk file
    brain._clear_continuation(session_id)
    assert not os.path.exists(filepath)
    assert brain._get_continuation(session_id) is None

def test_continuation_preserves_nemotron_provider_and_handoff_research(clean_continuation):
    session_id = clean_continuation
    mock_dispatcher = MagicMock(spec=Dispatcher)
    mock_dispatcher.execute.return_value = ToolObservation(
        tool_name="read_file",
        success=True,
        result="arkworks-rs is a Rust ecosystem for zkSNARKs."
    )

    brain = Brain(dispatcher=mock_dispatcher)
    brain.is_connected = True
    brain.max_steps = 2  # limit to 2 steps for testing step budget pause

    # Simulate Call 1 running on Nemotron
    brain.provider = "nvidia"
    brain.model_name = "nvidia/nemotron-3-ultra-550b-a55b"

    client1 = MagicMock()
    # Step 1 response from NVIDIA
    c1 = MagicMock()
    c1.message.content = json.dumps({
        "thought": "I will search for Arkworks documentation.",
        "action": "read_file",
        "params": {"path": "arkworks.md"}
    })
    r1 = MagicMock()
    r1.choices = [c1]

    # Step 2 response from NVIDIA (still not FINAL, reaching step budget of 2)
    c2 = MagicMock()
    c2.message.content = json.dumps({
        "thought": "I will examine benchmarks for Bellman.",
        "action": "read_file",
        "params": {"path": "bellman.md"}
    })
    r2 = MagicMock()
    r2.choices = [c2]

    client1.chat.completions.create.side_effect = [r1, r2]
    brain.client = client1

    with patch.object(brain, '_maybe_load_relevant_skill', return_value=""):
        resp1 = brain.think("Research Rust ZKP libraries and compare benchmarks", session_id=session_id)

    # Call 1 should hit step limit (2 steps) and instruct user to say 'continue'
    assert "reached the step limit (2 steps)" in resp1
    assert "continue" in resp1.lower()
    
    # Verify continuation state was recorded
    state = brain._get_continuation(session_id)
    assert state is not None
    assert state["provider"] == "nvidia"
    assert state["model_name"] == "nvidia/nemotron-3-ultra-550b-a55b"
    assert len(state["history"]) == 2

    # Now simulate Call 2: User says "continue"
    # Even if default settings would route simple inputs to fast_provider (gemini),
    # continuation must preserve nvidia/nemotron!
    client2 = MagicMock()
    prompts_received = []

    def mock_chat_create(**kwargs):
        messages = kwargs.get("messages", [])
        if messages:
            prompts_received.append(messages[0]["content"])
        c_res = MagicMock()
        c_res.message.content = json.dumps({
            "thought": "Continuing research from step 2. Arkworks and Bellman are evaluated. I will finalize.",
            "action": "FINAL",
            "params": {},
            "response": "Here is the comparison between Arkworks and Bellman: Arkworks offers flexible modular curves, while Bellman specializes in Groth16."
        })
        comp = MagicMock()
        comp.choices = [c_res]
        return comp

    client2.chat.completions.create.side_effect = mock_chat_create
    brain.client = client2

    with patch.object(brain, '_maybe_load_relevant_skill', return_value=""):
        resp2 = brain.think("continue", session_id=session_id)

    # Verification 1: Provider and model remained locked to Nemotron
    assert brain.provider == "nvidia"
    assert brain.model_name == "nvidia/nemotron-3-ultra-550b-a55b"

    # Verification 2: The prompt sent in Call 2 contained Call 1's research and steps 1 & 2
    assert len(prompts_received) > 0
    turn2_prompt = prompts_received[0]
    assert "Step 1:" in turn2_prompt
    assert "I will search for Arkworks documentation." in turn2_prompt
    assert "Step 2:" in turn2_prompt
    assert "I will examine benchmarks for Bellman." in turn2_prompt
    assert "arkworks-rs is a Rust ecosystem" in turn2_prompt
    assert "CONTINUATION NOTE" in turn2_prompt
    assert "Research Rust ZKP libraries and compare benchmarks" in turn2_prompt

    # Verification 3: Call 2 completed and finalized
    assert "Arkworks offers flexible modular curves" in resp2
    assert "[Task complete]" in resp2

    # Verification 4: Continuation state was automatically wiped upon FINAL
    assert brain._get_continuation(session_id) is None

def test_unrelated_query_clears_stale_continuation(clean_continuation):
    session_id = clean_continuation
    brain = Brain()
    brain._save_continuation(
        session_id=session_id,
        original_goal="Prior complex research",
        history=[{"thought": "old step", "action": "test", "params": {}, "observation": {"success": True, "result": "old"}}],
        provider="nvidia",
        model_name="nvidia/nemotron-3-ultra-550b-a55b",
        is_complex=True,
        active_groups=["research"]
    )
    assert brain._get_continuation(session_id) is not None

    with patch.object(brain, '_generate_text_or_json', return_value=json.dumps({
        "thought": "Answering simple question.",
        "action": "FINAL",
        "params": {},
        "response": "Today is Thursday."
    })), patch.object(brain, '_maybe_load_relevant_skill', return_value=""):
        brain.is_connected = True
        resp = brain.think("what day is it?", session_id=session_id)

    # Unrelated query should have cleared the prior continuation state
    assert brain._get_continuation(session_id) is None
    assert "Today is Thursday." in resp
