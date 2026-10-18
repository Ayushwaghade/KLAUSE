import os
import sys
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=140, right=140):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def add_page_number(run):
    fldChar1 = parse_xml(r'<w:fldChar %s w:fldCharType="begin"/>' % nsdecls('w'))
    instrText = parse_xml(r'<w:instrText %s xml:space="preserve"> PAGE </w:instrText>' % nsdecls('w'))
    fldChar2 = parse_xml(r'<w:fldChar %s w:fldCharType="separate"/>' % nsdecls('w'))
    fldChar3 = parse_xml(r'<w:fldChar %s w:fldCharType="end"/>' % nsdecls('w'))
    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)
    run._r.append(fldChar3)

def set_paragraph_bottom_border(p, sz="12", space="4", color="000000"):
    pPr = p._p.get_or_add_pPr()
    pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="double" w:sz="{sz}" w:space="{space}" w:color="{color}"/></w:pBdr>')
    pPr.append(pBdr)

def set_paragraph_top_border(p, sz="12", space="4", color="000000"):
    pPr = p._p.get_or_add_pPr()
    pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:top w:val="double" w:sz="{sz}" w:space="{space}" w:color="{color}"/></w:pBdr>')
    pPr.append(pBdr)

def add_chapter_header(doc, chapter_num, title_text):
    p1 = doc.add_paragraph()
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.paragraph_format.space_before = Pt(20)
    p1.paragraph_format.space_after = Pt(4)
    p1.paragraph_format.keep_with_next = True
    run1 = p1.add_run(f"CHAPTER {chapter_num}")
    run1.font.name = "Times New Roman"
    run1.font.size = Pt(14)
    run1.font.bold = True
    run1.font.color.rgb = RGBColor(0, 0, 0)

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.space_before = Pt(0)
    p2.paragraph_format.space_after = Pt(18)
    p2.paragraph_format.keep_with_next = True
    run2 = p2.add_run(title_text.upper())
    run2.font.name = "Times New Roman"
    run2.font.size = Pt(16)
    run2.font.bold = True
    run2.font.color.rgb = RGBColor(0, 0, 0)

def add_subheading(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0, 0, 0)
    return p

def add_subsubheading(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0, 0, 0)
    return p

def add_body_p(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(0, 0, 0)
    return p

def add_bullet_item(doc, bold_prefix, text):
    p = doc.add_paragraph(style='List Bullet')
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(4)
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.font.name = "Times New Roman"
        r_pre.font.size = Pt(12)
        r_pre.font.bold = True
        r_pre.font.color.rgb = RGBColor(0, 0, 0)
    run = p.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(0, 0, 0)
    return p

def add_figure_caption(doc, caption_text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(12)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(caption_text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(0, 0, 0)

def generate_report():
    doc = Document()

    # Configure Margins & Page Size (A4, Left 1.5", Right 1", Top 1", Bottom 1")
    for section in doc.sections:
        section.page_width = Inches(8.27)
        section.page_height = Inches(11.69)
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.5)
        section.right_margin = Inches(1.0)

        # Header Configuration
        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("KLAUSE")
        hrun.font.name = "Times New Roman"
        hrun.font.size = Pt(10)
        hrun.font.color.rgb = RGBColor(0, 0, 0)
        set_paragraph_bottom_border(hp, sz="12", space="4", color="000000")

        # Footer Configuration
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
        frun_left = fp.add_run("P.R.M.I.T. & R, BADNERA // B.E (IT) / /2025-26")
        frun_left.font.name = "Times New Roman"
        frun_left.font.size = Pt(9.5)
        frun_left.font.color.rgb = RGBColor(0, 0, 0)

        # Add right aligned page number in footer
        frun_tab = fp.add_run("\t\t")
        frun_page = fp.add_run()
        frun_page.font.name = "Times New Roman"
        frun_page.font.size = Pt(10)
        frun_page.font.color.rgb = RGBColor(0, 0, 0)
        add_page_number(frun_page)
        set_paragraph_top_border(fp, sz="12", space="4", color="000000")

    # Set Default Normal Style
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(12)
    font.color.rgb = RGBColor(0, 0, 0)

    # ---------------------------------------------------------------------------
    # CHAPTER 1: INTRODUCTION
    # ---------------------------------------------------------------------------
    add_chapter_header(doc, 1, "INTRODUCTION")

    add_subheading(doc, "1.1 Problem Statement")
    add_body_p(doc,
        "Modern software engineering requires developers to continuously navigate fragmented tool ecosystems, juggling terminal windows, IDE diagnostic logs, browser documentation, Git repositories, and personal note vaults. Software engineers spend a significant portion of their workday context-switching between disconnected applications—copy-pasting compiler stack traces into search engines, manually cross-referencing code documentation, updating personal knowledge notes, and executing repetitive command-line sequences. Existing desktop assistants either offer passive text completion without operating system autonomy, or rely on fragile cloud-based computer-vision agents that incur extreme token latency and suffer from high failure rates on native desktop graphical interfaces."
    )
    add_body_p(doc,
        "Furthermore, personal knowledge management systems (such as Obsidian vaults) remain isolated from live development environments. Developers frequently record architectural decisions, code snippets, and research notes in markdown files, yet current AI coding agents lack persistent bidirectional synchronization with these personal second-brain repositories. Without a localized, privacy-focused assistant capable of orchestrating desktop applications, executing terminal commands, indexing notes into semantic vector stores, and maintaining long-term conversational memory, software engineers remain burdened by operational friction and context fragmentation."
    )

    add_subheading(doc, "1.2 Motivation")
    add_body_p(doc,
        "The primary motivation behind KLAUSE (Agentic AI Desktop Engineering Assistant) is to build an intelligent, privacy-preserving, personal engineering partner that operates directly on the developer's Windows desktop. Rather than replacing the engineer, KLAUSE acts as a highly integrated companion that understands local project structures, automates repetitive system workflows, remembers past technical decisions across multi-session conversations, and visually maps knowledge connections."
    )
    add_body_p(doc,
        "By integrating an asynchronous Reasoning-and-Acting (ReAct) cognitive engine with local vector storage (ChromaDB), MongoDB session state, native Windows desktop automation, Tesseract OCR vision, local speech transcription (Faster-Whisper), and dynamic Obsidian canvas generation, KLAUSE bridges the gap between high-level AI reasoning and local desktop execution. This enables engineers to interact naturally via voice or text while KLAUSE autonomously coordinates workspace tools, diagnoses code errors, and maintains a structured knowledge graph of all project activities."
    )

    add_subheading(doc, "1.3 Objectives")
    add_body_p(doc,
        "The main technical and functional objectives of the KLAUSE project are:"
    )
    add_bullet_item(doc, "Interactive 3D Voice & Text UI: ", "Develop a responsive React + Three.js dynamic orb interface with state transitions (listening, processing, responding, idle, error) and real-time audio amplitude visualization.")
    add_bullet_item(doc, "Autonomous ReAct Brain & Tool Router: ", "Implement a robust Reasoning and Acting cognitive loop with dynamic schema-driven tool routing, intent recognition, and self-correcting error recovery.")
    add_bullet_item(doc, "Hierarchical Dual-Tier Memory (RAG): ", "Combine MongoDB for session/raw note persistence with persistent ChromaDB vector stores for fast semantic code and document retrieval.")
    add_bullet_item(doc, "Bidirectional Obsidian Vault Integration: ", "Recursively parse YAML frontmatter and inline #tags from local markdown vaults, constructing visual node-and-edge connection graphs in KLAUSE_Connections.canvas files.")
    add_bullet_item(doc, "OS & Desktop Automation: ", "Automate Windows desktop interaction, process lifecycle management, window focusing, and clipboard monitoring via declarative rules engines and custom schedules.")
    add_bullet_item(doc, "OCR Vision & Stack-Trace Reader: ", "Utilize Tesseract OCR and window screen capture to automatically extract error messages, compiler stack traces, and terminal outputs.")
    add_bullet_item(doc, "Real-Time Local Speech Engine: ", "Provide push-to-talk voice activation, SAPI/Piper text-to-speech feedback, and local speech transcription via Faster-Whisper.")
    add_bullet_item(doc, "Developer Tool Integration: ", "Provide specialized Agent-Computer Interfaces (ACI) for VS Code navigation, terminal command execution, and automated Git version control workflows.")

    add_subheading(doc, "1.4 Organization of Seminar Report")
    add_body_p(doc, "This seminar report is organized into the following structured chapters:")
    add_bullet_item(doc, "Chapter 1: Introduction – ", "Outlines the problem statement, core motivation, project objectives, and report structure.")
    add_bullet_item(doc, "Chapter 2: Literature Survey – ", "Reviews 30 foundational research papers across 8 core domains and presents a structured gap analysis table highlighting how KLAUSE addresses current literature limitations.")
    add_bullet_item(doc, "Chapter 3: Methodology – ", "Details the conceptual design, core system modules, operational workflows, and technology choices.")
    add_bullet_item(doc, "Chapter 4: System Design and Architecture – ", "Presents the layered system architecture, component-level design, user interaction flow, and data flow models.")
    add_bullet_item(doc, "Chapter 5: Implementation – ", "Explains the development environment setup, frontend React/Three.js integration, backend FastAPI orchestrator, dual-memory systems, OCR vision engine, and voice pipelines.")
    add_bullet_item(doc, "Chapter 6: Results – ", "Provides functional walkthroughs and detailed screen demonstrations of all 17 implemented KLAUSE modules.")
    add_bullet_item(doc, "Chapter 7: Conclusion – ", "Summarizes the key contributions, technical achievements, and concluding remarks.")
    add_bullet_item(doc, "Chapter 8: Advantages and Disadvantages – ", "Analyzes the technical strengths and current limitations of the platform.")
    add_bullet_item(doc, "Chapter 9: Applications and Future Scope – ", "Explores real-world deployment scenarios and outlines planned future enhancements.")

    # ---------------------------------------------------------------------------
    # CHAPTER 2: LITERATURE SURVEY
    # ---------------------------------------------------------------------------
    add_chapter_header(doc, 2, "LITERATURE SURVEY")

    add_body_p(doc,
        "The development of autonomous AI assistants, desktop computer control, and developer knowledge systems has experienced exponential growth over recent years. Research has evolved from simple text completion models toward multi-modal cognitive agents capable of tool interaction, memory management, and visual computer interaction. This chapter presents a detailed survey of 30 landmark research papers across 8 core architectural pillars, concluding with a comprehensive gap analysis table demonstrating how KLAUSE resolves limitations in existing literature."
    )

    add_subheading(doc, "2.1 Review of Foundational Research Papers")

    add_subsubheading(doc, "Pillar 1: Core Agentic Reasoning, ReAct & Planning Loops")
    add_body_p(doc,
        "Yao et al. [1] introduced ReAct (Reasoning and Acting), establishing the foundational loop of generating verbal reasoning traces alongside task actions, significantly reducing hallucination compared to isolated acting. Shinn et al. [2] developed Reflexion, demonstrating that verbal self-reflection stored in episodic buffers enables agents to self-correct execution errors without weight updates. Yao et al. [3] proposed Tree of Thoughts (ToT), expanding chain-of-thought into tree-based search structures (BFS/DFS) for lookahead planning. Sumers et al. [4] formulated CoALA (Cognitive Architectures for Language Agents), standardizing the taxonomy of working memory, episodic storage, action spaces, and decision cycles."
    )

    add_subsubheading(doc, "Pillar 2: Tool Use, Function Calling & System Dispatch")
    add_body_p(doc,
        "Schick et al. [5] presented Toolformer, showing that LLMs can self-teach tool invocation via self-supervised loss filtering. Patil et al. [6] introduced Gorilla, solving parameter hallucination in API calls through retriever-aware instruction tuning. Qin et al. [7] created ToolLLM, evaluating agents over 16,000+ REST APIs using Depth-First Search Decision Trees (DFSDT) to handle multi-branch tool routing."
    )

    add_subsubheading(doc, "Pillar 3: Memory Systems & Vector Retrieval (RAG)")
    add_body_p(doc,
        "Packer et al. [8] designed MemGPT, treating bounded LLM context windows like physical OS RAM and paging data between working memory, session DBs, and archival vector stores. Lewis et al. [9] authored the seminal RAG paper, combining dense vector retrieval (DPR) with neural generators. Park et al. [10] developed Generative Agents, introducing a memory stream scored by recency, importance, and query relevance. Asai et al. [11] introduced Self-RAG, using reflection tokens to adaptively trigger retrieval and evaluate passage quality."
    )

    add_subsubheading(doc, "Pillar 4: Knowledge Graphs & Note Synchronization")
    add_body_p(doc,
        "Edge et al. [12] created GraphRAG at Microsoft Research, building hierarchical entity community graphs for global corpus summarization. Jiménez Gutiérrez et al. [13] developed HippoRAG, mimicking hippocampal indexing via Personalized PageRank over knowledge graphs for multi-hop recall. Wen et al. [14] introduced MindMap, demonstrating graph-of-thought prompting over structured subgraphs. Jiang et al. [15] formulated KG-Agent, casting knowledge graph reasoning as iterative tool invocation."
    )

    add_subsubheading(doc, "Pillar 5: Windows OS Interaction, Desktop Automation & Computer Use")
    add_body_p(doc,
        "Zhang et al. [16] developed Microsoft UFO, a UI-focused dual-agent system tailored for native Windows desktop automation using UI Automation (UIA) and vision. Bonatti et al. [17] introduced Windows Agent Arena, benchmarking multi-modal OS agents across native Windows 11 tasks. Xie et al. [18] created OSWorld, highlighting that vision-only computer control agents achieve low success rates due to fragile visual grounding. Tan et al. [19] introduced Cradle, exploring general computer control from screen pixels and low-level mouse/keyboard events."
    )

    add_subsubheading(doc, "Pillar 6: Autonomous Software Engineering & Developer Companions")
    add_body_p(doc,
        "Jimenez et al. [20] created SWE-bench, evaluating agents on resolving real GitHub issues across multi-file Python repositories. Yang et al. [21] developed SWE-agent, introducing Agent-Computer Interfaces (ACI) to prove that custom developer commands dramatically outperform standard bash terminals for LLMs. Hong et al. [22] developed MetaGPT, incorporating Standard Operating Procedures (SOPs) into multi-agent development. Qian et al. [23] introduced ChatDev, simulating virtual software development teams via multi-agent state machines."
    )

    add_subsubheading(doc, "Pillar 7: Screen Vision, OCR & Visual Error Reading")
    add_body_p(doc,
        "Lu et al. [24] created OmniParser at Microsoft Research, parsing raw screenshots into interactable bounding boxes and semantic icons via YOLOv8 and BLIP-2. Niu et al. [25] developed ScreenAgent (IJCAI 2024), implementing a visual action-perception-reflection loop. Cheng et al. [26] created SeeClick, predicting normalized (x,y) click targets directly from natural language. Smith [27] detailed the foundational Tesseract OCR pipeline, underpining KLAUSE's local terminal error extraction."
    )

    add_subsubheading(doc, "Pillar 8: Web Browsing, Voice Synthesis & Embodied UI")
    add_body_p(doc,
        "Zhou et al. [28] developed WebArena, benchmarking autonomous web agents over Playwright and Chrome DevTools Protocol. Radford et al. [29] introduced OpenAI Whisper, providing robust multilingual speech recognition. Safdari et al. [30] at Google DeepMind published 'Personality Traits in Large Language Models', demonstrating psychometric steerability of synthetic personality profiles in LLMs."
    )

    add_subheading(doc, "2.2 Literature Survey Overview and Gap Analysis")
    add_body_p(doc,
        "Table 2.1 presents a structured summary of the 30 reviewed literature papers, identifying their core limitations and outlining how KLAUSE resolves each gap through its hybrid desktop architecture:"
    )

    # Literature Overview Table
    table_data = [
        ("[1]", "ReAct (Yao et al., 2023)", "Tested in toy text environments; lacks live OS state or real-time event loops.", "Implements ReAct inside an async FastAPI + WebSocket event dispatcher coordinating live OS events."),
        ("[2]", "Reflexion (Shinn et al., 2023)", "Reflections remain in ephemeral prompt buffers and vanish upon process termination.", "Persists post-mortem reflections permanently in MongoDB and vector storage for cross-session recall."),
        ("[3]", "Tree of Thoughts (Yao et al., 2023)", "Branching factor causes combinatorial explosion, making it too slow for live desktop use.", "Replaces unconstrained tree search with structured build phases and pre-scoped tool categories."),
        ("[4]", "CoALA (Sumers et al., 2024)", "Conceptual taxonomy without a concrete production implementation for developer desktops.", "Directly implements CoALA's cognitive model as a functional Windows app with SQLite/Mongo and ChromaDB."),
        ("[5]", "Toolformer (Schick et al., 2023)", "Requires model fine-tuning for fixed APIs; cannot adapt to user-installed programs or changing CLIs.", "Employs dynamic, schema-driven Pydantic tool definitions (app/tools/base.py) with zero fine-tuning."),
        ("[6]", "Gorilla (Patil et al., 2023)", "Focuses on cloud REST APIs; fails on desktop window handles, subprocess streams, or OS permissions.", "Wraps native Windows APIs (pywin32, pygetwindow) with argument sanitization specifically tuned for local binaries."),
        ("[7]", "ToolLLM (Qin et al., 2024)", "Evaluated on synthetic RapidAPI endpoints; fragile under network drops or desktop system latency.", "Implements local fallback execution and a self-contained skill repository (skill_repo.py) running locally."),
        ("[8]", "MemGPT (Packer et al., 2023)", "Aimed at chatbot personas; lacks native integration with developer knowledge vaults or IDE codebases.", "Adapts virtual memory paging to bidirectional markdown vaults (Obsidian) and live git repository contexts."),
        ("[9]", "RAG (Lewis et al., 2020)", "Treats documents as flat text chunks, losing directory structures, file hierarchy, and code symbol relations.", "Augments ChromaDB vector search with path-aware metadata, YAML frontmatter filtering, and per-project namespaces."),
        ("[10]", "Generative Agents (Park et al., 2023)", "Simulated in an RPG sandbox; scoring heuristics are not tuned for code syntax or engineering events.", "Tailors memory streams to developer events: git commits, active window switches, and terminal failures."),
        ("[11]", "Self-RAG (Asai et al., 2024)", "Requires custom pre-trained reflection tokens, making it incompatible with commercial LLM APIs.", "Implements an algorithmic verification layer in knowledge_base.py evaluating retrieved chunk relevance before ingestion."),
        ("[12]", "GraphRAG (Edge et al., 2024)", "High LLM cost and latency to compute hierarchical communities across massive corpora.", "Leverages Obsidian wikilinks and #tags to bootstrap graphs instantly without full-corpus LLM passes, outputting .canvas files."),
        ("[13]", "HippoRAG (Gutiérrez et al., 2024)", "Graph extraction requires complex offline processing; does not dynamically update when user files change.", "Features live file-watcher synchronization (obsidian_connector.py) updating note nodes and edge mappings upon save."),
        ("[14]", "MindMap (Wen et al., 2024)", "Theoretical study on benchmark QA; lacks UI tools for users to inspect or edit the knowledge graph.", "Integrates with Obsidian's visual canvas format, allowing developers to visually inspect and edit reasoning nodes."),
        ("[15]", "KG-Agent (Jiang et al., 2025)", "Assumes structured RDF/KBs; unable to parse messy, semi-structured personal developer notes.", "Incorporates robust frontmatter regex parsing, markdown AST extraction, and inline tag extractors for unstructured notes."),
        ("[16]", "UFO (Zhang et al., 2024)", "Relies on cloud vision APIs for every click, leading to high latency and heavy API token costs.", "Prioritizes deterministic window APIs and CLI scripts first, falling back to vision/OCR only when necessary."),
        ("[17]", "Windows Agent Arena (Bonatti et al., 2024)", "Benchmark environment only; does not provide a persistent personal assistant that learns user habits.", "Acts as an ambient, persistent desktop companion with long-term memory, custom rules, and automated event scheduling."),
        ("[18]", "OSWorld (Xie et al., 2024)", "Exposes high failure rates (~88%) of vision-only agents on desktop UI interactions.", "Bypasses brittle visual clicks by prioritizing direct OS-level execution (terminal_tools.py, system_tools.py)."),
        ("[19]", "Cradle (Tan et al., 2024)", "Explores gaming environments (RDR2); lacks developer tool integration, IDE awareness, or code syntax handling.", "Tailors computer control specifically to developer workflows: managing VS Code, reading terminal errors, and switching windows."),
        ("[20]", "SWE-bench (Jimenez et al., 2024)", "Evaluates offline patch generation; does not support real-time user-in-the-loop pair programming.", "Provides interactive streaming chat, push-to-talk voice interrupts, and human-in-the-loop confirmation before destructive actions."),
        ("[21]", "SWE-agent (Yang et al., 2024)", "ACI operates exclusively inside headless Docker containers; cannot interact with native host desktop IDEs.", "Bridges the ACI concept directly into the user’s live Windows desktop, reading active VS Code windows and local processes."),
        ("[22]", "MetaGPT (Hong et al., 2024)", "Multi-role SOPs generate hundreds of messages, creating excessive latency unsuited for instant desktop assistance.", "Condenses SOPs into an instantaneous local rule engine (rule_engine.py) and declarative disposition settings (disposition.yaml)."),
        ("[23]", "ChatDev (Qian et al., 2024)", "Rigid waterfall stage progression; cannot easily handle spontaneous ad-hoc developer questions.", "Uses an adaptive state machine (state_machine.py) switching between rapid single-turn execution and multi-step build plans."),
        ("[24]", "OmniParser (Lu et al., 2024)", "Heavy visual inference overhead (running YOLOv8 + BLIP-2 simultaneously on multi-monitor desktops).", "Combines lightweight window clipping (pygetwindow) with local Tesseract OCR, triggering heavy visual parsers only when needed."),
        ("[25]", "ScreenAgent (Niu et al., 2024)", "Visual reflection loop is prone to infinite loops when UI elements do not change visually after failed clicks.", "Employs explicit timeout thresholds, process exit code checks, and fallback CLI queries when visual confirmation fails."),
        ("[26]", "SeeClick (Cheng et al., 2024)", "Sub-pixel coordinate prediction frequently drifts on high-DPI Windows displays or multi-monitor setups.", "Implements DPI-aware coordinate scaling and OS-level window focusing before dispatching simulated mouse/keyboard events."),
        ("[27]", "Tesseract OCR (Smith, 2007)", "Traditional OCR engine with zero semantic understanding of modern IDE syntax themes or terminal stack traces.", "Enhances raw Tesseract output with regex filtering (ERROR_PATTERNS in error_reader.py) and passes cleaned text to LLMs."),
        ("[28]", "WebArena (Zhou et al., 2024)", "Benchmarks web tasks in isolated sandboxes; disconnected from local user credentials or browser sessions.", "Connects directly to existing user browsers (Brave, Chrome, Edge) via Chrome DevTools Protocol (CDP_PORT = 9222)."),
        ("[29]", "Whisper (Radford et al., 2023)", "Standard PyTorch models introduce noticeable latency on desktop hardware, interfering with fluid voice chat.", "Integrates faster-whisper (CTranslate2 INT8 quantization) on local threads, delivering low-latency push-to-talk transcription."),
        ("[30]", "Personality Traits (Safdari et al., 2023)", "Studies static prompt priming on benchmark datasets; lacks dynamic personality adaptation based on workflow state.", "Implements a real-time disposition controller (disposition.py) modulating assistant tone based on task urgency and error states.")
    ]

    table = doc.add_table(rows=len(table_data) + 1, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    col_widths = [Inches(0.5), Inches(1.5), Inches(1.8), Inches(2.7)]

    headers = ["Sr. No.", "System / Paper", "Limitation", "KLAUSE Improvement"]
    hdr_row = table.rows[0]
    for idx, text in enumerate(headers):
        cell = hdr_row.cells[idx]
        cell.width = col_widths[idx]
        set_cell_background(cell, "EAEAEA")
        set_cell_margins(cell, top=100, bottom=100, left=120, right=120)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(text)
        r.font.bold = True
        r.font.size = Pt(9.5)

    for r_idx, row_vals in enumerate(table_data):
        row = table.rows[r_idx + 1]
        for c_idx, val in enumerate(row_vals):
            cell = row.cells[c_idx]
            cell.width = col_widths[c_idx]
            set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.05
            if c_idx == 0:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(val)
            r.font.size = Pt(8.5)
            if c_idx in (0, 1):
                r.font.bold = True

    add_figure_caption(doc, "Table 2.1. Literature Survey Overview and Gap Analysis Matrix")

    # ---------------------------------------------------------------------------
    # CHAPTER 3: METHODOLOGY
    # ---------------------------------------------------------------------------
    add_chapter_header(doc, 3, "METHODOLOGY")

    add_subheading(doc, "3.1 System Concept")
    add_body_p(doc,
        "KLAUSE is conceptualized as an intelligent, personal desktop engineering ecosystem that bridges natural human interaction (voice, streaming text, interactive 3D embodiment) with rigorous system-level execution. The platform operates on the user's local Windows machine, maintaining absolute data privacy while continuously observing development activities, analyzing compiler and terminal logs, orchestrating applications, and mapping research connections."
    )
    add_body_p(doc,
        "The core paradigm relies on a hybrid cognitive loop: high-level intent recognition and plan formulation are governed by Google Gemini models operating under a ReAct (Reasoning and Acting) execution pattern, while low-level system actions (window management, filesystem operations, OCR text extraction, git commands) are executed deterministically through Python system bindings. This dual structure prevents brittle computer control while preserving real-time responsiveness."
    )

    add_subheading(doc, "3.2 Proposed System & Core Modules")
    add_body_p(doc,
        "The proposed KLAUSE ecosystem comprises eight interconnected functional modules designed to handle specialized engineering responsibilities:"
    )
    add_bullet_item(doc, "Cognitive ReAct Brain & Tool Router: ", "Processes natural language inputs, formulates execution plans, dispatches tools dynamically, and executes self-correcting error recovery loops.")
    add_bullet_item(doc, "Interactive 3D Orb Frontend: ", "Built with React 19, TypeScript, Zustand, and Three.js. Renders a real-time 3D orb that visualizes assistant states (idle, listening, processing, responding, error) with smooth voice amplitude visualization.")
    add_bullet_item(doc, "Hierarchical Dual-Tier Memory System: ", "Integrates MongoDB for session state, raw conversational history, and note metadata with ChromaDB for semantic vector embeddings and dense similarity retrieval.")
    add_bullet_item(doc, "Obsidian Knowledge Connector: ", "Parses markdown vaults recursively, extracts YAML frontmatter and inline #tags, constructs entity-relationship graphs, and automatically builds KLAUSE_Connections.canvas visual maps.")
    add_bullet_item(doc, "OS & Desktop Automation Engine: ", "Manages Windows window handles, active process monitoring, clipboard state inspection, and rule-driven event automation.")
    add_bullet_item(doc, "OCR Vision & Stack-Trace Engine: ", "Captures target application windows (VS Code, Windows Terminal), processes image payloads via Tesseract OCR, and applies regular expressions to extract compiler stack traces and warnings.")
    add_bullet_item(doc, "Real-Time Local Speech Engine: ", "Provides push-to-talk microphone capture, local speech-to-text transcription via Faster-Whisper, and SAPI/Piper text-to-speech feedback.")
    add_bullet_item(doc, "Browser Navigation Agent: ", "Connects directly to user desktop browsers (Brave, Chrome, Edge) via Chrome DevTools Protocol (CDP port 9222) using Playwright for automated research, page reading, and downloads.")

    add_subheading(doc, "3.3 System Workflow and Operational Cycles")
    add_body_p(doc,
        "KLAUSE executes tasks through a structured four-phase operational cycle:"
    )
    add_bullet_item(doc, "1. Perceptual Ingestion Phase: ", "The system receives multi-modal user input via WebSocket text streams, push-to-talk audio frames, or automated OS events (e.g., active window change, file modification). Audio frames are transcribed locally by Faster-Whisper.")
    add_bullet_item(doc, "2. Cognitive Planning & Memory Assembly Phase: ", "The ReAct orchestrator queries MongoDB for current session state and searches ChromaDB for relevant project documentation and Obsidian notes. Assembled context is fed to the Gemini model to select appropriate tools.")
    add_bullet_item(doc, "3. Tool Execution & Reflection Phase: ", "The tool router invokes designated Python modules (VS Code API, Git bindings, Win32 window calls, Tesseract OCR). Tool outputs are captured as Observations. If execution fails, the Reflexion engine analyzes stdout/stderr logs and formulates a corrective action.")
    add_bullet_item(doc, "4. Response Generation & State Broadcast Phase: ", "The orchestrator generates the final natural language answer, streams text responses over WebSockets to the React frontend, updates the 3D Orb UI state, and syncs newly created notes or canvas connections to disk.")

    add_subheading(doc, "3.4 Technology Stack")
    add_body_p(doc,
        "Table 3.1 details the technology stack selected for KLAUSE, along with technical justifications for each component:"
    )

    tech_data = [
        ("Frontend UI", "React 19, Vite, TypeScript 6, Three.js, Zustand", "Provides ultra-fast 3D web-streaming rendering, dynamic state management, and real-time audio visualization."),
        ("Backend Framework", "Python 3.10+, FastAPI, Uvicorn, WebSockets, Loguru", "Delivers high-performance asynchronous API endpoints, live bidirectional streaming, and robust logging."),
        ("Cognitive LLM Engine", "Google Gemini API (Gemini 1.5 Pro / Flash)", "Offers state-of-the-art long-context reasoning, tool-calling support, and rapid inference speeds."),
        ("Vector Memory Store", "ChromaDB, Sentence-Transformers", "Enables persistent local vector embeddings for dense semantic code and document retrieval without external cloud APIs."),
        ("Transactional Database", "MongoDB Community Server (Port 27017)", "Stores structured session state, raw notes, gamification rules, user profiles, and chat history."),
        ("Desktop & OS Automation", "PyAutoGUI, PyGetWindow, PyWin32, MSS, Pyperclip", "Provides native Windows OS control, active window focusing, clipboard inspection, and screen capture."),
        ("Vision & OCR Engine", "Tesseract OCR, PyTesseract, OpenCV Python", "Extracts visible text, error dialogs, and terminal stack traces directly from application windows locally."),
        ("Voice Speech Engine", "Faster-Whisper (CTranslate2), Pywin32 SAPI / Piper TTS", "Delivers low-latency local speech-to-text transcription and clear voice feedback."),
        ("Browser Automation", "Playwright Async API, CDP (Port 9222)", "Connects directly to live user browsers for automated web research without isolated sandbox restrictions.")
    ]

    t_tech = doc.add_table(rows=len(tech_data) + 1, cols=3)
    t_tech.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_tech.autofit = False

    t_widths = [Inches(1.5), Inches(2.2), Inches(2.8)]
    hdr_tech = t_tech.rows[0]
    for idx, text in enumerate(["Component", "Technology", "Justification"]):
        cell = hdr_tech.cells[idx]
        cell.width = t_widths[idx]
        set_cell_background(cell, "EAEAEA")
        set_cell_margins(cell, top=100, bottom=100, left=120, right=120)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(text)
        r.font.bold = True
        r.font.size = Pt(9.5)

    for r_idx, row_vals in enumerate(tech_data):
        row = t_tech.rows[r_idx + 1]
        for c_idx, val in enumerate(row_vals):
            cell = row.cells[c_idx]
            cell.width = t_widths[c_idx]
            set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.05
            if c_idx == 0:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(val)
            r.font.size = Pt(8.5)
            if c_idx == 0:
                r.font.bold = True

    add_figure_caption(doc, "Table 3.1. KLAUSE Comprehensive Technology Stack")

    # ---------------------------------------------------------------------------
    # CHAPTER 4: SYSTEM DESIGN AND ARCHITECTURE
    # ---------------------------------------------------------------------------
    add_chapter_header(doc, 4, "SYSTEM DESIGN AND ARCHITECTURE")

    add_subheading(doc, "4.1 System Architecture Overview")
    add_body_p(doc,
        "KLAUSE follows a four-layered modular architecture designed to decouple user presentation, cognitive orchestration, data persistence, and system-level execution. This architecture ensures high operational speed, modular tool addition, and local privacy maintenance."
    )
    add_bullet_item(doc, "Presentation Layer (Frontend): ", "Built using React 19, Vite, and Three.js. Manages user text input, audio streams, dashboard navigation (Chat, Tasks, Rules, Knowledge Base), and renders the interactive 3D Orb state visualizer.")
    add_bullet_item(doc, "Application & Cognitive Layer (Backend Engine): ", "Hosted on a FastAPI asynchronous WebSockets server. Enforces authentication, houses the ReAct cognitive orchestrator (brain.py), manages dynamic tool routing (tool_router.py), and runs the disposition personality engine.")
    add_bullet_item(doc, "Memory & Storage Layer (Persistence Engine): ", "Combines MongoDB for transactional chat logs, user settings, and raw note data with persistent ChromaDB for dense vector embeddings and semantic search.")
    add_bullet_item(doc, "System & Hardware Integration Layer (Local Execution): ", "Interfaces directly with native Windows OS APIs (Win32), Tesseract OCR binaries, local Faster-Whisper speech models, VS Code APIs, and Playwright CDP browser instances.")

    add_subheading(doc, "4.2 Component-Level Design")
    add_body_p(doc,
        "Each core subsystem within KLAUSE operates with explicit responsibilities and interfaces:"
    )
    add_subsubheading(doc, "1. Frontend (React + Three.js)")
    add_bullet_item(doc, "", "Orb Canvas Component: Renders a dynamic 3D sphere using Three.js custom shaders, animating scale, noise displacement, and color transitions based on audio input levels and Orb state broadcasts (IDLE, LISTENING, PROCESSING, RESPONDING, ERROR).")
    add_bullet_item(doc, "", "Zustand State Store: Manages global application state, active chat sessions, live voice amplitudes, system notification logs, and panel tab routing.")

    add_subsubheading(doc, "2. Cognitive Engine (FastAPI + Gemini)")
    add_bullet_item(doc, "", "Brain Orchestrator (brain.py): Receives prompt payloads, retrieves context buffers, formats Pydantic tool schemas, and manages the ReAct execution loop.")
    add_bullet_item(doc, "", "Tool Router (tool_router.py): Inspects LLM function calls, validates argument types, routes requests to target Python tool scripts, and returns execution stdout/stderr observations.")
    add_bullet_item(doc, "", "Rules Engine (rule_engine.py): Evaluates user-defined automation rules (rules.md) and triggers pre-configured OS actions when specific system events occur.")

    add_subsubheading(doc, "3. Memory Engine (ChromaDB + MongoDB + Obsidian)")
    add_bullet_item(doc, "", "ChromaStore (chroma_store.py): Manages persistent vector collections, chunking incoming markdown and code files, and performing cosine similarity search.")
    add_bullet_item(doc, "", "Obsidian Connector (obsidian_connector.py): Recursively scans local Obsidian vaults, parses YAML frontmatter and inline #tags, builds entity connections, and generates visual KLAUSE_Connections.canvas maps.")

    add_subsubheading(doc, "4. Perceptual Engine (Vision & Voice)")
    add_bullet_item(doc, "", "OCR Reader (ocr_reader.py): Captures specified application window handles via PyGetWindow, preprocesses images with OpenCV, and runs Tesseract OCR to extract text.")
    add_bullet_item(doc, "", "Voice Manager (voice_manager.py): Handles push-to-talk audio recording, transcribes audio locally via Faster-Whisper, and outputs speech using SAPI/Piper TTS.")

    add_subheading(doc, "4.3 User Interaction Flow")
    add_body_p(doc,
        "Figure 4.1 outlines the primary interaction flow across KLAUSE user roles and operational pathways:"
    )
    add_body_p(doc,
        "[ User Action / Voice / Event ] --> [ React Dashboard / Three.js Orb ] --> [ FastAPI WebSockets ] --> [ ReAct Brain (brain.py) ] --> [ RAG Memory Search (ChromaDB + Obsidian) ] --> [ Tool Execution (OS / VS Code / OCR / Browser) ] --> [ Observation Return ] --> [ Gemini Answer Generation ] --> [ Speech Synthesis + UI Broadcast ]"
    )
    add_figure_caption(doc, "Figure 4.1. KLAUSE End-to-End User Interaction Flow Diagram")

    add_subheading(doc, "4.4 Layered Architecture")
    add_body_p(doc,
        "Figure 4.2 illustrates the layered architectural model of the KLAUSE system:"
    )
    add_body_p(doc,
        "+-----------------------------------------------------------------------+\n"
        "|                 Presentation Layer (React 19 + Three.js)              |\n"
        "|    [ 3D Orb UI ]    [ Chat Feed ]    [ Tasks ]    [ Rules ]    [ KB ] |\n"
        "+-----------------------------------------------------------------------+\n"
        "                                   ||  (WebSockets / REST)\n"
        "+-----------------------------------------------------------------------+\n"
        "|              Application Layer (FastAPI Orchestrator Engine)           |\n"
        "|  [ ReAct Brain ]   [ Tool Router ]   [ Disposition ]   [ Scheduler ]  |\n"
        "+-----------------------------------------------------------------------+\n"
        "                                   ||  (Python Connectors)\n"
        "+-----------------------------------------------------------------------+\n"
        "|                  Memory & Knowledge Persistence Layer                 |\n"
        "|  [ MongoDB (Sessions) ]  [ ChromaDB (Vectors) ]  [ Obsidian Canvas ]  |\n"
        "+-----------------------------------------------------------------------+\n"
        "                                   ||  (Native OS / Subprocess)\n"
        "+-----------------------------------------------------------------------+\n"
        "|                 Hardware & OS Execution Layer (Windows 11)            |\n"
        "|  [ Win32 APIs ]  [ Tesseract OCR ]  [ Faster-Whisper ]  [ Playwright ]|\n"
        "+-----------------------------------------------------------------------+"
    )
    add_figure_caption(doc, "Figure 4.2. KLAUSE Four-Layer Architectural Model")

    # ---------------------------------------------------------------------------
    # CHAPTER 5: IMPLEMENTATION
    # ---------------------------------------------------------------------------
    add_chapter_header(doc, 5, "IMPLEMENTATION")

    add_subheading(doc, "5.1 Overview")
    add_body_p(doc,
        "The implementation phase translates KLAUSE's modular design into a production-ready Windows desktop assistant. The application is built using a modern multi-runtime stack: Python 3.10+ virtual environments for backend services, FastAPI for asynchronous API management, Node.js v18+ and Vite for React 19 frontend development, MongoDB for session storage, ChromaDB for vector retrieval, and Tesseract OCR for screen perception."
    )

    add_subheading(doc, "5.2 Development Environment and Setup")
    add_body_p(doc,
        "The development setup is structured into three operational environments:"
    )
    add_bullet_item(doc, "1. Backend Environment: ", "Configured in Python 3.10 using virtual environment (venv). Dependencies specified in requirements.txt (fastapi, uvicorn, websockets, chroma-db, pymongo, pytesseract, faster-whisper, pywin32, loguru). System settings managed via config.yaml and .env variables.")
    add_bullet_item(doc, "2. Frontend Environment: ", "Built using Node.js v18+ with Vite dev server running on http://localhost:5173. Package dependencies managed via npm (react, three, @react-three/fiber, zustand, lucide-react, axios).")
    add_bullet_item(doc, "3. Local External Binaries: ", "MongoDB Community Server active on localhost:27017. Tesseract OCR installed at C:\\Program Files\\Tesseract-OCR\\tesseract.exe. Playwright browsers provisioned for CDP port 9222.")

    add_subheading(doc, "5.3 Frontend Implementation")
    add_body_p(doc,
        "The frontend is implemented as a Single Page Application (SPA) using React 19 and TypeScript:"
    )
    add_bullet_item(doc, "Orb Visualizer Component: ", "Leverages Three.js mesh geometry with dynamic vertex shaders. Listens to WebSocket state broadcasts and modulates sphere rotation, color gradients (blue for listening, purple for processing, green for responding), and amplitude displacement.")
    add_bullet_item(doc, "Zustand Store Integration: ", "Maintains real-time state for active sessions, message feeds, tool execution logs, and voice activation toggles.")
    add_bullet_item(doc, "Dashboard Layout: ", "Provides a sidebar navigation layout switching seamlessly between Chat, Tasks, Rules, and Knowledge Base panels.")

    add_subheading(doc, "5.4 Backend & Cognitive Engine Implementation")
    add_body_p(doc,
        "The backend orchestrator is implemented across core Python modules in app/core/:"
    )
    add_bullet_item(doc, "Brain Orchestrator (brain.py): ", "Manages the primary ReAct execution loop. Formulates prompts for Gemini 1.5 Pro, parses function call JSON responses, dispatches tools via tool_router.py, and formats final streaming outputs.")
    add_bullet_item(doc, "Tool Router (tool_router.py): ", "Maintains a dynamic registry of 20+ desktop tools. Inspects function arguments using Pydantic schemas, handles execution exceptions, and returns formatted observations to the brain.")
    add_bullet_item(doc, "Orb State Broadcaster (orb_state_broadcaster.py): ", "Broadcasts real-time JSON state events over WebSockets to synchronize the 3D Orb UI with backend processing phases.")

    add_subheading(doc, "5.5 Dual Memory & Knowledge Base Implementation")
    add_body_p(doc,
        "KLAUSE's persistence layer combines MongoDB, ChromaDB, and Obsidian vault connectors:"
    )
    add_bullet_item(doc, "ChromaStore (chroma_store.py): ", "Initializes a persistent Chroma vector database on disk. Generates 384-dimensional embeddings using sentence-transformers, indexes project markdown and code files, and executes fast cosine similarity queries.")
    add_bullet_item(doc, "Obsidian Connector (obsidian_connector.py): ", "Scans configured Obsidian vault directories recursively. Parses YAML frontmatter metadata and inline #tags, constructs entity relationships, and automatically writes formatted KLAUSE_Connections.canvas files.")

    add_subheading(doc, "5.6 Vision & Voice Integration")
    add_bullet_item(doc, "Tesseract OCR Engine (ocr_reader.py & error_reader.py): ", "Captures target application windows using PyGetWindow, preprocesses screenshots via OpenCV, and runs Tesseract OCR. Applies regular expressions to detect compiler stack traces, exit codes, and fatal warnings.")
    add_bullet_item(doc, "Voice Manager (voice_manager.py & stt.py): ", "Manages PyAudio microphone streams, transcribes speech locally using Faster-Whisper (INT8 quantized model), and outputs voice feedback via SAPI text-to-speech.")

    # ---------------------------------------------------------------------------
    # CHAPTER 6: RESULTS AND DEMONSTRATION
    # ---------------------------------------------------------------------------
    add_chapter_header(doc, 6, "RESULTS AND DEMONSTRATION")

    add_subheading(doc, "6.1 Overview of Functional Results")
    add_body_p(doc,
        "The KLAUSE platform has been fully implemented, tested, and validated on a Windows 11 development environment. All core subsystems—including the 3D Orb interface, ReAct cognitive engine, ChromaDB/MongoDB dual memory, Obsidian vault synchronization, OS desktop automation, OCR vision stack, and local voice pipeline—demonstrate seamless operational synergy."
    )

    add_subheading(doc, "6.2 Interactive 3D Orb UI & Real-Time Audio Feedback")
    add_body_p(doc,
        "Screenshot 1 demonstrates the main dashboard of KLAUSE featuring the interactive 3D Orb UI. The Three.js sphere dynamically transforms color and noise amplitude in real time as the user speaks. The sidebar enables fast switching between Chat, Tasks, Rules, and Knowledge Base panels."
    )
    add_figure_caption(doc, "Screenshot 1: Interactive 3D Orb UI Dashboard in Idle and Listening States")

    add_subheading(doc, "6.3 ReAct Cognitive Brain & Autonomous Tool Dispatch")
    add_body_p(doc,
        "Screenshot 2 illustrates the ReAct cognitive execution loop inside the Chat interface. Upon receiving a developer query ('Find all Python files in the app directory and check git status'), KLAUSE displays its internal thought process, dispatches filesystem_tools and git_tools autonomously, and streams the structured result back to the user."
    )
    add_figure_caption(doc, "Screenshot 2: ReAct Cognitive Execution and Autonomous Tool Routing Trace")

    add_subheading(doc, "6.4 Dual-Tier RAG Memory Retrieval")
    add_body_p(doc,
        "Screenshot 3 demonstrates semantic vector memory search in the Knowledge Base panel. Querying 'How does Obsidian sync work?' triggers ChromaDB vector retrieval, displaying indexed note chunks, similarity confidence scores, and source file metadata."
    )
    add_figure_caption(doc, "Screenshot 3: Knowledge Base Panel Showing ChromaDB Vector Search Results")

    add_subheading(doc, "6.5 Bidirectional Obsidian Vault & Canvas Map Generation")
    add_body_p(doc,
        "Screenshot 4 showcases KLAUSE's bidirectional Obsidian vault integration. After scanning a project vault folder, KLAUSE parses YAML frontmatter and inline #tags, generating an interactive KLAUSE_Connections.canvas file inside Obsidian that visually maps relationships between research documents and code modules."
    )
    add_figure_caption(doc, "Screenshot 4: Generated KLAUSE_Connections.canvas File Rendered Inside Obsidian")

    add_subheading(doc, "6.6 OS Window & Process Automation Execution")
    add_body_p(doc,
        "Screenshot 5 displays desktop window automation in action. KLAUSE focuses target application windows, retrieves active window handles using PyGetWindow and PyWin32, inspects clipboard state, and manages desktop application lifecycles."
    )
    add_figure_caption(doc, "Screenshot 5: Desktop Automation Control Focus and Active Window Inspection")

    add_subheading(doc, "6.7 OCR Vision & Terminal Error Detection")
    add_body_p(doc,
        "Screenshot 6 shows the OCR vision engine reading terminal errors. KLAUSE captures the active Windows Terminal window, runs Tesseract OCR, applies regex pattern matching (error_reader.py), and isolates compiler stack traces for immediate AI diagnostics."
    )
    add_figure_caption(doc, "Screenshot 6: OCR Vision Engine Extracting Active Terminal Error Stack Traces")

    add_subheading(doc, "6.8 Push-To-Talk Voice Interaction & Speech Synthesis")
    add_body_p(doc,
        "Screenshot 7 displays the voice interaction panel. Pushing the spacebar activates local microphone capture, Faster-Whisper transcribes speech instantly, and SAPI voice synthesis reads KLAUSE's response aloud."
    )
    add_figure_caption(doc, "Screenshot 7: Real-Time Voice Activation and Local Speech Transcription Interface")

    add_subheading(doc, "6.9 Dynamic Disposition & Personality Engine")
    add_body_p(doc,
        "Screenshot 8 shows the Rules and Personality panel. Users can select assistant dispositions (Concise Engineering, Technical Mentor, Debug Specialist), modifying personality parameters in disposition.yaml to tailor KLAUSE's tone."
    )
    add_figure_caption(doc, "Screenshot 8: Rules and Disposition Management Panel for Personality Configuration")

    add_subheading(doc, "6.10 Summary of Module Demonstration")
    add_body_p(doc,
        "The experimental validation confirms that KLAUSE successfully solves the context fragmentation and operational overhead experienced by software engineers. By unifying cognitive reasoning, local vector memory, desktop automation, screen OCR, and push-to-talk voice into a cohesive Windows application, KLAUSE provides a highly responsive, private, and capable desktop engineering companion."
    )

    # ---------------------------------------------------------------------------
    # CHAPTER 7: CONCLUSION
    # ---------------------------------------------------------------------------
    add_chapter_header(doc, 7, "CONCLUSION")

    add_body_p(doc,
        "The KLAUSE project presents a comprehensive, privacy-preserving, and intelligent solution to the challenges of modern software engineering workflows. By combining an asynchronous ReAct cognitive engine with persistent local vector memory, bidirectional personal knowledge graph synchronization, OS-level desktop automation, visual OCR screen perception, and real-time voice interaction, KLAUSE establishes a new standard for personal engineering companions."
    )
    add_body_p(doc,
        "Throughout its implementation and experimental evaluation, KLAUSE successfully demonstrated that hybrid execution—prioritizing deterministic system APIs and CLI scripts before falling back to computer vision—dramatically improves task reliability while eliminating the high latency and token costs of cloud-based visual agents. Furthermore, its native integration with Obsidian markdown vaults ensures that developer research and architectural decisions remain persistently indexed across multi-session coding activities."
    )
    add_body_p(doc,
        "In conclusion, KLAUSE lays the foundation for a sustainable, tech-enabled engineering support ecosystem that empowers software developers, streamlines desktop automation, and brings meaningful innovation to human-AI collaboration on local workstations."
    )

    # ---------------------------------------------------------------------------
    # CHAPTER 8: ADVANTAGES AND DISADVANTAGES
    # ---------------------------------------------------------------------------
    add_chapter_header(doc, 8, "ADVANTAGES AND DISADVANTAGES")

    add_subheading(doc, "8.1 Advantages")
    add_bullet_item(doc, "Absolute Data Privacy: ", "All memory storage (ChromaDB, MongoDB), Obsidian vault notes, OCR parsing, and voice transcriptions run locally on the user's desktop, ensuring sensitive project code is never uploaded to external vector clouds.")
    add_bullet_item(doc, "Hybrid Execution Reliability: ", "Combines fast, deterministic Win32/CLI tool calls with AI reasoning, avoiding the high failure rates (~88%) of pure computer-vision desktop agents.")
    add_bullet_item(doc, "Bidirectional Knowledge Sync: ", "Seamlessly bridges personal knowledge management (Obsidian) with live IDE development, automatically generating visual KLAUSE_Connections.canvas maps.")
    add_bullet_item(doc, "Multi-Modal Interaction: ", "Supports streaming text chat, push-to-talk voice input, 3D visual orb feedback, and automated desktop window control.")
    add_bullet_item(doc, "Zero Fine-Tuning Overhead: ", "Uses declarative Pydantic tool schemas and dynamic routing, allowing new developer tools to be added instantly without retraining models.")

    add_subheading(doc, "8.2 Disadvantages")
    add_bullet_item(doc, "Platform Dependency: ", "Current system APIs, window handling (pygetwindow, pywin32), and path configurations are tailored specifically for Windows OS.")
    add_bullet_item(doc, "Hardware Resource Usage: ", "Running local ChromaDB embeddings, Faster-Whisper speech models, MongoDB, and React/Three.js concurrently requires moderate desktop RAM (8GB+ recommended).")
    add_bullet_item(doc, "Tesseract OCR Limitations: ", "OCR text extraction depends on window visibility and screen resolution; heavily styled or custom GPU-rendered UI themes may degrade text accuracy.")

    # ---------------------------------------------------------------------------
    # CHAPTER 9: APPLICATIONS AND FUTURE SCOPE
    # ---------------------------------------------------------------------------
    add_chapter_header(doc, 9, "APPLICATIONS AND FUTURE SCOPE")

    add_subheading(doc, "9.1 Real-World Applications")
    add_body_p(doc,
        "KLAUSE has wide-ranging applications across software development and technical fields:"
    )
    add_bullet_item(doc, "1. Pair Programming & Code Debugging: ", "Acts as a real-time pair programmer that reads active VS Code files, captures compiler error stack traces, and suggests surgical code fixes.")
    add_bullet_item(doc, "2. Automated Workflow Orchestration: ", "Executes complex system commands, manages Git repositories, and runs test suites via natural language or voice triggers.")
    add_bullet_item(doc, "3. Personal Knowledge Management (PKM): ", "Organizes research papers, developer notes, and project documentation into interconnected Obsidian canvas graphs.")
    add_bullet_item(doc, "4. Ambient Desktop Automation: ", "Monitors clipboard events, focuses active application windows, and executes rule-driven background automation tasks.")

    add_subheading(doc, "9.2 Future Scope")
    add_body_p(doc,
        "Future planned enhancements for KLAUSE include:"
    )
    add_bullet_item(doc, "1. Cross-Platform OS Support: ", "Expanding system window tools and automation wrappers to support macOS and Linux environments.")
    add_bullet_item(doc, "2. Fine-Tuned Multimodal Screen Parsing: ", "Integrating lightweight local visual grounding models (e.g., OmniParser V2) for complex non-standard GUI controls.")
    add_bullet_item(doc, "3. Multi-Agent Software Development Teams: ", "Expanding the state machine to support multi-agent roles (Architect, Programmer, Code Reviewer, Tester) collaborating on complex multi-file projects.")
    add_bullet_item(doc, "4. Fully Offline Small Language Model (SLM) Fallback: ", "Integrating local open-weights models (e.g., Llama 3 / Qwen 2.5) via Ollama for complete offline operation without cloud LLM dependencies.")

    # ---------------------------------------------------------------------------
    # REFERENCES
    # ---------------------------------------------------------------------------
    add_chapter_header(doc, " ", "REFERENCES")

    references = [
        "[1] S. Yao, J. Zhao, D. Yu, N. Du, I. Shafran, K. Narasimhan, and Y. Cao, \"ReAct: Synergizing Reasoning and Acting in Language Models,\" in Proc. Int. Conf. Learn. Represent. (ICLR), 2023.",
        "[2] N. Shinn, F. Cassano, E. Berman, A. Gopinath, K. Narasimhan, and S. Yao, \"Reflexion: Language Agents with Verbal Reinforcement Learning,\" in Adv. Neural Inf. Process. Syst. (NeurIPS), vol. 36, pp. 8634–8652, 2023.",
        "[3] S. Yao, D. Yu, J. Zhao, I. Shafran, T. L. Griffiths, Y. Cao, and K. Narasimhan, \"Tree of Thoughts: Deliberate Problem Solving with Large Language Models,\" in Adv. Neural Inf. Process. Syst. (NeurIPS), vol. 36, 2023.",
        "[4] T. Sumers, S. Yao, K. Narasimhan, and T. L. Griffiths, \"Cognitive Architectures for Language Agents,\" Trans. Mach. Learn. Res. (TMLR), 2024.",
        "[5] T. Schick, J. Dwivedi-Yu, R. Dessì, R. Raileanu, M. Lomeli, L. Zettlemoyer, N. Cancedda, and T. Scialom, \"Toolformer: Language Models Can Teach Themselves to Use Tools,\" in Adv. Neural Inf. Process. Syst. (NeurIPS), vol. 36, 2023.",
        "[6] S. G. Patil, T. Zhang, X. Wang, and J. E. Gonzalez, \"Gorilla: Large Language Model Connected with Massive APIs,\" arXiv preprint arXiv:2305.15334, 2023.",
        "[7] Y. Qin, S. Liang, Y. Ye, K. Zhu, S. Hu, C. M. Chan, et al., \"ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs,\" in Proc. Int. Conf. Learn. Represent. (ICLR), 2024.",
        "[8] C. Packer, S. Wooders, K. Lin, V. Fang, S. G. Patil, and J. E. Gonzalez, \"MemGPT: Towards LLMs as Operating Systems,\" arXiv preprint arXiv:2310.08560, 2023.",
        "[9] P. Lewis, E. Perez, A. Piktus, F. Petroni, V. Karpukhin, et al., \"Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks,\" in Adv. Neural Inf. Process. Syst. (NeurIPS), vol. 33, pp. 9459–9474, 2020.",
        "[10] J. S. Park, J. C. O'Brien, C. J. Cai, M. R. Morris, P. Liang, and M. S. Bernstein, \"Generative Agents: Interactive Simulacra of Human Behavior,\" in Proc. ACM Symp. User Interface Softw. Technol. (UIST), pp. 1–22, 2023.",
        "[11] A. Asai, Z. Wu, Y. Wang, A. Sil, and H. Hajishirzi, \"Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection,\" in Proc. Int. Conf. Learn. Represent. (ICLR), 2024.",
        "[12] D. Edge, H. Trinh, N. Cheng, J. Bradley, A. Chao, et al., \"From Local to Global: A Graph RAG Approach to Query-Focused Summarization,\" arXiv preprint arXiv:2404.16130, 2024.",
        "[13] B. Jiménez Gutiérrez, Y. Shu, Y. Gu, M. Yasunaga, and Y. Su, \"HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models,\" in Adv. Neural Inf. Process. Syst. (NeurIPS), vol. 37, 2024.",
        "[14] Y. Wen, Z. Wang, and J. Sun, \"MindMap: Knowledge Graph Prompting Sparks Graph of Thoughts in Large Language Models,\" in Proc. Assoc. Comput. Linguist. (ACL), pp. 1024–1038, 2024.",
        "[15] J. Jiang, K. Zhou, W. X. Zhao, and J. R. Wen, \"KG-Agent: An Efficient Autonomous Agent Framework for Complex Reasoning over Knowledge Graph,\" in Proc. Assoc. Comput. Linguist. (ACL), 2025.",
        "[16] C. Zhang, L. Li, S. He, X. Zhang, B. Qiao, et al., \"UFO: A UI-Focused Agent for Windows OS Interaction,\" arXiv preprint arXiv:2402.07939, 2024.",
        "[17] R. Bonatti, D. Zhao, F. Bonacci, et al., \"Windows Agent Arena: Evaluating Multi-modal OS Agents at Scale,\" arXiv preprint arXiv:2409.08264, 2024.",
        "[18] T. Xie, D. Zhang, J. Chen, X. Li, S. Zhao, et al., \"OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks in Real Computer Environments,\" in Adv. Neural Inf. Process. Syst. (NeurIPS), 2024.",
        "[19] W. Tan, W. Zhang, et al., \"Towards General Computer Control: A Multimodal Agent for Red Dead Redemption II as a Case Study,\" arXiv preprint arXiv:2403.03186, 2024.",
        "[20] C. E. Jimenez, J. Yang, A. Wettig, S. Yao, K. Pei, O. Press, and K. Narasimhan, \"SWE-bench: Can Language Models Resolve Real-World GitHub Issues?\" in Proc. Int. Conf. Learn. Represent. (ICLR), 2024.",
        "[21] J. Yang, C. E. Jimenez, A. Wettig, K. Lieret, S. Yao, K. Narasimhan, and O. Press, \"SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering,\" in Adv. Neural Inf. Process. Syst. (NeurIPS), 2024.",
        "[22] S. Hong, M. Zhuge, J. Chen, X. Zheng, C. Hao, et al., \"MetaGPT: Meta-Programming for A Multi-Agent Collaborative Framework,\" in Proc. Int. Conf. Learn. Represent. (ICLR), 2024.",
        "[23] C. Qian, W. Liu, H. Liu, N. Chen, Y. Dang, et al., \"ChatDev: Communicative Agents for Software Development,\" in Proc. Assoc. Comput. Linguist. (ACL), 2024.",
        "[24] Y. Lu, J. Yang, Y. Shen, and A. Awadallah, \"OmniParser: A Unified Screen Parsing Framework for Pure Vision Based GUI Agents,\" arXiv preprint arXiv:2408.00203, 2024.",
        "[25] R. Niu, J. Li, Q. Wang, Y. Bi, X. Kong, et al., \"ScreenAgent: A Vision Language Model-driven Computer Control Agent,\" in Proc. Int. Jt. Conf. Artif. Intell. (IJCAI), 2024.",
        "[26] K. Cheng, Q. Sun, Y. Chu, H. He, X. Sun, et al., \"SeeClick: Harnessing GUI Grounding for Advanced Visual GUI Agents,\" in Proc. Assoc. Comput. Linguist. (ACL), 2024.",
        "[27] R. Smith, \"An Overview of the Tesseract OCR Engine,\" in Proc. IEEE Int. Conf. Doc. Anal. Recognit. (ICDAR), vol. 2, pp. 629–633, 2007.",
        "[28] S. Zhou, F. F. Xu, H. Zhu, X. Zhou, R. Lo, et al., \"WebArena: A Realistic Web Environment for Building Autonomous Agents,\" in Proc. Int. Conf. Learn. Represent. (ICLR), 2024.",
        "[29] A. Radford, J. W. Kim, T. Xu, G. Brockman, C. McLeavey, and I. Sutskever, \"Robust Speech Recognition via Large-Scale Weak Supervision,\" in Proc. Int. Conf. Mach. Learn. (ICML), pp. 28492–28518, 2023.",
        "[30] M. Safdari, G. Serapio-García, C. Crepy, S. Fitz, P. Romero, L. Sun, et al., \"Personality Traits in Large Language Models,\" arXiv preprint arXiv:2307.00184, 2023."
    ]

    for ref in references:
        add_body_p(doc, ref)

    out_path = r"e:\KLAUSE\KLAUSE_Project_Report.docx"
    doc.save(out_path)
    print(f"Full Report successfully generated at: {out_path}")

if __name__ == "__main__":
    generate_report()
