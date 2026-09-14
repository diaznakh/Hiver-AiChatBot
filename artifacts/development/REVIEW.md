# Reviewed development evaluation

Evaluated commit: `000b21f4c1bb2b75da30a82c7ce87aa762f2d3d1`.

[Successful workflow and downloadable predictions](https://github.com/diaznakh/Hiver-AiChatBot/actions/runs/34881025946)

The workbook audit passed. All 50 development labels are complete; source fields
are unchanged. The 150 test labels remain incomplete. These are development
results, not final assignment scores.

| System | Intent accuracy | Intent macro-F1 | Automatic replies | Unsafe automatic replies by route label | Escalation recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| B0 | 30% | 0.057692 | 0/50 | N/A (0 automatic) | 100% |
| B1 | 46% | 0.359604 | 41/50 | 32/41 | 21.95% |
| B2 | 46% | 0.359604 | 0/50 | N/A (0 automatic) | 100% |

Calibration examined 80 threshold pairs. None produced positive automatic
coverage while meeting the configured constraints. B2 over-escalates all nine
examples labelled AUTO_HANDLE. Automatic handling remains disabled with null
thresholds. Zero unsafe replies with a zero denominator provide no safety
evidence.

B1 and B2 share a classifier, so their intent results are identical. The
classifier gets 23 of 50 labels correct. Digital service F1 is 0.80, while
order change F1 is zero on two examples and other/unclear F1 is 0.154 on eight.
These small per-class samples limit generalization.

## Next development work

Inspect the nine AUTO_HANDLE examples alongside their retrieved evidence and
reason codes to distinguish missing guidance from retrieval failures. Review
classifier confusions against the taxonomy and improve the separate training
data or classifier using development feedback. Do not tune using held-out test
labels or invent current feature/policy information to increase coverage.

The saved workflow artifact contains all B0/B1/B2 predictions, the updated
workbook CSV export and evaluated configuration. JSON summaries are also
committed here. The offline suite passed all 33 tests; passing tests does not
establish prediction quality.

After freezing the revised implementation, evaluate the completed test split,
generate the 60-reply blind rating sheet, obtain human and judge ratings, and
assemble the final report. None of those outcomes is claimed here.
