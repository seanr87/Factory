#!/usr/bin/env python3
"""
Test script for Factory GitHub App
Tests webhook signature verification and event handling
"""

import json
import hmac
import hashlib
from fastapi.testclient import TestClient

# Test configuration
TEST_SECRET = "test_webhook_secret"
TEST_PAYLOAD = {
    "action": "labeled",
    "issue": {
        "number": 1,
        "title": "Stage: Protocol Development",
        "labels": [{"name": "stage:protocol-development"}]
    },
    "label": {
        "name": "stage:protocol-development"
    },
    "repository": {
        "full_name": "test-org/study-test"
    }
}


def create_signature(payload: bytes, secret: str) -> str:
    """Create GitHub webhook signature."""
    signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


def test_health_check():
    """Test health check endpoints."""
    from main import app
    client = TestClient(app)
    
    # Test root endpoint
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    
    # Test health endpoint
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    
    print("✅ Health check tests passed")


def test_webhook_ping():
    """Test webhook ping event."""
    from main import app
    client = TestClient(app)
    
    payload = {"zen": "Design for failure."}
    response = client.post(
        "/webhook",
        json=payload,
        headers={"X-GitHub-Event": "ping"}
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "pong"
    
    print("✅ Webhook ping test passed")


def test_webhook_signature():
    """Test webhook signature verification."""
    import os
    from main import app
    
    # Set test secret
    os.environ["GITHUB_APP_WEBHOOK_SECRET"] = TEST_SECRET
    
    client = TestClient(app)
    
    # Test with valid signature
    payload_bytes = json.dumps(TEST_PAYLOAD).encode()
    signature = create_signature(payload_bytes, TEST_SECRET)
    
    response = client.post(
        "/webhook",
        content=payload_bytes,
        headers={
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": signature,
            "Content-Type": "application/json"
        }
    )
    
    assert response.status_code == 200
    print("✅ Valid signature test passed")
    
    # Test with invalid signature
    bad_signature = "sha256=invalid"
    
    response = client.post(
        "/webhook",
        content=payload_bytes,
        headers={
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": bad_signature,
            "Content-Type": "application/json"
        }
    )
    
    # Should fail with 401
    assert response.status_code == 401
    print("✅ Invalid signature test passed")


def test_issue_labeled_event():
    """Test issue labeled event handling."""
    from main import app
    client = TestClient(app)
    
    response = client.post(
        "/webhook",
        json=TEST_PAYLOAD,
        headers={"X-GitHub-Event": "issues"}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    
    print("✅ Issue labeled event test passed")


def test_issue_closed_event():
    """Test issue closed event handling."""
    from main import app
    client = TestClient(app)
    
    payload = {
        "action": "closed",
        "issue": {
            "number": 1,
            "title": "Stage: Protocol Development",
            "labels": [{"name": "stage:protocol-development"}]
        },
        "repository": {
            "full_name": "test-org/study-test"
        }
    }
    
    response = client.post(
        "/webhook",
        json=payload,
        headers={"X-GitHub-Event": "issues"}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    
    print("✅ Issue closed event test passed")


if __name__ == "__main__":
    print("🧪 Testing Factory GitHub App")
    print("==============================\n")
    
    try:
        test_health_check()
        test_webhook_ping()
        test_webhook_signature()
        test_issue_labeled_event()
        test_issue_closed_event()
        
        print("\n✨ All tests passed!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        exit(1)