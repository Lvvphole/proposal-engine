# Skill: Onboard Contractor

## Purpose

Set up a new contractor profile with all configuration needed to generate proposals on their behalf.

## Trigger

User says they want to add a new contractor, or this is the first time a contractor's name is mentioned.

## Workflow

1. **Gather contractor information.** Collect:
   - Full name and company name
   - Contact info (phone, email)
   - License number (for proposal headers)
   - Logo or branding preferences (optional)

2. **Configure markup rules.** Ask the contractor (or user) for:
   - Default markup percentage (typical: 15-25%)
   - Category overrides (e.g., materials at 15%, labor at 25%)
   - Any items to mark up differently (specialty materials, custom orders)

3. **Set payment terms.** Common options:
   - Due on completion
   - Net 30
   - 50% deposit, balance on completion
   - Progress payments (for large jobs)

4. **Register profile.** Call `rag/contractor_context.py::register_contractor()` with the collected information.

5. **Register via MCP.** If using the MCP server, also call the `register_contractor` MCP tool so the profile is accessible from Claude Desktop.

6. **Verify setup.** Run a test extraction on a sample document and generate a preview proposal to confirm markup and branding look correct.

7. **Document.** Log the new contractor setup in the audit trail.

## Output

- Registered contractor profile with unique ID
- Confirmation of markup rules and payment terms
- (Optional) Sample proposal preview

## Notes

- First extractions for a new contractor trigger mandatory human review per `policies/human_review_policy.json`
- The contractor ID is used to link proposals to the correct markup and branding configuration
