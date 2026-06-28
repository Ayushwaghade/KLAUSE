import json
from loguru import logger
from app.tools.base import tool
from app.memory.memory_manager import get_memory_manager

@tool(
    name="save_note",
    description="Saves a personal note to KLAUSE's long-term semantic memory. Argument: content (str), tags (str, comma-separated, optional).",
    destructive=False
)
def save_note(content: str, tags: str = "") -> str:
    """
    Saves a note to memory and indexes it for semantic search.
    """
    logger.info(f"Tool save_note invoked with content length: {len(content)}")
    mgr = get_memory_manager()
    note_id = mgr.save_note(project_id=None, content=content, tags=tags)
    return f"Success: Note saved with memory ID: {note_id}"


@tool(
    name="save_research",
    description="Saves research content or webpage text to KLAUSE's memory. Arguments: title (str), content (str), source_url (str, optional), tags (str, optional).",
    destructive=False
)
def save_research(title: str, content: str, source_url: str = "", tags: str = "") -> str:
    """
    Saves research text to memory and indexes it for semantic search.
    """
    logger.info(f"Tool save_research invoked: {title}")
    mgr = get_memory_manager()
    research_id = mgr.save_research(title=title, content=content, source_url=source_url, tags=tags)
    return f"Success: Research saved with memory ID: {research_id}"


@tool(
    name="search_memory",
    description="Searches long-term memory (notes and research) semantically using natural language queries. Argument: query (str).",
    destructive=False
)
def search_memory(query: str) -> str:
    """
    Performs a semantic vector query across notes and research collections.
    """
    logger.info(f"Tool search_memory invoked for query: {query}")
    mgr = get_memory_manager()
    results = mgr.search_semantic_memories(query, limit=5)
    
    if not results:
        return "Observation: No matching memories found."
        
    formatted_results = []
    for r in results:
        meta = r["metadata"]
        doc_type = r["type"].upper()
        tags = meta.get("tags", "none")
        source = f"Source: {meta.get('source_url', 'none')} | " if doc_type == "RESEARCH" else ""
        formatted_results.append(
            f"[{doc_type}] ID: {r['id']}\n"
            f"Content: {r['content']}\n"
            f"{source}Tags: {tags}\n"
            f"Similarity Score: {round(r['distance'], 4)}\n"
            "---"
        )
    
    return "Observation:\n" + "\n".join(formatted_results)
