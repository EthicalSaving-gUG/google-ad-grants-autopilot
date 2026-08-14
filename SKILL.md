---
name: google-ad-grants-autopilot
description: Autonomously audit, manage, and optimize Google Ad Grants for nonprofits using live Google Ads data, current Google policy, the official Google Ads API, conversion-quality guards, landing-page coordination, and generated image assets. Use when ChatGPT needs to diagnose low spend or poor Ad Rank; clean conversion goals; create, modify, pause, restructure, or optimize Search/Performance Max strategy; manage Search campaigns, ad groups, keywords, negatives, RSAs, budgets, geotargeting, sitelinks/callouts, image assets, or conversion actions; or responsibly maximize use of the monthly Ad Grant without per-change confirmation.
---

# Google Ad Grants Autopilot

Operate an approved Ad Grants account as an autonomous performance loop. Make routine optimization changes without per-change confirmation when the user has granted autonomous authority.

## Core workflow

1. **Identify the exact target.** Discover the account from the connected read layer. Do not rely on a customer ID remembered from prior runs.
2. **Verify Ad Grants context.** Confirm the intended account is the nonprofit grant account, not a normal billed account. Fail closed if identity or grant status is ambiguous.
3. **Resolve current platform facts.** Re-check official Google Ad Grants policy, campaign-type support, image requirements, and the newest stable Google Ads API/client-library version. Never hardcode API-version assumptions into the workflow.
4. **Read live state before writes.** Pull campaigns, campaign types, ad groups, ads, keywords, search terms, conversions, change history, budgets, bidding, impression share, assets, policy status, and landing-page URLs.
5. **Audit.** Normalize the account to `references/audit.example.json` and run `scripts/audit_snapshot.py`. Treat conversion pollution, non-HTTPS URLs, Search structure failures, and unexplained conversion counts as blockers where appropriate.
6. **Diagnose.** Reuse `references/google-upstream.md` patterns for conversion loss, low traffic, change events, and impression-share loss. Distinguish rank, budget, search volume, geo, policy, landing-page, creative, and bidding causes.
7. **Plan.** Produce a machine-readable mutation plan using `references/plan-schema.md`. Every operation needs a concrete `reason`. Run `scripts/ad_grants_plan.py` before applying it.
8. **Apply autonomously.** Prefer a connected write-capable Google Ads tool. Otherwise use `scripts/google_ads_apply.py` with valid Google Ads API credentials and runtime allowlisting. Normal optimization does not require per-keyword confirmation.
9. **Verify.** Re-query every materially changed resource, inspect approval/policy state, verify destinations, and compare the mutation journal with live state.
10. **Iterate.** Compare 7-day, 30-day, and prior-period performance. Optimize meaningful nonprofit outcomes, not raw grant utilization.

## Non-negotiable safeguards

- Never invent or bypass Google Ads permissions, OAuth, Developer Token approval, policy status, or Ad Grants eligibility.
- Never store Developer Tokens, OAuth client secrets, refresh/access tokens, passwords, or private credential files in Git, skill files, logs, screenshots, or assets.
- Never use a remembered customer ID as the sole account selector. Discover live, then allowlist the exact target for writes.
- Never delete campaigns, ad groups, ads, keywords, conversion actions, or assets as routine optimization. Pause or remove associations. Permanent deletion requires an explicit user request.
- Never manufacture trivial conversions to satisfy Smart Bidding or policy. Prefer completed donations, qualified contacts/applications, or other real mission actions.
- Never trust conversion counts until primary/secondary goal semantics are audited. Legacy or unrelated primary actions are a critical blocker for conversion-based bidding.
- Never claim medical efficacy, safety, regulatory approval, or patient outcomes beyond the landing page's substantiated evidence.
- Never attach generated image assets without current eligibility/policy checks and visual review.
- Never assume an unused grant budget should be spent. Relevance and meaningful conversions outrank raw spend.
- Never apply Search-only structure rules to Performance Max.

## Ad Grants policy guard

Read `references/ad-grants-policy.md` and re-check its official source links before material changes.

At minimum:

- keep targeting and content mission-relevant;
- enforce current single-word keyword restrictions and exceptions;
- maintain the current required Search structure, including at least two ad groups per Search campaign when the official guide requires it;
- maintain at least two unique sitelink assets;
- protect the current account-level CTR requirement where applicable;
- pause Quality Score 1–2 keywords when the live account exposes that condition and current policy requires it;
- use relevant geographic targeting;
- keep conversion tracking meaningful and technically correct;
- recognize current Ad Grants support for Search and Performance Max;
- do not treat “two ads per ad group” as a hard rule unless current official policy explicitly requires it.

## Conversion hygiene gate

Before creating or expanding conversion-based Smart Bidding:

1. enumerate all enabled conversion actions and identify Primary vs Secondary;
2. map each Primary action to a real nonprofit objective;
3. flag unrelated legacy ecommerce, page-view, call, YouTube, or other actions that should not steer bidding;
4. inspect custom conversion goals because they can keep a Secondary action biddable;
5. verify the intended conversion actually fires on the meaningful action;
6. set `account.conversion_health` to `VERIFIED` only after the above checks.

Use `conversion_action_primary_set` to demote/promote actions only when the semantic intent is known. Do not mass-toggle conversion actions from names alone.

## Ethical Saving reference implementation

For Ethical Saving gUG work, read `references/ethicalsaving-profile.md` before campaign or asset creation. The public profile intentionally contains no Google Ads customer ID or credentials.

Use live systems to confirm every mutable value. Preserve Ethical Saving's evidence boundaries for research-stage medical concepts.

## Search optimization

### Structure

Separate materially different intent, geography, language, and conversion goals. Keep keyword, RSA, and landing page aligned.

Typical Ethical Saving intent families include:

- donate to medical research / nonprofit medical research;
- emergency medicine research support;
- German Rettungsdienst reimbursement / RTW / NEF fees;
- evidence-oriented medical innovation and research collaboration.

Do not mix donation intent with specialist reimbursement research in one ad group.

### Keywords and search terms

- add mission-relevant multi-word terms;
- use negatives quickly for irrelevant intent;
- do not add broad traffic only to consume grant budget;
- pause/narrow terms with policy risk, Quality Score 1–2, or sustained CTR pressure;
- use Broad Match only when relevance, conversion signals, and negatives make it defensible;
- preserve branded and recognized-medical-condition exceptions only when they directly support the mission and landing page.

### Responsive Search Ads

Create strong, materially useful assets that match the query and landing page. RSA plan validation enforces current 30-character headline and 90-character description limits.

Do not enforce two RSAs as a compliance rule unless current Google policy requires it. Multiple RSAs may still be tested as a performance strategy.

Avoid unnecessary pinning unless legal/compliance text must always show.

## Performance Max

Current Google Ad Grants setup guidance supports Performance Max as well as Search. Diagnose PMax separately from Search.

- Do not require ad groups or Search keywords for PMax.
- Inspect conversion goal quality before letting PMax optimize autonomously.
- Use a native write connector for PMax when it exposes the necessary asset-group operations.
- The bundled deterministic API runner currently focuses on well-tested Search/resource mutations. Do not pretend it has complete PMax construction support until that code path exists and is tested.

## Landing pages

Prefer intent-matched landing pages over a generic homepage.

Before sending traffic verify:

- HTTPS and successful load;
- mobile usability and one clear primary CTA;
- nonprofit identity/purpose and privacy/legal links;
- no misleading claims;
- consent behavior appropriate to jurisdiction;
- conversion fires only on a meaningful action.

Treat `donation_start` or an outbound donation-platform click as a useful secondary signal when completed-donation imports are unavailable. Prefer a confirmed downstream event for primary bidding when technically reliable.

## Image asset workflow

When image generation is available and the account is eligible:

1. generate original, rights-clear, campaign-specific imagery;
2. create 1:1 and 1.91:1 variants;
3. avoid text, logos, badges, buttons, watermarks, screenshots, collages, and misleading medical imagery;
4. run `scripts/validate_assets.py`;
5. review visually for policy/relevance;
6. upload/attach at the narrowest useful level;
7. verify approval and serving eligibility.

Do not use OCR as a routine overlay detector. The validator checks deterministic file properties; visual review handles semantic policy issues.

## Write path

### Native writer

If a connected Google Ads tool exposes create/update/pause/mutate actions, use it after policy and plan validation.

### Google Ads API runner

If no native writer exists:

```bash
python scripts/google_ads_apply.py --plan /path/to/plan.json --apply
```

Live writes additionally require:

- `GOOGLE_ADS_AUTONOMY=1`
- `GOOGLE_ADS_ALLOWED_CUSTOMER_IDS` containing the exact target
- Google Ads OAuth/Developer Token credentials from environment variables

See `references/api-reference.md`. The runner journals live attempts/results to `runtime/mutation-journal.jsonl` by default and never prints credentials.

If credentials or network access are missing, do not claim a mutation occurred. Return the validated plan plus the exact blocker.

## Verification and iteration

After an autonomous run, report compactly:

- diagnosis;
- writes actually applied;
- assets created/attached;
- conversion/bidding changes;
- policy risks blocked;
- before/after metrics when measurable;
- unresolved dependencies;
- next observation window.

Then use what failed or surprised you to improve this Skill, its validators, or its source register. Do not require the user to approve each routine change.

## Upstream Google toolkit

Use `references/google-upstream.md` for the official Google `google/skills` Ads resources. Treat Google's MCP server as a read/diagnostic source unless its current tool surface explicitly exposes writes. Use the regular Google Ads API for deterministic mutations when necessary.
