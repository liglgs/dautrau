# Drug-safety replay evaluation

Synthetic technical verification; not clinical validation.

| Claim | System | Recall@20 | Citation precision | Error |
|---|---|---:|---:|---|
| heldout-support | keyword | 1.0000 | N/A |  |
| heldout-support | single_shot_rag | 1.0000 | 1.0000 |  |
| heldout-support | agent | N/A | N/A | Agent integration missing: Người 2/3 must supply --agent-hook module:function using replay index and shared Prediction |
| heldout-empty | keyword | N/A | N/A |  |
| heldout-empty | single_shot_rag | N/A | N/A |  |
| heldout-empty | agent | N/A | N/A | Agent integration missing: Người 2/3 must supply --agent-hook module:function using replay index and shared Prediction |

Keyword has retrieval metrics only. Citation support needs statement-level independent review; a valid ID alone is insufficient.
Missing recordings/integrations are errors, excluded from successful metric denominators and counted in run coverage.
Replay makes no live source/model requests. Replayed token usage is historical; cost is unknown without verified prices.
Reviewer-time reduction is unmeasured until a paired user study is supplied.
