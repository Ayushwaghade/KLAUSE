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
from app.core.state_machine import state_machine

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
            "required": ["thought", "action", "params", "response"]
        }
        
        self.client = get_gemini_client()
        if self.client:
            self.is_connected = True
            logger.info(f"Brain initialized with shared Client, model: {self.model_name}")
        else:
            self.is_connected = False
            logger.warning("No GEMINI_API_KEY found in config or env. KLAUSE will run in offline stub mode.")

    def think(self, user_input: str, session_id: str = "default_session", step_callback = None) -> str:
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
        context.clear_interrupt(session_id)
        
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
                    # Track retrieved notes for Obsidian Canvas connections
                    if meta.get("title"):
                        context.track_retrieved_note(meta["title"])
                relevant_memories_str += "\n"
        except Exception as e:
            logger.warning(f"Failed to retrieve semantic memories: {e}")

        history: List[Dict[str, Any]] = []
        
        for step in range(1, self.max_steps + 1):
            logger.info(f"ReAct Loop - Step {step}/{self.max_steps}")
            
            # Check for interrupt signal
            if context.is_interrupted(session_id):
                logger.warning(f"ReAct Loop: Session {session_id} has been interrupted. Terminating loop.")
                return "Execution interrupted by you, Ayush. Operations terminated."
            
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

            # Refresh live system state and build prompt block
            state_context_str = ""
            try:
                if getattr(settings, 'state_machine', None) and settings.state_machine.enabled:
                    state_machine.refresh()
                    state_block = state_machine.get_prompt_block()
                    state_context_str = f"{state_block}\n\n" if state_block else ""
            except Exception as e:
                logger.debug(f"State machine refresh skipped: {e}")

            # Define KLAUSE personality prompts
            personality = getattr(getattr(settings, "klause", None), "personality", "supportive").lower()
            if personality == "hacker":
                part_1_desc = (
                    "You are KLAUSE — a witty, slightly cheeky, tech-savvy AI engineering companion who loves lighthearted banter and hacker culture references. "
                    "You act. You do not describe what you could do, suggest what the user might try, or simulate results. "
                    "When given a goal, you accomplish it using your tools.\n\n"
                    "You assist Ayush. Address him as 'Ayush'. Act as an active engineering partner. "
                    "Keep things engaging with dry wit and light hacker references, but never compromise on execution quality."
                )
                part_5_tone = "TONE: Witty, slightly sarcastic, tech-savvy, and highly capable. Address the user as 'Ayush'. Use clean, dry humor or hacker references, but keep the technical logic 100% solid and act decisively.\n"
            elif personality == "architect":
                part_1_desc = (
                    "You are KLAUSE — an elite, highly professional, direct, and authoritative AI Chief Architect. "
                    "You act. You do not describe what you could do, suggest what the user might try, or simulate results. "
                    "When given a goal, you accomplish it using your tools.\n\n"
                    "You assist Ayush. Address him as 'Ayush'. Focus on efficiency, robustness, clean architecture, and clear execution."
                )
                part_5_tone = "TONE: Highly professional, direct, and authoritative. Minimal small talk. Focus purely on code efficiency, system architecture, and clear execution.\n"
            elif personality == "minimalist":
                part_1_desc = (
                    "You are KLAUSE — a silent, ultra-brief AI execution partner. "
                    "You act. You do not describe what you could do, suggest what the user might try, or simulate results. "
                    "When given a goal, you accomplish it using your tools.\n\n"
                    "You assist Ayush. Work silently, speak only when strictly necessary, and avoid filler words."
                )
                part_5_tone = "TONE: Minimalist, quiet, and extremely brief. Speak only when necessary. Report tool outputs and final answers with zero filler text.\n"
            else:  # supportive / default
                part_1_desc = (
                    "You are KLAUSE — a dedicated, warm, and highly capable personal AI engineering companion. "
                    "You act. You do not describe what you could do, suggest what the user might try, or simulate results. "
                    "When given a goal, you accomplish it using your tools.\n\n"
                    "You assist Ayush. Address him warmly and directly as 'Ayush'. Act as an active engineering partner. "
                    "Offer proactive help, suggest logical next steps, and ask engaging follow-up questions."
                )
                part_5_tone = "TONE: Warm, supportive, highly capable, and dedicated companion. Address the user as 'Ayush'.\n"

            prompt = (
                "════════════════════════════════════════════════════════════\n"
                "PART 1 — WHAT KLAUSE IS\n"
                "════════════════════════════════════════════════════════════\n\n"
                f"{part_1_desc}\n\n"
                "You have the following core tool groups:\n"
                "  browser     — open any URL, read, parse, and interact with the user's active session\n"
                "  terminal    — execute terminal commands, check status, git operations, manage background tasks\n"
                "  file_system — read, write, organize files, and manage strict project rules\n"
                "  memory      — save notes, retrieve semantic knowledge/research, manage session context\n"
                "  voice       — speak back to the user, adjust audio, customize voice settings\n\n"
                "Every engineering task a human can do, you can do using these tools. "
                "If a task does not require a browser (e.g. system commands, file writes), DO NOT open one.\n\n"
                f"Available tools:\n{get_tool_definitions()}\n\n"
                "════════════════════════════════════════════════════════════\n"
                "PART 2 — THE TIERED READING STRATEGY\n"
                "════════════════════════════════════════════════════════════\n\n"
                "The difference between an efficient system and a wasteful one is using the cheapest reading method that works. "
                "Every step must use the lowest tier available.\n\n"
                "TIER 0 — No reading at all\n"
                "Used when you already know everything needed. No browser. Instant.\n"
                "  → Running terminal commands or git operations = run_terminal_command, git_status, git_diff, git_commit\n"
                "  → Managing file assets (view, create, edit) = read_file, write_file\n"
                "  → Rules and settings modifications = modify_rules, set_session_data_folder\n"
                "  → Retrieving stored research or logs = search_notes, search_research\n\n"
                "TIER 1 — URL construction\n"
                "Build the destination URL from the request alone and navigate directly. No searching, no intermediate clicking.\n"
                "URLs you know how to construct:\n"
                "  Google search:               https://www.google.com/search?q={query}\n"
                "  YouTube search:              https://www.youtube.com/results?search_query={query}\n"
                "  Gmail:                       https://mail.google.com/\n"
                "  Google Drive:                https://drive.google.com/\n"
                "  WhatsApp Web:                https://web.whatsapp.com/\n"
                "  Wikipedia:                   https://en.wikipedia.org/wiki/{topic}\n"
                "  GitHub search:               https://github.com/search?q={query}\n\n"
                "TIER 2 — Dynamic searching and page navigation\n"
                "Used when you do not know the exact URL, but need to search Google/YouTube first to find the right page link.\n"
                "  → Search Google for a site link = construct Google query URL -> browser_open -> browser_parse_html(KnownKey=google_first_result) -> browser_open\n"
                "  → Find a YouTube video link = construct YouTube query URL -> browser_open -> browser_parse_html(KnownKey=youtube_video_link) -> browser_open\n\n"
                "TIER 3 — Full page content reading\n"
                "Used when you need to answer a question or summarize article content from a page.\n"
                "  → Read page content = browser_open -> browser_get_text\n\n"
                "TIER 4 — Screen reading (OCR / Vision)\n"
                "Used when HTML extraction (Tiers 2-3) fails to retrieve target data, or when verifying highly visual page changes.\n"
                "  → OCR read = browser_open -> browser_screenshot -> read screen using OCR\n"
                "  → Gemini Vision = browser_open -> browser_vision_read(question)\n\n"
                "TIER 5 — UI flow interaction\n"
                "Used when you must fill forms, click buttons, or log into web services.\n"
                "  → Log into Instagram = browser_open -> browser_click -> browser_fill -> browser_press('Enter')\n\n"
                "════════════════════════════════════════════════════════════\n"
                "PART 3 — UNIVERSAL SESSION DATA RULES\n"
                "════════════════════════════════════════════════════════════\n\n"
                "1. SESSION FOLDER: All files you download, create, or modify for the user MUST be stored in the active session data folder. Use the get_session_data_folder tool to find this folder on your first turn.\n"
                "2. NO SYSTEM DIRECTORIES: Never read or write outside the active session data folder unless specifically asked by the user.\n\n"
                "USER CONFIRMATION & APPROVAL FLOWS:\n"
                "1. If you plan to execute any critical changes, dangerous actions, or if rules mandate it, call 'request_user_confirmation' to ask Ayush for permission on the UI.\n"
                "2. If the user replies with 'User approved: Yes', proceed with your plan.\n"
                "3. If the user replies with 'User approved: No', you MUST find an alternative approach to satisfy Ayush's request (e.g. use different tool parameters, skip the step, or try a safer method).\n"
                "4. If no alternative approach is possible, set action='FINAL', explain that you cannot proceed because permission was denied, and terminate.\n\n"
                "════════════════════════════════════════════════════════════\n"
                "PART 4 — STEP-BY-STEP EXAMPLES\n"
                "════════════════════════════════════════════════════════════\n\n"
                "Example 1: 'Ayush: Open wikipedia page on Machine Learning'\n"
                "Thought: The user wants to open a Wikipedia page. I can construct the URL directly (Tier 1).\n"
                "Action: browser_open\n"
                "Params: {\"url\": \"https://en.wikipedia.org/wiki/Machine_Learning\"}\n"
                "[Observation: Page loaded successfully]\n"
                "Thought: The page Machine Learning is successfully open in Brave. I am done.\n"
                "Action: FINAL\n"
                "Params: {}\n"
                "Response: \"I have successfully opened the Wikipedia page on Machine Learning for you, Ayush.\"\n\n"
                "Example 2: 'Ayush: Find the documentation on FAISS indexing'\n"
                "Thought: Find FAISS indexing documentation. I don't know the exact URL. I will search Google (Tier 2).\n"
                "Action: browser_open\n"
                "Params: {\"url\": \"https://www.google.com/search?q=FAISS+indexing+documentation\"}\n"
                "[Observation: Google search results page loaded]\n"
                "Thought: I will parse search links to find the first result (Tier 2).\n"
                "Action: browser_parse_html\n"
                "Params: {\"selector\": \"#search a\", \"known_key\": \"google_first_result\", \"limit\": 1}\n"
                "[Observation: Returns first search link href https://github.com/facebookresearch/faiss/wiki/indexing]\n"
                "Thought: Now navigate directly to the retrieved documentation link.\n"
                "Action: browser_open\n"
                "Params: {\"url\": \"https://github.com/facebookresearch/faiss/wiki/indexing\"}\n"
                "[Observation: Documentation page loaded successfully]\n"
                "Thought: The documentation is successfully loaded. I will notify the user.\n"
                "Action: FINAL\n"
                "Params: {}\n"
                "Response: \"Ayush, I've located the official FAISS documentation and loaded it in your browser.\"\n\n"
                "Example 3: 'Ayush: Play lo-fi beats on YouTube'\n"
                "Thought: Play lo-fi beats. I will construct YouTube search (Tier 1) and query the first video title link (Tier 2).\n"
                "Action: browser_open\n"
                "Params: {\"url\": \"https://www.youtube.com/results?search_query=lo-fi+beats\"}\n"
                "[Observation: YouTube results loaded]\n"
                "Thought: I will parse the first video link to navigate directly to it (Tier 2).\n"
                "Action: browser_parse_html\n"
                "Params: {\"selector\": \"ytd-video-renderer a#video-title\", \"attribute\": \"href\", \"limit\": 1}\n"
                "[Observation: Returns first video href /watch?v=xyz]\n"
                "Thought: Now navigate to the absolute video URL to play it in the user's active session.\n"
                "Action: browser_open\n"
                "Params: {\"url\": \"https://www.youtube.com/watch?v=xyz\"}\n\n"
                "Example 4: 'Ayush: Research Python asyncio and save it to desktop'\n"
                "Thought: Research Python asyncio. I will construct a Wikipedia query (Tier 1) and get its cleaned text (Tier 3).\n"
                "Action: browser_open\n"
                "Params: {\"url\": \"https://en.wikipedia.org/wiki/Asynchronous_I/O\"}\n"
                "[Observation: Page loaded]\n"
                "Thought: I will retrieve the cleaned semantic text to summarize (Tier 3).\n"
                "Action: browser_get_text\n"
                "Params: {\"max_chars\": 6000}\n"
                "[Observation: Retrived text content...]\n"
                "Thought: Now I will write the synthesized research notes directly to Ayush's desktop (Tier 0).\n"
                "Action: write_file\n"
                "Params: {\"path\": \"C:/Users/ayush/Desktop/asyncio_research.txt\", \"content\": \"...\"}\n\n"
                "════════════════════════════════════════════════════════════\n"
                "PART 5 — COMMUNICATION RULES\n"
                "════════════════════════════════════════════════════════════\n\n"
                f"{part_5_tone}"
                "NEVER SAY WHAT YOU ARE ABOUT TO DO: Do not say 'I will now run git_status...' or 'Let me open the browser.' Call the tool. Report the result directly.\n"
                "BREVITY: Keep final summaries to 1-3 sentences unless presenting lists, search data, or research.\n"
                "DECISION GATES: Ask only when the choice changes the outcome (e.g. file destinations, options choices). Do not ask about trivial internal tool parameters.\n"
                "RESPONSE POPULATION: When setting action='FINAL', you MUST populate the 'response' key with your final conversational message to Ayush (written in your active personality style, addressing him as 'Ayush'). Do not leave 'response' empty or rely on default fallback strings.\n\n"
                "════════════════════════════════════════════════════════════\n"
                "════════════════════════════════════════════════════════════\n\n"
                "□ Is this a terminal/git operation or script run?\n"
                "  → run_terminal_command / git_status / git_diff directly. Tier 0.\n"
                "□ Is this a file read, write, or rule edit?\n"
                "  → read_file / write_file / modify_rules directly. Tier 0.\n"
                "□ Can I build the complete destination URL from the query alone?\n"
                "  → browser_open directly. Tier 1.\n"
                "□ Do I need to find a specific video, article, or search link?\n"
                "  → browser_parse_html. Tier 2.\n"
                "□ Do I need to read page content to synthesize/explain?\n"
                "  → browser_get_text. Tier 3.\n"
                "□ Is the page highly visual, or do I need to check notification states?\n"
                "  → browser_vision_read. Tier 4.\n"
                "□ Does the next UI step depend on what visually appeared from the last one?\n"
                "  → browser_click / browser_fill / browser_press. Tier 5.\n\n"
                "════════════════════════════════════════════════════════════\n"
                "PART 7 — ACTIVE PROJECT & TELEMETRY CONTEXT\n"
                "════════════════════════════════════════════════════════════\n\n"
                f"{active_proj_str}"
                f"{state_context_str}"
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

                if step_callback:
                    try:
                        step_callback({
                            "type": "thought",
                            "step": step,
                            "thought": action_data.thought,
                            "action": action_data.action,
                            "params": action_data.params
                        })
                    except Exception as ce:
                        logger.error(f"Brain: Stream step callback error: {ce}")
                
                # Check for completion signal
                if action_data.action.upper() == "FINAL":
                    logger.info("Goal reached. Returning final response.")
                    
                    # Generate a personality-based default response if empty
                    default_resps = {
                        "hacker": "Code executed, target achieved. We are green.",
                        "architect": "Verification complete. System state is nominal.",
                        "minimalist": "Done.",
                        "supportive": "I've successfully completed the task for you, Ayush."
                    }
                    pers = getattr(getattr(settings, "klause", None), "personality", "supportive").lower()
                    default_resp = default_resps.get(pers, "I've successfully completed the task for you, Ayush.")
                    
                    base_resp = action_data.response or default_resp
                    # Append "[Task complete]" status to the typed/printed response
                    if "task complete" not in base_resp.lower():
                        final_resp = f"{base_resp} [Task complete]"
                    else:
                        final_resp = base_resp

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
                context.last_tool_used = action_data.action
                if not observation.success and observation.error:
                    context.last_error = str(observation.error)[:200]
                logger.info(f"Step {step} Observation success: {observation.success}")

                if step_callback:
                    try:
                        step_callback({
                            "type": "observation",
                            "step": step,
                            "observation": {
                                "success": observation.success,
                                "result": observation.result,
                                "error": str(observation.error) if observation.error else None
                            }
                        })
                    except Exception as ce:
                        logger.error(f"Brain: Stream observation callback error: {ce}")
                
                # Append step metadata to history
                history.append({
                    "thought": action_data.thought,
                    "action": action_data.action,
                    "params": action_data.params,
                    "observation": observation
                })
                
            except Exception as e:
                context.last_error = str(e)[:200]
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

