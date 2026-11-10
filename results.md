# Results

Settings: max_tokens=6000, adaptive thinking, effort=medium, default temperature, 2 runs per model per task. Cost columns are relative indices computed from token counts at list prices (Opus 5.5 = 1.00).

| Task | Model | Run | Tests passed | Wall time (s) | Input tok | Output tok | Thinking tok | LOC | Stop |
|---|---|---|---|---|---|---|---|---|---|
| a_free_slots | Fable 5.2 | 1 | 29/29 | 15.8 | 740 | 1705 | 553 | 71 | end_turn |
| a_free_slots | Fable 5.2 | 2 | 29/29 | 17.4 | 740 | 1740 | 587 | 64 | end_turn |
| a_free_slots | Opus 5.5 | 1 | 29/29 | 15.3 | 740 | 1983 | 336 | 98 | end_turn |
| a_free_slots | Opus 5.5 | 2 | 29/29 | 14.2 | 740 | 1846 | 360 | 83 | end_turn |
| b_invoice_bugfix | Fable 5.2 | 1 | 25/25 | 39.2 | 1340 | 4339 | 1791 | 103 | end_turn |
| b_invoice_bugfix | Fable 5.2 | 2 | 25/25 | 39.1 | 1340 | 4344 | 1793 | 105 | end_turn |
| b_invoice_bugfix | Opus 5.5 | 1 | 25/25 | 27.9 | 1340 | 3486 | 1067 | 105 | end_turn |
| b_invoice_bugfix | Opus 5.5 | 2 | 25/25 | 29.3 | 1340 | 3594 | 1329 | 103 | end_turn |
| c_ttl_cache | Fable 5.2 | 1 | 27/27 | 35.2 | 1223 | 3961 | 1419 | 174 | end_turn |
| c_ttl_cache | Fable 5.2 | 2 | 27/27 | 32.4 | 1223 | 3629 | 1240 | 160 | end_turn |
| c_ttl_cache | Opus 5.5 | 1 | 27/27 | 29.4 | 1223 | 3758 | 850 | 216 | end_turn |
| c_ttl_cache | Opus 5.5 | 2 | 27/27 | 28.6 | 1223 | 3592 | 1000 | 179 | end_turn |

## Summary

| Model | Tests passed | Pass rate | Fully passing solutions | Relative total cost | Relative cost per fully passing solution | Mean wall time (s) | Mean output tokens | Mean LOC |
|---|---|---|---|---|---|---|---|---|
| Fable 5.2 | 162/162 | 100.0% | 6/6 | 2.15x | 2.15x | 29.8 | 3286 | 113 |
| Opus 5.5 | 162/162 | 100.0% | 6/6 | 1.00x | 1.00x | 24.1 | 3043 | 131 |

## Per task

| Task | Model | Tests passed | Mean wall time (s) | Mean output tokens |
|---|---|---|---|---|
| a_free_slots | Fable 5.2 | 58/58 | 16.6 | 1722 |
| a_free_slots | Opus 5.5 | 58/58 | 14.7 | 1914 |
| b_invoice_bugfix | Fable 5.2 | 50/50 | 39.1 | 4342 |
| b_invoice_bugfix | Opus 5.5 | 50/50 | 28.6 | 3540 |
| c_ttl_cache | Fable 5.2 | 54/54 | 33.8 | 3795 |
| c_ttl_cache | Opus 5.5 | 54/54 | 29.0 | 3675 |

## Blind code-quality judgement (LLM opinion, not a measurement)

| Model | Spec fidelity | Robustness | Readability | Maintainability | Overall |
|---|---|---|---|---|---|
| Fable 5.2 | 8.67 | 8.67 | 8.5 | 8.5 | 8.5 |
| Opus 5.5 | 8.83 | 8.67 | 8.5 | 8.5 | 8.67 |

Judge model: claude-sonnet-5-5, one call, solutions anonymised and shuffled. Per-task pick: a_free_slots -> Opus 5.5 run 2, b_invoice_bugfix -> Fable 5.2 run 2, c_ttl_cache -> Opus 5.5 run 1
