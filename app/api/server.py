import os
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, Query, Body, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId
from loguru import logger
import uvicorn

from app.api.security import verify_token, get_or_generate_token
from app.config.config import settings
from app.core.context import context
from app.core.brain import Brain
from app.memory.memory_manager import get_memory_manager
from app.automation.rule_engine import rule_engine, RuleModel
from app.automation.scheduler import scheduler
from app.voice.tts import tts_engine
from app.core.orb_state_broadcaster import orb_broadcaster
import datetime
from app.memory.obsidian_connector import (
    get_obsidian_vault_path,
    set_obsidian_vault_path,
    ObsidianConnector
)
from app.memory.knowledge_base import get_knowledge_base

app = FastAPI(title="KLAUSE Local Integration API")

# Explicit CORS allowance for Tauri custom schemes
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "tauri://localhost",
        "https://tauri.localhost",
        "http://localhost:5173", # Vite Dev Server
        "http://localhost:1420", # Tauri Dev Port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

brain = Brain()

# --- Pydantic Request Models ---
class TaskUpdate(BaseModel):
    task_id: str
    status: str

class RuleCreate(BaseModel):
    rule_id: str
    event_type: str
    action_type: str
    action_payload: Dict[str, Any]
    filter_pattern: str = None

class ProjectCreate(BaseModel):
    name: str
    path: str
    description: str = ""

# --- HTTP REST Handlers ---

@app.get("/api/auth/token", tags=["Auth"])
def get_auth_token():
    """Returns the current verification token (used during Tauri initialization)."""
    return {"token": get_or_generate_token()}

@app.get("/api/projects", tags=["Projects"], dependencies=[Depends(verify_token)])
def list_projects():
    """Retrieve all workspace projects from database."""
    try:
        mgr = get_memory_manager()
        projects = list(mgr.db.projects.find())
        result = []
        for p in projects:
            p["id"] = str(p.pop("_id"))
            result.append(p)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects", tags=["Projects"], dependencies=[Depends(verify_token)])
def create_project(data: ProjectCreate):
    """Manually register a new workspace project path."""
    try:
        mgr = get_memory_manager()
        res = mgr.save_project(name=data.name, path=data.path, description=data.description)
        return {"status": "success", "message": f"Project '{data.name}' registered successfully.", "result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects/open", tags=["Projects"], dependencies=[Depends(verify_token)])
def open_project_workspace(path: str = Body(..., embed=True)):
    """Sets KLAUSE's active project path."""
    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail=f"Directory '{path}' does not exist on disk.")
    context.current_project_path = os.path.abspath(path)
    return {"status": "success", "active_project": context.current_project_path}

@app.get("/api/tasks", tags=["Tasks"], dependencies=[Depends(verify_token)])
def list_tasks():
    """Fetch tasks for Kanban board."""
    try:
        mgr = get_memory_manager()
        tasks = list(mgr.db.tasks.find())
        result = []
        for t in tasks:
            t["id"] = str(t.pop("_id"))
            result.append(t)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks/batch-update", tags=["Tasks"], dependencies=[Depends(verify_token)])
def batch_update_tasks(updates: List[TaskUpdate]):
    """Batch updates task card status (e.g. Kanban drags)."""
    try:
        mgr = get_memory_manager()
        success_count = 0
        for up in updates:
            res = mgr.db.tasks.update_one(
                {"_id": ObjectId(up.task_id)},
                {"$set": {"status": up.status}}
            )
            if res.modified_count > 0:
                success_count += 1
        return {"status": "success", "updated_count": success_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rules", tags=["Rules"], dependencies=[Depends(verify_token)])
def list_rules():
    """Retrieve registered automation rules."""
    rules = rule_engine.rules
    return [r.model_dump() for r in rules]

@app.post("/api/rules", tags=["Rules"], dependencies=[Depends(verify_token)])
def add_rule(data: RuleCreate):
    """Add a new automation rule with basic schema verification."""
    try:
        rule = RuleModel(
            rule_id=data.rule_id,
            event_type=data.event_type,
            action_type=data.action_type,
            action_payload=data.action_payload,
            filter_pattern=data.filter_pattern,
            enabled=True
        )
        msg = rule_engine.add_rule(rule)
        return {"status": "success", "message": msg}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation failed: {e}")

@app.delete("/api/rules/{rule_id}", tags=["Rules"], dependencies=[Depends(verify_token)])
def delete_rule(rule_id: str):
    """Permanently deletes a registered automation rule."""
    if rule_engine.remove_rule(rule_id):
        return {"status": "success", "message": f"Rule '{rule_id}' removed successfully."}
    raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found.")

@app.get("/api/schedule", tags=["Schedule"], dependencies=[Depends(verify_token)])
def list_schedule_jobs():
    """List persistent scheduled cron/one-shot jobs."""
    try:
        return scheduler.list_jobs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/schedule/cron", tags=["Schedule"], dependencies=[Depends(verify_token)])
def add_cron_schedule(job_id: str = Body(...), command: str = Body(...), cron_expression: str = Body(...)):
    """Registers a recurring cron job."""
    res = scheduler.add_cron_job(job_id, command, cron_expression)
    if "Error" in res:
        raise HTTPException(status_code=400, detail=res)
    return {"status": "success", "message": res}

@app.delete("/api/schedule/{job_id}", tags=["Schedule"], dependencies=[Depends(verify_token)])
def delete_schedule_job(job_id: str):
    """Permanently deletes a scheduled job."""
    if scheduler.remove_job(job_id):
        return {"status": "success", "message": f"Job '{job_id}' removed successfully."}
    raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

# --- Knowledge Base & Obsidian Endpoints ---

class ObsidianConfig(BaseModel):
    vault_path: str

@app.get("/api/knowledge/search", tags=["Knowledge"], dependencies=[Depends(verify_token)])
def search_knowledge(query: str = Query(...), limit: int = Query(5)):
    """Semantic search on the vector store."""
    try:
        kb = get_knowledge_base()
        results = kb.search(query, limit=limit)
        # Format results for the frontend MemoryItem schema
        formatted = []
        for idx, r in enumerate(results):
            meta = r.get("metadata") or {}
            dist = r.get("distance", 1.0)
            relevance = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
            formatted.append({
                "id": r.get("id", f"s{idx}"),
                "timestamp": meta.get("created_at", "Unknown"),
                "type": meta.get("source_type", "knowledge_ingest"),
                "content": f"{meta.get('title', 'Document')}: {r.get('content', '')}",
                "relevance": relevance
            })
        return formatted
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/knowledge/timeline", tags=["Knowledge"], dependencies=[Depends(verify_token)])
def get_knowledge_timeline(limit: int = Query(20)):
    """Lists recent knowledge base ingestion events."""
    try:
        from app.memory.database import get_db
        db = get_db()
        cursor = db.research.find().sort([("created_at", -1)]).limit(limit)
        timeline = []
        for doc in cursor:
            created_at = doc.get("created_at")
            timestamp = "Recently"
            if isinstance(created_at, datetime.datetime):
                timestamp = created_at.strftime("%Y-%m-%d %H:%M")
            elif isinstance(created_at, str):
                timestamp = created_at[:16]
                
            source_type = doc.get("source_type", "knowledge_ingest")
            title = doc.get("title", "Document")
            
            content = f"Ingested: {title}"
            if doc.get("source_url"):
                content = f"Scraped URL: {doc.get('source_url')}"
            elif doc.get("file_path"):
                content = f"Indexed document: {doc.get('file_path')}"
                
            timeline.append({
                "id": str(doc["_id"]),
                "timestamp": timestamp,
                "type": source_type,
                "content": content
            })
        return timeline
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/knowledge/obsidian/status", tags=["Knowledge"], dependencies=[Depends(verify_token)])
def get_obsidian_status():
    """Returns the current path and sync statistics for the Obsidian Vault."""
    try:
        from app.memory.database import get_db
        db = get_db()
        vault_path = get_obsidian_vault_path()
        
        info = db.settings.find_one({"key": "obsidian_sync_info"}) or {}
        last_sync = info.get("last_sync", "Never")
        total_notes = info.get("total_notes", 0)
        
        return {
            "vault_path": vault_path,
            "last_sync": last_sync,
            "total_notes": total_notes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/knowledge/obsidian/config", tags=["Knowledge"], dependencies=[Depends(verify_token)])
def configure_obsidian(config: ObsidianConfig):
    """Configures the Obsidian Vault path."""
    try:
        set_obsidian_vault_path(config.vault_path)
        connector = ObsidianConnector()
        res = connector.scan_and_sync()
        return {
            "status": "success",
            "message": "Vault path configured successfully.",
            "sync_result": res
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/knowledge/obsidian/sync", tags=["Knowledge"], dependencies=[Depends(verify_token)])
def sync_obsidian():
    """Manually triggers an incremental sync of the Obsidian vault."""
    try:
        connector = ObsidianConnector()
        res = connector.scan_and_sync()
        if res.get("status") == "error":
            raise HTTPException(status_code=400, detail=res.get("message"))
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- WebSockets Streaming Channels ---

def parse_yes_no(text: str) -> Optional[bool]:
    clean = text.strip().lower().rstrip(".!?,")
    if clean in ("yes", "y", "yeah", "yup", "ok", "okay", "confirm", "approve", "go ahead", "sure", "do it"):
        return True
    if clean in ("no", "n", "nope", "nay", "cancel", "deny", "stop", "don't"):
        return False
    return None

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, token: str = Query(None)):
    """
    WebSocket route for real-time text prompt streaming, thinking steps, and tool execution logs.
    Supports asynchronous interrupts and yes/no user permission responses.
    """
    expected_token = get_or_generate_token()
    if token != expected_token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    await websocket.accept()
    logger.info("WS Chat: Client connection established.")
    
    loop = asyncio.get_running_loop()
    incoming_queue = asyncio.Queue()
    active_session_id = "default_session"

    def step_callback(step_data: Dict[str, Any]):
        """Runs inside executor thread, sends updates back asynchronously."""
        asyncio.run_coroutine_threadsafe(
            websocket.send_json(step_data),
            loop
        )

    # Register initial connection in the global thread-safe context
    context.set_connection(active_session_id, websocket, loop)

    # Background task to read messages from the client asynchronously
    async def ws_reader():
        nonlocal active_session_id
        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type")
                session_id = data.get("session_id", "default_session")
                
                # Dynamic context update if session ID shifts
                if session_id != active_session_id:
                    context.remove_connection(active_session_id)
                    active_session_id = session_id
                    context.set_connection(active_session_id, websocket, loop)

                if msg_type == "interrupt":
                    logger.warning(f"WS Chat: Received manual interrupt event for session '{active_session_id}'")
                    context.interrupt_session(active_session_id)
                    await websocket.send_json({
                        "type": "thought",
                        "step": 99,
                        "thought": "Ayush triggered an interrupt. Halting...",
                        "action": "HALT",
                        "params": {}
                    })
                elif msg_type == "confirmation_response":
                    approved = data.get("approved", False)
                    logger.info(f"WS Chat: Received confirmation response for session '{active_session_id}': approved={approved}")
                    context.resolve_confirmation(active_session_id, approved)
                else:
                    # Standard prompt message
                    prompt = data.get("prompt", "")
                    if not prompt:
                        continue
                        
                    # Check if there is an active confirmation prompt waiting for the user
                    if context.has_active_confirmation(active_session_id):
                        yes_no = parse_yes_no(prompt)
                        if yes_no is not None:
                            logger.info(f"WS Chat: Interpreted text prompt '{prompt}' as confirmation response approved={yes_no}")
                            context.resolve_confirmation(active_session_id, yes_no)
                            continue
                        else:
                            # Prompt is not a yes/no response, indicating the user wants to interrupt the current action!
                            logger.warning(f"WS Chat: Intercepted text prompt '{prompt}' while active confirmation is waiting. Triggering auto-interrupt.")
                            context.interrupt_session(active_session_id)
                            
                    await incoming_queue.put(data)
        except WebSocketDisconnect:
            logger.info("WS Chat: Reader connection disconnected.")
        except Exception as e:
            logger.error(f"WS Chat: Reader encounter error: {e}")

    reader_task = asyncio.create_task(ws_reader())

    try:
        while True:
            # Block waiting for items in the queue
            data = await incoming_queue.get()
            session_id = data.get("session_id", "default_session")
            prompt = data.get("prompt", "")
            
            logger.info(f"WS Chat: Processing prompt '{prompt}' for session '{session_id}'")
            
            # Instantly halt any active speaking output when a new prompt starts
            tts_engine.stop()
            
            def run_brain_thinking():
                return brain.think(prompt, session_id=session_id, step_callback=step_callback)
                
            final_response = await loop.run_in_executor(None, run_brain_thinking)
            
            # Update Obsidian Canvas connections after each thinking loop
            try:
                canvas_data = context.get_canvas_tracking()
                if canvas_data["created_notes"] or canvas_data["referenced_urls"] or canvas_data["retrieved_notes"]:
                    def run_canvas_update():
                        connector = ObsidianConnector()
                        connector.update_connections_canvas(
                            query=prompt,
                            created_notes=canvas_data["created_notes"],
                            referenced_urls=canvas_data["referenced_urls"],
                            retrieved_notes=canvas_data["retrieved_notes"]
                        )
                    await loop.run_in_executor(None, run_canvas_update)
            except Exception as e:
                logger.warning(f"WS Chat: Canvas update failed (non-critical): {e}")
            
            # Speak the final response back to the user out loud
            tts_engine.speak(final_response)
            
            # Send completion response back
            await websocket.send_json({
                "type": "final",
                "response": final_response
            })
            
    except Exception as e:
        logger.error(f"WS Chat: Websocket Loop error: {e}")
    finally:
        reader_task.cancel()
        context.remove_connection(active_session_id)
        try:
            await websocket.close()
        except Exception:
            pass


@app.websocket("/ws/audio")
async def websocket_audio(websocket: WebSocket, token: str = Query(None)):
    """
    WebSocket route for raw binary microphone audio streaming inputs.
    Transcribes audio to text and replies to the client.
    """
    expected_token = get_or_generate_token()
    if token != expected_token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    await websocket.accept()
    logger.info("WS Audio: Client connection established.")
    
    # Resolve temporary logs folder for voice
    logs_dir = settings.paths.logs
    os.makedirs(logs_dir, exist_ok=True)
    temp_wav_path = os.path.join(logs_dir, "ws_mic_input.wav")
    
    loop = asyncio.get_running_loop()
    
    try:
        while True:
            # Receive raw binary audio bytes
            audio_bytes = await websocket.receive_bytes()
            if not audio_bytes:
                continue
                
            # Write bytes to temp wav
            with open(temp_wav_path, "wb") as f:
                f.write(audio_bytes)
                
            # Run transcription inside executor
            def do_transcription():
                from app.voice.stt import transcribe_audio
                return transcribe_audio(temp_wav_path)
                
            text = await loop.run_in_executor(None, do_transcription)
            
            await websocket.send_json({
                "type": "transcript",
                "text": text or ""
            })
            
    except WebSocketDisconnect:
        logger.info("WS Audio: Client connection closed.")
    except Exception as e:
        logger.error(f"WS Audio: WebSocket error: {e}")
        try:
            await websocket.close()
        except Exception:
            pass

@app.websocket("/ws/orb-state")
async def websocket_orb_state(websocket: WebSocket, token: str = Query(None)):
    """
    WebSocket route for real-time orb visual state broadcasting.
    Clients receive {"type": "orb_state", "state": "<state>"} messages.
    """
    expected_token = get_or_generate_token()
    if token != expected_token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    await websocket.accept()
    logger.info("WS OrbState: Client connection established.")
    
    orb_broadcaster.register(websocket)
    
    # Send current state immediately on connect
    try:
        await websocket.send_json({"type": "orb_state", "state": orb_broadcaster.current_state})
    except Exception:
        orb_broadcaster.unregister(websocket)
        return
    
    try:
        while True:
            # Keep connection alive — client doesn't send data, just receives broadcasts
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WS OrbState: Client connection closed.")
    except Exception as e:
        logger.error(f"WS OrbState: WebSocket error: {e}")
    finally:
        orb_broadcaster.unregister(websocket)

def start_server(port: int = 8000):
    """Bootstraps the local FastAPI Uvicorn service."""
    logger.info(f"Starting KLAUSE Local Server on http://localhost:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
