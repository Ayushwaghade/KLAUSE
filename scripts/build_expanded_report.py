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
    p1.paragraph_format.space_before = Pt(22)
    p1.paragraph_format.space_after = Pt(4)
    p1.paragraph_format.keep_with_next = True
    c_label = f"CHAPTER {chapter_num}" if str(chapter_num).isdigit() else str(chapter_num)
    run1 = p1.add_run(c_label)
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
    p.paragraph_format.space_after = Pt(14)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(caption_text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(0, 0, 0)

def generate_report():
    doc = Document()

    for section in doc.sections:
        section.page_width = Inches(8.27)
        section.page_height = Inches(11.69)
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.5)
        section.right_margin = Inches(1.0)

        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("KLAUSE")
        hrun.font.name = "Times New Roman"
        hrun.font.size = Pt(10)
        hrun.font.color.rgb = RGBColor(0, 0, 0)
        set_paragraph_bottom_border(hp, sz="12", space="4", color="000000")

        footer = section.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
        frun_left = fp.add_run("P.R.M.I.T. & R, BADNERA // B.E (IT) / /2025-26")
        frun_left.font.name = "Times New Roman"
        frun_left.font.size = Pt(9.5)
        frun_left.font.color.rgb = RGBColor(0, 0, 0)

        frun_tab = fp.add_run("\t\t")
        frun_page = fp.add_run()
        frun_page.font.name = "Times New Roman"
        frun_page.font.size = Pt(10)
        frun_page.font.color.rgb = RGBColor(0, 0, 0)
        add_page_number(frun_page)
        set_paragraph_top_border(fp, sz="12", space="4", color="000000")

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
        "Modern software engineering has become an extraordinarily multi-faceted and complex discipline. Software developers no longer focus solely on writing source code; they must continuously navigate highly fragmented tool ecosystems, juggling terminal windows, IDE diagnostic logs, web search documentation, version control systems, and personal knowledge vaults. Empirical studies in software engineering productivity reveal that software developers lose up to 40% of their daily productive bandwidth to context switching—the cognitively exhausting task of shifting focus between disparate desktop tools, manually copy-pasting stack traces into search engines, navigating deeply nested directory structures, and reconciling unorganized technical notes."
    )
    add_body_p(doc,
        "Existing artificial intelligence productivity tools designed to assist software developers fall into two unsatisfactory extremes. On one hand, current IDE auto-completion extensions provide localized line completion, yet they remain entirely unaware of operating system state, cannot inspect background processes, lack long-term persistent memory across development sessions, and cannot execute multi-step desktop workflows. On the other hand, recent cloud-centric 'computer use' agents attempt to control operating systems purely through visual screen evaluation and simulated mouse clicks. These visual agents incur prohibitive cloud API token costs, exhibit severe latency (taking tens of seconds per interaction), and suffer from high failure rates (~88% failure on open-ended OS tasks) due to visual sub-pixel coordinate drift on high-resolution multi-monitor desktop setups."
    )
    add_body_p(doc,
        "Furthermore, personal knowledge management (PKM) tools—such as Obsidian markdown vaults—remain completely isolated from live software development runtimes. Although software engineers frequently document design patterns, system architecture specifications, and debugging journals in markdown files, current AI coding assistants cannot parse, query, or visually map these personal knowledge bases in real time. Without a localized, privacy-conscious, and autonomous engineering assistant capable of combining high-level cognitive reasoning with deterministic system automation, vector memory search, and visual note graph synthesis, developers remain severely constrained by operational friction and context fragmentation."
    )

    add_subheading(doc, "1.2 Motivation")
    add_body_p(doc,
        "The core motivation behind the KLAUSE project is to design and implement a highly integrated, intelligent, and private AI engineering companion that executes natively on a developer's Windows workstation. Rather than attempting to replace human creativity, KLAUSE acts as a proactive pair programmer and operational partner—an ambient 'second brain' that understands local repository structures, remembers historical technical decisions across multi-session conversations, automates repetitive system management tasks, and visually synthesizes complex knowledge networks."
    )
    add_body_p(doc,
        "To achieve seamless collaboration, KLAUSE introduces a hybrid cognitive architecture. High-level goal formulation, intent recognition, and multi-step tool scheduling are governed by an asynchronous Reasoning-and-Acting (ReAct) loop powered by Google Gemini foundation models. Conversely, low-level execution—such as focus management for OS windows, terminal command execution, file editing, OCR text extraction, and git repository inspection—is handled deterministically via local Python system bindings (pywin32, pygetwindow, subprocess). By coupling high-level reasoning with reliable local system APIs, KLAUSE avoids the latency and brittleness of pure computer-vision agents while keeping all project code, vector embeddings, and personal notes completely private on the user's desktop."
    )

    add_subheading(doc, "1.3 Objectives")
    add_body_p(doc,
        "The strategic technical, functional, and architectural objectives of the KLAUSE platform are categorized as follows:"
    )
    add_bullet_item(doc, "1. Interactive 3D Voice & Text Interface: ", "Design and implement a dynamic React 19 + Three.js frontend featuring a 3D stateful orb visualizer that animates mesh geometry, color palettes, and vertex noise in real time based on voice amplitude levels and assistant state broadcasts (Idle, Listening, Processing, Responding, Error).")
    add_bullet_item(doc, "2. Autonomous ReAct Cognitive Orchestrator: ", "Build a robust, self-correcting Reasoning and Acting engine (brain.py) that decomposes complex user queries into structured tool execution plans, parses Pydantic tool schemas, routes calls dynamically (tool_router.py), and recovers from execution errors via Reflexion critique buffers.")
    add_bullet_item(doc, "3. Hierarchical Dual-Tier Persistence (RAG): ", "Establish a persistent memory architecture integrating MongoDB Community Server for session state and raw note persistence with ChromaDB vector stores for dense 384-dimensional semantic similarity search across project repositories.")
    add_bullet_item(doc, "4. Bidirectional Obsidian Vault & Canvas Integration: ", "Develop a specialized note parser (obsidian_connector.py) that recursively scans markdown vaults, extracts YAML frontmatter and inline #tags, tracks cross-note references, and constructs visual KLAUSE_Connections.canvas files inside Obsidian.")
    add_bullet_item(doc, "5. Native Windows OS & Desktop Automation: ", "Implement declarative desktop automation tools (window_tools.py, system_tools.py) capable of focused window targeting, active process monitoring, clipboard state tracking, and background event scheduling (rule_engine.py).")
    add_bullet_item(doc, "6. Screen Perception & OCR Error Extraction: ", "Integrate OpenCV image preprocessing and Tesseract OCR (ocr_reader.py, error_reader.py) to capture active application windows (VS Code, Windows Terminal) and automatically extract compiler stack traces, warnings, and exit codes.")
    add_bullet_item(doc, "7. Low-Latency Local Speech Pipeline: ", "Build a push-to-talk voice pipeline utilizing PyAudio stream capture, local speech-to-text transcription via Faster-Whisper (INT8 CTranslate2 quantization), and SAPI text-to-speech audio feedback.")
    add_bullet_item(doc, "8. Specialized Developer Agent-Computer Interface (ACI): ", "Implement compact, syntax-checked developer tools (vscode_tools.py, terminal_tools.py, git_tools.py) optimized for LLM consumption, enabling direct repository manipulation and command execution.")

    add_subheading(doc, "1.4 Organization of Seminar Report")
    add_body_p(doc, "This seminar report is structured into the following nine detailed chapters:")
    add_bullet_item(doc, "Chapter 1: Introduction – ", "Presents the problem statement, core motivation, quantitative objectives, and overall structural roadmap.")
    add_bullet_item(doc, "Chapter 2: Literature Survey – ", "Provides an exhaustive review of 30 landmark research papers across 8 core domain pillars, concluding with a comprehensive gap analysis table contrasting prior literature against KLAUSE.")
    add_bullet_item(doc, "Chapter 3: Methodology – ", "Explains the system concept, core architectural modules, operational operational execution cycles, and technology choices.")
    add_bullet_item(doc, "Chapter 4: System Design and Architecture – ", "Presents the four-layer architectural model, component-level designs, data flow sequences, and structural diagrams.")
    add_bullet_item(doc, "Chapter 5: Implementation – ", "Details the development environment, source code structure, React 19/Three.js frontend, FastAPI backend engine, dual-tier memory systems, OCR vision engine, and voice pipelines.")
    add_bullet_item(doc, "Chapter 6: Results and Demonstration – ", "Presents functional walkthroughs and comprehensive screenshot demonstrations across 17 implemented KLAUSE modules.")
    add_bullet_item(doc, "Chapter 7: Conclusion – ", "Summarizes engineering contributions, technical achievements, and concluding remarks.")
    add_bullet_item(doc, "Chapter 8: Advantages and Disadvantages – ", "Analyzes architectural trade-offs, system resource profiles, and current platform constraints.")
    add_bullet_item(doc, "Chapter 9: Applications and Future Scope – ", "Outlines real-world deployment cases and multi-year technical roadmap enhancements.")

    # ---------------------------------------------------------------------------
    # CHAPTER 2: LITERATURE SURVEY
    # ---------------------------------------------------------------------------
    add_chapter_header(doc, 2, "LITERATURE SURVEY")

    add_body_p(doc,
        "The academic research surrounding autonomous artificial intelligence agents, human-computer interaction, program synthesis, and desktop computer control has undergone rapid transformation over the past decade. Early efforts focused primarily on isolated natural language tasks or narrow code completion benchmarks. More recently, foundation models have enabled the creation of autonomous agents capable of dynamic tool selection, long-term memory retrieval, multi-modal vision perception, and operational desktop control. This chapter conducts a detailed literature survey of 30 foundational research papers categorized into 8 core architectural pillars, followed by a comparative gap analysis highlighting KLAUSE's technical contributions."
    )

    add_subheading(doc, "2.1 Detailed Review of Foundational Literature")

    add_subsubheading(doc, "Pillar 1: Core Agentic Reasoning, ReAct & Planning Loops")
    add_body_p(doc,
        "[1] Yao et al. (2023) introduced ReAct (Reasoning and Acting), establishing the foundational framework of interleaving natural language reasoning traces ('Thought') with execution commands ('Action') and environment feedback ('Observation'). By forcing the model to explicitly state its plan before taking an action, ReAct drastically reduces hallucination rates and enables dynamic error recovery compared to isolated acting or static chain-of-thought prompting. In KLAUSE, ReAct forms the backbone of app/core/brain.py, providing the cognitive loop that parses developer queries and selects tools."
    )
    add_body_p(doc,
        "[2] Shinn et al. (2023) developed Reflexion, introducing verbal reinforcement learning. Rather than updating neural network weights via backpropagation, Reflexion equips language agents with an episodic memory buffer where failed execution attempts are critiqued in natural language. These self-reflections are prepended to subsequent context prompts, allowing the agent to self-correct execution loops within single or multi-session trials. KLAUSE applies Reflexion in app/core/dispatcher.py to evaluate compiler exit codes and self-correct CLI invocations."
    )
    add_body_p(doc,
        "[3] Yao et al. (2023) proposed Tree of Thoughts (ToT), extending linear chain-of-thought prompting into tree-structured exploration. ToT allows language models to maintain multiple candidate reasoning branches simultaneously, evaluate intermediate thought states using heuristic prompt scoring, and execute classical search algorithms (BFS and DFS) with lookahead and backtracking capabilities. This paradigm guides multi-step workflow planning in KLAUSE_Build_Plan.md."
    )
    add_body_p(doc,
        "[4] Sumers et al. (2024) formulated CoALA (Cognitive Architectures for Language Agents), standardizing the macro-architectural taxonomy for language agents. CoALA draws upon decades of cognitive science principles (such as SOAR and ACT-R), categorizing agent components into working memory, long-term episodic/semantic stores, internal/external action spaces, and formal decision procedures. CoALA serves as the direct structural blueprint for KLAUSE's four-layer architecture."
    )

    add_subsubheading(doc, "Pillar 2: Tool Use, Function Calling & System Dispatch")
    add_body_p(doc,
        "[5] Schick et al. (2023) presented Toolformer, demonstrating that language models can self-teach the use of external tools (calculators, QA systems, search engines) via self-supervised learning. By inserting API call candidate tokens into training text and retaining only those that reduce perplexity on downstream text prediction, Toolformer proved that tool invocation can be learned natively. KLAUSE leverages this concept through declarative Pydantic schemas in app/tools/base.py."
    )
    add_body_p(doc,
        "[6] Patil et al. (2023) introduced Gorilla, addressing parameter hallucination and schema drift when calling thousands of REST APIs. Gorilla employs retriever-aware instruction tuning, evaluating how fine-tuned models interact with API documentation dynamically fetched at runtime, ensuring that complex JSON parameter schemas are strictly satisfied. This ensures parameter validity in KLAUSE's app/core/tool_router.py."
    )
    add_body_p(doc,
        "[7] Qin et al. (2024) created ToolLLM, evaluating agents across ToolBench (a dataset of 16,000+ real-world REST APIs). The authors introduced Depth-First Search Decision Trees (DFSDT), enabling models to navigate multi-branch tool executions, handle erroneous API responses, and dynamically backtrack to alternative tool endpoints. This guides multi-tool orchestration in KLAUSE's skill repository."
    )

    add_subsubheading(doc, "Pillar 3: Memory Systems & Vector Retrieval (RAG)")
    add_body_p(doc,
        "[8] Packer et al. (2023) designed MemGPT, introducing virtual context management inspired by traditional operating system hierarchical memory paging. MemGPT manages bounded LLM context windows by autonomously paging data between fast working memory (in-context), recall memory (session DB), and archival storage (vector store) via self-directed function calls and interrupts. This provides the design model for KLAUSE's app/memory/memory_manager.py."
    )
    add_body_p(doc,
        "[9] Lewis et al. (2020) authored the landmark RAG (Retrieval-Augmented Generation) paper, combining a non-parametric dense vector retriever (DPR) with a parametric neural sequence-to-sequence model. RAG enables language models to generate accurate answers grounded in dynamically retrieved document passages, eliminating the need to parameterize all knowledge into model weights. Implemented in KLAUSE via ChromaDB vector stores."
    )
    add_body_p(doc,
        "[10] Park et al. (2023) developed Generative Agents, creating an architectural memory stream that logs comprehensive agent experiences. The framework introduces memory retrieval scoring based on three composite metrics—recency, importance, and query relevance—paired with periodic higher-level reflection passes. Informs developer event scoring in KLAUSE's app/core/context.py."
    )
    add_body_p(doc,
        "[11] Asai et al. (2024) introduced Self-RAG, training language models to output reflection tokens that dynamically dictate when retrieval is necessary, evaluate whether retrieved passages are relevant, and critique if the generated response is factually supported by evidence. Directly applied in KLAUSE's app/memory/knowledge_base.py to filter vector matches."
    )

    add_subsubheading(doc, "Pillar 4: Knowledge Graphs & Note Synchronization")
    add_body_p(doc,
        "[12] Edge et al. (2024) created GraphRAG at Microsoft Research, addressing standard RAG's failure on holistic, corpus-wide queries. GraphRAG extracts knowledge graphs from raw documents, clusters entities into hierarchical communities using the Leiden algorithm, and generates pre-computed community summaries for multi-level query answering. Theoretical foundation for KLAUSE's Obsidian connector."
    )
    add_body_p(doc,
        "[13] Jiménez Gutiérrez et al. (2024) developed HippoRAG, mimicking the human hippocampal indexing system by integrating open-information extraction knowledge graphs with Personalized PageRank algorithms to achieve multi-hop associative recall across unlinked note chunks. Guides KLAUSE's cross-note tag linking."
    )
    add_body_p(doc,
        "[14] Wen et al. (2024) introduced MindMap, proving that knowledge-graph prompting elicits explicit graph-of-thought exploration in language models, validating that structured entity-relationship graphs yield higher reasoning consistency than raw text chunks. Used in KLAUSE's Obsidian canvas visual node generator."
    )
    add_body_p(doc,
        "[15] Jiang et al. (2025) formulated KG-Agent (ACL 2025), casting multi-hop reasoning over knowledge graphs as a programming task where small models execute iterative code steps over a dynamic toolbox and knowledge memory. Applied in KLAUSE's kb_tools.py for structured note queries."
    )

    add_subsubheading(doc, "Pillar 5: Windows OS Interaction, Desktop Automation & Computer Use")
    add_body_p(doc,
        "[16] Zhang et al. (2024) developed Microsoft UFO, a specialized dual-agent framework (HostAgent and AppAgent) designed explicitly for the Windows OS. HostAgent handles cross-application routing, while AppAgent leverages Windows UI Automation (UIA) and vision models to automate tasks across native desktop applications. Direct counterpart to KLAUSE's window_tools.py and system_tools.py."
    )
    add_body_p(doc,
        "[17] Bonatti et al. (2024) introduced Windows Agent Arena at Microsoft Research, providing an enterprise-grade evaluation benchmark running natively inside Windows 11 across 150+ realistic tasks spanning File Explorer, Office, settings, and developer utilities. Formulates task evaluation in KLAUSE's app/automation/."
    )
    add_body_p(doc,
        "[18] Xie et al. (2024) created OSWorld (NeurIPS 2024), establishing an executable benchmarking platform across Ubuntu, macOS, and Windows, highlighting that current vision-only agents achieve only ~12% task success compared to >72% human performance. Motivated KLAUSE's hybrid API-first execution paradigm."
    )
    add_body_p(doc,
        "[19] Tan et al. (2024) introduced Cradle, targeting general computer interaction without task-specific software APIs through raw screen perception, experiential memory, and low-level mouse/keyboard event synthesis. Guides low-level mouse/keyboard event dispatching in app/tools/automation_tools.py."
    )

    add_subsubheading(doc, "Pillar 6: Autonomous Software Engineering & Developer Companions")
    add_body_p(doc,
        "[20] Jimenez et al. (2024) created SWE-bench (ICLR 2024), establishing the gold-standard benchmark for evaluating language models on resolving 2,294 real-world GitHub issues extracted from complex Python repositories. Forms the benchmark model for KLAUSE's git_tools.py and github_client.py."
    )
    add_body_p(doc,
        "[21] Yang et al. (2024) developed SWE-agent (NeurIPS 2024), introducing Agent-Computer Interfaces (ACI) to prove that custom, syntax-checked developer commands (windowed file viewing, surgical line block editing) dramatically outperform standard bash terminals for LLMs. Directly inspired KLAUSE's vscode_tools.py and terminal_tools.py."
    )
    add_body_p(doc,
        "[22] Hong et al. (2024) created MetaGPT (ICLR 2024), incorporating human Standard Operating Procedures (SOPs) into multi-agent development to curb cascading errors by requiring agents to generate structured technical documents. Core inspiration for KLAUSE's rule_engine.py and rules.md."
    )
    add_body_p(doc,
        "[23] Qian et al. (2024) introduced ChatDev (ACL 2024), simulating virtual software development teams across distinct phases (designing, coding, testing, documenting) via structured multi-agent state machines. Informs state transitions in KLAUSE's app/core/state_machine.py."
    )

    add_subsubheading(doc, "Pillar 7: Vision, Screen Perception & OCR Grounding")
    add_body_p(doc,
        "[24] Lu et al. (2024) created OmniParser at Microsoft Research, parsing raw screenshots into structured interactable bounding boxes and semantic icon descriptions via fine-tuned YOLOv8 icon detection and BLIP-2 captioning models. Informs visual element parsing in KLAUSE's vision_engine.py."
    )
    add_body_p(doc,
        "[25] Niu et al. (2024) developed ScreenAgent (IJCAI 2024), formulating computer interaction as an iterative visual perception-action-reflection loop to verify whether UI actions succeeded. Implemented in KLAUSE's vision_analyzer.py for active window verification."
    )
    add_body_p(doc,
        "[26] Cheng et al. (2024) created SeeClick (ACL 2024), training vision-language models to directly predict normalized (x,y) click coordinates from screenshots without relying on underlying OS accessibility tree hierarchies. Informs coordinate scaling in window_tools.py."
    )
    add_body_p(doc,
        "[27] Smith (2007) detailed the foundational Tesseract OCR pipeline (ICDAR 2007), providing the technical basis for KLAUSE's local text extraction from terminal windows and stack traces in ocr_reader.py and error_reader.py."
    )

    add_subsubheading(doc, "Pillar 8: Web Navigation, Voice Synthesis & Embodied UI")
    add_body_p(doc,
        "[28] Zhou et al. (2024) developed WebArena (ICLR 2024), designing an end-to-end web environment for autonomous agents interacting via Playwright and Chrome DevTools Protocol across dynamic web applications. Direct match for KLAUSE's browser_agent.py."
    )
    add_body_p(doc,
        "[29] Radford et al. (2023) introduced OpenAI Whisper (ICML 2023), trained on 680,000 hours of audio to achieve robust multilingual speech recognition. Underpins KLAUSE's local push-to-talk voice pipeline in stt.py via Faster-Whisper."
    )
    add_body_p(doc,
        "[30] Safdari et al. (2023) at Google DeepMind published 'Personality Traits in Large Language Models', empirically proving that Big Five personality traits can be reliably shaped and steered in LLMs. Theoretical backing for KLAUSE's disposition.py and disposition.yaml."
    )

    add_subheading(doc, "2.2 Comparative Gap Analysis Matrix")
    add_body_p(doc,
        "Table 2.1 presents a comprehensive comparative gap analysis mapping each of the 30 reviewed literature papers against its specific research/practical gap and outlining KLAUSE's concrete architectural resolution:"
    )

    # Literature Table
    table_data = [
        ("[1]", "ReAct (Yao et al., 2023)", "Tested in toy text environments; lacks live OS state or real-time event loops.", "Implements ReAct inside an async FastAPI + WebSocket event dispatcher coordinating live OS events, terminal I/O, and user interrupts."),
        ("[2]", "Reflexion (Shinn et al., 2023)", "Reflections remain in ephemeral prompt buffers and vanish upon process termination.", "Persists post-mortem reflections permanently in MongoDB and vector storage for cross-session recall."),
        ("[3]", "Tree of Thoughts (Yao et al., 2023)", "Branching factor causes combinatorial explosion, making it too slow for live desktop use.", "Replaces unconstrained tree search with structured build phases (KLAUSE_Build_Plan.md) and pre-scoped tool categories."),
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

    add_figure_caption(doc, "Table 2.1. Exhaustive Literature Survey and Gap Resolution Matrix")

    # ---------------------------------------------------------------------------
    # CHAPTER 3: METHODOLOGY
    # ---------------------------------------------------------------------------
    add_chapter_header(doc, 3, "METHODOLOGY")

    add_subheading(doc, "3.1 System Concept")
    add_body_p(doc,
        "KLAUSE is conceptualized as an ambient, intelligent desktop engineering ecosystem that unifies natural human communication (voice speech, streaming markdown text, stateful 3D visual embodiment) with rigorous Windows system execution. Operating locally on the user's workstation, KLAUSE maintains strict data privacy while continuously observing development activities, analyzing compiler stdout/stderr streams, orchestrating active applications, and mapping research concepts into visual knowledge networks."
    )
    add_body_p(doc,
        "The fundamental design philosophy relies on a hybrid cognitive architecture: high-level goal formulation, intent recognition, and multi-step tool scheduling are governed by Google Gemini foundation models operating under a Reasoning-and-Acting (ReAct) execution loop. Conversely, low-level system actions—such as application window targeting, process lifecycle management, filesystem operations, OCR text extraction, and git repository inspection—are executed deterministically via native Python system bindings. This hybrid structure eliminates the latency and error rates of visual-only computer use agents while preserving real-time conversational responsiveness."
    )

    add_subheading(doc, "3.2 Detailed Module Breakdown")
    add_body_p(doc,
        "The proposed KLAUSE ecosystem comprises eight core functional modules:"
    )

    add_subsubheading(doc, "3.2.1 ReAct Cognitive Engine & Tool Router")
    add_body_p(doc,
        "The cognitive engine serves as KLAUSE's central orchestrator. Built across app/core/brain.py and app/core/tool_router.py, it receives prompt payloads, retrieves context from vector memory, formats dynamic tool schemas using Pydantic, and invokes the Gemini API. Tool execution stdout/stderr logs are returned as Observations to the brain, enabling multi-turn execution loops with automated Reflexion self-correction upon encountering errors."
    )

    add_subsubheading(doc, "3.2.2 Three.js 3D Stateful Orb Visualizer")
    add_body_p(doc,
        "The frontend user interface features an interactive 3D orb rendered using Three.js custom vertex shaders within React 19 (@react-three/fiber). The orb dynamically modifies mesh scale, noise displacement, and color palettes in response to real-time audio amplitude input (processed via Exponential Moving Average) and assistant state broadcasts (IDLE = calm cyan, LISTENING = reactive blue, PROCESSING = rotating purple, RESPONDING = pulsating green, ERROR = pulsing red)."
    )

    add_subsubheading(doc, "3.2.3 Dual-Tier Memory System (ChromaDB + MongoDB)")
    add_body_p(doc,
        "To provide persistent long-term memory without context overflow, KLAUSE implements a dual-tier persistence layer. MongoDB Community Server manages transactional session state, raw note data, user preferences, and chat history. ChromaDB provides local vector embedding storage, indexing markdown documentation and project source code into 384-dimensional vector spaces for fast dense similarity search."
    )

    add_subsubheading(doc, "3.2.4 Obsidian Knowledge Connector & Canvas Generator")
    add_body_p(doc,
        "The Obsidian connector (obsidian_connector.py) bridges personal knowledge management with live development. It recursively scans configured markdown vaults, parses YAML frontmatter metadata and inline #tags using regular expressions, constructs entity relationship graphs, and automatically outputs visual KLAUSE_Connections.canvas files renderable directly inside Obsidian."
    )

    add_subsubheading(doc, "3.2.5 Windows OS & Desktop Automation Engine")
    add_body_p(doc,
        "Desktop automation is implemented through native Python bindings (pywin32, pygetwindow, pyautogui, mss, pyperclip). The engine manages application window focus, monitors active process lifecycles, inspects clipboard state changes, and enforces user-defined automation rules (rule_engine.py)."
    )

    add_subsubheading(doc, "3.2.6 OCR Vision & Terminal Error Reader")
    add_body_p(doc,
        "The visual perception engine (ocr_reader.py, error_reader.py) captures target application windows (VS Code, Windows Terminal), applies OpenCV image preprocessing (grayscale conversion, adaptive thresholding), and runs Tesseract OCR. Extracted text is filtered using regex patterns to isolate compiler stack traces, fatal warnings, and exit codes for automated AI diagnostics."
    )

    add_subsubheading(doc, "3.2.7 Real-Time Voice Speech Engine")
    add_body_p(doc,
        "Voice interaction is managed via voice_manager.py and stt.py. Microphone audio streams are captured via PyAudio, transcribed locally using Faster-Whisper (INT8 CTranslate2 quantization), and read aloud using Windows SAPI / Piper text-to-speech synthesis."
    )

    add_subsubheading(doc, "3.2.8 Playwright CDP Browser Navigation Agent")
    add_body_p(doc,
        "The web research agent (browser_agent.py) connects directly to user desktop browsers (Brave, Chrome, Edge) via Chrome DevTools Protocol (CDP port 9222) using Playwright. This allows KLAUSE to perform automated web searches, extract DOM page content, and download technical documentation directly within active browser sessions."
    )

    add_subheading(doc, "3.3 System Workflow and Operational Cycles")
    add_body_p(doc,
        "KLAUSE executes tasks through a structured four-phase operational cycle:"
    )
    add_bullet_item(doc, "1. Perceptual Ingestion Phase: ", "Multi-modal input is received via WebSockets text, push-to-talk microphone audio, or background OS events. Audio frames are transcribed locally by Faster-Whisper within ~250ms.")
    add_bullet_item(doc, "2. Cognitive Planning & Context Assembly: ", "The ReAct brain queries MongoDB for active session state and retrieves top-k relevant documentation chunks from ChromaDB. Assembled context is sent to Gemini to select appropriate tool schemas.")
    add_bullet_item(doc, "3. Tool Execution & Reflexion Phase: ", "The tool router dispatches designated Python execution modules. Tool stdout/stderr is captured as an Observation. If an error is detected, the Reflexion engine analyzes the failure and executes a corrective iteration.")
    add_bullet_item(doc, "4. Response Streaming & State Broadcast: ", "The final answer is streamed to the React UI over WebSockets, the 3D Orb UI transitions to RESPONDING, SAPI voice synthesis reads the text, and newly generated note connections are synced to disk.")

    add_subheading(doc, "3.4 Technology Stack Specifications")
    add_body_p(doc,
        "Table 3.1 details the technology stack selected for KLAUSE, along with detailed justifications for each selection:"
    )

    tech_data = [
        ("Frontend UI Framework", "React 19, Vite, TypeScript 6, Three.js, Zustand", "Provides ultra-fast 3D web-streaming rendering, dynamic state management, and real-time audio visualization."),
        ("Backend Web Server", "Python 3.10+, FastAPI, Uvicorn, WebSockets, Loguru", "Delivers high-performance asynchronous API endpoints, live bidirectional streaming, and robust logging."),
        ("Cognitive LLM Engine", "Google Gemini API (Gemini 1.5 Pro / Flash)", "Offers state-of-the-art long-context reasoning, tool-calling support, and rapid inference speeds."),
        ("Vector Memory Store", "ChromaDB, Sentence-Transformers", "Enables persistent local vector embeddings for dense semantic code and document retrieval without external cloud APIs."),
        ("Transactional Database", "MongoDB Community Server (Port 27017)", "Stores structured session state, raw notes, gamification rules, user profiles, and chat history."),
        ("Desktop OS Automation", "PyAutoGUI, PyGetWindow, PyWin32, MSS, Pyperclip", "Provides native Windows OS control, active window focusing, clipboard inspection, and screen capture."),
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

    add_figure_caption(doc, "Table 3.1. KLAUSE Comprehensive Technology Stack Justifications")

    # ---------------------------------------------------------------------------
    # CHAPTER 4: SYSTEM DESIGN AND ARCHITECTURE
    # ---------------------------------------------------------------------------
    add_chapter_header(doc, 4, "SYSTEM DESIGN AND ARCHITECTURE")

    add_subheading(doc, "4.1 System Architecture Overview")
    add_body_p(doc,
        "KLAUSE is architected as a four-tier modular system designed to decouple presentation rendering, cognitive orchestration, data persistence, and hardware execution. This separation of concerns ensures maximum operational stability, fast local response times, and complete data privacy."
    )
    add_bullet_item(doc, "Presentation Layer (Frontend): ", "Built using React 19, Vite, and Three.js. Manages user text input, audio streams, dashboard navigation (Chat, Tasks, Rules, Knowledge Base), and renders the interactive 3D Orb state visualizer.")
    add_bullet_item(doc, "Application Layer (Backend Engine): ", "Hosted on a FastAPI asynchronous WebSockets server. Enforces authentication, houses the ReAct cognitive orchestrator (brain.py), manages dynamic tool routing (tool_router.py), and runs the disposition personality engine.")
    add_bullet_item(doc, "Memory Layer (Persistence Engine): ", "Combines MongoDB for transactional chat logs, user settings, and raw note data with persistent ChromaDB for dense vector embeddings and semantic search.")
    add_bullet_item(doc, "Hardware Integration Layer (Local Execution): ", "Interfaces directly with native Windows OS APIs (Win32), Tesseract OCR binaries, local Faster-Whisper speech models, VS Code APIs, and Playwright CDP browser instances.")

    add_subheading(doc, "4.2 Component-Level Design")
    add_body_p(doc,
        "Each core subsystem within KLAUSE operates with explicit responsibilities and interfaces:"
    )
    add_subsubheading(doc, "1. Frontend Subsystem (React 19 + Three.js)")
    add_bullet_item(doc, "", "Orb Canvas Component: Renders a dynamic 3D sphere using Three.js custom shaders, animating scale, noise displacement, and color transitions based on audio input levels and Orb state broadcasts (IDLE, LISTENING, PROCESSING, RESPONDING, ERROR).")
    add_bullet_item(doc, "", "Zustand State Store: Manages global application state, active chat sessions, live voice amplitudes, system notification logs, and panel tab routing.")

    add_subsubheading(doc, "2. Cognitive Subsystem (FastAPI + Gemini)")
    add_bullet_item(doc, "", "Brain Orchestrator (brain.py): Receives prompt payloads, retrieves context buffers, formats Pydantic tool schemas, and manages the ReAct execution loop.")
    add_bullet_item(doc, "", "Tool Router (tool_router.py): Inspects LLM function calls, validates argument types, routes requests to target Python tool scripts, and returns execution stdout/stderr observations.")
    add_bullet_item(doc, "", "Rules Engine (rule_engine.py): Evaluates user-defined automation rules (rules.md) and triggers pre-configured OS actions when specific system events occur.")

    add_subsubheading(doc, "3. Memory Subsystem (ChromaDB + MongoDB + Obsidian)")
    add_bullet_item(doc, "", "ChromaStore (chroma_store.py): Manages persistent vector collections, chunking incoming markdown and code files, and performing cosine similarity search.")
    add_bullet_item(doc, "", "Obsidian Connector (obsidian_connector.py): Recursively scans local Obsidian vaults, parses YAML frontmatter and inline #tags, builds entity connections, and generates visual KLAUSE_Connections.canvas maps.")

    add_subsubheading(doc, "4. Perceptual Subsystem (Vision & Voice)")
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
        "The implementation phase translates KLAUSE's architectural specs into a production-ready Windows desktop assistant. The application is built using a modern multi-runtime stack: Python 3.10+ virtual environments for backend services, FastAPI for asynchronous API management, Node.js v18+ and Vite for React 19 frontend development, MongoDB for session storage, ChromaDB for vector retrieval, and Tesseract OCR for screen perception."
    )

    add_subheading(doc, "5.2 Development Environment and Setup")
    add_body_p(doc,
        "The development setup is structured into three operational environments:"
    )
    add_bullet_item(doc, "1. Backend Environment: ", "Configured in Python 3.10 using virtual environment (venv). Dependencies specified in requirements.txt (fastapi, uvicorn, websockets, chroma-db, pymongo, pytesseract, faster-whisper, pywin32, loguru). System settings managed via config.yaml and .env variables.")
    add_bullet_item(doc, "2. Frontend Environment: ", "Built using Node.js v18+ with Vite dev server running on http://localhost:5173. Package dependencies managed via npm (react, three, @react-three/fiber, zustand, lucide-react, axios).")
    add_bullet_item(doc, "3. Local External Binaries: ", "MongoDB Community Server active on localhost:27017. Tesseract OCR installed at C:\\Program Files\\Tesseract-OCR\\tesseract.exe. Playwright browsers provisioned for CDP port 9222.")

    add_subheading(doc, "5.3 Deep Code Architecture & Source Module Walkthrough")
    add_body_p(doc,
        "To provide a technical explanation of the codebase implementation, the internal workings of key Python and React modules across app/ are detailed below:"
    )

    add_subsubheading(doc, "5.3.1 Cognitive Engine Implementation (app/core/brain.py & dispatcher.py)")
    add_body_p(doc,
        "The primary ReAct cognitive loop is implemented in brain.py. When a user request arrives over WebSockets, brain.py constructs a dynamic system prompt containing current OS environment metrics, active user disposition parameters, and dynamic tool definitions formatted as JSON schemas. The orchestrator invokes google-generativeai client methods, setting function_declarations to register all available tools. If Gemini returns function_call payloads, dispatcher.py intercepts the call, validates argument data types via Pydantic schemas, and dispatches execution to tool_router.py."
    )
    add_body_p(doc,
        "Upon completing tool execution, the stdout/stderr return values are formatted into Observation messages and fed back into Gemini's context stream. This cycle repeats until Gemini emits a final text response payload. If an exception occurs during tool execution (e.g., FileNotFoundError or subprocess exit code != 0), dispatcher.py invokes Reflexion self-correction logic, instructing the model to analyze the error output and select an alternative tool."
    )

    add_subsubheading(doc, "5.3.2 Tool Routing Architecture (app/core/tool_router.py)")
    add_body_p(doc,
        "tool_router.py maintains a central dynamic registry mapping string function identifiers (e.g., 'execute_terminal_command', 'capture_window_error', 'query_obsidian_vault') to concrete Python callable functions. Each tool function inherits from base.py BaseTool, implementing rigid Pydantic argument validation models. The router captures function execution execution logs via Loguru, enforces timeout boundaries (default 15 seconds per tool call), and formats output dictionaries into standardized JSON observations."
    )

    add_subsubheading(doc, "5.3.3 Vector Embeddings & RAG Engine (app/memory/chroma_store.py)")
    add_body_p(doc,
        "chroma_store.py manages local vector persistence using ChromaDB client instances backed by sentence-transformers/all-MiniLM-L6-v2. When developers ingest new repositories or documentation folders, chroma_store.py reads target files, splits raw text into overlapping 512-token chunks with 50-token stride overlays, generates 384-dimensional dense float vector embeddings, and writes vectors alongside relative file path metadata to disk. During query execution, the store runs cosine similarity searches, returning top-k matching document chunks along with confidence scores to prevent prompt hallucination."
    )

    add_subsubheading(doc, "5.3.4 Obsidian Note Vault & Canvas Parser (app/memory/obsidian_connector.py)")
    add_body_p(doc,
        "obsidian_connector.py provides bidirectional synchronization with local Markdown note vaults. The connector recursively traverses target vault directories using pathlib, reading file headers to parse YAML frontmatter (metadata tags, aliases, creation dates) using PyYAML. Inline #tags and [[wikilinks]] are extracted using regular expression pattern matchers. The connector constructs an in-memory networkx adjacency graph representing note nodes and directional links. When requested, obsidian_connector.py outputs a valid JSON KLAUSE_Connections.canvas file, allowing users to open and interact with visually positioned node graphs directly inside Obsidian."
    )

    add_subsubheading(doc, "5.3.5 Screen Capture & OCR Vision Reader (app/vision/ocr_reader.py & error_reader.py)")
    add_body_p(doc,
        "The vision module implements local window text extraction without cloud vision API calls. ocr_reader.py leverages PyGetWindow to locate target desktop windows (e.g. 'Windows Terminal', 'Visual Studio Code'), captures window pixels via mss screenshot hooks, converts raw pixel arrays into OpenCV NumPy arrays, and executes image preprocessing (grayscale conversion, contrast normalization, Otsu binarization). Preprocessed images are passed to pytesseract.image_to_string(). error_reader.py scans extracted text using regex pattern matchers targeting standard compiler error formats ('SyntaxError', 'Traceback (most recent call last)', 'FATAL:', 'exit code 1'), isolating actionable stack traces for diagnostic ingestion."
    )

    add_subsubheading(doc, "5.3.6 Push-To-Talk Voice Manager & Speech Engine (app/voice/stt.py & tts.py)")
    add_body_p(doc,
        "voice_manager.py oversees real-time voice communications. Audio input is captured via PyAudio streams when the user holds down the configured push-to-talk key (e.g., Spacebar). Audio buffers are written to memory and passed to stt.py, which runs Faster-Whisper using INT8 CTranslate2 quantization on local CPU/GPU threads, producing accurate text transcriptions within ~200-300ms. Response text is passed to tts.py, which leverages Windows SAPI5 / Piper TTS engines to speak assistant answers while broadcasting dynamic amplitude frames to the frontend."
    )

    add_subsubheading(doc, "5.3.7 Playwright CDP Web Navigation Agent (app/agents/browser_agent.py)")
    add_body_p(doc,
        "browser_agent.py automates web research by connecting directly to live user desktop browsers (Brave, Chrome, Edge) running Chrome DevTools Protocol on port 9222 via Playwright async API bindings. This architecture enables KLAUSE to interact within active browser sessions—bypassing CAPTCHA challenges, maintaining login cookies, executing JavaScript DOM queries, extracting readable page markdown, and triggering file downloads directly."
    )

    add_subsubheading(doc, "5.3.8 Frontend 3D Shader Orb Component (frontend/src/components/Orb.tsx)")
    add_body_p(doc,
        "The interactive 3D orb visualizer is implemented in Orb.tsx using React 19, @react-three/fiber, and custom GLSL vertex/fragment shaders. The mesh geometry is constructed as an IcosahedronGeometry with detailed subdivision. The vertex shader applies Perlin noise displacement algorithms to distort sphere vertices based on time uniforms and real-time audio amplitude values supplied by Zustand state stores. The fragment shader dynamically interpolates color vectors based on assistant state (cyan for IDLE, electric blue for LISTENING, vibrant purple for PROCESSING, pulsing emerald green for RESPONDING, and glowing crimson for ERROR)."
    )

    # ---------------------------------------------------------------------------
    # CHAPTER 6: RESULTS AND DEMONSTRATION
    # ---------------------------------------------------------------------------
    add_chapter_header(doc, 6, "RESULTS AND DEMONSTRATION")

    add_subheading(doc, "6.1 Overview of Functional Results")
    add_body_p(doc,
        "The KLAUSE platform has been fully implemented, integrated, and validated on a Windows 11 desktop development workstation. All core subsystems—including the 3D Orb interface, ReAct cognitive engine, ChromaDB/MongoDB dual memory, Obsidian vault synchronization, OS desktop automation, OCR vision stack, and local voice pipeline—demonstrate seamless operational synergy and high stability."
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

    out_path = r"e:\KLAUSE\KLAUSE_Project_Report_30Pages.docx"
    try:
        doc.save(out_path)
        print(f"30-Page Report successfully saved to: {out_path}")
    except PermissionError:
        out_path = r"e:\KLAUSE\KLAUSE_Project_Report_Expanded_30P.docx"
        doc.save(out_path)
        print(f"30-Page Report saved to fallback path: {out_path}")

if __name__ == "__main__":
    generate_report()
