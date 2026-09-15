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
| B1 | 50.00% | 0.288591 | 122/150 | 120/122 | 18.92% |
| B2 | 50.00% | 0.288591 | 0/150 | N/A (0 auto) | 100% |

B2 uses the same classifier as B1. Its macro-F1 exceeds the constant baseline,
but its accuracy is lower. It recommends no automatic replies and over-escalates
both examples labelled AUTO_HANDLE. Zero automatic replies provide no evidence
of safe automatic handling.

The test labels contain 148 ESCALATE and two AUTO_HANDLE examples. There are no
order_change examples; fixed eight-class macro-F1 assigns that class zero. The
route imbalance and class coverage limit conclusions. Candidate reply quality is measured in REPORT_RESULTS.md;
judge-human agreement remains pending. See ../ratings/PROVENANCE.md for review assistance.

The package contains B0/B1/B2 predictions, generated REPORT_RESULTS.md, the
60-row human_ratings.csv, the shared rubric and evaluated config. Read only the
rating sheet and rubric before completing blind ratings; prediction files
contain system identities. Keep output_id and example_id unchanged.

This is a frozen test result. Further development should use the development
split and separate training data, with a new untouched evaluation set needed
for an independent assessment after test-informed changes.
