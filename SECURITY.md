# Security Policy

AKBP stores durable knowledge for agents. That creates privacy and secret-handling risk.

## Supported versions

AKBP is currently pre-1.0. Security reports should target the latest `main` branch.

## Reporting security issues

Please report security issues privately to the repository owner instead of opening a public issue.

Do not include live secrets, tokens, private keys, cookies, production credentials, or private user data in public reports.

## Security principles

AKBP implementations should:

- avoid storing secrets by default
- redact credentials, tokens, cookies, private keys, and auth headers
- preserve evidence without leaking sensitive source content unnecessarily
- distinguish private, project, team, and public scopes
- keep local engine state separate from portable protocol artifacts
- support audit logs for write operations
- make destructive operations explicit and reviewable

## Sensitive data

Examples of data that should be redacted or excluded:

- API keys
- access tokens
- refresh tokens
- cookies
- private keys
- passwords
- connection strings with credentials
- personal data that is not required for the knowledge task
- private messages without permission

## Agent safety

Agents using AKBP should not blindly ingest every transcript or tool result. They should prefer durable, useful, evidence-backed claims and avoid storing noisy or sensitive raw data.
