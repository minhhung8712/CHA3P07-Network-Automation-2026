# Detection Logic

[← Back to README](../README.md)

## Purpose

This document describes how `WF-ANALYZER` converts pfSense log data into security detections and how duplicate incidents are suppressed.

The exact numeric thresholds are treated as configuration and are intentionally not duplicated here. They are defined inside the Analyzer workflow and should be tuned for the target environment.

---

## 1. Analyzer Input

`WF-ANALYZER` reads the active log produced by the Python collector.

Each stored line contains:

```text
<collector receive timestamp>    <raw pfSense log>
```

The Analyzer uses the collector timestamp as a stable event-time reference when evaluating recent activity.

---

## 2. Log Separation

Before performing security analysis, the Analyzer separates DHCP-related messages from security-relevant messages.

DHCP identification includes standard DHCP event types such as:

```text
DHCPDISCOVER
DHCPREQUEST
DHCPOFFER
DHCPACK
DHCPNAK
DHCPDECLINE
DHCPRELEASE
DHCPINFORM
```

DHCP messages are routed to the DHCP workflow rather than treated as security detections.

---

## 3. Traffic Filtering

The Analyzer excludes traffic that should not be treated as an external attacker signal.

The workflow maintains configurable lists for:

- Internal network prefixes.
- Ignored network prefixes.
- Explicitly ignored addresses.

These values belong to environment configuration and should be reviewed whenever the system is deployed to a different network.

---

## 4. Security Signal Extraction

The Analyzer currently derives security signals from two main sources.

### SSH Authentication Failures

SSH logs containing failed authentication information are parsed into a normalized signal similar to:

```text
kind: auth_fail
source: <source IP>
service: SSH
```

These signals are used for authentication-based brute-force detection.

### Firewall / TCP Events

pfSense `filterlog` entries are parsed for:

- Source and destination addresses.
- Destination port.
- TCP flags.
- Firewall pass/block context.

Relevant records are normalized into connection-oriented signals such as:

```text
kind: syn
```

or:

```text
kind: fw_block
```

The normalized representation allows the same detection logic to operate even when the original log format differs.

---

## 5. Attacker Selection

The Analyzer determines which address represents the external source of interest.

The selection logic prefers an address outside the configured internal networks.

Before accepting the source, the workflow applies ignore rules to reduce noise from trusted, local, multicast, loopback, or otherwise irrelevant traffic.

---

## 6. Detection Models

The Analyzer currently supports three detection patterns.

### 6.1 Authentication-Based Brute Force

Repeated SSH authentication failures from the same source are grouped over a configurable time window.

A brute-force event is created when the configured authentication-failure threshold is crossed.

Configuration is maintained through fields equivalent to:

```text
BRUTE_FORCE.count
BRUTE_FORCE.window
```

### 6.2 Connection-Flood Brute Force

A service may be attacked even when the firewall blocks traffic before the target application generates authentication logs.

To cover this case, the Analyzer also evaluates repeated connection or firewall events targeting the same destination service.

The rule considers:

- Number of recent connection attempts.
- Concentration on one destination port.
- Whether the behavior still remains below the multi-port scan pattern.

Configuration is maintained through fields equivalent to:

```text
CONN_FLOOD.count
CONN_FLOOD.window
```

### 6.3 Port Scan

Port-scan detection looks for one source contacting multiple distinct destination ports inside a configured observation window.

The rule is based on:

```text
PORT_SCAN.distinctPorts
PORT_SCAN.window
```

The exact values are configuration choices rather than architectural constants.

---

## 7. Detection Priority

For a given source, the Analyzer evaluates attack patterns in a defined order:

```text
Authentication Brute Force
          ↓
Connection-Flood Brute Force
          ↓
Port Scan
```

This avoids classifying concentrated activity against one service as a port scan when it more closely matches brute-force behavior.

A source produces one selected finding for the evaluated event set.

---

## 8. Event Metadata

When a new incident is detected, the Analyzer creates structured metadata used by downstream workflows.

Typical fields include:

```text
event_id
scenario
src_ip
event_type
metric
source_event_at
analyzer_detected_at
```

The event identifier allows later workflows to correlate the automation result with the original detection.

---

## 9. Incident Deduplication

Detection and response are separated from duplicate suppression.

The Analyzer stores per-event-type state using n8n workflow static data.

For each source and event type, it tracks information equivalent to:

```text
event_id
first_detected_at
last_seen_at
last_signal_at
```

A configurable quiet period determines whether a repeated detection belongs to the same incident or represents a new incident.

The deduplication logic uses two references:

1. **Signal time** — derived from the events in the collected log.
2. **Analyzer observation time** — the wall-clock time when the Analyzer processes the data.

Using both references helps tolerate imperfect or shifted log timestamps.

If the event is considered part of an existing incident, the Analyzer updates the stored state but does not create a new response event.

---

## 10. Response Queue Output

New security incidents are written to two logical forms of output.

### Ban Queue

Contains the source that should enter the response workflow.

Used by:

```text
WF-BLOCK-SCAN
WF-BLOCK-BRUTE
```

### Event Queue

Contains structured event metadata for correlation and metrics.

The response workflow uses this data to identify which Analyzer event belongs to the source being processed.

---

## 11. Response-Workflow Deduplication

The blocking workflows apply another duplicate check before calling Ansible.

They maintain a processed-source list in workflow static data.

Conceptually:

```text
Read queue
   ↓
Already processed?
   ├─ Yes → Stop
   └─ No  → Continue to Ansible
```

This layer protects against repeated polling of an unchanged queue file.

---

## 12. Detection Limitations

The current model is threshold-based and therefore has known boundaries:

- Slow scans may remain below the configured observation window.
- Distributed brute force across many source addresses is not aggregated by username or target identity.
- Thresholds suitable for a lab may not suit production traffic.
- Static allow/ignore lists require environment-specific maintenance.
- File-based polling introduces a delay determined by workflow scheduling.
- Detection quality depends on the completeness and format of pfSense logs.

These are design limitations rather than workflow errors.

---

## 13. Tuning Guidance

When tuning detection logic:

- Start with representative benign traffic.
- Measure false positives before lowering thresholds.
- Test both burst and slow attack patterns.
- Keep scan detection distinct from single-service brute-force activity.
- Review ignore rules after network topology changes.
- Document every threshold change together with the reason for the change.

Threshold values should be maintained in the workflow configuration, not duplicated across multiple documentation files.

---

## 14. Verification Checklist

A detection test should confirm all of the following:

- The expected log reaches the collector.
- The Analyzer parses the event.
- The correct source is selected.
- The correct detection type is assigned.
- A new incident creates an event identifier.
- Repeated observations of the same incident are suppressed.
- The intended response queue is updated.
- The response workflow receives the event.
- Ansible is called only when the event passes deduplication.

For system architecture, see [architecture.md](architecture.md).  
For response timing, see [metrics.md](metrics.md).
