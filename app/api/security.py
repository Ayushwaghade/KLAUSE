import os
import secrets
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.security.api_key import APIKeyQuery
from loguru import logger

from app.config.config import settings

# Path to local token store
TOKEN_FILE = os.path.join("data", ".server_token")

# Bearer helper for standard HTTP routes
security_bearer = HTTPBearer(auto_error=False)

# Query param helper for WebSockets
security_query = APIKeyQuery(name="token", auto_error=False)

_cached_token = None

def get_or_generate_token() -> str:
    """
    Retrieve existing token or generate a secure new one.
    """
    global _cached_token
    if _cached_token:
        return _cached_token

    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                token = f.read().strip()
                if token:
                    _cached_token = token
                    logger.info("Security: Loaded existing server token.")
                    return token
        except Exception as e:
            logger.warning(f"Security: Failed to read token file: {e}")

    # Generate new one
    token = secrets.token_hex(32)
    try:
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(token)
        logger.info(f"Security: Generated new server token and saved to {TOKEN_FILE}")
    except Exception as e:
        logger.error(f"Security: Failed to write token file: {e}")
        
    _cached_token = token
    return token

def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security_bearer),
    token_query: str = Security(security_query)
) -> str:
    """
    Validates token via HTTP Header Bearer or query parameters (for WebSockets).
    """
    expected_token = get_or_generate_token()
    
    # Check Bearer Header
    if credentials and credentials.credentials == expected_token:
        return expected_token
        
    # Check query parameter (WebSockets)
    if token_query == expected_token:
        return expected_token
        
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication token."
    )
