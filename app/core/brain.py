import os
import json
from typing import List, Dict, Any, Optional
from loguru import logger
from google import genai
from google.genai import types
from app.config.config import settings
from app.models.agent import AgentAction, ToolObservation
from app.tools.base import get_tool_definitions
from app.core.dispatcher import Dispatcher
from app.memory.memory_manager import get_memory_manager
from app.core.context import context

# Force tool registration on package import
import app.tools

class Brain:
    def __init__(self, dispatcher: Optional[Dispatcher] = None):
        self.api_key = settings.gemini_api_key or os.environ.get("GEMINI_API_KEY")
        self.model_name = settings.ai.gemini_model
        self.max_steps = settings.ai.max_steps
        self.dispatcher = dispatcher or Dispatcher()
        # Build properties for params dynamically based on registered tools in tool_registry
        import inspect
        from app.tools.base import tool_registry
        
        params_properties = {}
        for tool_name, tool_inst in tool_registry.items():
            sig = inspect.signature(tool_inst.func)
            for param_name, param in sig.parameters.items():
                if param_name in ("confirm_fn", "self", "args", "kwargs"):
                    continue
                # Map python annotation to schema types
                schema_type = "string"
                if param.annotation == int:
                    schema_type = "integer"
                elif param.annotation == float:
                    schema_type = "number"
                elif param.annotation == bool:
                    schema_type = "boolean"
                elif param.annotation == list:
                    schema_type = "array"
                elif param.annotation == dict:
                    schema_type = "object"
                
                params_properties[param_name] = {
                    "type": schema_type,
                    "description": f"Tool argument '{param_name}'."
                }
        
        self.schema = {
            "type": "object",
            "properties": {
                "thought": {
                    "type": "string",
                    "description": "Your step-by-step reasoning on what to do next."
                },
                "action": {
                    "type": "string",
                    "description": "The name of the tool to invoke, or 'FINAL' when done."
                },
                "params": {
                    "type": "object",
                    "description": "Key-value parameters to pass to the tool.",
                    "properties": params_properties
                },
                "response": {
                    "type": "string",
                    "description": "The final answer to the user (only set when action='FINAL')."
                }
            },
            "required": ["thought", "action", "params"]
        }
        
        if self.api_key:
            try:
                # Initialize new google-genai Client
                self.client = genai.Client(api_key=self.api_key)
                self.is_connected = True
                logger.info(f"Brain initialized with new google-genai Client, model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini API: {e}")
        else:
            logger.warning("No GEMINI_API_KEY found in config or env. KLAUSE will run in offline stub mode.")

    def think(self, user_input: str, session_id: str = "default_session") -> str:
        logger.info(f"Received user goal: {user_input} (Session: {session_id})")
        
        if not self.is_connected:
            return (
                "KLAUSE is running in offline stub mode. To enable AI responses, "
                "please set your `GEMINI_API_KEY` in the `.env` file."
            )

        # Save user message to MongoDB conversations
        try:
            get_memory_manager().save_conversation(
                session_id=session_id,
                role="user",
                content=user_input
            )
        except Exception as e:
            logger.warning(f"Failed to auto-save user conversation: {e}")

        # Retrieve past conversation history from memory manager
        past_history_str = ""
        try:
            past_messages = get_memory_manager().get_conversation_history(session_id=session_id, limit=8)
            if past_messages:
                past_history_str = "Previous Conversation Turns:\n"
                for msg in past_messages:
                    # Skip the current user_input we just logged to avoid duplication
                    if msg["role"] == "user" and msg["content"] == user_input:
                        continue
                    role_lbl = "User" if msg["role"] == "user" else "KLAUSE"
                    past_history_str += f"{role_lbl}: {msg['content']}\n"
                past_history_str += "\n"
        except Exception as e:
            logger.warning(f"Failed to retrieve conversation history: {e}")

        history: List[Dict[str, Any]] = []
        
        for step in range(1, self.max_steps + 1):
            logger.info(f"ReAct Loop - Step {step}/{self.max_steps}")
            
            # Format history for LLM prompt
            history_str = ""
            for idx, h in enumerate(history, 1):
                history_str += (
                    f"\nStep {idx}:\n"
                    f"Thought: {h['thought']}\n"
                    f"Action: {h['action']}\n"
                    f"Params: {json.dumps(h['params'])}\n"
                    f"Observation: {'Success' if h['observation'].success else 'Failure'}. "
                    f"Result: {h['observation'].result} "
                    f"Error: {h['observation'].error or 'None'}\n"
                )
                
            active_proj_str = f"Active Project Workspace Path: {context.current_project_path or 'None (You must open a project first using open_project before running terminal/git/vscode tools)'}\n\n"
            
            prompt = (
                "You are KLAUSE, a personal AI engineering assistant.\n"
                "Your objective is to solve the User Goal using the available tools.\n"
                "At each step, output a JSON object matching the AgentAction schema.\n\n"
                f"Available tools:\n{get_tool_definitions()}\n\n"
                "Instructions:\n"
                "1. Read the current progress history carefully to understand what actions you already performed.\n"
                "2. Choose the next tool to run. Make sure to provide exact parameters.\n"
                "3. If you have completed the goal, set action='FINAL' and provide your final response to the user.\n"
                "4. Avoid repeating a failing action with the exact same parameters.\n\n"
                f"{active_proj_str}"
                f"{past_history_str}"
                f"User Goal: {user_input}\n\n"
                f"Current Progress:\n{history_str or 'No steps taken yet.'}\n"
            )
            
            try:
                logger.debug(f"Sending prompt to Gemini:\n{prompt}")
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=self.schema
                    )
                )
                
                # Parse raw response to handle potential root-level parameter outputs
                raw_text = response.text.strip()
                logger.debug(f"Raw response: {raw_text}")
                
                try:
                    raw_data = json.loads(raw_text)
                except Exception as je:
                    raise ValueError(f"Failed to parse JSON response: {je}. Raw: {raw_text}")
                
                # Check for root-level tool arguments fallback
                if isinstance(raw_data, dict):
                    action_val = raw_data.get("action", "")
                    if action_val.upper() != "FINAL" and (not raw_data.get("params") or not isinstance(raw_data.get("params"), dict)):
                        extra_keys = {
                            k: v for k, v in raw_data.items()
                            if k not in ("thought", "action", "params", "response")
                        }
                        if extra_keys:
                            logger.info(f"Self-healing: Found root-level parameters {list(extra_keys.keys())}. Moving to 'params'.")
                            raw_data["params"] = extra_keys
                            
                # Validate response matching AgentAction schema
                action_data = AgentAction.model_validate(raw_data)
                logger.info(f"Step {step} Thought: {action_data.thought}")
                logger.info(f"Step {step} Action: {action_data.action} | Params: {action_data.params}")
                
                # Check for completion signal
                if action_data.action.upper() == "FINAL":
                    logger.info("Goal reached. Returning final response.")
                    final_resp = action_data.response or "Task complete."
                    try:
                        get_memory_manager().save_conversation(
                            session_id=session_id,
                            role="assistant",
                            content=final_resp
                        )
                    except Exception as e:
                        logger.warning(f"Failed to auto-save assistant response: {e}")
                    return final_resp
                    
                # Execute tool using dispatcher
                observation = self.dispatcher.execute(action_data.action, action_data.params)
                logger.info(f"Step {step} Observation success: {observation.success}")
                
                # Append step metadata to history
                history.append({
                    "thought": action_data.thought,
                    "action": action_data.action,
                    "params": action_data.params,
                    "observation": observation
                })
                
            except Exception as e:
                error_msg = f"ReAct Loop Error at step {step}: {e}"
                logger.exception(error_msg)
                return f"Sorry, I encountered an error running the agent loop: {e}"
                
        # Limit reached
        warning_msg = f"KLAUSE reached the maximum steps limit of {self.max_steps} without resolving the goal."
        logger.warning(warning_msg)
        final_resp = f"Warning: I was unable to complete the task within {self.max_steps} steps. Last progress: {history[-1]['thought'] if history else 'None'}"
        try:
            get_memory_manager().save_conversation(
                session_id=session_id,
                role="assistant",
                content=final_resp
            )
        except Exception as e:
            logger.warning(f"Failed to auto-save assistant warning response: {e}")
        return final_resp
