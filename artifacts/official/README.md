# Held-out evaluation

Evaluated commit: `f1be66b440a825d9bdf8430332af9ee31731e499`.
Frozen agent/configuration commit before test results: `28404a715a105a98d90872a0bc8fed0a74c042fb`.
Workbook SHA256: `a3671a0789aad8d00b3aae622260233b772efe35be257af6d9f09ef82f951ba3`.

[Successful run and downloadable evaluation package](https://github.com/diaznakh/Hiver-AiChatBot/actions/runs/34884517647)

All 150 test rows passed annotation validation. This checks required fields,
taxonomy values and review flags; it does not independently establish label
correctness. Source fields match the original after exact numeric ID normalization.

| System | Intent accuracy | Macro-F1 | Auto coverage | Unsafe auto by route label | Escalation recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| B0 | 52.67% | 0.086245 | 0/150 | N/A (0 auto) | 100% |
| B1 | 53.33% | 0.321053 | 113/150 | 111/113 | 25.00% |
| B2 | 53.33% | 0.321053 | 6/150 | 6/6 | 95.95% |

B2 uses the same classifier as B1. Its macro-F1 exceeds the constant baseline. It limits automatic replies to 4.0% of the test set and achieves 95.95% escalation recall. However, all six predicted automatic cases were unsafe relative to the current evaluation labels, so the system is not ready for autonomous handling.

The test labels contain 148 ESCALATE and two AUTO_HANDLE examples. There are no
order_change examples; fixed eight-class macro-F1 assigns that class zero. The
route imbalance and class coverage limit conclusions. Candidate reply quality is measured in REPORT_RESULTS.md.
60 reply outputs were evaluated by humans. Corresponding LLM-judge ratings were collected and agreement statistics were calculated. The final report discusses the observed agreement and its limitations.

The package contains B0/B1/B2 predictions, generated REPORT_RESULTS.md, the
60-row human_ratings.csv, the shared rubric and evaluated config. Read only the
rating sheet and rubric before completing blind ratings; prediction files
contain system identities. Keep output_id and example_id unchanged.

This is a frozen test result. Further development should use the development
split and separate training data, with a new untouched evaluation set needed
for an independent assessment after test-informed changes.
