# LLM Prompting Contract

## Overview
This contract defines how LLM assistants should interact with the Factory codebase.

## Required Process

### 1. Read First
Before generating any code:
- Review relevant briefing packet sections
- Check existing patterns in `/examples/`
- Understand current implementation

### 2. Plan
Provide a plan citing packet sources:
```markdown
## Plan
Based on `briefing/workflows/reusable.md`, I will:
1. Create reusable workflow for study provisioning
2. Follow permission patterns from `briefing/actions/permissions.md`
3. Implement webhook handler per `briefing/apps/authentication.md`
```

### 3. Generate Code
- Match existing code style
- Follow Factory patterns
- Include inline citations

Example:
```yaml
# Following briefing/security/best-practices.md#action-pinning
uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1
```

### 4. Validation Checklist
Include with every change:
```markdown
## Validation
- [ ] Permissions follow least-privilege (briefing/actions/permissions.md)
- [ ] Actions SHA-pinned (briefing/security/best-practices.md)
- [ ] Secrets via GitHub Secrets (briefing/security/best-practices.md)
- [ ] Tested with `act` locally
- [ ] Passes `actionlint` validation
```

## Citation Requirements

### Must Cite
- Security decisions
- Permission scopes
- Authentication methods
- Reusable patterns

### Citation Format
```yaml
# Per briefing/path/to/file.md#section
implementation_here
```

## Code Generation Rules

### Workflows
1. Start from `/examples/workflows/` templates
2. Use reusable workflows when possible
3. Pin all third-party actions
4. Minimal permissions only

### GitHub App
1. Use FastAPI + httpx pattern
2. Implement webhook verification
3. Cache installation tokens
4. Handle rate limits gracefully

### Security
1. No hardcoded secrets
2. No `write-all` permissions
3. No unguarded `pull_request_target`
4. Verify all webhooks

## Factory-Specific Patterns

### Study Creation
```markdown
Cite: briefing/workflows/reusable.md#study-lifecycle
Pattern: provision-study.yml workflow
```

### Portfolio Sync
```markdown
Cite: briefing/apps/authentication.md#factory-app-permissions  
Pattern: Webhook handler for issue events
```

### Stage Management
```markdown
Cite: examples/workflows/advance-stage.yml
Pattern: Label-based stage transitions
```

## Response Template

```markdown
## Analysis
[Review current state, cite briefing sections]

## Plan
[Steps to implement, with citations]

## Implementation
[Code with inline citations]

## Validation
[Checklist of verifications]

## Sources
- briefing/[relevant]/[files].md
- examples/[patterns]/[used].yml
```

## Prohibited Actions

Never:
- Generate code without citing sources
- Create new patterns without justification
- Skip validation checklist
- Modify security controls
- Access production secrets

## Quality Metrics

Good LLM responses:
- ✅ 100% of security decisions cited
- ✅ Validation checklist included
- ✅ Existing patterns reused
- ✅ No new dependencies without approval
- ✅ Passes all automated checks