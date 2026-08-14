# Google Ad Grants policy guard

This is a runtime checklist, not a substitute for live policy verification. Re-check official Google sources before significant account changes because Ad Grants requirements and product capabilities change.

## Official sources to verify

- Ad Grants policy compliance guide: https://support.google.com/nonprofits/answer/9314402
- Account management policy: https://support.google.com/nonprofits/answer/117827
- Mission-based campaigns: https://support.google.com/nonprofits/answer/4410314
- Single-keyword exceptions: https://support.google.com/nonprofits/answer/7587473
- Budgets and bidding: https://support.google.com/nonprofits/answer/1332166
- Website policy: https://support.google.com/nonprofits/answer/1657899
- Ad Grants campaign setup (Search / Performance Max): https://support.google.com/nonprofits/answer/9841727
- Search image assets: https://support.google.com/google-ads/answer/9566341
- Image-asset format requirements: https://support.google.com/adspolicy/answer/10347108
- Conversion goals in Google Ads API: https://developers.google.com/google-ads/api/docs/conversions/goals/overview
- Google Ads API release notes: https://developers.google.com/google-ads/api/docs/release-notes

## Current guardrails captured 2026-08-14

1. Ad Grants provides up to USD 10,000/month of in-kind advertising. Google describes an approximate USD 329/day account budget. Treat this as a limit, not guaranteed spend. For non-USD accounts, resolve the live converted allowance rather than hardcoding currency conversion.
2. Current Ad Grants setup guidance supports **Search and Performance Max** campaign creation. Do not apply Search-only structure rules to Performance Max.
3. Search campaigns and their keywords/ads must be mission based and relevant to the nonprofit's programs/services.
4. Single-word keywords are generally disallowed except official exceptions such as owned brands, recognized medical conditions, acronyms, and Google's published exception terms.
5. Quality Score 1 or 2 keywords must not remain active where the rule applies and the score is exposed.
6. Maintain at least two ad groups per Search campaign under the current compliance guide.
7. Maintain at least two unique sitelink assets.
8. Maintain at least 5% monthly account-level CTR where the current policy applies; two consecutive months below the requirement can trigger temporary deactivation.
9. Use specific, mission-relevant geographic targeting.
10. Accurate, meaningful conversion tracking is foundational for conversion-based Smart Bidding. Do not use page views or unrelated legacy actions as fake success signals.
11. Google's current budget/bidding guidance allows Maximize Clicks as an initial data-gathering strategy when conversion data is not ready, with a priority on validating conversions and moving to conversion-based bidding as appropriate.
12. The destination website must be owned/controlled by the nonprofit and provide a high-quality, functional user experience that accurately reflects the mission.
13. Ad Grants accounts also remain subject to standard Google Ads policies.
14. Do **not** treat “two ads per ad group” as a hard Ad Grants policy unless current official policy explicitly says so. Multiple RSAs may still be a performance experiment, not a compliance assumption.

## Search image assets

Current Google guidance includes:

- square 1:1 required; recommended 1200x1200, minimum 300x300
- landscape 1.91:1 optional/recommended; recommended 1200x628, minimum 600x314
- PNG or JPG
- maximum 5120 KB
- important content centered within the safe area
- no digitally added text, logos, or graphic overlays
- account eligibility requirements can apply before image assets are available
- Google recommends multiple unique images to maximize serving eligibility

Always verify the current official source before generating/uploading assets.

## Conversion-goal guard

The Google Ads API uses `ConversionAction.primary_for_goal` to distinguish actions used for bidding from secondary actions. Before enabling conversion-based Smart Bidding:

- enumerate all primary actions,
- mark each as mission-relevant or not,
- demote unrelated/legacy actions to secondary where technically and semantically appropriate,
- check for campaign custom goals, because custom goals can still make a secondary action biddable,
- verify the selected goal fires on the intended meaningful event.

Do not infer conversion correctness from conversion counts alone.
