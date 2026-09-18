# Performance Metrics

[← Back to README](../README.md)

## Purpose

This document describes how the system records and reports automation performance.

The goal is to measure automation behavior without mixing unrelated delays into the same metric.

---

## 1. Measurement Scope

Metrics are collected for the main automation scenarios:

```text
Port-scan response
Brute-force response
DHCP device approval
```

All scenarios write structured records to a common metrics store.

Each record identifies the scenario, target identity, status, and relevant timestamps.

---

## 2. Why Event Correlation Is Required

The response workflows do not independently decide that an attack exists.

That decision is made earlier by `WF-ANALYZER`.

For security workflows, the response workflow therefore correlates the source being processed with the structured Analyzer event.

The `Find Analyzer Event` step exists for this purpose.

It retrieves the event metadata required to measure the automation from the correct detection point.

---

## 3. Security Response Timing

For port-scan and brute-force automation, the principal measurement starts when the Analyzer has classified a new incident and ends when the automated response workflow finishes.

In plain language:

```text
Analyzer confirms incident
        ↓
Response workflow processes event
        ↓
Ansible action is executed
        ↓
Workflow completes
```

The recorded processing duration represents the automation-response period rather than the complete time since the first network packet was observed.

The Analyzer also keeps source-event timing information, allowing deeper end-to-end analysis when required.

---

## 4. DHCP Timing

DHCP approval contains a human decision, so two different periods exist:

```text
New device detected
      ↓
Waiting for administrator
      ↓
APPROVE received
      ↓
Automated mapping and verification
      ↓
Processing complete
```

For automation-performance reporting, the workflow prioritizes the period **after administrator approval**.

This prevents human response time from being interpreted as system automation latency.

The full workflow timestamps remain available for deeper analysis when needed.

---

## 5. Metric Record Structure

A security-response record contains fields conceptually equivalent to:

```json
{
  "scenario": "<scenario>",
  "event_id": "<correlated event>",
  "ip": "<processed source>",
  "status": "<execution result>",
  "analyzer_detected_at": "<timestamp>",
  "processing_finished_at": "<timestamp>",
  "total_processing_seconds": "<duration>"
}
```

A DHCP approval record additionally contains device information and the approval timestamp.

Exact field names are defined by the workflow JSON and should be treated as the source of truth.

---

## 6. Success and Failure

The reporting workflow separates successful records from non-successful records.

A successful automation record is expected to contain:

- A recognized scenario.
- A completion status.
- A valid processing duration.
- Sufficient identity information for the scenario.

Records with invalid timing data are excluded from duration statistics rather than silently distorting the report.

---

## 7. Report Statistics

The report workflow calculates:

- Total records
- Successful executions
- Failed executions
- Success rate
- Average duration
- Median duration
- Minimum duration
- Maximum duration
- P95 duration
- Latest processed event

These statistics provide both a general summary and a view of slower outlier behavior.

---

## 8. Scenario Filtering

The reporting workflow supports a combined view and scenario-specific views.

Conceptually, requests can return:

```text
All scenarios
Port-scan response only
Brute-force response only
DHCP approval only
```

The Telegram command parser maps the operator request to the corresponding scenario filter.

---

## 9. Duration Validation

The report builder validates stored durations before using them.

If the preferred duration field is unavailable or invalid, the workflow can attempt to derive a duration from compatible start and finish timestamps.

Records that still cannot produce a valid duration are reported as invalid and excluded from time-based calculations.

This protects aggregate metrics from malformed records.

---

## 10. Latest Event

In addition to aggregate statistics, the report includes the most recently completed automation event.

Depending on the scenario, identity information may include:

- Source IP for security response.
- MAC address and assigned network information for DHCP approval.

This provides a quick operational check without requiring the operator to inspect the raw metrics file.

---

## 11. Metrics Storage

The current implementation uses JSON Lines (`.jsonl`) as a lightweight append-oriented metrics store.

Advantages:

- Easy to append.
- Human-readable.
- Easy to parse with n8n or scripts.
- Suitable for lab-scale evaluation.

Limitations:

- No transactional guarantees.
- Limited concurrent-write protection.
- No built-in indexing.
- Long-term analytics become less efficient as the file grows.

A database or observability platform would be more suitable for larger or long-running deployments.

---

## 12. Interpretation Guidance

When evaluating results:

- Compare like-for-like scenarios.
- Do not mix human approval delay with automated DHCP execution time.
- Exclude malformed or incomplete records.
- Use median together with average to reduce sensitivity to outliers.
- Use P95 to understand slower executions.
- Treat lab measurements as evidence for that environment, not as universal performance guarantees.
- Record the environment and workflow version when publishing benchmark results.

---

## 13. Recommended Future Metrics

Possible future additions include:

- Detection latency as a separate metric.
- Ansible API request duration.
- pfSense verification duration.
- Retry count.
- Failure category.
- Queue age.
- Workflow scheduling delay.
- Per-stage breakdown.
- Long-term trend metrics.

For detection correlation, see [detection-logic.md](detection-logic.md).  
For DHCP approval timing, see [dhcp-automation.md](dhcp-automation.md).
