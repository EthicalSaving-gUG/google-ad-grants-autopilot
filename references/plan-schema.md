# Mutation plan schema

Use a reviewable JSON plan before every write. The plan is the boundary between live diagnostics and mutation.

```json
{
  "schema": "ethical-saving/google-ad-grants-plan/v1",
  "account": {
    "customer_id": "1234567890",
    "account_kind": "AD_GRANTS",
    "verified_ad_grants": true,
    "conversion_health": "VERIFIED",
    "currency_code": "EUR",
    "allowed_domains": ["example.org"],
    "grant_daily_budget_limit_micros": 300000000
  },
  "operations": []
}
```

The budget above is an **example only**. Resolve the live Ad Grants allowance in the account currency before a budget-changing plan.

## Required account assertions

- `account_kind` must be `AD_GRANTS`.
- `verified_ad_grants` must be `true` before writes.
- `conversion_health` should be `VERIFIED`, `UNVERIFIED`, or `BROKEN`. Conversion-based Smart Bidding creation is blocked unless it is `VERIFIED`.
- `allowed_domains` is optional but strongly recommended. When present, RSA and sitelink final URLs must be HTTPS and inside those domains.
- `grant_daily_budget_limit_micros` is required when creating campaigns and must come from the live allowance, not a hardcoded currency conversion.

## Operation examples

### Create Search campaign

```json
{
  "type": "campaign_create",
  "name": "DE | Medical Research Donations",
  "daily_budget_micros": 50000000,
  "status": "PAUSED",
  "bidding": {"strategy": "MAXIMIZE_CONVERSIONS"},
  "reason": "Create a dedicated donation-intent Search campaign after conversion health verification."
}
```

### Create ad group

```json
{
  "type": "ad_group_create",
  "campaign_id": "123456789",
  "name": "Medical research donations",
  "status": "ENABLED",
  "reason": "Split donation intent from general research-support intent."
}
```

### Keyword

```json
{
  "type": "keyword_create",
  "ad_group_id": "1234567890",
  "text": "medical research donation",
  "match_type": "PHRASE",
  "reason": "Add a mission-relevant multi-word donation query."
}
```

### Negative keyword

```json
{
  "type": "negative_keyword_create",
  "ad_group_id": "1234567890",
  "text": "jobs",
  "match_type": "EXACT",
  "reason": "Exclude employment intent."
}
```

### Responsive Search Ad

```json
{
  "type": "rsa_create",
  "ad_group_id": "1234567890",
  "final_url": "https://example.org/donate/",
  "headlines": ["Support Medical Research", "Nonprofit Research Support", "Evidence Before Claims"],
  "descriptions": ["Support transparent, evidence-oriented nonprofit medical research.", "See the work, evidence boundaries and ways to support the mission."],
  "reason": "Replace a generic-homepage ad with a query-matched landing page and stronger assets."
}
```

### Image asset

```json
{
  "type": "image_asset_create_attach",
  "scope": "AD_GROUP",
  "scope_id": "1234567890",
  "path": "/secure/work/assets/research-square.jpg",
  "field_type": "SQUARE_MARKETING_IMAGE",
  "name": "medical-research-square-v1",
  "reason": "Add an original, policy-safe visual relevant to this research-support ad group."
}
```

## Validation expectations

- Every mutation requires a human-readable `reason` for auditability.
- Positive single-word keywords are blocked unless an official exception is explicitly documented.
- Final URLs must use HTTPS; optional domain allowlisting prevents cross-domain mistakes.
- RSAs require 3–15 headlines of at most 30 characters and 2–4 descriptions of at most 90 characters.
- Image operations must reference PNG/JPG files validated separately.
- Permanent deletion is intentionally absent from the normal autonomous mutation vocabulary.

### Set conversion action Primary/Secondary

```json
{
  "type": "conversion_action_primary_set",
  "conversion_action_id": "123456789",
  "primary_for_goal": false,
  "reason": "Demote an unrelated legacy conversion action so it no longer steers standard goal bidding."
}
```

Before using this operation, inspect campaign custom conversion goals: a custom goal can still make a Secondary conversion action biddable.
