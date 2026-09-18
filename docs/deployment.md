# Deployment Guide

[← Back to README](../README.md)

## Purpose

This document describes how to deploy the project into a target environment.

All network addresses, credentials, local paths, and environment-specific values are represented as placeholders.

---

## 1. Prerequisites

Required components:

- pfSense with remote logging enabled.
- Python 3.
- n8n with permission to read and write local runtime files.
- Ansible automation service/API.
- Telegram Bot credentials.
- Network connectivity between the required components.
- A host capable of receiving pfSense Syslog traffic.

---

## 2. Recommended Deployment Layout

```text
pfSense
   │
   │ Syslog
   ▼
Collector / n8n Host
   │
   ├── Python Collector
   ├── n8n
   └── Runtime Files
            │
            ▼
       Ansible API
            │
            ▼
         pfSense

Telegram ↔ n8n
```

The collector and n8n may run on the same host, as in the current lab design, or may be separated if shared storage and access are designed accordingly.

---

## 3. Clone the Repository

```bash
git clone https://github.com/minhhung8712/CHA3P07-Network-Automation-2026.git
cd CHA3P07-Network-Automation-2026
```

---

## 4. Configure the Python Collector

Review the collector configuration in:

```text
pf_collector.py
```

Environment-specific settings include:

```text
LISTEN_IP
LISTEN_PORT
PFSENSE_IP
ONLY_ACCEPT_FROM_PFSENSE
LOG_DIR
ACTIVE_LOG_NAME
ROTATE_MAX_BYTES
```

Recommended approach:

- Bind only to the required interface when possible.
- Set the expected pfSense source address.
- Enable source filtering in non-lab environments.
- Store logs in a directory accessible to n8n.
- Ensure the runtime directory is not committed to Git.

---

## 5. Prepare Runtime Storage

Create a runtime directory outside the repository.

Suggested logical structure:

```text
<RUNTIME_DIR>/
├── pflogs/
├── metrics/
└── telegram/
```

The workflows require runtime files for:

- Active pfSense logs.
- Security queues/events.
- DHCP device state.
- Approval events.
- Metrics.
- Telegram polling offsets.

Some n8n file-read nodes expect their target file to exist. Create empty files where required before workflow activation.

---

## 6. Configure pfSense Remote Logging

Configure pfSense to forward the required log categories to the collector.

Use:

```text
Destination: <COLLECTOR_HOST>:<SYSLOG_PORT>
Protocol: UDP
```

Ensure the collector host firewall permits the selected Syslog traffic.

Verify log delivery before configuring detection workflows.

---

## 7. Start the Collector

Run:

```bash
python pf_collector.py
```

Confirm:

- The process binds successfully.
- pfSense messages are received.
- The active log file is created.
- New messages are appended.
- File rotation works as expected.

---

## 8. Configure n8n File Paths

Imported workflow JSON files contain environment-specific file locations.

After import, update all file-read and file-write nodes to use the target runtime directory.

Recommended practice:

```text
Do not rely on developer workstation absolute paths.
```

Where possible, centralize path configuration instead of repeating it across nodes.

---

## 9. Import n8n Workflows

Import the workflows into the same n8n instance.

Recommended logical order:

```text
1. WF-DHCP-WATCH
2. WF-ANALYZER
3. WF-BLOCK-SCAN
4. WF-BLOCK-BRUTE
5. WF-DHCP-CALLBACK
6. WF-METRICS-REPORT
```

After import:

- Reconnect credentials.
- Review sub-workflow references.
- Review workflow IDs.
- Review file paths.
- Review API endpoints.
- Review Telegram configuration.
- Review scheduling intervals.
- Confirm workflows are active only after validation.

---

## 10. Configure Ansible API

The n8n workflows expect an automation API that provides actions equivalent to:

```text
POST /block-ip
POST /add-static-mapping
```

The exact host and port belong to deployment configuration.

The API should:

- Validate request payloads.
- Authenticate callers.
- Return clear success/failure status.
- Use idempotent infrastructure operations.
- Log infrastructure changes.
- Apply least-privilege access.

---

## 11. Configure Telegram

Configure a Telegram Bot credential in n8n.

Required uses include:

- Device approval requests.
- Security notifications.
- Performance reports.
- Callback processing.

Do not embed the bot token directly into exported workflow JSON.

If an HTTP Request node must call Telegram directly, reference a protected credential or environment variable.

---

## 12. Configure Detection Environment

Review Analyzer configuration for the target network.

Environment-dependent settings include:

- Internal networks.
- Ignored address prefixes.
- Explicitly ignored addresses.
- Detection thresholds.
- Observation windows.
- Incident quiet periods.

These values should be tuned after observing representative benign traffic.

---

## 13. Configure DHCP Environment

Review DHCP-specific settings:

- Approved/pending/rejected state files.
- Address allocation pool.
- Target DHCP interface/subnet.
- Ansible static-mapping action.
- Verification timing.

The address pool should be valid for the target environment and must not conflict with existing network assignments.

---

## 14. Activation Sequence

Recommended activation process:

```text
1. Verify pfSense → Collector
2. Verify Collector → Runtime Log
3. Verify Analyzer can read the log
4. Verify DHCP sub-workflow reference
5. Verify Ansible API connectivity
6. Verify Telegram credentials
7. Activate response workflows
8. Activate Analyzer
9. Activate callback/reporting workflows
10. Run controlled tests
```

Avoid enabling all workflows before dependencies are validated.

---

## 15. Post-Deployment Verification

### Collector

Confirm a known pfSense log reaches the active log file.

### Analyzer

Confirm a controlled event is parsed and routed to the expected branch.

### Security Response

Confirm a controlled test event reaches the appropriate response workflow and produces the expected Ansible request.

### DHCP

Confirm a new test device generates one approval request and that approval produces the expected mapping and verification.

### Metrics

Confirm completed workflows append a metrics record and the report workflow can summarize it.

---

## 16. Backup and Recovery

Back up:

- n8n workflow exports.
- n8n credentials using the platform-supported method.
- Runtime device-state files.
- Relevant metrics if they are part of the evaluation.
- Ansible playbooks/API code.
- Environment configuration.

Do not back up exposed secrets into source control.

When restoring, validate workflow IDs, sub-workflow references, and filesystem paths before activation.

---

## 17. Upgrade Procedure

Before updating workflow JSON:

1. Export the currently working workflow.
2. Record environment-specific changes.
3. Import or update the new workflow.
4. Reconnect credentials and references.
5. Validate file paths.
6. Test with controlled input.
7. Activate only after successful verification.

This reduces the risk of overwriting environment-specific configuration.

---

## 18. Deployment Checklist

- [ ] pfSense remote logging configured
- [ ] Collector receives logs
- [ ] Runtime directories exist
- [ ] Required runtime files exist
- [ ] n8n workflows imported
- [ ] File paths updated
- [ ] Workflow references validated
- [ ] Ansible API reachable
- [ ] Telegram credentials configured
- [ ] Detection configuration reviewed
- [ ] DHCP configuration reviewed
- [ ] Controlled security test passed
- [ ] Controlled DHCP test passed
- [ ] Metrics/reporting test passed

For architecture, see [architecture.md](architecture.md).  
For security guidance, see [security-notes.md](security-notes.md).
