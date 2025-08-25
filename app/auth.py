"""
GitHub App authentication module.
Per briefing/apps/authentication.md
"""

import os
import jwt
import time
import logging
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Configuration
APP_ID = os.getenv("GITHUB_APP_ID", "")
PRIVATE_KEY_PATH = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH", "")
GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com")

# Cache for installation tokens (simple in-memory cache)
_token_cache = {}


def create_jwt(app_id: str = APP_ID, private_key_path: str = PRIVATE_KEY_PATH) -> str:
    """
    Create JWT for GitHub App authentication.
    Per briefing/apps/authentication.md#jwt-creation
    """
    if not app_id or not private_key_path:
        raise ValueError("App ID and private key path required")
    
    # Read private key
    private_key = Path(private_key_path).read_text()
    
    # Create JWT payload
    now = int(time.time())
    payload = {
        "iat": now,
        "exp": now + 600,  # 10 minutes
        "iss": app_id
    }
    
    # Sign and return JWT
    token = jwt.encode(payload, private_key, algorithm="RS256")
    logger.info("Created JWT for GitHub App authentication")
    return token


async def get_installation_token(
    installation_id: str,
    app_id: str = APP_ID,
    private_key_path: str = PRIVATE_KEY_PATH
) -> str:
    """
    Exchange JWT for installation access token.
    Per briefing/apps/authentication.md#installation-token-exchange
    
    Implements simple caching to avoid unnecessary API calls.
    """
    # Check cache
    cache_key = f"token_{installation_id}"
    cached = _token_cache.get(cache_key)
    if cached:
        expires_at = cached.get("expires_at", 0)
        if time.time() < expires_at - 300:  # 5 minute buffer
            logger.info(f"Using cached token for installation {installation_id}")
            return cached["token"]
    
    # Create new JWT
    jwt_token = create_jwt(app_id, private_key_path)
    
    # Exchange for installation token
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    url = f"{GITHUB_API_URL}/app/installations/{installation_id}/access_tokens"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers)
        response.raise_for_status()
        data = response.json()
    
    # Cache the token
    _token_cache[cache_key] = {
        "token": data["token"],
        "expires_at": time.time() + 3600  # Tokens expire in 1 hour
    }
    
    logger.info(f"Obtained new installation token for {installation_id}")
    return data["token"]


async def get_app_installation_id(repo_full_name: str) -> Optional[str]:
    """
    Get installation ID for a repository.
    This is a simplified version - in production, you'd cache this mapping.
    """
    # Create JWT
    jwt_token = create_jwt()
    
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Get repository installation
    url = f"{GITHUB_API_URL}/repos/{repo_full_name}/installation"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return str(data["id"])
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to get installation for {repo_full_name}: {e}")
        return None


def clear_token_cache():
    """Clear the token cache (useful for testing)."""
    global _token_cache
    _token_cache = {}
    logger.info("Cleared token cache")