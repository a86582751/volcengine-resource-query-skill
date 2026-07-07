# Volcengine Resource Query Skill

Query Volcano Engine billing resource packages from Codex, then use the result as a budget safety gate for Doubao/Ark generation workflows such as Seedance long videos.

This skill is intentionally small: it calls Volcano Engine Billing OpenAPI `ListResourcePackages`, filters effective Seedance 2.0 Fast packages, converts package units to tokens, and reports whether the planned resource-package debit fits the remaining balance.

## What It Does

- Lists Volcano Engine resource packages.
- Checks Seedance 2.0 Fast resource-package balance.
- Compares `resource_package_tokens_estimated` from a generation plan with remaining package tokens.
- Returns `ok`, required tokens, remaining tokens, deficit/surplus tokens, and matched package metadata.
- Reads credentials from process environment first, then a local env file fallback.

## Install In Codex

Clone this repository, then copy or install the skill folder into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
cp -R volcengine-resource-query ~/.codex/skills/
```

Restart Codex after installing a new skill.

## Credentials

The script reads process environment variables first, then falls back to:

```text
~/.codex/volcengine-billing.env
```

Create it from the example:

```bash
cp .env.example ~/.codex/volcengine-billing.env
```

Supported keys:

```text
VOLC_ACCESS_KEY_ID=your_volcano_access_key_id
VOLC_SECRET_ACCESS_KEY=your_volcano_secret_access_key
VOLC_REGION=cn-beijing
```

You can also set `VOLC_BILLING_ENV_FILE` to point at a custom env file.

Get or manage the required Volcano Engine IAM user access keys here:

https://console.volcengine.com/iam/identitymanage/user

Never commit real keys, local env files, logs, or signed API responses. This repository only includes placeholder examples.

## Commands

List resource packages:

```bash
python volcengine-resource-query/scripts/volc_resource_query.py list-packages
```

Check whether a Seedance 2.0 Fast plan has enough package balance:

```bash
python volcengine-resource-query/scripts/volc_resource_query.py \
  seedance-fast-quota --required-tokens 5521745.45
```

Example output shape:

```json
{
  "ok": true,
  "required_tokens": 5521745.45,
  "remaining_tokens": 6000000.0,
  "deficit_tokens": 0.0,
  "surplus_tokens": 478254.55,
  "matched_packages": []
}
```

## Use With Doubao Seedance Video

After `doubao-seedance-video` reports an estimate such as:

```text
resource_package_tokens_estimated: 4650000
```

run:

```bash
python ~/.codex/skills/volcengine-resource-query/scripts/volc_resource_query.py \
  seedance-fast-quota --required-tokens 4650000
```

If `ok` is `false`, pause the video workflow and ask the user to recharge or reduce the plan before starting paid generation. Volcano's billing console remains the authoritative source of final usage and balance.

## Repository Layout

```text
volcengine-resource-query/
  SKILL.md
  agents/openai.yaml
  scripts/
    volc_resource_query.py
```

## Privacy And Safety

The skill masks nothing by printing credentials in the first place: AK/SK values are only read for request signing and are never included in normal output. Still, review terminal logs and API output before sharing, because billing responses can contain account-specific package IDs and expiry information.

## License

MIT. See [LICENSE](LICENSE).
