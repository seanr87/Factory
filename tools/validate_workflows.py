#!/usr/bin/env python3
"""
Validate workflows against Factory security policies.
Per briefing/security/best-practices.md
"""

import yaml
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Security policy rules
FORBIDDEN_PERMISSIONS = ["write-all", "admin"]
REQUIRED_PIN_ORGS = ["actions", "github", "docker"]
DANGEROUS_EVENTS = ["pull_request_target", "workflow_run"]

def check_permissions(workflow: Dict, path: str) -> List[str]:
    """Check for proper permission scoping."""
    issues = []
    
    # Check top-level permissions
    if "permissions" in workflow:
        perms = workflow["permissions"]
        if isinstance(perms, str) and perms in FORBIDDEN_PERMISSIONS:
            issues.append(f"❌ {path}: Forbidden permission '{perms}' at workflow level")
    
    # Check job-level permissions
    if "jobs" in workflow:
        for job_name, job in workflow["jobs"].items():
            if "permissions" in job:
                perms = job["permissions"]
                if isinstance(perms, str) and perms in FORBIDDEN_PERMISSIONS:
                    issues.append(f"❌ {path}: Forbidden permission '{perms}' in job '{job_name}'")
    
    return issues

def check_action_pinning(workflow: Dict, path: str) -> List[str]:
    """Check that third-party actions are properly pinned."""
    issues = []
    
    if "jobs" not in workflow:
        return issues
    
    for job_name, job in workflow["jobs"].items():
        if "steps" not in job:
            continue
            
        for i, step in enumerate(job["steps"]):
            if "uses" not in step:
                continue
                
            action = step["uses"]
            
            # Check if it's a third-party action that should be pinned
            for org in REQUIRED_PIN_ORGS:
                if action.startswith(f"{org}/"):
                    # Check if it's SHA-pinned (40 char hex)
                    if "@" in action:
                        ref = action.split("@")[1]
                        if not (len(ref) == 40 and all(c in "0123456789abcdef" for c in ref.lower())):
                            if not ref.startswith("v"):  # Allow version tags for official actions
                                issues.append(
                                    f"⚠️  {path}: Action '{action}' in job '{job_name}' step {i+1} "
                                    f"should be SHA-pinned"
                                )
                    else:
                        issues.append(
                            f"❌ {path}: Action '{action}' in job '{job_name}' step {i+1} "
                            f"is not pinned at all"
                        )
    
    return issues

def check_dangerous_triggers(workflow: Dict, path: str) -> List[str]:
    """Check for potentially dangerous workflow triggers."""
    issues = []
    
    if "on" not in workflow:
        return issues
    
    triggers = workflow["on"]
    
    # Handle both string and dict formats
    if isinstance(triggers, str):
        triggers = [triggers]
    elif isinstance(triggers, dict):
        triggers = list(triggers.keys())
    
    for trigger in triggers:
        if trigger in DANGEROUS_EVENTS:
            issues.append(
                f"⚠️  {path}: Uses potentially dangerous trigger '{trigger}'. "
                f"Ensure proper guards are in place."
            )
    
    return issues

def check_secrets(workflow: Dict, path: str) -> List[str]:
    """Check for hardcoded secrets or improper secret usage."""
    issues = []
    
    # Simple check for potential hardcoded secrets
    workflow_str = str(workflow)
    
    # Common secret patterns (simplified)
    suspicious_patterns = [
        "sk-", "api_key:", "password:", "token:", "secret:",
        "AKIA",  # AWS access key prefix
    ]
    
    for pattern in suspicious_patterns:
        if pattern in workflow_str:
            issues.append(
                f"🔍 {path}: Potential hardcoded secret detected (contains '{pattern}'). "
                f"Please review."
            )
    
    return issues

def validate_workflow(path: Path) -> Tuple[List[str], List[str]]:
    """Validate a single workflow file."""
    issues = []
    warnings = []
    
    try:
        with open(path) as f:
            workflow = yaml.safe_load(f)
        
        if not workflow:
            return issues, warnings
        
        # Run all checks
        issues.extend(check_permissions(workflow, str(path)))
        warnings.extend(check_action_pinning(workflow, str(path)))
        warnings.extend(check_dangerous_triggers(workflow, str(path)))
        issues.extend(check_secrets(workflow, str(path)))
        
    except yaml.YAMLError as e:
        issues.append(f"❌ {path}: Invalid YAML - {e}")
    except Exception as e:
        issues.append(f"❌ {path}: Error reading file - {e}")
    
    return issues, warnings

def main():
    """Run validation on all workflows."""
    workflows_dir = Path("/mnt/c/Users/soreill5/Factory/.github/workflows")
    
    if not workflows_dir.exists():
        print("❌ No .github/workflows directory found")
        return 1
    
    # Find all workflow files
    workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
    
    if not workflow_files:
        print("⚠️  No workflow files found")
        return 0
    
    all_issues = []
    all_warnings = []
    
    print(f"🔍 Validating {len(workflow_files)} workflow files...\n")
    
    for workflow_path in workflow_files:
        issues, warnings = validate_workflow(workflow_path)
        all_issues.extend(issues)
        all_warnings.extend(warnings)
    
    # Report results
    if all_issues:
        print("❌ CRITICAL ISSUES FOUND:\n")
        for issue in all_issues:
            print(f"  {issue}")
        print()
    
    if all_warnings:
        print("⚠️  WARNINGS:\n")
        for warning in all_warnings:
            print(f"  {warning}")
        print()
    
    if not all_issues and not all_warnings:
        print("✅ All workflows pass validation!")
        return 0
    
    print(f"Summary: {len(all_issues)} critical issues, {len(all_warnings)} warnings")
    
    # Return non-zero if critical issues found
    return 1 if all_issues else 0

if __name__ == "__main__":
    sys.exit(main())