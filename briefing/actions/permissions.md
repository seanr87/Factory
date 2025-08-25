# GitHub Actions Permissions

## Overview
GitHub Actions uses a least-privilege model for the `GITHUB_TOKEN`. Always specify minimal required permissions.

## Permission Scopes

### Repository Permissions
```yaml
permissions:
  contents: read        # Clone repo, read files
  issues: write        # Create/update issues
  pull-requests: write # Create/update PRs
  actions: read        # Read workflow runs
  packages: write      # Publish packages
```

### Organization Permissions
For org-wide operations, use a Personal Access Token (PAT) or GitHub App token stored as a secret:
```yaml
env:
  GH_TOKEN: ${{ secrets.ORG_ADMIN_TOKEN }}
```

## Best Practices

### ✅ DO
- Specify permissions at job level when possible
- Use `read` permissions by default
- Escalate to `write` only when needed
- Use GitHub App tokens for cross-repo access

### ❌ DON'T
- Use `permissions: write-all`
- Share tokens between workflows
- Hardcode tokens in workflows
- Use admin tokens for read operations

## Factory-Specific Patterns

### Study Provisioning
```yaml
permissions:
  contents: read    # Read template
  issues: write     # Create Factory issue

env:
  GH_TOKEN: ${{ secrets.ORG_ADMIN_TOKEN }}  # For repo creation
```

### Portfolio Updates
```yaml
permissions:
  issues: write         # Update Factory issues
  projects: write       # Update project boards
  repository-projects: write  # Access project v2
```

## Token Types

| Token Type | Use Case | Scope |
|------------|----------|-------|
| GITHUB_TOKEN | Same-repo operations | Current repo only |
| PAT | Cross-repo, org operations | User-defined |
| GitHub App | Service operations | App-defined |

## Security Notes
- Tokens expire after job completion
- Use environments for production secrets
- Rotate PATs regularly (90 days)
- Audit token usage in Security tab