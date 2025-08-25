#!/usr/bin/env python3
"""
Package the briefing packet into a zip file for LLM ingestion.
Per SPEC-002 requirements.
"""

import zipfile
import json
from pathlib import Path
from datetime import datetime

def create_briefing_zip():
    """Create briefing.zip with all necessary documentation."""
    
    factory_root = Path("/mnt/c/Users/soreill5/Factory")
    output_path = factory_root / "briefing.zip"
    
    # Directories to include
    include_dirs = [
        "briefing",
        "vendor/docs",
        ".github/workflows",
    ]
    
    # Individual files to include
    include_files = [
        "docs/SPEC-001.md",
        "docs/SPEC-002_briefing-packet.md",
        "IMPLEMENTATION_PLAN.md",
        "Makefile",
    ]
    
    # Create the zip file
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        
        # Add directories
        for dir_name in include_dirs:
            dir_path = factory_root / dir_name
            if dir_path.exists():
                for file_path in dir_path.rglob("*"):
                    if file_path.is_file():
                        # Calculate relative path for zip
                        arcname = file_path.relative_to(factory_root)
                        zipf.write(file_path, arcname)
                        print(f"  📄 Added: {arcname}")
        
        # Add individual files
        for file_name in include_files:
            file_path = factory_root / file_name
            if file_path.exists():
                zipf.write(file_path, file_name)
                print(f"  📄 Added: {file_name}")
        
        # Create and add metadata
        metadata = {
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "purpose": "Factory briefing packet for LLM assistance",
            "spec_compliance": ["SPEC-001", "SPEC-002"],
            "contents": {
                "briefing": "Core implementation guidance",
                "vendor_docs": "Snapshotted GitHub documentation",
                "workflows": "Active GitHub Actions workflows",
                "specs": "System specifications"
            }
        }
        
        # Write metadata to zip
        metadata_json = json.dumps(metadata, indent=2)
        zipf.writestr("MANIFEST.json", metadata_json)
        print(f"  📋 Added: MANIFEST.json")
        
        # Create a quick reference index
        index_content = """# Factory Briefing Packet Index

## Quick Start
1. Review SPEC-001.md for requirements
2. Review SPEC-002_briefing-packet.md for approach
3. Check briefing/ for implementation guidance
4. Use .github/workflows/ as templates

## Key Files
- briefing/index.md - Main briefing entry point
- briefing/prompting/contract.md - LLM interaction rules
- IMPLEMENTATION_PLAN.md - Development roadmap

## Citation Format
When referencing this packet, use:
`Per briefing/[section]/[file].md#anchor`
"""
        
        zipf.writestr("INDEX.md", index_content)
        print(f"  📑 Added: INDEX.md")
    
    # Report results
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"\n✅ Created briefing.zip ({size_mb:.2f} MB)")
    print(f"📍 Location: {output_path}")
    
    # Verify the zip
    with zipfile.ZipFile(output_path, 'r') as zipf:
        file_count = len(zipf.namelist())
        print(f"📦 Contains {file_count} files")
    
    return str(output_path)

if __name__ == "__main__":
    print("📦 Packaging Factory briefing packet...")
    print()
    
    try:
        zip_path = create_briefing_zip()
        print("\n✨ Briefing packet ready for LLM ingestion!")
        print(f"\nUsage: Upload {zip_path} to Claude or other LLM")
    except Exception as e:
        print(f"\n❌ Error creating briefing packet: {e}")
        import traceback
        traceback.print_exc()
        exit(1)