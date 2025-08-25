#!/usr/bin/env python3
"""
Factory GitHub App - Minimal MVP
Per briefing/apps/authentication.md
"""

import os
import hmac
import hashlib
import logging
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from auth import create_jwt, get_installation_token
from handlers import handle_issue_labeled, handle_issue_closed

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Factory GitHub App",
    description="Minimal webhook handler for OHDSI Study Factory",
    version="1.0.0"
)

# Configuration from environment
WEBHOOK_SECRET = os.getenv("GITHUB_APP_WEBHOOK_SECRET", "")
APP_ID = os.getenv("GITHUB_APP_ID", "")
PRIVATE_KEY_PATH = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH", "")


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify GitHub webhook signature.
    Per briefing/apps/authentication.md#webhook-verification
    """
    if not secret:
        logger.warning("No webhook secret configured, skipping verification")
        return True
    
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(
        f"sha256={expected}",
        signature
    )


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "app": "Factory GitHub App"}


@app.get("/healthz")
async def health():
    """Kubernetes-style health check."""
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(
    request: Request,
    x_github_event: str = Header(None),
    x_hub_signature_256: Optional[str] = Header(None)
):
    """
    Handle GitHub webhook events.
    Currently handles:
    - issues.labeled: Update Factory tracking when stage labels change
    - issues.closed: Mark stage as complete
    """
    
    # Get raw payload for signature verification
    payload = await request.body()
    
    # Verify webhook signature
    if x_hub_signature_256 and WEBHOOK_SECRET:
        if not verify_signature(payload, x_hub_signature_256, WEBHOOK_SECRET):
            logger.error("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse JSON payload
    data = await request.json()
    
    # Log event
    action = data.get("action", "unknown")
    logger.info(f"Received event: {x_github_event}.{action}")
    
    # Route to appropriate handler
    try:
        if x_github_event == "issues":
            if action == "labeled":
                await handle_issue_labeled(data)
            elif action == "closed":
                await handle_issue_closed(data)
        
        elif x_github_event == "ping":
            logger.info("Received ping event")
            return {"message": "pong"}
        
        else:
            logger.info(f"Ignoring event: {x_github_event}.{action}")
    
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        # Don't fail the webhook, just log the error
    
    return {"status": "accepted"}


@app.on_event("startup")
async def startup_event():
    """Validate configuration on startup."""
    if not APP_ID:
        logger.warning("GITHUB_APP_ID not configured")
    
    if not PRIVATE_KEY_PATH or not os.path.exists(PRIVATE_KEY_PATH):
        logger.warning("GitHub App private key not found")
    
    if not WEBHOOK_SECRET:
        logger.warning("GITHUB_APP_WEBHOOK_SECRET not configured")
    
    logger.info("Factory GitHub App started")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)