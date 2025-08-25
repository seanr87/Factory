# Factory Briefing Packet

## Purpose
This packet provides the authoritative guidance for maintaining and extending the OHDSI Study Factory system. It serves as the primary reference for both human developers and LLM coding assistants.

## Structure

### Core Concepts
- [`actions/`](./actions/) - GitHub Actions runners, permissions, caching, artifacts
- [`workflows/`](./workflows/) - Workflow syntax, reusable patterns, best practices
- [`apps/`](./apps/) - GitHub App architecture, authentication, webhooks
- [`security/`](./security/) - Least-privilege patterns, secret management, OIDC

### Development Guidance
- [`prompting/`](./prompting/) - LLM interaction contract and templates
- [`checklists/`](./checklists/) - PR review, release, and validation checklists

## Usage

### For Human Developers
1. Review relevant sections before making changes
2. Follow patterns from `/examples/` directory
3. Run validation tools before committing
4. Update this packet when GitHub features change

### For LLM Assistants
1. Always cite specific packet files when proposing changes
2. Follow the prompting contract in `prompting/contract.md`
3. Generate code matching patterns in `/examples/`
4. Include validation checklist with each PR

## Quick Links
- [GitHub Actions Permissions](./actions/permissions.md)
- [Reusable Workflow Patterns](./workflows/reusable.md)
- [GitHub App Authentication](./apps/authentication.md)
- [Security Best Practices](./security/best-practices.md)

## Version
- Last Updated: 2025-01-25
- GitHub API Version: 2022-11-28
- Runner Images: ubuntu-latest (22.04)