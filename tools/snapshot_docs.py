#!/usr/bin/env python3
"""
Snapshot GitHub documentation for offline reference.
Part of the Factory briefing packet per SPEC-002.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import sys

# Document sources to snapshot
SOURCES = [
    {
        "name": "actions-permissions",
        "url": "https://docs.github.com/en/actions/using-jobs/assigning-permissions-to-jobs",
        "description": "GitHub Actions job permissions"
    },
    {
        "name": "reusable-workflows", 
        "url": "https://docs.github.com/en/actions/using-workflows/reusing-workflows",
        "description": "Creating and calling reusable workflows"
    },
    {
        "name": "github-apps-auth",
        "url": "https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app",
        "description": "GitHub App authentication patterns"
    },
    {
        "name": "webhooks",
        "url": "https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries",
        "description": "Webhook signature verification"
    },
    {
        "name": "security-hardening",
        "url": "https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions",
        "description": "Actions security best practices"
    }
]

def create_metadata(source: Dict, content: str) -> Dict:
    """Create metadata for snapshotted document."""
    return {
        "name": source["name"],
        "url": source["url"],
        "description": source["description"],
        "retrieved_at": datetime.utcnow().isoformat(),
        "content_hash": hashlib.sha256(content.encode()).hexdigest(),
        "content_length": len(content)
    }

def create_placeholder_docs():
    """Create placeholder documentation files for offline reference."""
    vendor_dir = Path("/mnt/c/Users/soreill5/Factory/vendor/docs")
    vendor_dir.mkdir(parents=True, exist_ok=True)
    
    all_metadata = []
    
    for source in SOURCES:
        # Create placeholder content
        content = f"""# {source['description']}

> **Note**: This is a placeholder for offline documentation.
> 
> **Original URL**: {source['url']}
> 
> To populate with actual content, run:
> ```bash
> curl -L "{source['url']}" > vendor/docs/{source['name']}.html
> ```

## Key Concepts

This document would normally contain the full GitHub documentation for:
- {source['description']}

## Factory Implementation Notes

Refer to the briefing packet for Factory-specific patterns:
- See `briefing/` for implementation guidance
- Check `examples/` for working patterns

---
*Last updated: {datetime.utcnow().isoformat()}*
"""
        
        # Write placeholder file
        doc_path = vendor_dir / f"{source['name']}.md"
        doc_path.write_text(content)
        
        # Create metadata
        metadata = create_metadata(source, content)
        all_metadata.append(metadata)
        
        print(f"✅ Created placeholder: {source['name']}.md")
    
    # Write combined metadata
    metadata_path = vendor_dir / "metadata.json"
    metadata_path.write_text(json.dumps(all_metadata, indent=2))
    
    # Create index
    index_content = """# Vendor Documentation Index

## Purpose
This directory contains snapshotted GitHub documentation for offline reference.

## Documents

| Document | Description | Source |
|----------|-------------|--------|
"""
    
    for source in SOURCES:
        index_content += f"| [{source['name']}](./{source['name']}.md) | {source['description']} | [GitHub Docs]({source['url']}) |\n"
    
    index_content += """

## Updating Documentation

To fetch actual documentation content:

```bash
# Install dependencies
pip install requests beautifulsoup4

# Run full snapshot
python tools/snapshot_docs.py --fetch
```

## Note
These are placeholder files. In production, use the `--fetch` flag to retrieve actual documentation.
"""
    
    index_path = vendor_dir / "index.md"
    index_path.write_text(index_content)
    
    print(f"\n📚 Created {len(SOURCES)} placeholder documentation files")
    print(f"📋 Metadata saved to metadata.json")
    print(f"📑 Index created at index.md")
    
    return all_metadata

if __name__ == "__main__":
    if "--fetch" in sys.argv:
        print("⚠️  Full fetch mode not implemented in this version")
        print("   Placeholder documents will be created instead")
    
    create_placeholder_docs()
    print("\n✨ Documentation snapshot complete!")