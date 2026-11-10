# Provenance

Adapted November 10, 2026 from Clarity Works private outbound tooling at source revision `2160b3b9f2e8bbbe88707c06b0f065c4ee48aa35`.

`outbound_demo/render.py` extracts `_variant`, `_first_name` and `_render` from the production drafting module. `outbound_demo/rules.py` extracts the dash-normalization and unsupported-hiring-claim checks. Imports/types were reduced to a standalone data model. The remaining orchestration is a compact adaptation of the documented enrichment, routing, review, upload and sync boundaries.

The local ledger, hash-bound approval fixtures, synthetic research/model outputs, CLI, tests and CI are additions for this showcase. They are not claims that the private production system contains identical implementations. Real campaign copy, prospect lists, research accounts, model adapters, mailboxes and sending integrations are excluded.

Prepared by Vatsal Jain with AI-assisted development. This is a bounded demonstration of a workflow he operates, not a complete production export, a load test or a record of real outreach. No open-source license has been assigned.
