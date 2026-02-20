# NotebookLM Auth Governance

## Policy
- Use dedicated service account only.
- Personal accounts are prohibited for shared environments.
- Store session material only in approved profile storage (Docker volume or approved secure path).

## Access control
- Limit service account ownership to designated operators.
- Enforce MFA and rotation cadence according to org policy.

## Rotation
1. Disable NotebookLM flags.
2. Revoke session for service account.
3. Clear local profile storage.
4. Re-authenticate with service account.
5. Re-enable flags after smoke validation.
