# Future: Lead Generation Engine

## Status: Planned (not yet implemented)

## Concept

Once the proposal engine is validated with 3-5 pilot contractors, the lead generation engine will automate contractor acquisition using the same diagnostic playbook that drives manual outreach today.

## Architecture (Planned)

```
Contractor Database (public records, permit data)
        │
        ▼
  Qualification Filter (volume, job size, geography)
        │
        ▼
  Diagnostic Scorer (estimate revenue loss from slow follow-up)
        │
        ▼
  Outreach Sequence (personalized email/LinkedIn based on score)
        │
        ▼
  Booking Flow → Pilot Onboarding
```

## Data Sources (To Evaluate)

- County building permit records (public data, shows active contractors and job volumes)
- Google Business profiles (reviews indicate volume and specialization)
- BBB and licensing databases (verify legitimacy)
- Construction industry associations (membership lists)

## Key Constraint

This is explicitly NOT the first priority. The proposal engine must prove product-market fit with manual sales before automating lead generation. Building a lead engine for a product that doesn't convert is a waste of time.

## Prerequisites

- 3+ contractors completing the pilot with positive ROI
- Close rate data proving the performance pricing model works
- At least one case study with concrete revenue numbers
- Proposal engine accuracy consistently above 90%

## Revenue Model Integration

Lead generation cost becomes the primary customer acquisition cost. At $17K+ annual revenue per contractor (from ADR-004 example), the allowable CAC is significant — but only if retention is strong. Focus on retention (proposal accuracy, turnaround speed) before scaling acquisition.
