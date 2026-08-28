# Model Routing SOP

## Routing order

Use deterministic/local capability first, then approved low-cost routed models,
then premium models only when complexity, risk, or expected value justifies the
escalation. ARC owns provider architecture; Al implements approved configuration;
Invictus reviews secret and data-exposure boundaries.

## Configuration

Provider selection, model name, and gateway base URL are centralized in CADRE
runtime settings. Provider credentials remain server-side and outside Git.
OpenRouter and LiteLLM adapters report configuration and discovered capability;
they do not treat an endpoint string as a successful live provider check.

## Health and fallback

Activation requires a bounded health check and one authenticated completion
through the intended route. Liveness is not provider readiness. Timeouts,
authentication failure, quota/rate limits, invalid response shape, and provider
unavailability are classified separately. Fallback must respect data
classification: confidential or restricted content never falls through to an
unapproved external provider.

The local provider-free route remains the safe default while LiteLLM and
OpenRouter are blocked or only configured-unverified.

## Diagnostics and privacy

Record provider, model, route class, latency, safe token/usage metadata, status,
and sanitized error class. Do not log provider keys or unnecessary prompt
content. Gateway request receipts retain a digest by default.
