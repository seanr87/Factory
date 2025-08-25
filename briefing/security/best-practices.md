# Security Best Practices

## Secrets Management

### ✅ DO
```yaml
# Use GitHub secrets
env:
  API_KEY: ${{ secrets.API_KEY }}

# Use environments for production
environment: production
```

### ❌ DON'T
```yaml
# Never hardcode secrets
env:
  API_KEY: "sk-abc123..."  # NEVER DO THIS

# Don't echo secrets
run: echo ${{ secrets.API_KEY }}  # EXPOSED IN LOGS
```

## Action Pinning

### Use SHA Pinning for Third-Party Actions
```yaml
# Good - SHA pinned
uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1

# Acceptable - Official actions with version
uses: actions/setup-python@v4

# Bad - Unpinned
uses: some-org/some-action@main  # VULNERABLE
```

## Pull Request Security

### Safe PR Handling
```yaml
# Safe - limited token permissions
on:
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: read
  pull-requests: write
```

### Dangerous Pattern
```yaml
# DANGEROUS - gives PR code access to secrets
on:
  pull_request_target:  # Runs on base branch with secrets

# Mitigation if required
jobs:
  safe-pr:
    if: github.event.pull_request.head.repo.full_name == github.repository
```

## OIDC for Cloud Access

### Preferred: OIDC Instead of Long-Lived Keys
```yaml
permissions:
  id-token: write
  contents: read

steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: arn:aws:iam::123456:role/GitHubActions
      aws-region: us-east-1
```

## Factory-Specific Security

### Study Provisioning
- Use org-admin token only for repo creation
- Immediately downgrade to repo-specific permissions
- Audit all repo creations

### Portfolio Updates  
- App token scoped to specific installation
- Webhook signature verification required
- Rate limit monitoring

### Data Partner Access
- No direct access to Factory workflows
- Partner updates via PR only
- Automated validation before merge

## Security Checklist

- [ ] All secrets in GitHub Secrets or environment
- [ ] Third-party actions pinned to SHA
- [ ] Minimal permissions specified
- [ ] No `pull_request_target` without guards
- [ ] OIDC for cloud authentication
- [ ] Webhook signatures verified
- [ ] Logs sanitized (no secret exposure)
- [ ] Regular security audit (monthly)

## Incident Response

1. **Leaked Secret**: Immediately rotate via Settings → Secrets
2. **Compromised Action**: Pin to last known good SHA
3. **Suspicious PR**: Close and report to security team
4. **Rate Limit Hit**: Implement caching and backoff

## Compliance

- SOC 2: Audit logs enabled
- HIPAA: No PHI in workflows
- GDPR: No PII in public logs