# Security Notes

[← Back to README](../README.md)

## Purpose

This document records security and operational guidance for deploying the project safely.

It describes design expectations rather than environment-specific secrets, addresses, or incident details.

---

## 1. Trust Boundaries

The system contains several trust boundaries:

```text
pfSense → Collector
Collector Files → n8n
n8n → Ansible API
n8n ↔ Telegram
Ansible → pfSense
```

Each boundary should be treated as an independent security interface.

A component being trusted does not imply that every input it receives should be trusted automatically.

---

## 2. Secrets Management

Sensitive values include:

- Telegram Bot tokens.
- n8n credentials.
- API authentication secrets.
- pfSense credentials used by Ansible.
- SSH keys.
- Environment-specific access tokens.

Requirements:

- Do not hard-code secrets in exported workflow JSON.
- Do not commit secrets to Git.
- Use n8n Credentials, environment variables, or an external secret manager.
- Rotate any secret that may have been exposed.
- Give each integration only the permissions it needs.

---

## 3. Syslog Source Validation

UDP Syslog does not provide strong sender authentication by itself.

The collector supports source filtering and should restrict accepted senders in non-lab environments.

Additional network controls may include:

- Host firewall rules.
- Dedicated management network.
- ACLs.
- Restricted routing.

The collector should not be exposed broadly when it only needs to receive logs from pfSense.

---

## 4. Input Validation

Automation endpoints must validate all inputs before using them in infrastructure operations.

Examples:

### IP Address

Validate:

- Syntax.
- Allowed address family.
- Whether the address belongs to a protected/reserved range.
- Whether the address should ever be blocked.

### MAC Address

Validate:

- Canonical format.
- Expected length.
- Allowed characters.

### Hostname

Validate or sanitize before passing into shell commands, configuration templates, or infrastructure tools.

Never assume that data originating from a log file is automatically safe for command execution.

---

## 5. Ansible API Protection

The Ansible API can modify network infrastructure and should not be treated as a normal public web endpoint.

Recommended controls:

- Authentication.
- Network-level restriction.
- TLS where appropriate.
- Request validation.
- Rate limiting if exposed to a larger network.
- Audit logging.
- Least-privilege service account.
- Explicit allow-list of supported operations.

Do not provide a generic remote command execution endpoint.

---

## 6. Idempotency

Network automation should be idempotent.

Examples:

- Blocking an already blocked source should not create duplicate firewall entries.
- Creating an existing DHCP mapping should converge to the intended state rather than create conflicting entries.
- A retry after a timeout should be safe.

Idempotency is especially important because an API request can time out after the infrastructure change has already succeeded.

---

## 7. Retry Strategy

Retries should distinguish between:

- Transport failure.
- API failure before execution.
- API timeout with unknown infrastructure state.
- Confirmed infrastructure failure.
- Successful operation with delayed verification.

Before retrying a state-changing action, determine whether the previous request may already have been applied.

Where possible, use:

- Idempotent playbooks.
- State checks before changes.
- Stable operation identifiers.
- Verification after execution.

---

## 8. Deduplication State

n8n workflow static data is used by parts of the project to suppress duplicates.

Operational considerations:

- Understand when static data is persisted.
- Test behavior after workflow restart.
- Test behavior after n8n restart.
- Test backup/restore behavior.
- Do not rely on in-memory assumptions for critical long-term state.

For stronger durability, move critical deduplication state to persistent storage.

---

## 9. File Permissions

Runtime files may contain:

- Security events.
- Device MAC addresses.
- Network identity information.
- Automation results.
- Operational logs.

Apply least-privilege filesystem permissions.

Only the collector, n8n, and authorized administrators should have the access required for their role.

Avoid placing runtime files in publicly served directories.

---

## 10. Telegram Security

Telegram is used as an operator interaction channel.

Consider:

- Restricting accepted chat/user identities.
- Rejecting callbacks from unexpected chats.
- Avoiding sensitive infrastructure secrets in messages.
- Treating callback data as untrusted input until validated.
- Protecting bot credentials.
- Preventing multiple workflows from consuming the same updates incorrectly.

Administrator approval should be bound to the intended device identity.

---

## 11. Human-in-the-Loop Approval

DHCP approval intentionally retains a human decision point.

Security expectations:

- Detection alone must not authorize a new device.
- The callback must identify the target device unambiguously.
- Pending state should prevent duplicate approval prompts.
- Approval should be verified against network state.
- Rejection should not accidentally create infrastructure changes.

---

## 12. Logging and Privacy

Network logs can contain identifiable technical information.

Operational policy should define:

- Who can access logs.
- How long logs are retained.
- Whether MAC/IP data needs masking in exported reports.
- How metrics are shared outside the lab.
- When rotated logs are deleted.

Do not publish runtime logs containing sensitive environment information unless they have been reviewed and sanitized.

---

## 13. Production Hardening

Before production deployment:

- Move all secrets to protected credential storage.
- Restrict Syslog ingestion to trusted sources.
- Authenticate the Ansible API.
- Use network segmentation.
- Validate all automation inputs.
- Remove lab-only reset mechanisms.
- Make playbooks idempotent.
- Add structured error handling.
- Add safe retry behavior.
- Store critical state durably.
- Implement log retention.
- Monitor workflow failures.
- Monitor collector availability.
- Back up configuration safely.

---

## 14. Security Review Questions

During review, ask:

- Can an untrusted host inject logs that trigger automation?
- Can a forged IP cause a legitimate host to be blocked?
- Can a Telegram callback approve the wrong device?
- What happens if Ansible times out after applying a change?
- Are duplicate requests safe?
- Which state survives restart?
- Which files contain sensitive network information?
- What credentials are required by each component?
- Can a compromised n8n instance directly modify pfSense?
- Is there a recovery path for an incorrect automated action?

These questions help evaluate the system beyond the happy path.

---

## 15. Scope

This project demonstrates security automation concepts. It should not be treated as production-ready solely because the workflows execute successfully in a laboratory environment.

Production readiness also requires:

- Threat modeling.
- Access control.
- Secret management.
- Reliability testing.
- False-positive evaluation.
- Recovery procedures.
- Monitoring.
- Change management.

For deployment, see [deployment.md](deployment.md).  
For detection behavior, see [detection-logic.md](detection-logic.md).
