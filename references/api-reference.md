# Google Ads API write path

This project uses Google's regular Ads API for deterministic mutations when no native write connector is available.

## Resolve versions dynamically

Before live execution, resolve the newest stable Google Ads API and current supported client-library/runtime requirements from Google's official release notes and client-library docs. Do not hardcode a stale major API version in generated integration code.

Official release notes: https://developers.google.com/google-ads/api/docs/release-notes

## Credentials

Load credentials only from environment variables or a secret manager:

- `GOOGLE_ADS_DEVELOPER_TOKEN`
- `GOOGLE_ADS_CLIENT_ID`
- `GOOGLE_ADS_CLIENT_SECRET`
- `GOOGLE_ADS_REFRESH_TOKEN`
- `GOOGLE_ADS_LOGIN_CUSTOMER_ID` when an MCC hierarchy requires it
- `GOOGLE_ADS_CUSTOMER_ID` target account

Live mutation additionally requires:

- `GOOGLE_ADS_AUTONOMY=1`
- `GOOGLE_ADS_ALLOWED_CUSTOMER_IDS` containing the exact target customer ID

Never place the values in Git, issue bodies, screenshots, generated assets, or mutation journals.

## Runner

Dry-run validation:

```bash
python scripts/google_ads_apply.py --plan references/plan.example.json
```

Live apply:

```bash
python scripts/google_ads_apply.py --plan plan.json --apply
```

Default journal:

```text
runtime/mutation-journal.jsonl
```

The journal contains operation type, reason, result/resource name, timestamp and failure text. It must never contain credentials.

## Current deterministic mutation vocabulary

| Plan operation | Google Ads resource/service |
|---|---|
| `campaign_create` | `CampaignBudgetService`, `CampaignService` |
| `campaign_status` | `CampaignService` |
| `campaign_budget_set` | `CampaignBudgetService` |
| `ad_group_create` | `AdGroupService` |
| `ad_group_status` | `AdGroupService` |
| `keyword_create` | `AdGroupCriterionService` |
| `negative_keyword_create` | `AdGroupCriterionService` |
| `keyword_status` | `AdGroupCriterionService` |
| `rsa_create` | `AdGroupAdService` |
| `sitelink_create_attach` | `AssetService`, `CampaignAssetService` |
| `callout_create_attach` | `AssetService`, `CampaignAssetService` |
| `image_asset_create_attach` | `AssetService`, `CampaignAssetService` / `AdGroupAssetService` |
| `location_target_add` | `CampaignCriterionService` |
| `language_target_add` | `CampaignCriterionService` |
| `conversion_action_create` | `ConversionActionService` |
| `conversion_action_primary_set` | `ConversionActionService` update of `primary_for_goal` |

## Conversion-goal warning

`ConversionAction.primary_for_goal=false` normally makes an action Secondary/non-biddable for standard customer/campaign goals. A `CustomConversionGoal` can still make a Secondary action biddable. Audit custom goals before assuming a primary/secondary toggle fully removes a signal from optimization.

See: https://developers.google.com/google-ads/api/docs/conversions/goals/overview

## Performance Max

Current Google Ad Grants setup guidance supports Performance Max. The bundled deterministic runner does **not yet** construct full PMax campaigns/asset groups. Prefer a native writer that explicitly exposes PMax resources, or add/test a dedicated PMax operation set before claiming deterministic support.

## Failure behavior

- local validation failure: no API client is loaded and no write happens;
- missing autonomy flag/allowlist: fail closed;
- missing credential: fail closed without printing secret values;
- API mutation failure: write a redacted failed journal record and stop;
- successful API response: record the returned resource name, then re-query through the read layer for post-write verification.
