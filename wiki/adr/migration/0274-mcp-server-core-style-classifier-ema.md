---
title: "ADR-0274 — mcp_server/core/style_classifier_ema.py rationale"
status: accepted
source: mcp_server/core/style_classifier_ema.py
---

# ADR-0274 — mcp_server/core/style_classifier_ema.py

Migrated source rationale. The excerpts below are preserved verbatim from the source snapshot; historical identifiers inside quotations are not current identities.

## module — original line 40 (comment)

````text
# At or above this EMA alpha the new observation outweighs the stored style,
# so categorical dimensions adopt the new observation.
# source: pre-existing tuned value, extracted unchanged (#197 family 3);
# provenance not recorded at introduction
````
