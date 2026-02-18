# Tenant API Key Management and Rotation Runbook

## Purpose
Define deterministic operational procedures for tenant API key lifecycle management: generation, rotation, and revocation.

## Configuration Format
Security settings are provided via environment variables:

- `COMPLIANCE_APP_SECURITY_ENABLED` (`true`/`false`)
- `COMPLIANCE_APP_AUTH_API_KEYS` (comma-separated global fallback keys)
- `COMPLIANCE_APP_AUTH_TENANT_KEYS` (comma-separated `tenant:key` pairs)

Example:

```bash
COMPLIANCE_APP_SECURITY_ENABLED=true
COMPLIANCE_APP_AUTH_API_KEYS=global-readonly-key
COMPLIANCE_APP_AUTH_TENANT_KEYS=tenant-a:key-a-v1,tenant-a:key-a-v2,tenant-b:key-b-v1
```

Validation rules:
- Each tenant mapping must follow `tenant:key`.
- Empty tenant IDs or keys are rejected.
- When security is enabled, at least one key must be configured.

## Key Generation
1. Generate a random key using a cryptographically secure generator.
2. Prefix keys with tenant and version in your secrets manager metadata (not in key value).
3. Store keys only in approved secret stores.

Recommended command:

```bash
openssl rand -base64 32
```

## Rotation Cadence
- Rotate tenant keys at least every 90 days.
- Keep overlap window with old+new keys for controlled rollout.
- Add new key first, deploy, verify traffic, then remove old key.

Rotation sequence:
1. Add `tenant:key-v2` while keeping `tenant:key-v1`.
2. Roll client configuration to `key-v2`.
3. Monitor authentication failures for one full business cycle.
4. Remove `key-v1` from `COMPLIANCE_APP_AUTH_TENANT_KEYS`.

## Revocation Procedure
Immediate revocation is required if key compromise is suspected.

1. Remove compromised key from auth environment variables.
2. Redeploy service to apply updated configuration.
3. Confirm requests with revoked key now return `403`.
4. Issue replacement key and update clients.
5. Record incident and timeline in security log.

## Verification Checklist
- Startup succeeds with current key map.
- Malformed key maps fail fast at startup.
- Tenant-scoped endpoints reject cross-tenant key usage.
- Audit logs and run events capture security-relevant operations.
