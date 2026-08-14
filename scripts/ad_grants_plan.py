#!/usr/bin/env python3
"""Validate autonomous Google Ad Grants mutation plans without network access."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from urllib.parse import urlparse
from typing import Any

SCHEMA = "ethical-saving/google-ad-grants-plan/v1"
ALLOWED_MATCH_TYPES = {"EXACT", "PHRASE", "BROAD"}
SMART_BIDDING = {"MAXIMIZE_CONVERSIONS", "MAXIMIZE_CONVERSION_VALUE", "TARGET_CPA", "TARGET_ROAS"}
WRITE_TYPES = {
    "campaign_create", "campaign_status", "campaign_budget_set",
    "ad_group_create", "ad_group_status", "ad_status", "keyword_create",
    "negative_keyword_create", "keyword_status", "rsa_create",
    "sitelink_create_attach", "callout_create_attach",
    "image_asset_create_attach", "location_target_add",
    "language_target_add", "conversion_action_create", "conversion_action_primary_set",
}


def require(obj: dict[str, Any], key: str, where: str, errors: list[str]) -> Any:
    value = obj.get(key)
    if value is None or value == "":
        errors.append(f"{where}: missing {key}")
    return value


def validate_url(url: Any, where: str, account: dict[str, Any], errors: list[str]) -> None:
    if not isinstance(url, str) or not url.startswith("https://"):
        errors.append(f"{where}: final_url must use https")
        return
    host = (urlparse(url).hostname or "").lower()
    allowed = [str(x).lower() for x in account.get("allowed_domains", [])]
    if allowed and not any(host == d or host.endswith("." + d) for d in allowed):
        errors.append(f"{where}: final_url host {host!r} is outside account.allowed_domains")


def validate_plan(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if plan.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA!r}")

    account = plan.get("account")
    if not isinstance(account, dict):
        return errors + ["account must be an object"]
    customer_id = require(account, "customer_id", "account", errors)
    if customer_id and not str(customer_id).replace("-", "").isdigit():
        errors.append("account.customer_id must contain digits (hyphens optional)")
    if account.get("account_kind") != "AD_GRANTS":
        errors.append("account.account_kind must be AD_GRANTS")

    operations = plan.get("operations")
    if not isinstance(operations, list):
        return errors + ["operations must be an array"]
    if operations and account.get("verified_ad_grants") is not True:
        errors.append("account.verified_ad_grants must be true before writes")

    planned_campaign_budgets: list[int] = []
    conversion_health = account.get("conversion_health", "UNVERIFIED")

    for i, op in enumerate(operations):
        where = f"operations[{i}]"
        if not isinstance(op, dict):
            errors.append(f"{where}: operation must be an object")
            continue
        typ = require(op, "type", where, errors)
        if typ not in WRITE_TYPES:
            errors.append(f"{where}: unsupported type {typ!r}")
            continue
        require(op, "reason", where, errors)

        if typ == "campaign_create":
            require(op, "name", where, errors)
            budget = require(op, "daily_budget_micros", where, errors)
            if isinstance(budget, int) and budget > 0:
                planned_campaign_budgets.append(budget)
            else:
                errors.append(f"{where}: daily_budget_micros must be a positive integer")
            bidding = op.get("bidding", {}) or {}
            strategy = bidding.get("strategy", "MAXIMIZE_CONVERSIONS")
            if strategy in SMART_BIDDING and conversion_health != "VERIFIED":
                errors.append(f"{where}: {strategy} requires account.conversion_health=VERIFIED")

        elif typ == "campaign_budget_set":
            require(op, "campaign_id", where, errors)
            budget = require(op, "daily_budget_micros", where, errors)
            if not isinstance(budget, int) or budget <= 0:
                errors.append(f"{where}: daily_budget_micros must be a positive integer")

        elif typ == "campaign_status":
            require(op, "campaign_id", where, errors)
            if op.get("status") not in {"ENABLED", "PAUSED"}:
                errors.append(f"{where}: status must be ENABLED or PAUSED")

        elif typ == "ad_group_create":
            require(op, "campaign_id", where, errors)
            require(op, "name", where, errors)

        elif typ == "ad_group_status":
            require(op, "ad_group_id", where, errors)
            if op.get("status") not in {"ENABLED", "PAUSED"}:
                errors.append(f"{where}: status must be ENABLED or PAUSED")

        elif typ == "ad_status":
            require(op, "ad_group_id", where, errors)
            require(op, "ad_id", where, errors)
            if op.get("status") not in {"ENABLED", "PAUSED"}:
                errors.append(f"{where}: status must be ENABLED or PAUSED")

        elif typ in {"keyword_create", "negative_keyword_create"}:
            require(op, "ad_group_id", where, errors)
            text = require(op, "text", where, errors)
            mt = op.get("match_type", "PHRASE")
            if mt not in ALLOWED_MATCH_TYPES:
                errors.append(f"{where}: invalid match_type {mt!r}")
            if typ == "keyword_create" and isinstance(text, str):
                stripped = text.strip()
                if stripped and len(stripped.split()) == 1 and not op.get("single_word_exception"):
                    errors.append(f"{where}: positive single-word keyword requires an official exception")
                if op.get("single_word_exception") and not op.get("exception_reason"):
                    errors.append(f"{where}: single_word_exception requires exception_reason")

        elif typ == "keyword_status":
            require(op, "criterion_id", where, errors)
            require(op, "ad_group_id", where, errors)
            if op.get("status") not in {"ENABLED", "PAUSED"}:
                errors.append(f"{where}: status must be ENABLED or PAUSED")

        elif typ == "rsa_create":
            require(op, "ad_group_id", where, errors)
            validate_url(require(op, "final_url", where, errors), where, account, errors)
            headlines = op.get("headlines")
            descriptions = op.get("descriptions")
            if not isinstance(headlines, list) or not (3 <= len(headlines) <= 15):
                errors.append(f"{where}: headlines must contain 3-15 items")
            else:
                for j, text in enumerate(headlines):
                    if not isinstance(text, str) or not text.strip() or len(text) > 30:
                        errors.append(f"{where}.headlines[{j}]: must be non-empty and at most 30 characters")
            if not isinstance(descriptions, list) or not (2 <= len(descriptions) <= 4):
                errors.append(f"{where}: descriptions must contain 2-4 items")
            else:
                for j, text in enumerate(descriptions):
                    if not isinstance(text, str) or not text.strip() or len(text) > 90:
                        errors.append(f"{where}.descriptions[{j}]: must be non-empty and at most 90 characters")

        elif typ in {"sitelink_create_attach", "callout_create_attach"}:
            require(op, "campaign_id", where, errors)
            require(op, "text", where, errors)
            if typ == "sitelink_create_attach":
                validate_url(require(op, "final_url", where, errors), where, account, errors)

        elif typ == "image_asset_create_attach":
            require(op, "scope", where, errors)
            require(op, "scope_id", where, errors)
            path = require(op, "path", where, errors)
            if isinstance(path, str) and pathlib.Path(path).suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                errors.append(f"{where}: image path must be JPG or PNG")
            if op.get("field_type") not in {"MARKETING_IMAGE", "SQUARE_MARKETING_IMAGE"}:
                errors.append(f"{where}: field_type must be MARKETING_IMAGE or SQUARE_MARKETING_IMAGE")

        elif typ in {"location_target_add", "language_target_add"}:
            require(op, "campaign_id", where, errors)
            require(op, "constant_id", where, errors)

        elif typ == "conversion_action_create":
            require(op, "name", where, errors)
            require(op, "category", where, errors)
            require(op, "action_type", where, errors)

        elif typ == "conversion_action_primary_set":
            require(op, "conversion_action_id", where, errors)
            if not isinstance(op.get("primary_for_goal"), bool):
                errors.append(f"{where}: primary_for_goal must be boolean")

    if planned_campaign_budgets:
        limit = account.get("grant_daily_budget_limit_micros")
        if not isinstance(limit, int) or limit <= 0:
            errors.append("account.grant_daily_budget_limit_micros is required for campaign_create plans")
        elif sum(planned_campaign_budgets) > limit:
            errors.append(
                f"planned campaign budgets ({sum(planned_campaign_budgets)}) exceed live grant daily limit ({limit})"
            )

    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan", help="Path to JSON mutation plan")
    args = ap.parse_args()
    try:
        plan = json.loads(pathlib.Path(args.plan).read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: could not read plan: {exc}", file=sys.stderr)
        return 2
    errors = validate_plan(plan)
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1
    print("OK: plan passes local Ad Grants validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
