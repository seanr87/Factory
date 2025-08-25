# Vendor Documentation Index

## Purpose
This directory contains snapshotted GitHub documentation for offline reference.

## Documents

| Document | Description | Source |
|----------|-------------|--------|
| [actions-permissions](./actions-permissions.md) | GitHub Actions job permissions | [GitHub Docs](https://docs.github.com/en/actions/using-jobs/assigning-permissions-to-jobs) |
| [reusable-workflows](./reusable-workflows.md) | Creating and calling reusable workflows | [GitHub Docs](https://docs.github.com/en/actions/using-workflows/reusing-workflows) |
| [github-apps-auth](./github-apps-auth.md) | GitHub App authentication patterns | [GitHub Docs](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app) |
| [webhooks](./webhooks.md) | Webhook signature verification | [GitHub Docs](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries) |
| [security-hardening](./security-hardening.md) | Actions security best practices | [GitHub Docs](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions) |


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
