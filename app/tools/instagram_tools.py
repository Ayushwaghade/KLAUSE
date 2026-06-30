from typing import Optional, Callable
from pathlib import Path
from app.tools.base import tool
from app.config.config import settings
from app.agents.instagram_client import get_instagram_client

# Session rate limit counters
_session_likes = 0
_session_follows = 0

def _check_credentials() -> Optional[str]:
    from dotenv import load_dotenv
    import os
    load_dotenv(override=True)
    client = get_instagram_client()
    client.username = os.environ.get("INSTAGRAM_USERNAME") or settings.instagram.username
    client.password = os.environ.get("INSTAGRAM_PASSWORD") or settings.instagram.password

    if (not client.username or not client.password or 
        client.username in ("", "your_username") or 
        client.password in ("", "your_password")):
        return (
            "Error: Instagram credentials are not configured. "
            "Please configure INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in your .env file."
        )
    return None

# Helper for confirmation
def _request_permission(confirm_fn: Optional[Callable[[str], bool]], prompt: str) -> bool:
    if not confirm_fn:
        # Default behavior if confirm_fn is missing (raise error for safety)
        return False
    return confirm_fn(prompt)


# ─── Read-Only Tools (No confirmation required) ───────────────────

@tool(
    name="instagram_search_users",
    description="Searches for user profiles on Instagram matching query. Arguments: query (str). Optional: limit (int, default 5)."
)
def instagram_search_users(query: str, limit: int = 5, **kwargs) -> str:
    """Search for users on Instagram."""
    cred_err = _check_credentials()
    if cred_err:
        return cred_err

    try:
        client = get_instagram_client()
        users = client.search_users(query, limit=limit)
        if not users:
            return f"No users found matching query '{query}'."

        lines = [f"Search results for '{query}':"]
        for u in users:
            lines.append(f"  - @{u['username']} | Name: {u['full_name']} | Followers: {u['follower_count']}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


@tool(
    name="instagram_get_user_info",
    description="Retrieves profile description, biography, and follower counts of an Instagram username. Arguments: username (str)."
)
def instagram_get_user_info(username: str, **kwargs) -> str:
    """Get Instagram user info."""
    cred_err = _check_credentials()
    if cred_err:
        return cred_err

    try:
        client = get_instagram_client()
        info = client.get_user_info(username)
        return (
            f"User profile details for @{info['username']}:\n"
            f"  Full Name: {info['full_name']}\n"
            f"  Bio: {info['biography']}\n"
            f"  Followers: {info['follower_count']}\n"
            f"  Following: {info['following_count']}\n"
            f"  Posts Count: {info['media_count']}"
        )
    except Exception as e:
        return f"Error: {e}"


@tool(
    name="instagram_get_direct_threads",
    description="Retrieves a list of recent direct message (DM) chat threads with user names and latest message previews. Optional: limit (int, default 10)."
)
def instagram_get_direct_threads(limit: int = 10, **kwargs) -> str:
    """Retrieve direct threads."""
    cred_err = _check_credentials()
    if cred_err:
        return cred_err

    try:
        client = get_instagram_client()
        threads = client.get_direct_threads(limit=limit)
        if not threads:
            return "No direct threads found."

        lines = [f"Recent Direct Threads (latest {len(threads)}):"]
        for t in threads:
            lines.append(f"  - Chat with: {t['name']} | Last message: {t['last_message']}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


@tool(
    name="instagram_get_user_posts",
    description="Retrieves recent post media IDs and captions for a user profile. Useful before commenting or liking. Arguments: username (str). Optional: limit (int, default 5)."
)
def instagram_get_user_posts(username: str, limit: int = 5, **kwargs) -> str:
    """Get recent user posts."""
    cred_err = _check_credentials()
    if cred_err:
        return cred_err

    try:
        client = get_instagram_client()
        posts = client.get_user_posts(username, limit=limit)
        if not posts:
            return f"No posts found for user @{username}."

        lines = [f"Recent posts for @{username} (showing {len(posts)}):"]
        for p in posts:
            lines.append(f"  - Post Code: {p['code']} | Media ID: {p['media_id']} | Caption: {p['caption']}... ({p['like_count']} likes)")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


# ─── Write Tools (Input validation + confirmation required) ──────

@tool(
    name="instagram_send_message",
    description="Sends a direct message (DM) to an Instagram username. Validates first, then prompts for your permission. Arguments: username (str), text (str)."
)
def instagram_send_message(username: str, text: Optional[str] = None, confirm_fn: Optional[Callable[[str], bool]] = None, **kwargs) -> str:
    """Send DM message."""
    cred_err = _check_credentials()
    if cred_err:
        return cred_err

    # Resilient argument fallback resolution
    resolved_text = text or kwargs.get("caption") or kwargs.get("message") or kwargs.get("body")
    if not resolved_text:
        return "Error: Message content parameter 'text' is missing."

    # Ask for permission
    prompt = f"Send Instagram DM to @{username} containing: '{resolved_text}'?"
    if not _request_permission(confirm_fn, prompt):
        return "Action cancelled by user: message was not sent."

    try:
        client = get_instagram_client()
        return client.send_direct_message(username, resolved_text)
    except Exception as e:
        return f"Error: {e}"


@tool(
    name="instagram_post_photo",
    description="Uploads a photo post to the Instagram feed. Validates file path and format first, then prompts for your permission. Arguments: image_path (str), caption (str)."
)
def instagram_post_photo(image_path: str, caption: Optional[str] = None, confirm_fn: Optional[Callable[[str], bool]] = None, **kwargs) -> str:
    """Upload post photo."""
    cred_err = _check_credentials()
    if cred_err:
        return cred_err

    # Resilient argument fallback resolution
    resolved_caption = caption or kwargs.get("text") or kwargs.get("description") or ""

    # Validation: File path and extension check
    path = Path(image_path)
    if not path.exists():
        return f"Error: Image file not found at path '{image_path}'."
    if path.suffix.lower() not in [".jpg", ".jpeg"]:
        return f"Error: Image at '{image_path}' must be in JPEG format (.jpg or .jpeg)."

    # Ask for permission
    prompt = f"Upload photo '{image_path}' to your feed with caption: '{resolved_caption}'?"
    if not _request_permission(confirm_fn, prompt):
        return "Action cancelled by user: photo was not uploaded."

    try:
        client = get_instagram_client()
        return client.post_photo(image_path, resolved_caption)
    except Exception as e:
        return f"Error: {e}"


@tool(
    name="instagram_comment",
    description="Writes a comment on an Instagram media post. Validates first, then prompts for your permission. Arguments: media_id (str), text (str)."
)
def instagram_comment(media_id: str, text: Optional[str] = None, confirm_fn: Optional[Callable[[str], bool]] = None, **kwargs) -> str:
    """Comment on a post."""
    cred_err = _check_credentials()
    if cred_err:
        return cred_err

    # Resilient argument fallback resolution
    resolved_text = text or kwargs.get("comment") or kwargs.get("body")
    if not resolved_text:
        return "Error: Comment content parameter 'text' is missing."

    # Ask for permission
    prompt = f"Write comment on media post '{media_id}': '{resolved_text}'?"
    if not _request_permission(confirm_fn, prompt):
        return "Action cancelled by user: comment was not posted."

    try:
        client = get_instagram_client()
        return client.comment_on_media(media_id, resolved_text)
    except Exception as e:
        return f"Error: {e}"


@tool(
    name="instagram_like",
    description="Likes an Instagram media post. Validates session limits first, then prompts for your permission. Arguments: media_id (str)."
)
def instagram_like(media_id: str, confirm_fn: Optional[Callable[[str], bool]] = None, **kwargs) -> str:
    """Like a post."""
    global _session_likes
    cred_err = _check_credentials()
    if cred_err:
        return cred_err

    # Validation: Session limits check
    max_likes = settings.instagram.max_likes
    if _session_likes >= max_likes:
        return f"Error: Session rate limit reached ({max_likes} likes). Automated action blocked to protect account."

    # Ask for permission
    prompt = f"Like Instagram media post {media_id}?"
    if not _request_permission(confirm_fn, prompt):
        return "Action cancelled by user: post was not liked."

    try:
        client = get_instagram_client()
        res = client.like_media(media_id)
        if "successfully" in res.lower():
            _session_likes += 1
        return res
    except Exception as e:
        return f"Error: {e}"


@tool(
    name="instagram_follow",
    description="Follows an Instagram username. Validates session limits first, then prompts for your permission. Arguments: username (str)."
)
def instagram_follow(username: str, confirm_fn: Optional[Callable[[str], bool]] = None, **kwargs) -> str:
    """Follow a user."""
    global _session_follows
    cred_err = _check_credentials()
    if cred_err:
        return cred_err

    # Validation: Session limits check
    max_follows = settings.instagram.max_follows
    if _session_follows >= max_follows:
        return f"Error: Session rate limit reached ({max_follows} follows). Automated action blocked to protect account."

    # Ask for permission
    prompt = f"Follow Instagram user @{username}?"
    if not _request_permission(confirm_fn, prompt):
        return "Action cancelled by user: user was not followed."

    try:
        client = get_instagram_client()
        res = client.follow_user(username)
        if "successfully" in res.lower():
            _session_follows += 1
        return res
    except Exception as e:
        return f"Error: {e}"


@tool(
    name="instagram_unfollow",
    description="Unfollows an Instagram username. Validates first, then prompts for your permission. Arguments: username (str)."
)
def instagram_unfollow(username: str, confirm_fn: Optional[Callable[[str], bool]] = None, **kwargs) -> str:
    """Unfollow a user."""
    cred_err = _check_credentials()
    if cred_err:
        return cred_err

    # Ask for permission
    prompt = f"Unfollow Instagram user @{username}?"
    if not _request_permission(confirm_fn, prompt):
        return "Action cancelled by user: user was not unfollowed."

    try:
        client = get_instagram_client()
        return client.unfollow_user(username)
    except Exception as e:
        return f"Error: {e}"
