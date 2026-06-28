import os
from typing import Callable, Optional
from app.tools.base import tool

@tool(
    name="read_file",
    description="Reads the contents of a file from the local workspace. Argument: path (str)."
)
def read_file(path: str) -> str:
    """Reads a file and returns its content."""
    try:
        if not os.path.exists(path):
            return f"Error: File '{path}' does not exist."
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file '{path}': {e}"

@tool(
    name="write_file",
    description="Writes content to a file in the local workspace. Arguments: path (str), content (str)."
)
def write_file(path: str, content: str, confirm_fn: Optional[Callable[[str], bool]] = None) -> str:
    """Writes content to a file. Prompts confirmation if overwriting."""
    try:
        # Create parent directories if they don't exist
        parent = os.path.dirname(path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
            
        # Check overwrite safety
        if os.path.exists(path):
            if confirm_fn:
                approved = confirm_fn(f"File '{path}' already exists. Overwrite?")
                if not approved:
                    return f"Action cancelled. File '{path}' was not overwritten."
            else:
                return f"Error: File '{path}' exists and no confirmation callback was provided."
                
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Success: Content written to '{path}'."
    except Exception as e:
        return f"Error writing file '{path}': {e}"

@tool(
    name="web_search",
    description="Performs a web search for the query and returns matching webpage titles, links, and text descriptions. Argument: query (str)."
)
def web_search(query: str) -> str:
    """
    Performs a real web search. Uses Serper API if configured, otherwise falls back to
    Google Custom Search JSON API, and finally falls back to DuckDuckGo Lite.
    """
    from loguru import logger
    from app.config.config import settings
    import urllib.request
    import urllib.parse
    import json
    
    serper_key = settings.serper_api_key
    if serper_key:
        logger.info(f"Web Search Tool: Querying Serper API for '{query}'")
        url = "https://google.serper.dev/search"
        payload = json.dumps({"q": query, "num": 5}).encode('utf-8')
        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    'X-API-KEY': serper_key,
                    'Content-Type': 'application/json'
                }
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                
            organic = res_data.get("organic", [])
            if not organic:
                return f"Observation: No Serper search results found for '{query}'."
                
            lines = [f"Observation: Google Search Results for '{query}':"]
            for idx, item in enumerate(organic[:5], 1):
                title = item.get("title", "No Title")
                link = item.get("link", "No Link")
                snippet = item.get("snippet", "No Description")
                lines.append(
                    f"{idx}. {title}\n"
                    f"   Link: {link}\n"
                    f"   Description: {snippet}\n"
                )
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Serper API failed: {e}. Falling back to Google Custom Search.")
            
    google_key = settings.google_search_api_key
    google_cx = settings.google_search_cx
    
    if google_key and google_cx:
        logger.info(f"Web Search Tool: Querying Google Custom Search API for '{query}'")
        url = f"https://www.googleapis.com/customsearch/v1?key={google_key}&cx={google_cx}&q={urllib.parse.quote(query)}"
        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                
            items = res_data.get("items", [])
            if not items:
                return f"Observation: No Google search results found for '{query}'."
                
            lines = [f"Observation: Google Search Results for '{query}':"]
            for idx, item in enumerate(items[:5], 1):
                title = item.get("title", "No Title")
                link = item.get("link", "No Link")
                snippet = item.get("snippet", "No Description")
                lines.append(
                    f"{idx}. {title}\n"
                    f"   Link: {link}\n"
                    f"   Description: {snippet}\n"
                )
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Google Custom Search API failed: {e}. Falling back to DuckDuckGo.")
            
    # DuckDuckGo Lite Fallback
    logger.info(f"Web Search Tool: Querying DuckDuckGo Lite for '{query}'")
    import urllib.request
    import urllib.parse
    import re
    
    url = "https://lite.duckduckgo.com/lite/"
    try:
        data = urllib.parse.urlencode({'q': query}).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
        results = re.findall(r"<a[^>]*href=['\"]([^'\"]+)['\"][^>]*class=['\"]result-link['\"][^>]*>(.*?)</a>", html, re.DOTALL)
        
        if not results:
            return f"Observation: No search results found for '{query}'."
            
        blocks = html.split("class='result-link'")
        
        lines = [f"Observation: Web Search Results for '{query}':"]
        for idx, (link, title_html) in enumerate(results[:5], 1):
            title = re.sub(r'<[^>]+>', '', title_html).strip()
            snippet = ""
            if idx < len(blocks):
                s_match = re.search(r"class=['\"]result-snippet['\"][^>]*>(.*?)</td>", blocks[idx], re.DOTALL)
                if s_match:
                    snippet = re.sub(r'<[^>]+>', '', s_match.group(1)).strip()
                    snippet = re.sub(r'\s+', ' ', snippet)
            
            lines.append(
                f"{idx}. {title}\n"
                f"   Link: {link}\n"
                f"   Description: {snippet}\n"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"DuckDuckGo Lite search failed: {e}")
        return f"Error: Web search failed: {e}"

@tool(
    name="download_file",
    description="Downloads a file from a specified URL to a local destination path. Arguments: url (str), dest_path (str)."
)
def download_file(url: str, dest_path: str) -> str:
    """Downloads a file from the internet."""
    import urllib.request
    import os
    from loguru import logger
    
    logger.info(f"Download File Tool: Downloading from '{url}' to '{dest_path}'")
    try:
        # Create directories if they don't exist
        dest_dir = os.path.dirname(dest_path)
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)
            
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        with urllib.request.urlopen(req, timeout=30) as response, open(dest_path, 'wb') as out_file:
            data = response.read()
            out_file.write(data)
            
        size = len(data)
        logger.info(f"Download File Tool: Success. File size: {size} bytes")
        return f"Success: File downloaded to '{dest_path}' ({size} bytes)."
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return f"Error downloading file: {e}"
