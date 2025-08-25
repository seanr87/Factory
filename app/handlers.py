"""
Webhook event handlers for Factory GitHub App.
Handles stage progression tracking.
"""

import os
import logging
from typing import Dict, Any

import httpx
from githubkit import GitHub
from githubkit.auth import AppAuth

from auth import get_installation_token, get_app_installation_id

logger = logging.getLogger(__name__)

# Configuration
FACTORY_REPO = os.getenv("FACTORY_REPO", "")
GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com")

# Stage label mapping
STAGE_LABELS = {
    "stage:initiation": "Initiation",
    "stage:protocol-development": "Protocol Development",
    "stage:phenotype-development": "Phenotype Development",
    "stage:analysis-specifications": "Analysis Specifications",
    "stage:network-execution": "Network Execution",
    "stage:results-evaluation": "Results Evaluation"
}


async def handle_issue_labeled(payload: Dict[str, Any]):
    """
    Handle issue.labeled event.
    Updates Factory tracking issue when a stage label is added.
    """
    issue = payload.get("issue", {})
    label = payload.get("label", {})
    repo = payload.get("repository", {})
    
    label_name = label.get("name", "")
    repo_full_name = repo.get("full_name", "")
    
    # Check if it's a stage label
    if not label_name.startswith("stage:"):
        logger.info(f"Ignoring non-stage label: {label_name}")
        return
    
    stage_name = STAGE_LABELS.get(label_name, label_name)
    logger.info(f"Stage label added: {stage_name} in {repo_full_name}")
    
    # Update Factory tracking issue
    await update_factory_tracking(repo_full_name, stage_name, "started")


async def handle_issue_closed(payload: Dict[str, Any]):
    """
    Handle issue.closed event.
    Updates Factory tracking when a stage issue is closed (completed).
    """
    issue = payload.get("issue", {})
    repo = payload.get("repository", {})
    
    # Check if issue has a stage label
    labels = issue.get("labels", [])
    stage_labels = [l for l in labels if l.get("name", "").startswith("stage:")]
    
    if not stage_labels:
        logger.info("Issue closed but no stage label found")
        return
    
    # Get the stage name
    label_name = stage_labels[0].get("name", "")
    stage_name = STAGE_LABELS.get(label_name, label_name)
    repo_full_name = repo.get("full_name", "")
    
    logger.info(f"Stage completed: {stage_name} in {repo_full_name}")
    
    # Update Factory tracking issue
    await update_factory_tracking(repo_full_name, stage_name, "completed")


async def update_factory_tracking(
    study_repo: str,
    stage_name: str,
    status: str
):
    """
    Update the Factory tracking issue for a study.
    This is a simplified version - finds and updates the tracking issue.
    """
    if not FACTORY_REPO:
        logger.warning("FACTORY_REPO not configured, skipping update")
        return
    
    try:
        # Get installation token for Factory repo
        installation_id = await get_app_installation_id(FACTORY_REPO)
        if not installation_id:
            logger.error(f"No installation found for {FACTORY_REPO}")
            return
        
        token = await get_installation_token(installation_id)
        
        # Search for tracking issue
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Find the tracking issue by searching for the repo URL in the body
        search_query = f"repo:{FACTORY_REPO} is:issue is:open {study_repo}"
        search_url = f"{GITHUB_API_URL}/search/issues?q={search_query}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(search_url, headers=headers)
            response.raise_for_status()
            data = response.json()
        
        if data.get("total_count", 0) == 0:
            logger.warning(f"No tracking issue found for {study_repo}")
            return
        
        # Get the first matching issue
        issue = data["items"][0]
        issue_number = issue["number"]
        current_body = issue["body"] or ""
        
        # Update the stage checklist in the body
        # This is a simple string replacement - in production, use proper markdown parsing
        if status == "completed":
            # Mark stage as complete
            old_line = f"- [ ] {stage_name}"
            new_line = f"- [x] {stage_name}"
            updated_body = current_body.replace(old_line, new_line)
        else:
            # Just update the timestamp
            updated_body = current_body
        
        # Update last activity
        import datetime
        timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        updated_body = updated_body.replace(
            "Last updated:",
            f"Last updated: {timestamp}\nLast stage: {stage_name} ({status})\nPrevious:"
        )
        
        # Update the issue
        update_url = f"{GITHUB_API_URL}/repos/{FACTORY_REPO}/issues/{issue_number}"
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                update_url,
                headers=headers,
                json={"body": updated_body}
            )
            response.raise_for_status()
        
        logger.info(f"Updated Factory tracking issue #{issue_number}")
        
    except Exception as e:
        logger.error(f"Failed to update Factory tracking: {e}")