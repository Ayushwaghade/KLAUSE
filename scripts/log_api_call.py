import os
import sys
import json
from pathlib import Path
from loguru import logger

# Set the working directory to E:\KLAUSE so imports work cleanly
sys.path.insert(0, "E:\\KLAUSE")

from app.core.brain import Brain
from app.core.context import context

def log_api_call():
    logger.info("Initializing KLAUSE Brain instance...")
    
    # Configure mock session context to simulate a fresh query
    context.session_id = "diagnostic_session"
    context.current_project_path = "E:\\KLAUSE"
    
    # Instantiate the Brain matching KLAUSE configuration
    brain = Brain()
    
    user_input = "open brave for me"
    logger.info(f"Target user prompt: '{user_input}'")
    
    # We will temporarily intercept the logger.debug messages or construct the prompt
    # and call the API exactly as brain.think does, logging the contents to files.
    
    # Let's rebuild the prompt logic exactly from brain.py to write it to disk
    from app.tools.base import get_tool_definitions
    from app.core.rules_manager import get_rules_manager
    from app.memory.memory_manager import get_memory_manager
    
    active_proj_str = f"Active Project Path: '{context.current_project_path}'\n"
    state_context_str = f"Active Desktop Window Title: 'VS Code - check_sync.py'\n"
    session_folder_str = f"Active Session Data Folder: 'E:\\KLAUSE\\clause'\n\n"
    
    rules_str = get_rules_manager().get_rules(filter_tag=None)
    rules_block_str = f"STRICT USER RULES (rules.md):\n{rules_str}\n\n" if rules_str else ""
    
    # Check memories
    relevant_memories_str = ""
    try:
        memories = get_memory_manager().search_semantic_memories(user_input, limit=8)
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
        logger.warning(f"RAG lookup failed: {e}")
        
    part_1_desc = (
        "You are KLAUSE — a dedicated, warm, and highly capable personal AI engineering companion. "
        "You act. You do not describe what you could do, suggest what the user might try, or simulate results. "
        "When given a goal, you accomplish it using your tools.\n\n"
        "You assist Ayush. Address him warmly and directly as 'Ayush'. Act as an active engineering partner. "
        "Offer proactive help, suggest logical next steps, and ask engaging follow-up questions."
    )
    part_5_tone = "TONE: Warm, supportive, highly capable, and dedicated companion. Address the user as 'Ayush'.\n"
    
    # Construct complete prompt
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
        "  Gmail:                       https://mail.google.com/\n\n"
        "════════════════════════════════════════════════════════════\n"
        "PART 5 — COMMUNICATION RULES\n"
        "════════════════════════════════════════════════════════════\n\n"
        f"{part_5_tone}"
        "NEVER SAY WHAT YOU ARE ABOUT TO DO: Do not say 'I will now run git_status...' or 'Let me open the browser.' Call the tool. Report the result directly.\n"
        "BREVITY: Keep final summaries to 1-3 sentences unless presenting lists, search data, or research.\n"
        "RESPONSE POPULATION: When setting action='FINAL', you MUST populate the 'response' key with your final conversational message to Ayush. Do not leave 'response' empty.\n\n"
        "════════════════════════════════════════════════════════════\n"
        "PART 7 — ACTIVE PROJECT & TELEMETRY CONTEXT\n"
        "════════════════════════════════════════════════════════════\n\n"
        f"{active_proj_str}"
        f"{state_context_str}"
        f"{session_folder_str}"
        f"{rules_block_str}"
        f"{relevant_memories_str}"
        f"User Goal: {user_input}\n\n"
        f"Current Progress:\nNo steps taken yet.\n"
    )

    logger.info("Writing generated raw prompt to E:\\KLAUSE\\logs\\sent_prompt.txt...")
    Path("E:\\KLAUSE\\logs").mkdir(exist_ok=True)
    Path("E:\\KLAUSE\\logs\\sent_prompt.txt").write_text(prompt, encoding="utf-8")
    
    # Call Gemini API
    logger.info("Executing API request to Gemini...")
    from google import genai
    from google.genai import types
    
    response = brain.client.models.generate_content(
        model=brain.model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=brain.schema
        )
    )
    
    raw_response = response.text.strip()
    logger.info("Writing received raw response to E:\\KLAUSE\\logs\\received_response.json...")
    Path("E:\\KLAUSE\\logs\\received_response.json").write_text(raw_response, encoding="utf-8")
    
    print("\n--- SENT PROMPT SUMMARY (Saved to logs/sent_prompt.txt) ---")
    print(f"Total prompt length: {len(prompt)} characters")
    print("User Goal:", user_input)
    print("\n--- RECEIVED API RESPONSE (Saved to logs/received_response.json) ---")
    print(raw_response)

if __name__ == "__main__":
    log_api_call()
