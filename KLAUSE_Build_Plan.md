# KLAUSE — Complete Build Plan
### Your Personal AI Engineering Assistant

---

## What is KLAUSE?

KLAUSE is a personal AI assistant that runs on your Windows desktop.
It understands your projects, automates repetitive tasks, remembers everything,
and acts as your daily engineering partner.

You talk to it. It acts.

---

## Development Phases Overview

| Phase | Name               | What You Build                          | Est. Time |
|-------|--------------------|-----------------------------------------|-----------|
| 0     | Foundation         | Project setup, config, core skeleton    | 3–4 days  |
| 1     | Brain              | Gemini integration, intent, responses   | 4–5 days  |
| 2     | Memory             | SQLite + FAISS, conversation history    | 4–5 days  |
| 3     | Developer Tools    | VS Code, Git, Terminal control          | 5–7 days  |
| 4     | Desktop Automation | Files, apps, windows, clipboard         | 4–5 days  |
| 5     | Voice              | Wake word, speech-to-text, TTS          | 4–5 days  |
| 6     | Browser Agent      | Web search, page reading, downloads     | 5–6 days  |
| 7     | Knowledge Base     | Research storage, semantic search       | 4–5 days  |
| 8     | Vision             | Screen capture, OCR, error reading      | 4–5 days  |
| 9     | Event Engine       | System events, automation triggers      | 4–5 days  |
| 10    | UI                 | React + Tauri desktop interface         | 7–10 days |

---

## Phase 0 — Foundation

> Goal: Get the skeleton running. Every future module plugs into this.

### Tasks

- [ ] Create project folder structure
- [ ] Set up Python virtual environment
- [ ] Install base dependencies
- [ ] Create config system (YAML + .env)
- [ ] Set up logging (Loguru)
- [ ] Create a basic CLI entry point
- [ ] Write a simple "KLAUSE is alive" test

### Project Folder Structure

```
klause/
│
├── app/
│   ├── core/               # Orchestrator, planner, dispatcher
│   ├── agents/             # Research, coding, browser, memory agents
│   ├── tools/              # Filesystem, terminal, VS Code, Git
│   ├── memory/             # SQLite + FAISS
│   ├── automation/         # Scheduler, workflows, event engine
│   ├── vision/             # OCR, screen capture
│   ├── voice/              # Wake word, STT, TTS
│   ├── api/                # FastAPI endpoints
│   ├── models/             # Pydantic data models
│   └── config/             # YAML configs
│
├── frontend/               # React + Tauri UI
│
├── plugins/                # Future extensions
│
├── knowledge_base/         # Indexed research and documents
│   ├── embeddings/
│   └── documents/
│
├── projects/               # Per-project metadata and context
│
├── logs/
│
├── tests/
│
├── .env
├── config.yaml
├── requirements.txt
└── main.py
```

### Config System (config.yaml)

```yaml
klause:
  name: KLAUSE
  version: 0.1.0
  wake_word: "klause"

ai:
  gemini_model: gemini-1.5-pro
  embedding_model: models/embedding-001
  max_tokens: 8192

memory:
  db_path: ./data/klause.db
  vector_store_path: ./data/faiss_index
  max_conversation_history: 50

voice:
  enabled: false
  stt_model: base
  tts_engine: piper

paths:
  knowledge_base: ./knowledge_base
  projects: ./projects
  logs: ./logs
```

### Base Dependencies

```
# AI
google-generativeai
openai                   # optional fallback

# Backend
fastapi
uvicorn
websockets

# Memory
sqlmodel
faiss-cpu
sentence-transformers

# Automation
pyautogui
pygetwindow
pyperclip
pywin32
mss

# Voice
faster-whisper
TTS

# Browser
playwright

# Vision
pytesseract
opencv-python

# Utilities
loguru
python-dotenv
pyyaml
apscheduler
gitpython
rich                     # nice terminal output
typer                    # CLI framework
```

---

## Phase 1 — Brain (Core AI)

> Goal: KLAUSE can understand what you say and respond intelligently.

### Tasks

- [ ] Connect Gemini API
- [ ] Build Intent Recognizer (what does the user want?)
- [ ] Build Planner (break goal into steps)
- [ ] Build Dispatcher (send steps to right module)
- [ ] Build Response Handler (format output nicely)
- [ ] Handle errors gracefully

### How the Brain Works

```
User Input
    ↓
Intent Recognizer
    ↓
Planner (Gemini)       ← creates a step-by-step action plan
    ↓
Dispatcher             ← routes each step to the right tool
    ↓
Tool Execution
    ↓
Response Handler       ← formats and returns result to user
```

### Intent Categories

| Intent              | Example Input                          |
|---------------------|----------------------------------------|
| OPEN_PROJECT        | "continue the antivirus project"       |
| RUN_COMMAND         | "start the dev server"                 |
| SEARCH_WEB          | "search for FAISS documentation"       |
| EXPLAIN_CODE        | "explain this function"                |
| CREATE_FILE         | "create a new Python file for auth"    |
| SAVE_RESEARCH       | "save this article to knowledge base"  |
| SHOW_TASKS          | "what are my pending tasks?"           |
| OPEN_APP            | "open VS Code"                         |
| AUTOMATION          | "run my morning routine"               |
| MEMORY_QUERY        | "what did I work on yesterday?"        |

### Planner Prompt (System Prompt for Gemini)

```
You are KLAUSE, a personal AI engineering assistant.

Your job is to understand what the user wants to do and
break it into a list of concrete actions.

Available tools:
- open_vscode(project_path)
- run_terminal_command(command)
- open_browser(url)
- search_web(query)
- read_file(path)
- write_file(path, content)
- open_application(name)
- save_to_memory(content, category)
- query_memory(query)
- save_research(content, title, tags)

Always return a JSON action plan like:
{
  "goal": "...",
  "steps": [
    {"tool": "tool_name", "params": {...}, "reason": "..."},
    ...
  ]
}
```

---

## Phase 2 — Memory

> Goal: KLAUSE never forgets anything important.

### Tasks

- [ ] Set up SQLite database with SQLModel
- [ ] Create tables: conversations, projects, tasks, notes, research
- [ ] Build memory write functions
- [ ] Build memory read/query functions
- [ ] Set up FAISS vector store
- [ ] Build semantic search (find related memories by meaning)
- [ ] Auto-save every conversation

### Database Schema

```sql
-- Conversations
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    session_id TEXT,
    role TEXT,              -- 'user' or 'assistant'
    content TEXT,
    timestamp DATETIME,
    project_id INTEGER
);

-- Projects
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    path TEXT,
    description TEXT,
    last_opened DATETIME,
    status TEXT,            -- 'active', 'paused', 'completed'
    tags TEXT               -- JSON array
);

-- Tasks
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    title TEXT,
    description TEXT,
    status TEXT,            -- 'pending', 'done', 'cancelled'
    priority TEXT,
    created_at DATETIME,
    completed_at DATETIME
);

-- Notes
CREATE TABLE notes (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    content TEXT,
    tags TEXT,
    created_at DATETIME
);

-- Research
CREATE TABLE research (
    id INTEGER PRIMARY KEY,
    title TEXT,
    content TEXT,
    source_url TEXT,
    tags TEXT,
    embedding_id TEXT,      -- reference to FAISS vector
    created_at DATETIME
);

-- Commands
CREATE TABLE commands (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    command TEXT,
    description TEXT,
    used_count INTEGER DEFAULT 0,
    last_used DATETIME
);
```

### Memory API

```python
# Save
memory.save_conversation(session_id, role, content, project_id)
memory.save_task(project_id, title, description, priority)
memory.save_note(project_id, content, tags)
memory.save_research(title, content, url, tags)
memory.save_command(project_id, command, description)

# Read
memory.get_conversation_history(session_id, limit=20)
memory.get_project(name)
memory.get_pending_tasks(project_id)
memory.get_recent_notes(project_id)
memory.search(query)               # semantic search across all memory
memory.get_project_context(name)   # full project snapshot
```

---

## Phase 3 — Developer Tools

> Goal: KLAUSE understands and controls your development environment.

### Tasks

- [ ] Build VS Code controller (open, switch file, run task)
- [ ] Build Terminal controller (run commands, read output)
- [ ] Build Git integration (status, log, diff, commit)
- [ ] Build Project Context loader (read codebase summary)
- [ ] Build TODO scanner (find TODOs in code)
- [ ] Store per-project session state

### VS Code Controller

```python
class VSCodeController:
    def open_project(self, path: str)
    def open_file(self, file_path: str)
    def run_task(self, task_name: str)          # runs tasks.json task
    def open_terminal(self)
    def install_extension(self, extension_id: str)
    def get_open_files(self) -> list[str]
```

### Terminal Controller

```python
class TerminalController:
    def run(self, command: str) -> str          # run and return output
    def run_async(self, command: str)           # fire and forget
    def run_in_vscode_terminal(self, command: str)
    def kill_process(self, process_name: str)
    def get_running_processes(self) -> list
```

### Git Integration

```python
class GitController:
    def get_status(self, repo_path: str) -> dict
    def get_recent_commits(self, repo_path: str, n=10) -> list
    def get_diff(self, repo_path: str) -> str
    def commit(self, repo_path: str, message: str)
    def get_branches(self, repo_path: str) -> list
    def get_current_branch(self, repo_path: str) -> str
```

### Project Context (What KLAUSE loads when you open a project)

```python
class ProjectContext:
    name: str
    path: str
    description: str
    last_session_notes: str
    pending_tasks: list[Task]
    recent_commits: list[str]
    open_files: list[str]
    running_servers: list[str]
    recent_errors: list[str]
    tech_stack: list[str]
```

---

## Phase 4 — Desktop Automation

> Goal: KLAUSE can control your Windows desktop.

### Tasks

- [ ] Build App Launcher (open any application)
- [ ] Build File Manager (create, move, delete, search files)
- [ ] Build Window Manager (focus, resize, arrange windows)
- [ ] Build Clipboard Manager (read/write clipboard)
- [ ] Build Download Manager (watch downloads folder)
- [ ] Build Notification System (show Windows notifications)

### Desktop Controller

```python
class DesktopController:
    # Apps
    def open_app(self, name: str)
    def close_app(self, name: str)
    def focus_window(self, title: str)
    def list_open_windows(self) -> list[str]

    # Files
    def open_file(self, path: str)
    def create_folder(self, path: str)
    def move_file(self, src: str, dest: str)
    def delete_file(self, path: str)
    def search_files(self, query: str, directory: str) -> list[str]
    def find_file(self, filename: str) -> str

    # Clipboard
    def copy_to_clipboard(self, text: str)
    def read_clipboard(self) -> str

    # Notifications
    def notify(self, title: str, message: str)
```

### Automation Workflows

```python
# Example: Morning Routine
morning_routine = Workflow(
    name="morning_routine",
    steps=[
        Step(tool="open_app", params={"name": "Chrome"}),
        Step(tool="open_url", params={"url": "https://github.com"}),
        Step(tool="open_vscode", params={"project": "last_active"}),
        Step(tool="show_tasks", params={"filter": "today"}),
        Step(tool="speak", params={"text": "Good morning. Here are your tasks for today."})
    ]
)

# Example: Project Startup
project_startup = Workflow(
    name="start_project",
    steps=[
        Step(tool="open_vscode", params={"project": "{project_name}"}),
        Step(tool="run_command", params={"cmd": "npm run dev"}),
        Step(tool="open_browser", params={"url": "http://localhost:3000"}),
        Step(tool="show_tasks", params={"project": "{project_name}"}),
        Step(tool="summarize_commits", params={"project": "{project_name}"})
    ]
)
```

---

## Phase 5 — Voice

> Goal: You can talk to KLAUSE hands-free.

### Tasks

- [ ] Set up wake word detection ("Klause")
- [ ] Build Speech-to-Text (Faster-Whisper)
- [ ] Build Text-to-Speech (Piper offline)
- [ ] Handle continuous listening mode
- [ ] Build voice command pipeline
- [ ] Add push-to-talk mode (optional)

### Voice Pipeline

```
Microphone
    ↓
Wake Word Detection    ← listens always for "Klause"
    ↓
Speech Recording       ← records until silence
    ↓
Faster-Whisper STT     ← converts speech to text
    ↓
Brain (Phase 1)        ← processes intent
    ↓
Piper TTS              ← speaks the response
    ↓
Speaker
```

### Voice Controller

```python
class VoiceController:
    def start_listening(self)                  # begin wake word detection
    def stop_listening(self)
    def transcribe(self, audio_file) -> str    # speech to text
    def speak(self, text: str)                 # text to speech
    def set_voice(self, voice_name: str)
    def set_speaking_speed(self, speed: float)
```

### Voice Config

```yaml
voice:
  enabled: true
  wake_word: "klause"
  wake_word_sensitivity: 0.7
  stt_model: base.en           # faster-whisper model size
  tts_engine: piper
  tts_voice: en_US-ryan-medium
  speaking_speed: 1.0
  push_to_talk_key: "ctrl+space"
```

---

## Phase 6 — Browser Agent

> Goal: KLAUSE can browse the internet for you.

### Tasks

- [ ] Set up Playwright browser automation
- [ ] Build Web Search (Google/DuckDuckGo)
- [ ] Build Page Reader (extract readable text from any URL)
- [ ] Build Form Filler
- [ ] Build Download Manager
- [ ] Build Screenshot Capture (for vision)
- [ ] Build GitHub Integration (issues, PRs, repos)

### Browser Agent

```python
class BrowserAgent:
    def search(self, query: str) -> list[SearchResult]
    def open_url(self, url: str)
    def read_page(self, url: str) -> str              # extract clean text
    def screenshot(self, url: str) -> bytes
    def click(self, selector: str)
    def fill_form(self, fields: dict)
    def download_file(self, url: str, destination: str)
    def get_current_url(self) -> str
    def get_page_title(self) -> str

    # GitHub specific
    def get_github_issues(self, repo: str) -> list
    def get_github_prs(self, repo: str) -> list
    def get_github_commits(self, repo: str) -> list
```

### Search Result Model

```python
class SearchResult:
    title: str
    url: str
    snippet: str
    full_content: str | None   # fetched on demand
```

---

## Phase 7 — Knowledge Base

> Goal: Everything you research stays searchable forever.

### Tasks

- [ ] Build document ingestion pipeline (PDF, DOCX, MD, TXT, URL)
- [ ] Generate embeddings with Gemini
- [ ] Store embeddings in FAISS
- [ ] Build semantic search
- [ ] Build knowledge base query interface
- [ ] Organize by topics/tags
- [ ] Auto-save research from browser

### Knowledge Base Structure

```
knowledge_base/
├── documents/
│   ├── malware_analysis/
│   ├── web_security/
│   ├── python/
│   ├── react/
│   └── ...
├── embeddings/
│   └── faiss_index/
└── metadata.db
```

### Knowledge Base API

```python
class KnowledgeBase:
    def add_document(self, file_path: str, tags: list[str])
    def add_url(self, url: str, title: str, tags: list[str])
    def add_text(self, content: str, title: str, tags: list[str])
    def search(self, query: str, top_k=5) -> list[KnowledgeResult]
    def search_by_tag(self, tag: str) -> list[KnowledgeResult]
    def get_all_topics(self) -> list[str]
    def delete(self, document_id: str)
    def update_tags(self, document_id: str, tags: list[str])
```

### How Search Works

```
User query: "how does FAISS indexing work?"
    ↓
Generate embedding for query (Gemini Embedding API)
    ↓
FAISS similarity search → top 5 most relevant chunks
    ↓
Retrieve full context from SQLite
    ↓
Send to Gemini with context: "Answer using this knowledge..."
    ↓
Grounded, accurate answer from your own research
```

---

## Phase 8 — Vision

> Goal: KLAUSE can see your screen and understand what's happening.

### Tasks

- [ ] Build screen capture (mss)
- [ ] Build OCR for text extraction (Tesseract)
- [ ] Build error detector (reads terminal/console errors)
- [ ] Build VS Code reader (current file, current error)
- [ ] Build screenshot analyzer (Gemini Vision)
- [ ] Build PDF reader (PyMuPDF)

### Vision Controller

```python
class VisionController:
    def capture_screen(self) -> bytes                    # full screen
    def capture_region(self, x, y, w, h) -> bytes       # specific area
    def capture_window(self, window_title: str) -> bytes
    def extract_text(self, image: bytes) -> str          # OCR
    def analyze_screenshot(self, image: bytes) -> str    # Gemini Vision
    def read_terminal_error(self) -> str                 # detect error in terminal
    def read_vscode_error(self) -> str                   # detect error in VS Code
    def read_pdf(self, path: str) -> str
```

### Key Use Cases

```
You hit an error in your terminal
    ↓
KLAUSE captures the terminal window
    ↓
OCR extracts the error text
    ↓
Gemini analyzes it
    ↓
KLAUSE explains the error and suggests a fix
```

---

## Phase 9 — Event Engine

> Goal: KLAUSE reacts to things that happen on your system automatically.

### Tasks

- [ ] Build event listener system
- [ ] Define event types
- [ ] Build event handlers
- [ ] Build rule engine (if event X → do action Y)
- [ ] Build scheduler (run workflow at time T)

### Event Types

```python
class EventType(Enum):
    # System
    USB_CONNECTED         = "usb_connected"
    BATTERY_LOW           = "battery_low"
    NETWORK_CHANGED       = "network_changed"

    # Development
    BUILD_FAILED          = "build_failed"
    BUILD_SUCCESS         = "build_success"
    GIT_COMMIT            = "git_commit"
    FILE_CHANGED          = "file_changed"
    TEST_FAILED           = "test_failed"

    # Downloads
    DOWNLOAD_COMPLETE     = "download_complete"

    # Schedule
    MORNING_ROUTINE       = "morning_routine"
    DAILY_BACKUP          = "daily_backup"
    REMINDER              = "reminder"

    # Window
    APP_OPENED            = "app_opened"
    APP_CLOSED            = "app_closed"
```

### Event Rules (Examples)

```python
rules = [
    Rule(
        event=EventType.BUILD_FAILED,
        action="capture_terminal_and_analyze_error"
    ),
    Rule(
        event=EventType.DOWNLOAD_COMPLETE,
        action="notify_and_open_downloads"
    ),
    Rule(
        event=EventType.BATTERY_LOW,
        action="notify('Battery low. Save your work.')"
    ),
    Rule(
        event=EventType.GIT_COMMIT,
        action="save_commit_to_memory"
    ),
]
```

### Scheduler

```python
scheduler.add_job("morning_routine", cron="0 9 * * *")     # 9am daily
scheduler.add_job("daily_backup",    cron="0 23 * * *")    # 11pm daily
scheduler.add_reminder("Review PRs", at="2026-07-01 10:00")
```

---

## Phase 10 — UI (Desktop Interface)

> Goal: A clean desktop app to interact with KLAUSE visually.

### Tech Choice: React + Tauri

Use **Tauri** (not Electron) because:
- Much lighter on RAM (important on your laptop)
- Faster startup
- Smaller app size
- Native Windows feel

### UI Screens

**1. Chat Interface** (main screen)
- Talk to KLAUSE by text or voice
- See action steps being executed live
- See KLAUSE's responses with code blocks, links

**2. Project Dashboard**
- List of all your projects
- Status, last opened, pending tasks
- One-click to open any project

**3. Tasks Board**
- All pending tasks across all projects
- Kanban-style: Pending / In Progress / Done

**4. Knowledge Base Browser**
- Browse all your saved research
- Search by topic or semantic query
- Add new documents or URLs

**5. Automation Manager**
- List of all your automation workflows
- Enable/disable
- Trigger manually or by schedule

**6. Memory Timeline**
- Timeline of what you worked on
- Filter by project, date, type

### Frontend Stack

```
React 18
Tauri 2.0
Tailwind CSS
Zustand (state management)
React Query (API calls)
Lucide React (icons)
```

---

## Full Tech Stack Summary

### AI
| Component          | Technology                  |
|--------------------|-----------------------------|
| LLM                | Gemini 1.5 Pro (API)        |
| Embeddings         | Gemini Embedding API        |
| Vision             | Gemini 1.5 Pro Multimodal   |
| Speech-to-Text     | Faster-Whisper (local)      |
| Text-to-Speech     | Piper (local, offline)      |

### Backend
| Component          | Technology                  |
|--------------------|-----------------------------|
| Framework          | FastAPI                     |
| Async              | asyncio                     |
| WebSocket          | FastAPI WebSockets          |
| Scheduler          | APScheduler                 |
| CLI                | Typer + Rich                |

### Memory
| Component          | Technology                  |
|--------------------|-----------------------------|
| Database           | SQLite                      |
| ORM                | SQLModel                    |
| Vector Store       | FAISS                       |
| Embeddings Cache   | Local disk                  |

### Automation
| Component          | Technology                  |
|--------------------|-----------------------------|
| Mouse & Keyboard   | PyAutoGUI                   |
| Windows API        | pywin32                     |
| Window Management  | pygetwindow                 |
| Clipboard          | pyperclip                   |
| Screen Capture     | mss                         |
| OCR                | Tesseract + pytesseract     |
| Image Processing   | OpenCV                      |

### Browser
| Component          | Technology                  |
|--------------------|-----------------------------|
| Browser Control    | Playwright                  |
| HTTP               | httpx                       |
| HTML Parsing       | BeautifulSoup4              |

### Frontend
| Component          | Technology                  |
|--------------------|-----------------------------|
| Framework          | React 18                    |
| Desktop Shell      | Tauri 2.0                   |
| Styling            | Tailwind CSS                |
| State              | Zustand                     |
| API Calls          | React Query                 |

### DevOps
| Component          | Technology                  |
|--------------------|-----------------------------|
| Logging            | Loguru                      |
| Config             | YAML + python-dotenv        |
| Testing            | pytest                      |
| Formatting         | black + ruff                |

---

## Recommended Build Order

```
Week 1-2:    Phase 0 + Phase 1     →  KLAUSE can think and respond
Week 3:      Phase 2               →  KLAUSE remembers everything
Week 4-5:    Phase 3               →  KLAUSE controls your dev tools
Week 6:      Phase 4               →  KLAUSE controls your desktop
Week 7:      Phase 5               →  You can speak to KLAUSE
Week 8-9:    Phase 6               →  KLAUSE can browse the web
Week 10:     Phase 7               →  KLAUSE stores your research
Week 11:     Phase 8               →  KLAUSE can see your screen
Week 12:     Phase 9               →  KLAUSE reacts to system events
Week 13-14:  Phase 10              →  KLAUSE gets a proper UI
```

---

## Versioning Roadmap

| Version | What Works                                                     |
|---------|----------------------------------------------------------------|
| v0.1    | CLI + Gemini responses + basic memory                          |
| v0.2    | VS Code + Terminal + Git control                               |
| v0.3    | Voice input/output                                             |
| v0.4    | Browser agent + web search                                     |
| v0.5    | Knowledge base + research storage                              |
| v0.6    | Vision + error detection                                       |
| v0.7    | Event engine + automation workflows                            |
| v1.0    | Full desktop UI + all modules stable                           |

---

## First Thing To Build (Day 1)

Before anything else, get this working:

```python
# main.py
from rich.console import Console
from app.core.brain import Brain

console = Console()
brain = Brain()

console.print("[bold green]KLAUSE is online.[/bold green]")

while True:
    user_input = input("You: ")
    if user_input.lower() == "exit":
        break
    response = brain.think(user_input)
    console.print(f"[cyan]KLAUSE:[/cyan] {response}")
```

That's your foundation. Everything else plugs in around it.
