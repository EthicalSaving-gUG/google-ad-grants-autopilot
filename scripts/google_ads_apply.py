#!/usr/bin/env python3
"""Apply validated Google Ad Grants mutation plans with Google's Python client.

This runner intentionally implements common safe mutations and omits permanent
delete operations. It never prints credential values.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sys
from typing import Any

from ad_grants_plan import validate_plan


def env_required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


def load_client():
    try:
        from google.ads.googleads.client import GoogleAdsClient
    except ImportError as exc:
        raise RuntimeError(
            "google-ads package is not installed; install the current supported release from Google"
        ) from exc

    config = {
        "developer_token": env_required("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": env_required("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": env_required("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": env_required("GOOGLE_ADS_REFRESH_TOKEN"),
        "use_proto_plus": True,
    }
    login = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", "").strip()
    if login:
        config["login_customer_id"] = login
    return GoogleAdsClient.load_from_dict(config)


def enum(client, enum_name: str, value: str):
    return getattr(client.enums, enum_name)[value]


def campaign_resource(customer_id: str, campaign_id: str) -> str:
    return f"customers/{customer_id}/campaigns/{campaign_id}"


def ad_group_resource(customer_id: str, ad_group_id: str) -> str:
    return f"customers/{customer_id}/adGroups/{ad_group_id}"


def ad_group_ad_resource(customer_id: str, ad_group_id: str, ad_id: str) -> str:
    return f"customers/{customer_id}/adGroupAds/{ad_group_id}~{ad_id}"


def apply_one(client, customer_id: str, op: dict[str, Any]) -> str:
    typ = op["type"]

    if typ == "campaign_create":
        budget_service = client.get_service("CampaignBudgetService")
        bop = client.get_type("CampaignBudgetOperation")
        budget = bop.create
        budget.name = f"{op['name']} | Budget"
        budget.amount_micros = int(op["daily_budget_micros"])
        budget.delivery_method = enum(client, "BudgetDeliveryMethodEnum", "STANDARD")
        budget.explicitly_shared = False
        bresp = budget_service.mutate_campaign_budgets(customer_id=customer_id, operations=[bop])
        budget_name = bresp.results[0].resource_name

        service = client.get_service("CampaignService")
        cop = client.get_type("CampaignOperation")
        c = cop.create
        c.name = op["name"]
        c.campaign_budget = budget_name
        c.advertising_channel_type = enum(client, "AdvertisingChannelTypeEnum", "SEARCH")
        c.status = enum(client, "CampaignStatusEnum", op.get("status", "PAUSED"))
        c.network_settings.target_google_search = True
        c.network_settings.target_search_network = bool(op.get("search_partners", False))
        c.network_settings.target_content_network = False
        bidding = op.get("bidding", {})
        strategy = bidding.get("strategy", "MAXIMIZE_CONVERSIONS")
        if strategy == "MAXIMIZE_CONVERSIONS":
            target = bidding.get("target_cpa_micros")
            if target is not None:
                c.maximize_conversions.target_cpa_micros = int(target)
            else:
                _ = c.maximize_conversions
        elif strategy == "MAXIMIZE_CONVERSION_VALUE":
            target = bidding.get("target_roas")
            if target is not None:
                c.maximize_conversion_value.target_roas = float(target)
            else:
                _ = c.maximize_conversion_value
        elif strategy == "TARGET_CPA":
            c.target_cpa.target_cpa_micros = int(bidding["target_cpa_micros"])
        elif strategy == "TARGET_ROAS":
            c.target_roas.target_roas = float(bidding["target_roas"])
        elif strategy == "MAXIMIZE_CLICKS":
            ceiling = bidding.get("cpc_bid_ceiling_micros")
            if ceiling is not None:
                c.maximize_clicks.cpc_bid_ceiling_micros = int(ceiling)
            else:
                _ = c.maximize_clicks
        else:
            raise RuntimeError(f"unsupported bidding strategy: {strategy}")
        resp = service.mutate_campaigns(customer_id=customer_id, operations=[cop])
        return resp.results[0].resource_name

    if typ == "campaign_status":
        service = client.get_service("CampaignService")
        operation = client.get_type("CampaignOperation")
        item = operation.update
        item.resource_name = campaign_resource(customer_id, str(op["campaign_id"]))
        item.status = enum(client, "CampaignStatusEnum", op["status"])
        operation.update_mask.paths.append("status")
        resp = service.mutate_campaigns(customer_id=customer_id, operations=[operation])
        return resp.results[0].resource_name

    if typ == "campaign_budget_set":
        ga = client.get_service("GoogleAdsService")
        query = (
            "SELECT campaign.campaign_budget FROM campaign "
            f"WHERE campaign.id = {int(op['campaign_id'])} LIMIT 1"
        )
        rows = list(ga.search(customer_id=customer_id, query=query))
        if not rows:
            raise RuntimeError("campaign not found for budget update")
        budget_name = rows[0].campaign.campaign_budget
        service = client.get_service("CampaignBudgetService")
        operation = client.get_type("CampaignBudgetOperation")
        item = operation.update
        item.resource_name = budget_name
        item.amount_micros = int(op["daily_budget_micros"])
        operation.update_mask.paths.append("amount_micros")
        resp = service.mutate_campaign_budgets(customer_id=customer_id, operations=[operation])
        return resp.results[0].resource_name

    if typ == "ad_group_create":
        service = client.get_service("AdGroupService")
        operation = client.get_type("AdGroupOperation")
        item = operation.create
        item.name = op["name"]
        item.campaign = campaign_resource(customer_id, str(op["campaign_id"]))
        item.status = enum(client, "AdGroupStatusEnum", op.get("status", "ENABLED"))
        item.type_ = enum(client, "AdGroupTypeEnum", "SEARCH_STANDARD")
        resp = service.mutate_ad_groups(customer_id=customer_id, operations=[operation])
        return resp.results[0].resource_name

    if typ == "ad_group_status":
        service = client.get_service("AdGroupService")
        operation = client.get_type("AdGroupOperation")
        item = operation.update
        item.resource_name = ad_group_resource(customer_id, str(op["ad_group_id"]))
        item.status = enum(client, "AdGroupStatusEnum", op["status"])
        operation.update_mask.paths.append("status")
        resp = service.mutate_ad_groups(customer_id=customer_id, operations=[operation])
        return resp.results[0].resource_name

    if typ in {"keyword_create", "negative_keyword_create"}:
        service = client.get_service("AdGroupCriterionService")
        operation = client.get_type("AdGroupCriterionOperation")
        item = operation.create
        item.ad_group = ad_group_resource(customer_id, str(op["ad_group_id"]))
        item.status = enum(client, "AdGroupCriterionStatusEnum", "ENABLED")
        item.negative = typ == "negative_keyword_create"
        item.keyword.text = op["text"]
        item.keyword.match_type = enum(client, "KeywordMatchTypeEnum", op.get("match_type", "PHRASE"))
        resp = service.mutate_ad_group_criteria(customer_id=customer_id, operations=[operation])
        return resp.results[0].resource_name

    if typ == "keyword_status":
        service = client.get_service("AdGroupCriterionService")
        operation = client.get_type("AdGroupCriterionOperation")
        item = operation.update
        item.resource_name = (
            f"customers/{customer_id}/adGroupCriteria/{op['ad_group_id']}~{op['criterion_id']}"
        )
        item.status = enum(client, "AdGroupCriterionStatusEnum", op["status"])
        operation.update_mask.paths.append("status")
        resp = service.mutate_ad_group_criteria(customer_id=customer_id, operations=[operation])
        return resp.results[0].resource_name

    if typ == "ad_status":
        service = client.get_service("AdGroupAdService")
        operation = client.get_type("AdGroupAdOperation")
        item = operation.update
        item.resource_name = ad_group_ad_resource(
            customer_id, str(op["ad_group_id"]), str(op["ad_id"])
        )
        item.status = enum(client, "AdGroupAdStatusEnum", op["status"])
        operation.update_mask.paths.append("status")
        resp = service.mutate_ad_group_ads(customer_id=customer_id, operations=[operation])
        return resp.results[0].resource_name

    if typ == "rsa_create":
        service = client.get_service("AdGroupAdService")
        operation = client.get_type("AdGroupAdOperation")
        item = operation.create
        item.ad_group = ad_group_resource(customer_id, str(op["ad_group_id"]))
        item.status = enum(client, "AdGroupAdStatusEnum", op.get("status", "ENABLED"))
        item.ad.final_urls.append(op["final_url"])
        for text in op["headlines"]:
            asset = client.get_type("AdTextAsset")
            asset.text = text
            item.ad.responsive_search_ad.headlines.append(asset)
        for text in op["descriptions"]:
            asset = client.get_type("AdTextAsset")
            asset.text = text
            item.ad.responsive_search_ad.descriptions.append(asset)
        resp = service.mutate_ad_group_ads(customer_id=customer_id, operations=[operation])
        return resp.results[0].resource_name

    if typ in {"sitelink_create_attach", "callout_create_attach"}:
        asset_service = client.get_service("AssetService")
        aop = client.get_type("AssetOperation")
        asset = aop.create
        asset.name = op.get("name", op["text"])
        if typ == "sitelink_create_attach":
            asset.sitelink_asset.link_text = op["text"]
            asset.final_urls.append(op["final_url"])
            field_type = "SITELINK"
        else:
            asset.callout_asset.callout_text = op["text"]
            field_type = "CALLOUT"
        aresp = asset_service.mutate_assets(customer_id=customer_id, operations=[aop])
        asset_name = aresp.results[0].resource_name
        service = client.get_service("CampaignAssetService")
        operation = client.get_type("CampaignAssetOperation")
        item = operation.create
        item.asset = asset_name
        item.campaign = campaign_resource(customer_id, str(op["campaign_id"]))
        item.field_type = enum(client, "AssetFieldTypeEnum", field_type)
        resp = service.mutate_campaign_assets(customer_id=customer_id, operations=[operation])
        return resp.results[0].resource_name

    if typ == "image_asset_create_attach":
        path = pathlib.Path(op["path"])
        data = path.read_bytes()
        asset_service = client.get_service("AssetService")
        aop = client.get_type("AssetOperation")
        asset = aop.create
        asset.name = op.get("name", path.stem)
        asset.image_asset.data = data
        aresp = asset_service.mutate_assets(customer_id=customer_id, operations=[aop])
        asset_name = aresp.results[0].resource_name
        field_type = enum(client, "AssetFieldTypeEnum", op["field_type"])
        if op["scope"] == "AD_GROUP":
            service = client.get_service("AdGroupAssetService")
            operation = client.get_type("AdGroupAssetOperation")
            item = operation.create
            item.ad_group = ad_group_resource(customer_id, str(op["scope_id"]))
            item.asset = asset_name
            item.field_type = field_type
            resp = service.mutate_ad_group_assets(customer_id=customer_id, operations=[operation])
        elif op["scope"] == "CAMPAIGN":
            service = client.get_service("CampaignAssetService")
            operation = client.get_type("CampaignAssetOperation")
            item = operation.create
            item.campaign = campaign_resource(customer_id, str(op["scope_id"]))
            item.asset = asset_name
            item.field_type = field_type
            resp = service.mutate_campaign_assets(customer_id=customer_id, operations=[operation])
        else:
            raise RuntimeError("image scope must be AD_GROUP or CAMPAIGN")
        return resp.results[0].resource_name

    if typ in {"location_target_add", "language_target_add"}:
        service = client.get_service("CampaignCriterionService")
        operation = client.get_type("CampaignCriterionOperation")
        item = operation.create
        item.campaign = campaign_resource(customer_id, str(op["campaign_id"]))
        if typ == "location_target_add":
            item.location.geo_target_constant = f"geoTargetConstants/{op['constant_id']}"
        else:
            item.language.language_constant = f"languageConstants/{op['constant_id']}"
        resp = service.mutate_campaign_criteria(customer_id=customer_id, operations=[operation])
        return resp.results[0].resource_name

    if typ == "conversion_action_create":
        service = client.get_service("ConversionActionService")
        operation = client.get_type("ConversionActionOperation")
        item = operation.create
        item.name = op["name"]
        item.category = enum(client, "ConversionActionCategoryEnum", op["category"])
        item.type_ = enum(client, "ConversionActionTypeEnum", op["action_type"])
        item.status = enum(client, "ConversionActionStatusEnum", op.get("status", "ENABLED"))
        if "default_value" in op:
            item.value_settings.default_value = float(op["default_value"])
            item.value_settings.always_use_default_value = bool(op.get("always_use_default_value", False))
        if op.get("currency_code"):
            item.value_settings.default_currency_code = op["currency_code"]
        resp = service.mutate_conversion_actions(customer_id=customer_id, operations=[operation])
        return resp.results[0].resource_name

    if typ == "conversion_action_primary_set":
        service = client.get_service("ConversionActionService")
        operation = client.get_type("ConversionActionOperation")
        item = operation.update
        item.resource_name = f"customers/{customer_id}/conversionActions/{op['conversion_action_id']}"
        item.primary_for_goal = bool(op["primary_for_goal"])
        operation.update_mask.paths.append("primary_for_goal")
        resp = service.mutate_conversion_actions(customer_id=customer_id, operations=[operation])
        return resp.results[0].resource_name

    raise RuntimeError(f"unsupported operation type: {typ}")


def _journal(path: pathlib.Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"time_utc": dt.datetime.now(dt.timezone.utc).isoformat(), **record}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _enforce_runtime_guard(customer_id: str, plan: dict[str, Any]) -> None:
    if os.environ.get("GOOGLE_ADS_AUTONOMY", "").strip() != "1":
        raise RuntimeError("GOOGLE_ADS_AUTONOMY=1 is required for live mutations")
    allowed = {
        value.replace("-", "").strip()
        for value in os.environ.get("GOOGLE_ADS_ALLOWED_CUSTOMER_IDS", "").split(",")
        if value.strip()
    }
    if customer_id not in allowed:
        raise RuntimeError("target customer is not in GOOGLE_ADS_ALLOWED_CUSTOMER_IDS")
    account = plan.get("account", {})
    if account.get("account_kind") != "AD_GRANTS" or account.get("verified_ad_grants") is not True:
        raise RuntimeError("plan must explicitly identify a verified AD_GRANTS account")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--apply", action="store_true", help="Apply mutations. Without this flag, validate only.")
    ap.add_argument(
        "--journal",
        default="runtime/mutation-journal.jsonl",
        help="JSONL change journal path used only for live --apply runs.",
    )
    args = ap.parse_args()

    plan = json.loads(pathlib.Path(args.plan).read_text(encoding="utf-8"))
    errors = validate_plan(plan)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("OK: local plan validation passed")
    if not args.apply:
        print("DRY RUN: no Google Ads mutations requested")
        return 0

    customer_id = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", str(plan["account"]["customer_id"]))
    customer_id = customer_id.replace("-", "")
    if customer_id != str(plan["account"]["customer_id"]).replace("-", ""):
        raise RuntimeError("GOOGLE_ADS_CUSTOMER_ID does not match the validated plan account")
    _enforce_runtime_guard(customer_id, plan)

    journal = pathlib.Path(args.journal)
    client = load_client()
    for index, op in enumerate(plan["operations"]):
        safe = {"index": index, "type": op["type"], "reason": op.get("reason", "")}
        _journal(journal, {**safe, "status": "started", "customer_id": customer_id})
        try:
            resource = apply_one(client, customer_id, op)
        except Exception as exc:
            _journal(journal, {**safe, "status": "failed", "error_type": type(exc).__name__, "error": str(exc)})
            raise
        _journal(journal, {**safe, "status": "succeeded", "resource_name": resource})
        print(json.dumps({"index": index, "type": op["type"], "resource_name": resource}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
