from app.tools.base import tool
from app.memory.knowledge_base import get_knowledge_base

def _parse_tags(tags_str: str) -> list:
    """Helper to convert comma-separated tags string to list."""
    if not tags_str:
        return []
    return [t.strip().lower() for t in tags_str.split(",") if t.strip()]

@tool(
    name="kb_add_document",
    group="memory",
    description="Ingests, parses, chunks, and indexes a local file (.txt, .md, .pdf, .docx) into the Knowledge Base. Arguments: file_path (str), tags (str - comma-separated tags, optional, e.g. 'python,security'), chunk_size (int - optional, default 1000)."
)
def kb_add_document(file_path: str, tags: str = "", chunk_size: int = 1000) -> str:
    """Ingest file to KB."""
    tags_list = _parse_tags(tags)
    return get_knowledge_base().add_document(file_path, tags_list, chunk_size=chunk_size)

@tool(
    name="kb_add_url",
    group="memory",
    description="Downloads, parses, and indexes a webpage URL into the Knowledge Base. Falls back to a browser agent if the page has dynamic Javascript. Arguments: url (str), tags (str - comma-separated, optional), chunk_size (int - optional, default 1000)."
)
def kb_add_url(url: str, tags: str = "", chunk_size: int = 1000) -> str:
    """Ingest URL to KB."""
    tags_list = _parse_tags(tags)
    return get_knowledge_base().add_url(url, tags_list, chunk_size=chunk_size)

@tool(
    name="kb_add_text",
    group="memory",
    description="Directly index custom text content/notes into the Knowledge Base. Arguments: title (str), content (str), tags (str - comma-separated, optional), chunk_size (int - optional, default 1000)."
)
def kb_add_text(title: str, content: str, tags: str = "", chunk_size: int = 1000) -> str:
    """Ingest custom text block."""
    tags_list = _parse_tags(tags)
    return get_knowledge_base().add_text(title, content, tags_list, chunk_size=chunk_size)

@tool(
    name="kb_delete",
    group="memory",
    description="Removes a specific document and all its indexed chunks from the Knowledge Base by document ID. Arguments: document_id (str)."
)
def kb_delete(document_id: str) -> str:
    """Delete document from KB."""
    success = get_knowledge_base().delete_document(document_id)
    if success:
        return f"Observation: Successfully deleted document ID '{document_id}' from the Knowledge Base."
    return f"Observation: Document ID '{document_id}' not found in the Knowledge Base."

@tool(
    name="kb_clear",
    group="memory",
    description="Purges all documents and matching vector chunks from the Knowledge Base. Argument: none."
)
def kb_clear() -> str:
    """Clear KB."""
    return get_knowledge_base().clear_kb()

@tool(
    name="kb_search",
    group="memory",
    description="Performs semantic similarity search on the Knowledge Base and returns matching snippets. Arguments: query (str), limit (int - optional, default 5)."
)
def kb_search(query: str, limit: int = 5) -> str:
    """Query semantic search."""
    results = get_knowledge_base().search(query, limit=limit)
    if not results:
        return "Observation: No matching research snippets found in the Knowledge Base."
    
    formatted = "Observation: Found matching research items:\n\n"
    for idx, item in enumerate(results, 1):
        meta = item.get("metadata", {})
        source = meta.get("source_url") or meta.get("file_path") or "Direct text upload"
        distance = item.get("distance", 0.0)
        formatted += (
            f"### Result {idx}: {meta.get('title', 'Untitled')}\n"
            f"- **ID**: `{meta.get('parent_id')}`\n"
            f"- **Source**: {source}\n"
            f"- **Tags**: {meta.get('tags', '')}\n"
            f"- **Relevance Score**: {1 - distance:.4f} (Distance: {distance:.4f})\n"
            f"- **Snippet**:\n"
            f"```\n{item['content'].strip()}\n```\n\n"
        )
    return formatted

@tool(
    name="kb_list_topics",
    group="memory",
    description="Retrieves a list of all unique tags and topics indexed in the Knowledge Base. Argument: none."
)
def kb_list_topics() -> str:
    """List topics."""
    topics = get_knowledge_base().get_all_topics()
    if not topics:
        return "Observation: No tags or topics found in the Knowledge Base."
    return f"Observation: Active Knowledge Base Topics: {', '.join(topics)}"
