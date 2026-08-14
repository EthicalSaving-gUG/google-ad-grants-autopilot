# Official Google upstream skills

Use the official `google/skills` repository as the primary upstream toolkit for Google Ads setup and diagnostics. Resolve the current files from GitHub at execution time rather than vendoring stale copies.

## Upstream repository

- Repository: `google/skills`
- License: Apache License 2.0
- Ads skill root: `skills/ads/`

## Relevant skills

### google-ads-api-quickstart

Path: `skills/ads/google-ads-api-quickstart/SKILL.md`

Use for:

- Developer Token and OAuth setup
- customer/login-customer ID routing
- selecting official client libraries or REST
- dynamically resolving the current Google Ads API version
- common authentication errors

Important upstream rule: resolve the latest stable Google Ads API/client-library version dynamically before generating version-specific code.

### google-ads-api-mcp-setup

Path: `skills/ads/google-ads-api-mcp-setup/SKILL.md`

Use for:

- installing/configuring Google's official Google Ads MCP server
- read/query integration through MCP
- standard credential environment variables

Do not assume the MCP server can mutate Google Ads. Inspect its current exposed tools. If it remains query-only, use the regular Google Ads API write runner in this skill for mutations.

### google-ads-api-account-diagnostics

Path: `skills/ads/google-ads-api-account-diagnostics/SKILL.md`

Reuse its diagnostic logic for:

- conversion/conversion-value loss
- low lead flow
- search impression share lost to rank or budget
- `change_event` inspection
- offline conversion upload health

Prefer Google's native read/MCP tools for these diagnostics when available.

## Attribution

This project references Google's public skill names, workflows, and documentation but does not vendor their full source files. If Google skill source is copied into this repository later, retain the required Apache-2.0 notices and clearly mark modifications.
