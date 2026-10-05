# Drug-safety replay evaluation

Synthetic technical verification; not clinical validation.

| Claim | System | Recall@20 | Citation precision | Error |
|---|---|---:|---:|---|
| broad | keyword | 1.0000 | N/A |  |
| broad | single_shot_rag | 1.0000 | 1.0000 |  |
| broad | agent | N/A | N/A | Agent integration missing: Người 2/3 must supply --agent-hook module:function using replay index and shared Prediction |
| apparent | keyword | 1.0000 | N/A |  |
| apparent | single_shot_rag | 1.0000 | 1.0000 |  |
| apparent | agent | N/A | N/A | Agent integration missing: Người 2/3 must supply --agent-hook module:function using replay index and shared Prediction |
| faers | keyword | 1.0000 | N/A |  |
| faers | single_shot_rag | 1.0000 | 1.0000 |  |
| faers | agent | N/A | N/A | Agent integration missing: Người 2/3 must supply --agent-hook module:function using replay index and shared Prediction |
| replan | keyword | 1.0000 | N/A |  |
| replan | single_shot_rag | 1.0000 | 1.0000 |  |
| replan | agent | N/A | N/A | Agent integration missing: Người 2/3 must supply --agent-hook module:function using replay index and shared Prediction |

Keyword has retrieval metrics only. Citation support needs statement-level independent review; a valid ID alone is insufficient.
Missing recordings/integrations are errors, excluded from successful metric denominators and counted in run coverage.
Replay makes no live source/model requests. Replayed token usage is historical; cost is unknown without verified prices.
Reviewer-time reduction is unmeasured until a paired user study is supplied.
