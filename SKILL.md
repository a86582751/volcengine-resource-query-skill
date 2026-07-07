---
name: volcengine-resource-query
description: Query Volcano Engine billing resource packages and budget safety for Doubao/Ark work. Use when Codex needs to check Volcengine resource package balances, Seedance quota, billing package remaining tokens, ListResourcePackages output, or whether a planned Seedance/Seedream/Ark generation budget fits available package quota.
---

# 查询火山平台资源

Use this skill to query Volcano Engine Billing OpenAPI resource packages, especially Doubao/Ark resource package balances for Seedance budget checks.

## Credentials

Read credentials from process environment first, then from:

```text
C:\Users\isund\.codex\volcengine-billing.env
```

Supported keys:

```text
VOLC_ACCESS_KEY_ID=...
VOLC_SECRET_ACCESS_KEY=...
VOLC_REGION=cn-beijing
VOLC_BILLING_ENV_FILE=C:\optional\custom\volcengine-billing.env
```

Get or manage IAM user access keys at:

```text
https://console.volcengine.com/iam/identitymanage/user
```

Never print full AK/SK. Do not store credentials in the skill directory or Git.

## Tool

Run:

```powershell
python C:\Users\isund\.codex\skills\volcengine-resource-query\scripts\volc_resource_query.py list-packages
```

For Seedance 2.0 Fast quota checks:

```powershell
python C:\Users\isund\.codex\skills\volcengine-resource-query\scripts\volc_resource_query.py seedance-fast-quota --required-tokens 5521745.45
```

The script uses Volcano OpenAPI action `ListResourcePackages` with `ResourceType=Package`, `MaxResults=20`, and follows `NextToken` pages.

## Budget Workflow

1. Estimate the planned Seedance cost with the Seedance skill.
2. Convert resource package usage to tokens.
3. Run `seedance-fast-quota --required-tokens <tokens>`.
4. If `ok` is false, stop generation and report the deficit.

Relevant package match:

```text
ConfigurationCode contains Doubao_Seedance_2.0_fast
Status == Effective
Unit == 千tokens or token/tokens
```

For `千tokens`, multiply `AvailableAmount` by 1000.
