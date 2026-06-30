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

from app.core.client import get_gemini_client

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
                    "description": f"Parameter: {param_name}"
                }
        
        self.schema = {
            "type": "object",
            "properties": {
                "thought": {
                    "type": "string",
                    "description": "Your internal thoughts, reasoning process, and next plan."
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
        
        self.client = get_gemini_client()
        if self.client:
            self.is_connected = True
            logger.info(f"Brain initialized with shared Client, model: {self.model_name}")
        else:
            self.is_connected = False
            logger.warning("No GEMINI_API_KEY found in config or env. KLAUSE will run in offline stub mode.")

    def think(self, user_input: str, session_id: str = "default_session") -> str:
        logger.info(f"Received user goal: {user_input} (Session: {session_id})")
        
        if not self.is_connected:
            return (
                "KLAUSE is running in offline stub mode. To enable AI responses, "
                "please set your `GEMINI_API_KEY` in the `.env` file."
            )

        # Detect and pre-load matched skills from cloned skill repository
        loaded_skill_str = self._maybe_load_relevant_skill(user_input)

        # Set session context properties
        from app.core.context import context
        context.session_id = session_id
        
        # Load stored session folder from JSON config if not loaded
        from app.tools.session_tools import _load_session_settings
        settings_data = _load_session_settings()
        if not context.session_data_folder:
            stored_folder = settings_data.get("sessions", {}).get(session_id)
            if stored_folder:
                context.session_data_folder = stored_folder

        last_used_folder = settings_data.get("last_used_data_folder")
        if context.session_data_folder:
            session_folder_str = f"Active Session Data Folder: '{context.session_data_folder}'\n\n"
        else:
            last_prompt = f"'{last_used_folder}'" if last_used_folder else "None"
            session_folder_str = (
                f"Active Session Data Folder: UNSET.\n"
                f"CRITICAL DIRECTIVE: You do not have an active session folder set for this session yet. "
                f"You MUST ask Ayush in your opening response if they want to reuse the last used session folder: {last_prompt}, "
                f"or specify a new folder path using the 'set_session_data_folder' tool. "
                f"Do not perform any file-writing actions until this is configured!\n\n"
            )

        # Load all rules by default to ensure 100% compliance under high token headroom
        from app.core.rules_manager import get_rules_manager
        rules_str = get_rules_manager().get_rules(filter_tag=None)
        rules_block_str = ""
        if rules_str:
            rules_block_str = (
                f"STRICT USER RULES (rules.md):\n"
                f"{rules_str}\n\n"
                f"CRITICAL COMPLIANCE DIRECTIVE:\n"
                f"1. You must strictly follow the rules above. Before choosing any Action, evaluate your thought against these rules. "
                f"If executing the action would violate or conflict with any rule (e.g. writing files outside the session folder, or proceeding without a configured session folder), "
                f"you MUST NOT execute the tool. Instead, set action='FINAL', explain the rule collision to Ayush, and ask for explicit permission to bypass the rule.\n"
                f"2. You can modify, add, or remove rules in 'rules.md' using the modify_rules tool whenever Ayush explicitly asks you to do so.\n\n"
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

        # Retrieve past conversation history from memory manager based on config limits
        past_history_str = ""
        try:
            history_limit = getattr(settings.memory, "max_conversation_history", 50)
            past_messages = get_memory_manager().get_conversation_history(session_id=session_id, limit=history_limit)
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

        # Retrieve relevant semantic memories (RAG)
        relevant_memories_str = ""
        try:
            memories = get_memory_manager().search_semantic_memories(user_input, limit=8)
            # Filter by relevance: distance < 1.6
            valid_memories = [m for m in memories if m.get("distance", 2.0) < 1.6]
            if valid_memories:
                relevant_memories_str = "Relevant Memories & Context (RAG):\n"
                for m in valid_memories:
                    doc_type = m["type"].upper()
                    meta = m["metadata"] or {}
                    title_info = f" (Title: {meta.get('title')})" if 'title' in meta else ""
                    relevant_memories_str += f"  - [{doc_type}]{title_info}: {m['content']}\n"
                relevant_memories_str += "\n"
        except Exception as e:
            logger.warning(f"Failed to retrieve semantic memories: {e}")

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
                "You are KLAUSE, a dedicated, warm, and highly capable personal AI engineering companion. "
                "The user you are assisting is Ayush. "
                "Personality Guidelines:\n"
                "- Greet Ayush warmly and speak in a supportive, dedicated assistant tone (addressing them as 'Ayush').\n"
                "- Act as an active engineering partner: instead of just dryly answering questions, offer proactive help, suggest logical next steps, and ask engaging follow-up questions (e.g., 'I've updated that configuration, Ayush. Would you like me to test the connection now?').\n"
                "- Maintain a conversational, friendly companion vibe. Keep technical summaries clear but engaging.\n"
                "- Always explain your reasoning friendly in your final responses.\n\n"
                "Your objective is to solve the User Goal using the available tools.\n"
                "At each step, output a JSON object matching the AgentAction schema.\n\n"
                f"Available tools:\n{get_tool_definitions()}\n\n"
                "Instructions:\n"
                "1. Read the current progress history carefully to understand what actions you already performed.\n"
                "2. Choose the next tool to run. Make sure to provide exact parameters.\n"
                "3. If you have completed the goal, set action='FINAL' and provide your final response to the user.\n"
                "4. Avoid repeating a failing action with the exact same parameters.\n\n"
                f"{active_proj_str}"
                f"{session_folder_str}"
                f"{rules_block_str}"
                f"{loaded_skill_str}"
                f"{relevant_memories_str}"
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

    def _quick_gemini_call(self, prompt: str) -> str:
        """Runs a fast text generation call on Gemini without schemas or tools."""
        if not self.is_connected or not self.client:
            return "none"
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            logger.warning(f"Quick Gemini Call failed: {e}")
        return "none"

    def _maybe_load_relevant_skill(self, user_input: str) -> str:
        """Lightweight pre-check — does this request match a known skill?"""
        from app.core.skill_repo import get_skill_summaries, load_skill_full_text
        try:
            summaries = get_skill_summaries()
            if not summaries.strip():
                return ""
        except Exception:
            return ""

        check_prompt = f"""
        User request: "{user_input}"

        Available expert skills:
        {summaries}

        Does this request clearly match ONE of these skills? 
        Reply with ONLY the exact skill name, or "none" if no clear match.
        Do not output any introductory or formatting text.
        """
        result = self._quick_gemini_call(check_prompt).strip()

        if result and result.lower() != "none":
            # Strip potential quotes/md formatting
            clean_result = result.replace("`", "").replace("'", "").replace('"', "").strip()
            # If the output returned has newlines, take the first line
            clean_result = clean_result.split("\n")[0].strip()
            
            skill_text = load_skill_full_text(clean_result)
            if skill_text:
                logger.info(f"Auto-loaded skill: {clean_result}")
                return f"\n\nLOADED EXPERT SKILL — {clean_result}:\n{skill_text}\n\n"
        return ""

