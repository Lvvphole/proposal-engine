# Weekly Tracking Dashboard

## Purpose

Provide contractors with a simple weekly view of proposal activity and pipeline value. Doubles as the mechanism for reporting closed proposals (which drives our revenue).

## Dashboard Sections

### 1. This Week's Activity

| Metric | Value |
|---|---|
| Quotes received | [count] |
| Proposals generated | [count] |
| Proposals approved & sent | [count] |
| Proposals pending your review | [count] |
| Average turnaround time | [hours] |

### 2. Pipeline Value

| Stage | Count | Total Value |
|---|---|---|
| Proposal sent, awaiting customer response | [n] | $[amount] |
| Customer requested revision | [n] | $[amount] |
| Verbally accepted, not yet confirmed | [n] | $[amount] |

### 3. Closed This Week

**Mark proposals as closed by selecting from the list below.**

| Proposal # | Customer | Amount | Date Sent | Status |
|---|---|---|---|---|
| PE-001 | Johnson Residence | $12,450 | 06/01 | ☐ Closed ☐ Lost ☐ Still open |
| PE-002 | Smith Remodel | $8,200 | 06/03 | ☐ Closed ☐ Lost ☐ Still open |

*Selecting "Closed" triggers the performance fee calculation at the agreed rate.*

### 4. Monthly Summary

| Month | Quotes | Proposals Sent | Closed | Revenue Generated | Service Fee |
|---|---|---|---|---|---|
| June 2024 | 42 | 38 | 14 | $168,000 | $13,440 |
| May 2024 | 35 | 31 | 11 | $132,000 | $10,560 |

### 5. Accuracy Report

| Metric | This Week | Trailing 30 Days |
|---|---|---|
| Extraction accuracy | 94% | 92% |
| Proposals approved without edits | 85% | 82% |
| Proposals requiring corrections | 15% | 18% |

## Implementation Notes

- MVP: Google Sheet shared with the contractor, updated weekly by the system
- V2: Web dashboard with real-time updates from the proposal engine API
- V3: Automated via the MCP server — contractor interacts through Claude Desktop

## Close Reporting UX

The close reporting step is critical — it drives our revenue and provides feedback for accuracy improvement. Design principles:

- Make it the first thing they see (not buried below charts)
- Pre-populate with proposals sent in the last 45 days
- One tap/click to mark as closed
- Auto-calculate the service fee and show it inline
- Send a weekly reminder if proposals are unmarked for > 14 days
