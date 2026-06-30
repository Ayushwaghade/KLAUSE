import os
import json
from typing import List, Dict, Any
from pathlib import Path
from loguru import logger
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ClientError
from app.config.config import settings

class InstagramClient:
    """
    Wrapper agent for instagrapi (Instagram Private API).
    Manages persistent JSON sessions, self-healing logins, formatting, and limits.
    """

    def __init__(self):
        self.client = Client()
        project_root = Path(__file__).resolve().parent.parent.parent
        self.session_path = project_root / "data" / "instagram_session.json"
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        self.username = os.environ.get("INSTAGRAM_USERNAME") or settings.instagram.username
        self.password = os.environ.get("INSTAGRAM_PASSWORD") or settings.instagram.password

    def login(self, force_fresh: bool = False) -> bool:
        """Log in to Instagram and dump settings to reuse sessions."""
        from dotenv import load_dotenv
        import os
        load_dotenv(override=True)
        self.username = os.environ.get("INSTAGRAM_USERNAME") or settings.instagram.username
        self.password = os.environ.get("INSTAGRAM_PASSWORD") or settings.instagram.password

        if (not self.username or not self.password or 
            self.username in ("", "your_username") or 
            self.password in ("", "your_password")):
            logger.error("Instagram credentials are not configured or are placeholders.")
            return False

        # Attempt to load session if not forcing fresh
        if not force_fresh and self.session_path.exists():
            try:
                logger.info(f"Loading Instagram session from {self.session_path}...")
                self.client.load_settings(self.session_path)
                # Try simple login check
                self.client.login(self.username, self.password)
                logger.info("Instagram login successful using saved session settings.")
                return True
            except Exception as e:
                logger.warning(f"Failed to login with existing session: {e}. Attempting fresh login.")

        # Fresh login
        try:
            logger.info(f"Executing fresh Instagram login for username '{self.username}'...")
            self.client.login(self.username, self.password)
            self.client.dump_settings(self.session_path)
            logger.info("Fresh Instagram login successful; session settings persisted.")
            return True
        except Exception as e:
            logger.error(f"Fresh Instagram login failed: {e}")
            return False

    def ensure_logged_in(self):
        """Lightweight login check executed before every API action. Re-logs in if expired."""
        try:
            # Quick lightweight request to check session state
            self.client.get_timeline_feed()
        except (LoginRequired, ClientError):
            logger.warning("Instagram session went stale. Triggering automatic self-healing login...")
            if not self.login(force_fresh=True):
                raise RuntimeError("Instagram self-healing login failed. Please verify credentials.")
        except Exception as e:
            # If it's a connection issue or other error, try a login anyway
            logger.warning(f"Instagram session check encountered error: {e}. Trying re-login.")
            if not self.login(force_fresh=False):
                raise RuntimeError(f"Instagram login check failed: {e}")

    # ─── Operational Read-Only Methods ────────────────────────────

    def search_users(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch profiles matching query. Caps results and returns clean fields."""
        self.ensure_logged_in()
        logger.info(f"Instagram: Searching for users matching '{query}' (limit: {limit})")
        
        try:
            users = self.client.search_users(query)
            results = []
            for u in users[:limit]:
                results.append({
                    "username": u.username,
                    "full_name": u.full_name,
                    "follower_count": getattr(u, "follower_count", "unknown"),
                    "pk": u.pk
                })
            return results
        except Exception as e:
            logger.error(f"Instagram search failed: {e}")
            raise

    def get_user_info(self, username: str) -> Dict[str, Any]:
        """Fetch bio, follower counts, and profile details for a username."""
        self.ensure_logged_in()
        logger.info(f"Instagram: Fetching user info for '{username}'")
        
        try:
            user_id = self.client.user_id_from_username(username)
            info = self.client.user_info(user_id)
            return {
                "username": info.username,
                "full_name": info.full_name,
                "biography": info.biography,
                "follower_count": info.follower_count,
                "following_count": info.following_count,
                "media_count": info.media_count,
                "pk": info.pk
            }
        except Exception as e:
            logger.error(f"Instagram fetch user info failed for '{username}': {e}")
            raise

    def get_direct_threads(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent DM threads showing username and latest message preview."""
        self.ensure_logged_in()
        logger.info(f"Instagram: Retrieving direct threads (limit: {limit})")
        
        try:
            threads = self.client.direct_threads(amount=limit)
            results = []
            for t in threads:
                # Find users in thread that are not the current user
                other_users = [u.username for u in t.users if u.username != self.username]
                thread_name = ", ".join(other_users) if other_users else "Unknown Thread"
                
                latest_msg = ""
                if t.messages:
                    raw_text = t.messages[0].text or "[Non-text message]"
                    latest_msg = (raw_text[:60] + "...") if len(raw_text) > 60 else raw_text
                
                results.append({
                    "thread_id": t.id,
                    "name": thread_name,
                    "last_message": latest_msg,
                    "users": other_users
                })
            return results
        except Exception as e:
            logger.error(f"Instagram list DM threads failed: {e}")
            raise

    def get_user_posts(self, username: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieves recent posts for a user, containing media ID and caption preview."""
        self.ensure_logged_in()
        logger.info(f"Instagram: Fetching posts for '{username}' (limit: {limit})")
        
        try:
            user_id = self.client.user_id_from_username(username)
            medias = self.client.user_medias(user_id, amount=limit)
            results = []
            for m in medias:
                results.append({
                    "media_id": m.id,
                    "code": m.code,
                    "media_type": m.media_type,
                    "caption": m.caption_text[:60] if m.caption_text else "",
                    "like_count": m.like_count
                })
            return results
        except Exception as e:
            logger.error(f"Instagram fetch posts failed for user '{username}': {e}")
            raise

    # ─── Operational Write Methods ────────────────────────────────

    def send_direct_message(self, username: str, text: str) -> str:
        """Send a DM to a user by username."""
        self.ensure_logged_in()
        logger.info(f"Instagram: Sending message to '{username}'...")
        
        try:
            user_id = self.client.user_id_from_username(username)
            result = self.client.direct_send(text, user_ids=[user_id])
            return f"Successfully sent message to @{username}. Message ID: {result.id}"
        except Exception as e:
            logger.error(f"Instagram send DM failed: {e}")
            return f"Error sending message: {e}"

    def post_photo(self, image_path: str, caption: str) -> str:
        """Uploads a photo post to the feed."""
        self.ensure_logged_in()
        logger.info(f"Instagram: Uploading photo '{image_path}' to feed...")
        
        try:
            media = self.client.photo_upload(Path(image_path), caption)
            return f"Successfully posted photo to Instagram. Media Code: {media.code}"
        except Exception as e:
            logger.error(f"Instagram photo upload failed: {e}")
            return f"Error posting photo: {e}"

    def comment_on_media(self, media_id: str, text: str) -> str:
        """Write a comment on a media post."""
        self.ensure_logged_in()
        logger.info(f"Instagram: Writing comment on media {media_id}...")
        
        try:
            comment = self.client.media_comment(media_id, text)
            return f"Successfully commented on post. Comment ID: {comment.pk}"
        except Exception as e:
            logger.error(f"Instagram comment failed: {e}")
            return f"Error posting comment: {e}"

    def like_media(self, media_id: str) -> str:
        """Like a media post."""
        self.ensure_logged_in()
        logger.info(f"Instagram: Liking media {media_id}...")
        
        try:
            self.client.media_like(media_id)
            return f"Successfully liked post {media_id}."
        except Exception as e:
            logger.error(f"Instagram like failed: {e}")
            return f"Error liking post: {e}"

    def follow_user(self, username: str) -> str:
        """Follow a user by username."""
        self.ensure_logged_in()
        logger.info(f"Instagram: Following user '{username}'...")
        
        try:
            user_id = self.client.user_id_from_username(username)
            self.client.user_follow(user_id)
            return f"Successfully followed user @{username}."
        except Exception as e:
            logger.error(f"Instagram follow failed: {e}")
            return f"Error following user: {e}"

    def unfollow_user(self, username: str) -> str:
        """Unfollow a user by username."""
        self.ensure_logged_in()
        logger.info(f"Instagram: Unfollowing user '{username}'...")
        
        try:
            user_id = self.client.user_id_from_username(username)
            self.client.user_unfollow(user_id)
            return f"Successfully unfollowed user @{username}."
        except Exception as e:
            logger.error(f"Instagram unfollow failed: {e}")
            return f"Error unfollowing user: {e}"


# Singleton client helper
_instagram_client_inst = None

def get_instagram_client() -> InstagramClient:
    global _instagram_client_inst
    if _instagram_client_inst is None:
        _instagram_client_inst = InstagramClient()
    return _instagram_client_inst
