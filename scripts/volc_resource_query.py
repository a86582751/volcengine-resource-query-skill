#!/usr/bin/env python3
import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import sys
import urllib.parse
import urllib.request


ENV_FILE = os.environ.get(
    "VOLC_BILLING_ENV_FILE",
    r"C:\Users\isund\.codex\volcengine-billing.env",
)
SERVICE = "billing"
HOST = "open.volcengineapi.com"
VERSION = "2022-01-01"


def load_env_file(path):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def require_config():
    load_env_file(ENV_FILE)
    ak = os.environ.get("VOLC_ACCESS_KEY_ID") or os.environ.get("VOLC_AK")
    sk = os.environ.get("VOLC_SECRET_ACCESS_KEY") or os.environ.get("VOLC_SK")
    region = os.environ.get("VOLC_REGION", "cn-beijing")
    if not ak or not sk:
        raise SystemExit(
            "Missing VOLC_ACCESS_KEY_ID/VOLC_SECRET_ACCESS_KEY. "
            f"Set process env or {ENV_FILE}."
        )
    return ak, sk, region


def hmac_sha256(key, msg):
    if isinstance(key, str):
        key = key.encode("utf-8")
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def sign_key(secret_key, date, region, service):
    k_date = hmac_sha256(secret_key, date)
    k_region = hmac_sha256(k_date, region)
    k_service = hmac_sha256(k_region, service)
    return hmac_sha256(k_service, "request")


def call_openapi(action, body):
    ak, sk, region = require_config()
    now = dt.datetime.now(dt.UTC)
    date = now.strftime("%Y%m%d")
    x_date = now.strftime("%Y%m%dT%H%M%SZ")
    payload = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    payload_hash = hashlib.sha256(payload).hexdigest()

    query = {
        "Action": action,
        "Version": VERSION,
    }
    canonical_query = urllib.parse.urlencode(sorted(query.items()))
    signed_headers = "content-type;host;x-content-sha256;x-date"
    content_type = "application/json; charset=utf-8"
    canonical_headers = (
        f"content-type:{content_type}\n"
        f"host:{HOST}\n"
        f"x-content-sha256:{payload_hash}\n"
        f"x-date:{x_date}\n"
    )
    canonical_request = "\n".join(
        [
            "POST",
            "/",
            canonical_query,
            canonical_headers,
            signed_headers,
            payload_hash,
        ]
    )
    credential_scope = f"{date}/{region}/{SERVICE}/request"
    string_to_sign = "\n".join(
        [
            "HMAC-SHA256",
            x_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )
    signature = hmac.new(
        sign_key(sk, date, region, SERVICE),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    authorization = (
        f"HMAC-SHA256 Credential={ak}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    url = f"https://{HOST}/?{canonical_query}"
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", content_type)
    req.add_header("Host", HOST)
    req.add_header("X-Date", x_date)
    req.add_header("X-Content-Sha256", payload_hash)
    req.add_header("Authorization", authorization)
    with urllib.request.urlopen(req, timeout=35) as resp:
        text = resp.read().decode("utf-8")
    return json.loads(text)


def list_packages(status=None, max_pages=5):
    all_items = []
    next_token = ""
    page_count = 0
    while page_count < max_pages:
        page_count += 1
        body = {
            "ResourceType": "Package",
            "MaxResults": "20",
            "NextToken": next_token,
        }
        if status:
            body["Status"] = status
        data = call_openapi("ListResourcePackages", body)
        meta = data.get("ResponseMetadata", {})
        if "Error" in meta:
            raise SystemExit(json.dumps(data, ensure_ascii=False, indent=2))
        result = data.get("Result", {})
        all_items.extend(result.get("List", []))
        next_token = result.get("NextToken") or ""
        if not next_token:
            break
    return all_items


def amount_to_tokens(item):
    amount = float(item.get("AvailableAmount") or 0)
    unit = (item.get("Unit") or "").lower()
    if "千" in unit:
        return amount * 1000
    return amount


def seedance_fast_quota(required_tokens, max_pages=2):
    items = list_packages(status="Effective", max_pages=max_pages)
    matches = [
        item
        for item in items
        if "Doubao_Seedance_2.0_fast" in (item.get("ConfigurationCode") or "")
        or "Seedance-2.0-fast" in (item.get("ConfigurationName") or "")
    ]
    remaining = sum(amount_to_tokens(item) for item in matches)
    return {
        "ok": remaining >= required_tokens,
        "required_tokens": required_tokens,
        "remaining_tokens": remaining,
        "deficit_tokens": max(0.0, required_tokens - remaining),
        "surplus_tokens": max(0.0, remaining - required_tokens),
        "matched_packages": [
            {
                "ConfigurationName": item.get("ConfigurationName"),
                "ConfigurationCode": item.get("ConfigurationCode"),
                "Status": item.get("Status"),
                "AvailableAmount": item.get("AvailableAmount"),
                "Unit": item.get("Unit"),
                "available_tokens": amount_to_tokens(item),
                "ExpiryTime": item.get("ExpiryTime"),
                "InstanceNo": item.get("InstanceNo"),
            }
            for item in matches
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Query Volcano Engine resource packages.")
    sub = parser.add_subparsers(dest="command", required=True)
    p_list = sub.add_parser("list-packages")
    p_list.add_argument("--status", default=None)
    p_list.add_argument("--max-pages", type=int, default=5)
    p_fast = sub.add_parser("seedance-fast-quota")
    p_fast.add_argument("--required-tokens", type=float, required=True)
    p_fast.add_argument("--max-pages", type=int, default=2)
    args = parser.parse_args()

    if args.command == "list-packages":
        data = list_packages(status=args.status, max_pages=args.max_pages)
        print(json.dumps({"count": len(data), "packages": data}, ensure_ascii=False, indent=2))
    elif args.command == "seedance-fast-quota":
        data = seedance_fast_quota(args.required_tokens, max_pages=args.max_pages)
        print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
