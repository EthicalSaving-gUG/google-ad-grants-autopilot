#!/usr/bin/env python3
"""Offline audit for a normalized Google Ad Grants account snapshot.

The script is intentionally connector-agnostic: export/query live account data with
whatever read layer is available, normalize it to references/audit.example.json,
and run this before proposing mutations.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

SEV = {"INFO": 0, "WARN": 1, "ERROR": 2, "CRITICAL": 3}
SMART_BIDDING = {
    "MAXIMIZE_CONVERSIONS",
    "MAXIMIZE_CONVERSION_VALUE",
    "TARGET_CPA",
    "TARGET_ROAS",
}


def finding(severity: str, code: str, message: str, **context: Any) -> dict[str, Any]:
    return {"severity": severity, "code": code, "message": message, "context": context}


def audit(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    account = snapshot.get("account", {})
    campaigns = snapshot.get("campaigns", [])
    conversions = snapshot.get("conversion_actions", [])

    if account.get("account_kind") != "AD_GRANTS":
        out.append(finding("CRITICAL", "ACCOUNT_KIND_UNVERIFIED", "Account is not verified as AD_GRANTS."))

    relevant_primary = [
        c for c in conversions
        if c.get("primary") is True and c.get("mission_relevant") is True and c.get("status", "ENABLED") == "ENABLED"
    ]
    irrelevant_primary = [
        c for c in conversions
        if c.get("primary") is True and c.get("mission_relevant") is not True and c.get("status", "ENABLED") == "ENABLED"
    ]
    if irrelevant_primary:
        out.append(finding(
            "CRITICAL",
            "PRIMARY_CONVERSION_POLLUTION",
            "One or more primary conversion actions are not marked mission-relevant.",
            actions=[c.get("name", "unnamed") for c in irrelevant_primary],
        ))
    if not relevant_primary:
        out.append(finding(
            "ERROR",
            "NO_MEANINGFUL_PRIMARY_CONVERSION",
            "No enabled primary conversion is marked mission-relevant.",
        ))

    for c in conversions:
        clicks = c.get("attributed_clicks")
        convs = c.get("conversions")
        if isinstance(clicks, (int, float)) and isinstance(convs, (int, float)) and convs > 0 and clicks == 0:
            out.append(finding(
                "CRITICAL",
                "CONVERSIONS_WITHOUT_CLICKS",
                "Conversion action reports conversions with zero attributed clicks; validate attribution and goal semantics.",
                action=c.get("name"), conversions=convs,
            ))

    for campaign in campaigns:
        if campaign.get("status") != "ENABLED":
            continue
        name = campaign.get("name", "unnamed")
        ctype = str(campaign.get("type", "")).upper().replace(" ", "_")
        impressions = campaign.get("impressions", 0) or 0
        clicks = campaign.get("clicks", 0) or 0
        conversions_count = campaign.get("conversions", 0) or 0

        if ctype == "SEARCH":
            enabled_groups = campaign.get("enabled_ad_groups")
            if isinstance(enabled_groups, int) and enabled_groups < 2:
                out.append(finding(
                    "ERROR",
                    "SEARCH_TOO_FEW_AD_GROUPS",
                    "Enabled Search campaign has fewer than two enabled ad groups.",
                    campaign=name, enabled_ad_groups=enabled_groups,
                ))

        if impressions == 0:
            out.append(finding(
                "WARN",
                "NO_IMPRESSIONS",
                "Enabled campaign recorded zero impressions in the snapshot window.",
                campaign=name, campaign_type=ctype,
            ))

        if conversions_count > 0 and clicks == 0:
            out.append(finding(
                "CRITICAL",
                "CAMPAIGN_CONVERSIONS_WITHOUT_CLICKS",
                "Campaign reports conversions with zero clicks; do not trust conversion-based bidding until explained.",
                campaign=name, conversions=conversions_count,
            ))

        rank_lost = campaign.get("search_rank_lost_impression_share")
        budget_lost = campaign.get("search_budget_lost_impression_share")
        if ctype == "SEARCH" and isinstance(rank_lost, (int, float)) and rank_lost >= 0.5:
            if not isinstance(budget_lost, (int, float)) or budget_lost < 0.1:
                out.append(finding(
                    "WARN",
                    "RANK_NOT_BUDGET",
                    "High Search impression-share loss is driven by rank, not budget; do not solve this by budget increases alone.",
                    campaign=name, rank_lost=rank_lost, budget_lost=budget_lost,
                ))

        bidding = str(campaign.get("bidding_strategy", "")).upper().replace(" ", "_")
        if bidding in SMART_BIDDING and not relevant_primary:
            out.append(finding(
                "CRITICAL",
                "SMART_BIDDING_WITHOUT_CLEAN_GOAL",
                "Conversion-based Smart Bidding is configured without a validated mission-relevant primary conversion.",
                campaign=name, bidding_strategy=bidding,
            ))

        for ad in campaign.get("ads", []) or []:
            if ad.get("status", "ENABLED") != "ENABLED":
                continue
            final_url = str(ad.get("final_url", "") or "")
            if final_url and not final_url.startswith("https://"):
                out.append(finding(
                    "ERROR",
                    "NON_HTTPS_FINAL_URL",
                    "Enabled ad uses a non-HTTPS final URL.",
                    campaign=name, final_url=final_url,
                ))
            strength = str(ad.get("strength", "")).upper()
            if strength in {"POOR", "PENDING"}:
                out.append(finding(
                    "WARN",
                    "WEAK_AD_STRENGTH",
                    "Enabled ad has weak or pending Ad Strength; review relevance and asset diversity.",
                    campaign=name, strength=strength,
                ))

    return sorted(out, key=lambda x: (-SEV[x["severity"]], x["code"], x["message"]))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot", help="Normalized JSON snapshot")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    parser.add_argument("--fail-on", choices=["INFO", "WARN", "ERROR", "CRITICAL"], default="CRITICAL")
    args = parser.parse_args()

    try:
        data = json.loads(pathlib.Path(args.snapshot).read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: could not read snapshot: {exc}", file=sys.stderr)
        return 2

    findings = audit(data)
    if args.json:
        print(json.dumps({"findings": findings}, ensure_ascii=False, indent=2))
    else:
        if not findings:
            print("OK: no audit findings")
        for item in findings:
            print(f"{item['severity']}: {item['code']}: {item['message']}")

    threshold = SEV[args.fail_on]
    return 1 if any(SEV[f["severity"]] >= threshold for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
